import json
import os
from pathlib import Path
from typing import Any

import mcp
import numpy as np
from gigachat import GigaChat
from mcp import types
from mcp.server.fastmcp import FastMCP
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from dotenv import load_dotenv

from db.adapter import DBAdapter
from mcp_apps.repo_funcs_crawler import process_text_query, load_statics

load_dotenv(override=True)

server = Server("example-server")

GIGA_CREDS = os.getenv("GIGA_CREDS")

index, embeddings_ids, id2fn = load_statics(
    index_file_path=Path(os.getenv("INDEX_PATH")),
    embeddings_file_path=Path(os.getenv("EMBEDDINGS_PATH")),
    data_file_path=Path(os.getenv("OUTPUT_FUNCTIONS_PATH")),
)

db_adapter = DBAdapter()
db_adapter.init_db()


@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    return [
        types.Prompt(
            name="system",
            description="Ты помощник в поиске похожих функций в моем проекте. "
                        "Тебе на вход дается текстовый запрос пользователя и функция search_candidates, "
                        "которая возвращает похожих кандидатов для запроса пользователя. "
                        "Выведи content похожей функции среди этих кандидатов, "
                        "либо сообщи что похожих функций для запроса нет.",
        )
    ]


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="search_candidates",
            description="Возвращает кандидатов похожих на текстовый запрос пользователя",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Что ищет пользователь"
                    }
                },
                "required": ["query"]
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(
        name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    if name == "search_candidates":
        with GigaChat(credentials=GIGA_CREDS, verify_ssl_certs=False) as giga:
            embs = giga.embeddings(texts=[arguments["query"]])
        q_emb = np.array(embs.data[0].embedding)
        q_emb = q_emb / np.linalg.norm(q_emb)
        candidates_dist, candidates_indices = index.search(np.array([q_emb]), k=10)

        candidates = db_adapter.get_by_vectors(candidates_indices[0])

        result = {
            "status": "success",
            "candidates": [
                {
                    "path": cand["url"],
                    "content": cand["code"]
                }
                for cand in candidates
            ]
        }
        return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

    raise RuntimeError("unknown")


async def run():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="example",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(run())
