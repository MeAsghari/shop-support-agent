from .connection import get_connection


def seed() -> None:
    # "with" closes the connection and saves (commits) changes automatically
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Stop if data already exists, so we never insert twice
            cur.execute("SELECT COUNT(*) FROM customers")
            if cur.fetchone()[0] > 0:
                print("Data already exists. Nothing to do.")
                return

            # Insert customers
            cur.execute(
                "INSERT INTO customers (name, email) VALUES "
                "('Ali Rezaei', 'ali@example.com'), "
                "('Sara Ahmadi', 'sara@example.com')"
            )

            # Insert products
            cur.execute(
                "INSERT INTO products (name, price, stock) VALUES "
                "('Wireless Mouse', 25.00, 50), "
                "('Mechanical Keyboard', 80.00, 20), "
                "('USB-C Cable', 8.50, 200)"
            )

            # Insert one order for customer 1 (Ali)
            cur.execute(
                "INSERT INTO orders (customer_id, status) VALUES (1, 'shipped')"
            )

            # Insert two items inside order 1
            cur.execute(
                "INSERT INTO order_items (order_id, product_id, quantity, unit_price) "
                "VALUES (1, 1, 1, 25.00), (1, 3, 2, 8.50)"
            )

    print("Sample data inserted.")


if __name__ == "__main__":
    seed()