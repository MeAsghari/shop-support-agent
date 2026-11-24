from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from third_agent.rag.retrieval import search

from third_agent.llm import ask_llm

import re

from third_agent.mcp.client import call_tool

from pydantic import ValidationError

from third_agent.schemas import Classification



# The shared state: every node reads from it and writes to it
class SupportState(TypedDict):
    question: str
    intent: str  # what kind of question this is: docs, orders, or other
    email: str  # email found in the question, or "" if none
    chunks: list[dict]
    answer: str

# Rules for the model: answer only from the given documents
SYSTEM_PROMPT = """You are a customer support assistant for an online shop.
Answer the customer's question in Persian, using ONLY the documents provided.
If the documents do not contain the answer, say you do not have this information.
Keep the answer short and clear. Never invent facts, numbers, or policies."""


CLASSIFY_PROMPT = """Classify the customer's question into exactly one category.

docs: general questions about the shop's rules and policies, such as return
conditions, refund timing, shipping cost, delivery time, or how tracking works.
These questions do NOT depend on a specific customer or order.

orders: questions about the customer's OWN specific order, such as its status,
its items, or where it is now. These usually include an email or say "my order".

other: anything not related to this shop at all.

Examples:
- "ارسال برای خرید بالای یک میلیون رایگانه؟" -> docs
- "پول بعد از مرجوعی چند روزه برمی‌گرده؟" -> docs
- "کد رهگیری رو چطور می‌گیرم؟" -> docs
- "وضعیت سفارش من با ایمیل a@b.com چیه؟" -> orders
- "سفارشم الان کجاست؟" -> orders
- "بهترین گوشی کدومه؟" -> other

Reply with only a JSON object like this, and nothing else:
{"intent": "docs", "email": null}
If the question contains an email address, put it in "email". Otherwise use null."""


def classify_node(state: SupportState) -> dict:
    """Ask the model for a JSON answer, then validate it with Pydantic."""
    reply = ask_llm(CLASSIFY_PROMPT, state["question"])

    # Models sometimes add extra text, so we keep only the part inside { ... }
    start, end = reply.find("{"), reply.rfind("}")
    json_text = reply[start : end + 1] if start != -1 and end != -1 else ""

    try:
        result = Classification.model_validate_json(json_text)
    except ValidationError:
        # Broken or invalid output: take the safest path
        return {"intent": "other", "email": ""}

    # Trust the email only if it really appears in the customer's text
    email = result.email
    if not email or email not in state["question"]:
        email = ""

    return {"intent": result.intent, "email": email}



def route_by_intent(state: SupportState) -> str:
    """Return the label that the conditional edge will follow."""
    return state["intent"]



ORDERS_PROMPT = """You are a customer support assistant for an online shop.
Answer the customer's question in Persian only, using ONLY the order data provided.
The data belongs to the customer who asked, so never say the data is unavailable.
Mention the order number, its status, and the products with their quantities.
Status words: shipped = ارسال شده, pending = در حال پردازش.
Do not mention tracking codes, websites, sections, or anything not in the data.
Use only Persian letters and numbers. Keep the answer short."""


def format_orders(orders: list[dict]) -> str:
    """Turn order rows into short plain text lines that are easy for the model."""
    lines = []
    for item in orders:
        lines.append(
            f"Order number {item['order_id']} | status: {item['status']} | "
            f"product: {item['product']} | quantity: {item['quantity']} | "
            f"unit price: {item['unit_price']}"
        )
    return "\n".join(lines)


def orders_node(state: SupportState) -> dict:
    """Look up the customer's orders with the MCP tool, then write the answer."""
    email = state["email"]
    if not email:
        return {"answer": "برای پیگیری سفارش، لطفاً ایمیل ثبت‌شده‌ی خود را بنویسید."}

    orders = call_tool("get_customer_orders", {"email": email})
    if not orders:
        return {"answer": "سفارشی با این ایمیل پیدا نشد."}

    user_message = (
        f"Order data:\n{format_orders(orders)}\n\n"
        f"Customer question: {state['question']}"
    )
    return {"answer": ask_llm(ORDERS_PROMPT, user_message)}



def retrieve_node(state: SupportState) -> dict:
    """Find the document chunks closest to the question."""
    chunks = search(state["question"], k=3)
    # Return only what changed. LangGraph merges it into the state
    return {"chunks": chunks}


def answer_node(state: SupportState) -> dict:
    """Write the final answer with the language model, using the chunks."""
    documents = "\n\n".join(chunk["content"] for chunk in state["chunks"])

    # Put the documents and the question in one message for the model
    user_message = f"Documents:\n{documents}\n\nCustomer question: {state['question']}"

    return {"answer": ask_llm(SYSTEM_PROMPT, user_message)}


def fallback_node(state: SupportState) -> dict:
    """Used when we cannot answer from our documents."""
    return {"answer": "متأسفم، این اطلاعات در اسناد ما موجود نیست."}


def route_after_retrieve(state: SupportState) -> str:
    """Decide the next node. It returns a label, not a node name."""
    if state["chunks"]:
        return "has_info"
    return "no_info"


# Build the graph: START -> retrieve -> answer -> END
builder = StateGraph(SupportState)
builder.add_node("classify", classify_node)
builder.add_node("retrieve", retrieve_node)
builder.add_node("answer", answer_node)
builder.add_node("fallback", fallback_node)
builder.add_node("orders", orders_node)

builder.add_edge(START, "classify")

# First decision: the model's classification picks the path
builder.add_conditional_edges(
    "classify",
    route_by_intent,
    {"docs": "retrieve", "orders": "orders", "other": "fallback"},
)

# Second decision: did the search find anything?
builder.add_conditional_edges(
    "retrieve",
    route_after_retrieve,
    {"has_info": "answer", "no_info": "fallback"},
)

builder.add_edge("answer", END)
builder.add_edge("fallback", END)
builder.add_edge("orders", END)

# compile() turns the blueprint into a runnable graph
graph = builder.compile()


if __name__ == "__main__":
    questions = [
        "اگه جنس خراب رسید هزینه برگشتش با کیه؟",
        "سفارش من با ایمیل ali@example.com کجاست؟",
        "بهترین گوشی برای عکاسی کدومه؟",
    ]
    for question in questions:
        result = graph.invoke(
            {"question": question, "intent": "", "email": "", "chunks": [], "answer": ""}
        )
        print("\nQUESTION:", question)
        print("INTENT:", result["intent"])
        print("ANSWER:", result["answer"])