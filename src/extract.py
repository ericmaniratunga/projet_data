import pandas as pd
from psycopg2.extensions import connection


def extract_data(conn: connection, query: str) -> pd.DataFrame:
    """Extract data from PostgreSQL into a pandas DataFrame."""
    return pd.read_sql(query, conn)
