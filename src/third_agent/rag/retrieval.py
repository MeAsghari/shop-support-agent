from psycopg.rows import dict_row

from third_agent.database.connection import get_connection
from third_agent.rag.embeddings import embed_texts


def search(question: str, k: int = 3, max_distance: float = 0.55) -> list[dict]:
    """Return the k chunks whose meaning is closest to the question."""
    # Turn the question into a vector (embed_texts takes a list, so we use [0])
    question_vector = embed_texts([question])[0]

    sql = """
        SELECT
            source,
            content,
            embedding <=> %s::vector AS distance
        FROM document_chunks
        ORDER BY distance
        LIMIT %s
    """

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (str(question_vector), k))
            rows = cur.fetchall()
    # Keep only chunks that are close enough to the question
    return [row for row in rows if row["distance"] <= max_distance]

if __name__ == "__main__":
    # Several test questions, including one that has no answer in our documents
    questions = [
        "اگه جنس خراب رسید هزینه برگشتش با کیه؟",
        "سفارشم کی می‌رسه؟",
        "ارسال برای خرید گرون رایگانه؟",
        "پول کی به حسابم برمی‌گرده؟",
        "بهترین گوشی برای عکاسی کدومه؟",  # unrelated question
    ]

    for question in questions:
        print("\nQUESTION:", question)
        for row in search(question, k=2):
            print(" ", round(row["distance"], 3), row["source"], "->", row["content"][:40])