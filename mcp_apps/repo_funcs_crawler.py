import json
import os
from pathlib import Path
import sys

from faiss import read_index
from gigachat import GigaChat
from typing import Generator
import uuid
from dotenv import load_dotenv

from gigachat.models import Chat, Messages, MessagesRole
import numpy as np
import faiss

from git import Repo
from tree_sitter import Language, Parser
import tree_sitter_python as tspython

load_dotenv(override=True)

PY_LANGUAGE = Language(tspython.language())
parser = Parser(PY_LANGUAGE)

REPO_URL = "https://github.com/salute-developers/smart_app_framework.git"

REPOS_PATH = Path(__file__).parent / "repos"
REPOS_PATH.resolve().mkdir(exist_ok=True)

OUTPUT_DIR_PATH = Path(__file__).parent / "output"
OUTPUT_DIR_PATH.resolve().mkdir(exist_ok=True)

OUTPUT_EMBEDDINGS_PATH = Path(__file__).parent / "embeddings"
OUTPUT_EMBEDDINGS_PATH.mkdir(exist_ok=True)

GIGA_CREDS = os.getenv("GIGA_CREDS")


def get_repo_name(repo_url: str) -> str:
    repo_name = repo_url.split("/")[-1].removesuffix(".git")
    return repo_name


def clone_repo(repo_url: str) -> Repo:
    repo_name = get_repo_name(repo_url)
    to_path = REPOS_PATH / repo_name
    if to_path.exists() and (to_path / ".git").exists():
        return Repo(to_path)
    rep = Repo.clone_from(repo_url, to_path, depth=1)
    return rep


def walk_all_python_files(repo_path: Path) -> Generator[Path]:
    for f in repo_path.glob("**/*.py"):
        yield f


def walk_ast_tree(node, source_code: bytes, functions: list) -> None:
    if node.type == "function_definition":
        function_name = None
        parameters = None
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        content = source_code[node.start_byte:node.end_byte].decode()

        for child in node.children:
            if child.type == "identifier":
                function_name = source_code[child.start_byte:child.end_byte]
            elif child.type == "parameters":
                parameters = source_code[child.start_byte:child.end_byte]

        functions.append({
            "name": function_name.decode(),
            "parameters": parameters.decode(),
            "start_line": start_line,
            "end_line": end_line,
            "content": content,
        })

    for child in node.children:
        walk_ast_tree(child, source_code, functions)


def get_all_functions_from_file(file_path: Path) -> list[dict]:
    with open(file_path) as fd:
        file_data = fd.read()
    tree = parser.parse(file_data.encode())
    root = tree.root_node
    functions = []
    walk_ast_tree(root, file_data.encode(), functions)
    return functions


def process_repo_and_create_functions(repo_url: str):
    repo_name = get_repo_name(repo_url)
    clone_repo(repo_url)
    repo_path = REPOS_PATH / repo_name

    output_functions_path = OUTPUT_DIR_PATH / f"{repo_name}.jsonl"
    with open(output_functions_path, "w+") as fd:
        for file_path in walk_all_python_files(repo_path):
            funcs = get_all_functions_from_file(file_path)
            for fn in funcs:
                fn["id"] = str(uuid.uuid4())
                fn["path"] = str(file_path)
                if file_path.name == "__init__.py":
                    continue
                if "test" in file_path.name:
                    continue
                if fn["name"] == "__init__":
                    continue

                content_lines = len(fn["content"].split("\n"))
                parameters_lines = len(fn["parameters"].split("\n"))
                body_lines = content_lines - parameters_lines
                if body_lines < 4:
                    continue

                content = fn["content"]
                if len(content) > 1500:
                    fn["content"] = content[:1500]

                fd.write(json.dumps(fn, ensure_ascii=False) + "\n")

    return output_functions_path


def create_embeddings_for_functions(functions_path: Path) -> Path:
    output_path = OUTPUT_EMBEDDINGS_PATH / functions_path.name
    window_size = 4
    cur_window = []
    with (
        GigaChat(credentials=GIGA_CREDS, verify_ssl_certs=False) as giga,
        open(functions_path, "r") as fd_in,
        open(output_path, "w+") as fd_out,
    ):
        for line in fd_in:
            fn = json.loads(line)
            cur_window.append(fn)
            if len(cur_window) == window_size:
                embs = giga.embeddings(texts=[f["content"] for f in cur_window])
                for f, e in zip(cur_window, [e.embedding for e in embs.data]):
                    fd_out.write(json.dumps({"id": f["id"], "embedding": e}) + "\n")
                cur_window = []

        if cur_window:
            embs = giga.embeddings(texts=[f["content"] for f in cur_window])
            for f, e in zip(cur_window, [e.embedding for e in embs.data]):
                fd_out.write(json.dumps({"id": f["id"], "embedding": e}) + "\n")

    return output_path


def cosine(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def load_statics(index_file_path: Path, embeddings_file_path: Path, data_file_path: Path):
    index = read_index(index_file_path)

    embeddings_ids = []
    with open(embeddings_file_path, "r") as fd:
        for line in fd:
            e = json.loads(line)
            embeddings_ids.append(e["id"])

    id2fn = {}
    with open(data_file_path, "r") as fd:
        for line in fd:
            fn = json.loads(line)
            id2fn[fn["id"]] = fn

    return index, embeddings_ids, id2fn


def build_index_from_embeddings(embeddings_file_path: Path, data_file_path: Path):
    embeddings_ids = []
    embeddings_matrix = []
    with open(embeddings_file_path, "r") as fd:
        for line in fd:
            e = json.loads(line)
            embeddings_ids.append(e["id"])
            embeddings_matrix.append(np.array(e["embedding"], dtype="float32"))
    embeddings_matrix = np.array(embeddings_matrix)

    id2fn = {}
    with open(data_file_path, "r") as fd:
        for line in fd:
            fn = json.loads(line)
            id2fn[fn["id"]] = fn

    faiss.normalize_L2(embeddings_matrix)
    index = faiss.IndexFlatIP(embeddings_matrix[0].shape[0])
    index.add(embeddings_matrix)
    return index, embeddings_ids, id2fn


def process_text_query(q, index, embeddings_ids, id2fn):
    with GigaChat(credentials=GIGA_CREDS, verify_ssl_certs=False) as giga:
        embs = giga.embeddings(texts=[q])
        q_emb = np.array(embs.data[0].embedding)

    # normalize
    q_emb = q_emb / np.linalg.norm(q_emb)

    candidates = []
    candidates_dist, candidates_indices = index.search(np.array([q_emb]), k=10)
    for score, idx in zip(candidates_dist[0], candidates_indices[0]):
        fn = id2fn[embeddings_ids[idx]]
        print(score, fn["content"])
        candidates.append({
            "score": score,
            "fn": fn,
        })

    return


def main():
    # output_functions_path = process_repo_and_create_functions(REPO_URL)
    output_functions_path = Path(os.getenv("OUTPUT_FUNCTIONS_PATH"))
    # embeddings_path = create_embeddings_for_functions(output_functions_path)
    embeddings_path = Path(os.getenv("EMBEDDINGS_PATH"))
    index, embeddings_ids, id2fn = build_index_from_embeddings(
        embeddings_file_path=embeddings_path, data_file_path=output_functions_path
    )

    while True:
        q = input("Ваш вопрос: ")
        process_text_query(q=q, index=index, embeddings_ids=embeddings_ids, id2fn=id2fn)
        print()


if __name__ == "__main__":
    main()
