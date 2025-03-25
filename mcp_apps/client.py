from fastapi import FastAPI, Request
from gigachat import GigaChat
import gigachat.models
from gigachat.models import Chat, Function, Messages, MessagesRole
import mcp
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from repo_funcs_crawler import GIGA_CREDS

app = FastAPI()

server_params = StdioServerParameters(
    command="python",
    args=["server.py"],
    env=None,
)

giga = GigaChat(credentials=GIGA_CREDS, verify_ssl_certs=False)


def convert_tool_to_function(t: mcp.Tool) -> gigachat.models.Function:
    return Function(**{
        "name": t.name,
        "description": t.description,
        "parameters": t.inputSchema,
    })

@app.post("/api/chat")
async def chat(req: Request):
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            req_d = await req.json()
            messages = [Messages(**m) for m in req_d["messages"]]

            prompts = await session.list_prompts()
            print("prompts", prompts)
            system_prompt = [p for p in prompts.prompts if p.name == "system"][0]

            messages = [Messages(
                role=MessagesRole.SYSTEM,
                content=system_prompt.description,
            )] + messages

            tools = await session.list_tools()
            available_functions = [convert_tool_to_function(t) for t in tools.tools]

            payload = Chat(
                model="GigaChat-2-Max",
                messages=messages,
                functions=available_functions,
            )
            response = giga.chat(payload)
            choice = response.choices[0]

            answer = []

            # Process response and handle tool calls
            while True:
                if choice.finish_reason == "stop":
                    answer.append({
                        "role": "assistant",
                        "content": choice.message.content,
                    })
                    return {"answer": answer}
                elif choice.finish_reason == "function_call":
                    tool_name = choice.message.function_call.name
                    tool_args = choice.message.function_call.arguments
                    print("Execute tool call", tool_name, tool_args)
                    func_result = await session.call_tool(tool_name, tool_args)
                    print("func_result", func_result)
                    func_result_content = func_result.content[0].text
                    payload.messages.extend([
                        choice.message,
                        Messages(
                            role=MessagesRole.FUNCTION,
                            name=tool_name,
                            content=func_result_content,
                        )
                    ])
                    answer.extend([
                        {
                            "role": "assistant",
                            "content": choice.message.content,
                            "function_call": choice.message.function_call,
                        },
                        {
                            "role": "function",
                            "name": tool_name,
                            "content": func_result_content,
                        }
                    ])
                    # Get next response
                    response = giga.chat(payload)
                    choice = response.choices[0]
