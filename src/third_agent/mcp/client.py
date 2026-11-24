import asyncio
import json
import sys
import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# How to start our MCP server (as a separate process)
SERVER_PARAMS = StdioServerParameters(
    command=sys.executable,
    args=["-m", "third_agent.mcp.server"],
    env=dict(os.environ),
)


async def _call_tool_async(name: str, arguments: dict) -> list[dict]:
    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments)

            # Each returned item arrives as a JSON text, so we parse it back
            return [json.loads(item.text) for item in result.content]


def call_tool(name: str, arguments: dict) -> list[dict]:
    """Normal (sync) function that hides the async code inside."""
    return asyncio.run(_call_tool_async(name, arguments))


if __name__ == "__main__":
    # Quick manual test
    print(call_tool("get_customer_orders", {"email": "ali@example.com"}))