import os

import httpx
from dotenv import load_dotenv

load_dotenv()

# Send one text to OpenRouter and get its vector back
response = httpx.post(
    "https://openrouter.ai/api/v1/embeddings",
    headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
    json={
        "model": os.getenv("EMBEDDING_MODEL"),
        "input": "مهلت بازگشت کالا چند روز است؟",
    },
    timeout=30,
)

# Show an error clearly if the request failed
response.raise_for_status()

vector = response.json()["data"][0]["embedding"]
print("Vector size:", len(vector))
print("First 5 numbers:", vector[:5])