from langgraph.checkpoint.postgres import PostgresSaver
from psycopg.rows import dict_row

from third_agent.database.connection import get_connection

# Same connection settings as the rest of the project (host comes from .env)
with get_connection(autocommit=True, row_factory=dict_row) as conn:
    # Creates the tables LangGraph needs (safe to run again)
    PostgresSaver(conn).setup()

print("Checkpointer tables are ready.")