# Tool descriptions in the format that chat models understand.
# The model reads the "description" to decide when to use each tool.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": (
                "Search the shop's rules and policies (returns, refunds, "
                "shipping cost, delivery time, tracking). Use it for general "
                "questions that do not depend on a specific customer."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question to search for, in Persian",
                    }
                },
                "required": ["question"],
            },
        },
    },
    {
            "type": "function",
            "function": {
                "name": "get_customer_orders",
                "description": (
                    "Get the orders of the customer who is currently logged in. "
                    "Use it when the customer asks about their own orders. "
                    "It needs no arguments."
                ),
                "parameters": {"type": "object", "properties": {}},
            },
        },

    {
        "type": "function",
        "function": {
            "name": "create_ticket",
            "description": (
                "Create a support ticket for the logged-in customer. Use it only "
                "when the customer clearly asks to file a complaint or open a "
                "ticket. A human reviewer must approve it before it is created."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "subject": {
                        "type": "string",
                        "description": "A short title for the ticket, in Persian",
                    },
                    "description": {
                        "type": "string",
                        "description": "What happened, in Persian",
                    },
                },
                "required": ["subject", "description"],
            },
        },
    },        
]