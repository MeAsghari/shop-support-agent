from mcp.server.fastmcp import FastMCP

from third_agent.database.queries import get_orders_by_email

# Create the MCP server with a name
mcp = FastMCP("third-agent-shop")


@mcp.tool()
def get_customer_orders(email: str) -> list[dict]:
    """Get all orders and their items for a customer, using the customer's email."""
    rows = get_orders_by_email(email)

    # Convert values to simple types, so they can be sent as JSON
    for row in rows:
        row["created_at"] = row["created_at"].isoformat()
        row["unit_price"] = float(row["unit_price"])

    return rows


if __name__ == "__main__":
    # Run the server and talk through stdin/stdout
    mcp.run()