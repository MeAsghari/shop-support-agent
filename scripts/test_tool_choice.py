from third_agent.agent.tools import TOOLS
from third_agent.llm import chat_with_tools

SYSTEM_PROMPT = (
    "You are a customer support assistant for an online shop. "
    "Use the tools when you need information. Answer in Persian."
)

questions = [
    "مهلت بازگشت کالا چند روزه؟",
    "سفارش من با ایمیل ali@example.com کجاست؟",
    "بهترین گوشی برای عکاسی کدومه؟",
]

for question in questions:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    reply = chat_with_tools(messages, TOOLS)

    print("\nQUESTION:", question)
    if reply.get("tool_calls"):
        for call in reply["tool_calls"]:
            print("TOOL:", call["function"]["name"], call["function"]["arguments"])
    else:
        print("NO TOOL. TEXT:", reply["content"])