import json
from collections import defaultdict

from db.adapter import DbAdapter

a = DbAdapter()
a.init_db()
try:
    vectors = defaultdict(dict)
    with open("../static/embeddings.jsonl", "r") as embeddings, open(
        "../static/functions.jsonl", "r"
    ) as functions:
        for line in embeddings:
            embedding = json.loads(line)
            vectors[embedding["id"]]["embedding"] = embedding["embedding"]
        for line in functions:
            function = json.loads(line)
            vectors[function["id"]]["code"] = function["content"]
            vectors[function["id"]]["url"] = function["path"]

    for id, vector in vectors.items():
        a.add_entity(vector["embedding"], vector["code"], vector["url"])
except Exception as e:
    raise (e)
finally:
    a.close_db()
