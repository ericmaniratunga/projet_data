import psycopg2
from psycopg2.extensions import connection
from typing import Dict


def connect_db(db_config: Dict[str, str]) -> connection:
    """Create a PostgreSQL connection."""
    return psycopg2.connect(**db_config)
