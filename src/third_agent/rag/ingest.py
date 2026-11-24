from third_agent.database.connection import get_connection
from third_agent.rag.chunking import load_chunks
from third_agent.rag.embeddings import embed_texts


def ingest(folder: str = "docs/knowledge") -> None:
    chunks = load_chunks(folder)
    vectors = embed_texts([chunk["content"] for chunk in chunks])

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Clear old rows, so running this script twice never duplicates data
            cur.execute("TRUNCATE document_chunks")

            for chunk, vector in zip(chunks, vectors):
                # str(vector) looks like "[0.1, 0.2, ...]", which pgvector understands
                cur.execute(
                    "INSERT INTO document_chunks (source, content, embedding) "
                    "VALUES (%s, %s, %s::vector)",
                    (chunk["source"], chunk["content"], str(vector)),
                )

    print(f"Inserted {len(chunks)} chunks.")


if __name__ == "__main__":
    ingest()