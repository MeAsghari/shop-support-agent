from psycopg.rows import dict_row

from .connection import get_connection
from psycopg.types.json import Jsonb


def get_orders_by_email(email: str) -> list[dict]:
    """Return all order items for the customer with this email."""
    # %s is a placeholder. psycopg fills it in safely (see the note below)
    sql = """
        SELECT
            o.id AS order_id,
            o.status,
            o.created_at,
            p.name AS product,
            oi.quantity,
            oi.unit_price
        FROM customers c
        JOIN orders o ON o.customer_id = c.id
        JOIN order_items oi ON oi.order_id = o.id
        JOIN products p ON p.id = oi.product_id
        WHERE c.email = %s
        ORDER BY o.id
    """

    with get_connection() as conn:
        # dict_row gives each row as a dict, like {"order_id": 1, ...}
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (email,))
            return cur.fetchall()


def create_ticket(email: str, subject: str, description: str) -> int | None:
    """Create a support ticket for the customer with this email.

    Returns the new ticket id, or None if no customer has this email.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Find the customer first
            cur.execute("SELECT id FROM customers WHERE email = %s", (email,))
            row = cur.fetchone()
            if row is None:
                return None

            # RETURNING gives us the id of the row we just inserted
            cur.execute(
                "INSERT INTO tickets (customer_id, subject, description) "
                "VALUES (%s, %s, %s) RETURNING id",
                (row[0], subject, description),
            )
            return cur.fetchone()[0]
        

def add_approval_request(thread_id: str, customer_email: str, payload: dict) -> int:
    """Put a request in the review queue. Returns its id."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            # If this thread is already waiting, do not add a second row
            cur.execute(
                "SELECT id FROM approval_requests "
                "WHERE thread_id = %s AND status = 'pending'",
                (thread_id,),
            )
            row = cur.fetchone()
            if row is not None:
                return row[0]

            cur.execute(
                "INSERT INTO approval_requests (thread_id, customer_email, payload) "
                "VALUES (%s, %s, %s) RETURNING id",
                (thread_id, customer_email, Jsonb(payload)),
            )
            return cur.fetchone()[0]


def list_pending_approvals() -> list[dict]:
    """Return all requests that still wait for a human decision."""
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT id, thread_id, customer_email, payload, created_at "
                "FROM approval_requests WHERE status = 'pending' ORDER BY id"
            )
            return cur.fetchall()


def decide_approval(request_id: int, approved: bool) -> str | None:
    """Record the human decision. Returns the thread_id, or None if it was
    already decided (or does not exist)."""
    new_status = "approved" if approved else "rejected"
    with get_connection() as conn:
        with conn.cursor() as cur:
            # "AND status = 'pending'" makes this safe: only the first decision wins
            cur.execute(
                "UPDATE approval_requests SET status = %s "
                "WHERE id = %s AND status = 'pending' RETURNING thread_id",
                (new_status, request_id),
            )
            row = cur.fetchone()
            return row[0] if row else None


def get_password_hash(email: str) -> str | None:
    """Return the stored password hash, or None if the customer does not exist."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT password_hash FROM customers WHERE email = %s", (email,))
            row = cur.fetchone()
            return row[0] if row else None


def set_password_hash(email: str, password_hash: str) -> bool:
    """Save a password hash. Returns False if there is no such customer."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE customers SET password_hash = %s WHERE email = %s",
                (password_hash, email),
            )
            return cur.rowcount == 1


if __name__ == "__main__":
    # Quick manual test
    for row in get_orders_by_email("ali@example.com"):
        print(row)