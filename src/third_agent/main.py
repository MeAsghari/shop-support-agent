from third_agent.database.connection import get_connection


def main():
    with get_connection() as conn:
        result = conn.execute("SELECT version()").fetchone()
        print("Connected to PostgreSQL!")
        print(result[0])


if __name__ == "__main__":
    main()
