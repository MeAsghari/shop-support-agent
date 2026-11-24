import os

import psycopg
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()


def get_connection(**options):
    """Open a connection. Extra options (like autocommit) are passed to psycopg."""
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        **options,
    )
