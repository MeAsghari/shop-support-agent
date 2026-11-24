import os

import httpx
from dotenv import load_dotenv

load_dotenv()


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Turn a list of texts into a list of vectors (one request for all)."""
    response = httpx.post(
        "https://openrouter.ai/api/v1/embeddings",
        headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
        json={"model": os.getenv("EMBEDDING_MODEL"), "input": texts},
        timeout=60,
    )
    response.raise_for_status()

    # Sort by "index" so vectors stay in the same order as our texts
    data = sorted(response.json()["data"], key=lambda item: item["index"])
    return [item["embedding"] for item in data]