import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Tell the client how to start our server (as a separate process)
server_params = StdioServerParameters(
    command=sys.executable,  # the Python inside our .venv
    args=["-m", "third_agent.mcp.server"],
)


async def main() -> None:
    # Start the server and connect to it
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Step 1: discover the tools (the agent will do this later)
            tools = await session.list_tools()
            for tool in tools.tools:
                print("TOOL:", tool.name, "-", tool.description)

            # Step 2: call the tool with an argument
            result = await session.call_tool(
                "get_customer_orders",
                {"email": "ali@example.com"},
            )
            for item in result.content:
                print("RESULT:", item.text)


if __name__ == "__main__":
    asyncio.run(main())