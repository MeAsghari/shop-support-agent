import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from third_agent.agent.loop import MAX_STEPS, SYSTEM_PROMPT, run_tool
from third_agent.agent.tools import TOOLS
from third_agent.llm import chat_with_tools

import uuid
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg.rows import dict_row
from third_agent.database.connection import get_connection
from third_agent.security import REFUSAL_MESSAGE, is_suspicious
import json
from langgraph.types import Command, interrupt


class AgentState(TypedDict):
    messages: Annotated[list[dict], operator.add]
    steps: int
    customer_email: str  # who is logged in: it comes from the system, never from the model
    approved: bool


def agent_node(state: AgentState) -> dict:
    """Ask the model what to do next: answer, or call tools."""
    reply = chat_with_tools(state["messages"], TOOLS)
    return {"messages": [reply], "steps": state["steps"] + 1}


def tools_node(state: AgentState) -> dict:
    """Run every tool the model asked for, and return the results as messages."""
    last_message = state["messages"][-1]
    results = []

    for call in last_message["tool_calls"]:
        name = call["function"]["name"]
        try:
            arguments = json.loads(call["function"]["arguments"])
            result = run_tool(name, arguments, state["customer_email"])
        except Exception as error:
            # Never crash the graph. Tell the model what went wrong instead
            result = f"Tool error: {error}"

        print(f"  [step {state['steps']}] tool: {name} {call['function']['arguments']}")
        results.append(
            {"role": "tool", "tool_call_id": call["id"], "content": result}
        )

    return {"messages": results}

def guard_node(state: AgentState) -> dict:
    """Check the newest user message before the model sees it."""
    last_message = state["messages"][-1]

    if last_message.get("role") == "user" and is_suspicious(last_message["content"]):
        # Add a refusal as the "answer". The model is never called.
        return {"messages": [{"role": "assistant", "content": REFUSAL_MESSAGE}]}

    return {}  # nothing to change


def route_after_guard(state: AgentState) -> str:
    """If the last message is already an assistant message, we blocked the request."""
    if state["messages"][-1].get("role") == "assistant":
        return "blocked"
    return "ok"

# Tools that change data: a human must approve them first
SENSITIVE_TOOLS = {"create_ticket"}

def route_after_agent(state: AgentState) -> str:
    """Decide: end, run tools, or ask a human first."""
    last_message = state["messages"][-1]
    if last_message.get("tool_calls") and state["steps"] < MAX_STEPS:
        names = {call["function"]["name"] for call in last_message["tool_calls"]}
        if names & SENSITIVE_TOOLS:
            return "approval"
        return "tools"
    return "end"


def approval_node(state: AgentState) -> dict:
    """Pause the graph and wait for a human decision."""
    # Nobody is logged in: nothing to approve, the tool will explain the problem
    if not state["customer_email"]:
        return {"approved": True}

    last_message = state["messages"][-1]
    requests = [
        {"tool": call["function"]["name"], "arguments": call["function"]["arguments"]}
        for call in last_message["tool_calls"]
    ]

    # The graph stops here. This node runs again from the top when we resume,
    # so there must be NO database writes before this line.
    decision = interrupt({"customer": state["customer_email"], "requests": requests})

    if decision:
        return {"approved": True}

    # Rejected: every tool call still needs an answer, so we answer "rejected"
    rejected = [
        {
            "role": "tool",
            "tool_call_id": call["id"],
            "content": "Rejected by a human reviewer. The request was NOT carried out.",
        }
        for call in last_message["tool_calls"]
    ]
    return {"approved": False, "messages": rejected}


def route_after_approval(state: AgentState) -> str:
    """Approved: run the tools. Rejected: go back to the model with the rejection."""
    return "tools" if state["approved"] else "agent"


builder = StateGraph(AgentState)
builder.add_node("guard", guard_node)
builder.add_node("agent", agent_node)
builder.add_node("approval", approval_node)
builder.add_node("tools", tools_node)

builder.add_edge(START, "guard")
builder.add_conditional_edges(
    "guard", route_after_guard, {"ok": "agent", "blocked": END}
)
builder.add_conditional_edges(
    "agent",
    route_after_agent,
    {"tools": "tools", "approval": "approval", "end": END},
)
builder.add_conditional_edges(
    "approval", route_after_approval, {"tools": "tools", "agent": "agent"}
)
builder.add_edge("tools", "agent")  # this edge creates the loop

# Compiled without memory: only used to draw the graph shape
graph = builder.compile()


PENDING_TEXT = "درخواست شما ثبت شد و پس از تأیید کارشناس انجام می‌شود."


def _result_to_text(result: dict) -> str:
    """Turn the graph result into text for the customer."""
    # The graph paused and is waiting for a human
    if result.get("__interrupt__"):
        return PENDING_TEXT

    last_message = result["messages"][-1]
    # If we stopped because of the step limit, there is no final text
    if last_message.get("tool_calls"):
        return "متأسفم، نتوانستم پاسخ را کامل کنم."
    return last_message["content"]


def run_agent(question: str, thread_id: str, customer_email: str = "") -> str:
    """Run one turn of a conversation. The same thread_id means the same memory."""
    config = {"configurable": {"thread_id": thread_id}}

    with get_connection(autocommit=True, row_factory=dict_row) as conn:
        app = builder.compile(checkpointer=PostgresSaver(conn))

        new_messages = []
        # Empty saved state means this is a new conversation: add the rules once
        if not app.get_state(config).values:
            new_messages.append({"role": "system", "content": SYSTEM_PROMPT})
        new_messages.append({"role": "user", "content": question})

        result = app.invoke(
            {"messages": new_messages, "steps": 0, "customer_email": customer_email},
            config,
        )

    return _result_to_text(result)


def get_pending_request(thread_id: str) -> dict | None:
    """If the conversation is paused, return what the human must approve."""
    config = {"configurable": {"thread_id": thread_id}}

    with get_connection(autocommit=True, row_factory=dict_row) as conn:
        app = builder.compile(checkpointer=PostgresSaver(conn))
        state = app.get_state(config)

        for task in state.tasks:
            for item in task.interrupts:
                return item.value
    return None


def resume_agent(thread_id: str, approved: bool) -> str:
    """Continue a paused conversation with the human's decision."""
    config = {"configurable": {"thread_id": thread_id}}

    with get_connection(autocommit=True, row_factory=dict_row) as conn:
        app = builder.compile(checkpointer=PostgresSaver(conn))
        # The value we pass here becomes the result of interrupt() in the node
        result = app.invoke(Command(resume=approved), config)

    return _result_to_text(result)


if __name__ == "__main__":
    # A random id, so every run starts with a fresh conversation
    thread_a = "demo-" + uuid.uuid4().hex[:8]
    thread_b = "demo-" + uuid.uuid4().hex[:8]

    print("--- Conversation A, question 1 ---")
    print(run_agent("سفارش من با ایمیل ali@example.com کجاست؟", thread_a))

    print("\n--- Conversation A, question 2 (no email this time) ---")
    print(run_agent("ایمیلم رو یادته؟ تعداد کابل‌هام چندتا بود؟", thread_a))

    print("\n--- Conversation B (a different thread) ---")
    print(run_agent("ایمیلم رو یادته؟ تعداد کابل‌هام چندتا بود؟", thread_b))


