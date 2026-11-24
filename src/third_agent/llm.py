import os

import httpx
from dotenv import load_dotenv

load_dotenv()


def ask_llm(system_prompt: str, user_message: str) -> str:
    """Send one question to the chat model and return its text answer."""
    response = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
        json={
            "model": os.getenv("CHAT_MODEL"),
            "messages": [
                # The system message sets the rules for the model
                {"role": "system", "content": system_prompt},
                # The user message is the actual request
                {"role": "user", "content": user_message},
            ],
            "temperature": 0,  # 0 = most stable answers, less creativity
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def chat_with_tools(messages: list[dict], tools: list[dict]) -> dict:
    """Send a conversation and the tool list. Return the model's message."""
    response = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
        json={
            "model": os.getenv("CHAT_MODEL"),
            "messages": messages,
            "tools": tools,
            "temperature": 0,
        },
        timeout=60,
    )
    if response.is_error:
        print("SERVER ERROR:", response.status_code, response.text)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]


if __name__ == "__main__":
    # Quick manual test
    print(ask_llm("You are a helpful assistant. Answer in Persian.", "سلام، حالت چطوره؟"))