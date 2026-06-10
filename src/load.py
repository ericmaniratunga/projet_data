from typing import Dict
from pandas import DataFrame
from psycopg2 import sql
from psycopg2.extras import execute_batch


def load_table(conn, table_name: str, dataframe: DataFrame, column_mapping: Dict[str, str]) -> None:
    """Load one table into the warehouse."""
    if dataframe.empty:
        return

    schema, table = table_name.split(".", 1)
    source_columns = list(column_mapping.keys())
    target_columns = [column_mapping[col] for col in source_columns]
    values = [tuple(row[col] for col in source_columns) for _, row in dataframe.iterrows()]

    insert_query = sql.SQL(
        "INSERT INTO {}.{} ({}) VALUES ({}) ON CONFLICT DO NOTHING"
    ).format(
        sql.Identifier(schema),
        sql.Identifier(table),
        sql.SQL(", ").join(sql.Identifier(name) for name in target_columns),
        sql.SQL(", ").join(sql.Placeholder() for _ in target_columns),
    )

    with conn.cursor() as cursor:
        execute_batch(cursor, insert_query, values)
    conn.commit()


def _load_dimension_key_map(conn, table_name: str, natural_key: str) -> Dict:
    """Load a natural key -> surrogate key map from a dimension table."""
    schema, table = table_name.split(".", 1)
    query = sql.SQL(
        "SELECT {natural}, id FROM {}.{}"
    ).format(
        sql.Identifier(schema),
        sql.Identifier(table),
        natural=sql.Identifier(natural_key),
    )

    with conn.cursor() as cursor:
        cursor.execute(query)
        return {row[0]: row[1] for row in cursor.fetchall()}


def _to_native(value):
    if hasattr(value, "item") and not isinstance(value, (bytes, bytearray)):
        try:
            return value.item()
        except Exception:
            pass
    return value


def load_fact_sales(conn, fact_df: DataFrame) -> None:
    """Load the sales fact table using dimension surrogate keys."""
    if fact_df.empty:
        return

    client_map = _load_dimension_key_map(conn, "warehouse.dim_client", "client_id")
    produit_map = _load_dimension_key_map(conn, "warehouse.dim_produit", "produit_id")
    temps_map = _load_dimension_key_map(conn, "warehouse.dim_temps", "date_jour")

    fact = fact_df.copy()
    fact["client_key"] = fact["client_id"].map(client_map)
    fact["produit_key"] = fact["produit_id"].map(produit_map)
    fact["temps_key"] = fact["date_jour"].map(temps_map)

    if fact["client_key"].isna().any() or fact["produit_key"].isna().any() or fact["temps_key"].isna().any():
        missing = fact[fact[["client_key", "produit_key", "temps_key"]].isna().any(axis=1)]
        raise ValueError(
            "Impossible de résoudre toutes les clés de dimensions pour les lignes de faits.\n"
            f"Lignes manquantes:\n{missing.to_string(index=False)}"
        )

    fact_values = fact[["client_key", "produit_key", "temps_key", "quantite", "montant"]].to_records(index=False)
    values = [tuple(_to_native(value) for value in row) for row in fact_values]

    insert_query = sql.SQL(
        "INSERT INTO warehouse.fait_ventes (client_key, produit_key, temps_key, quantite, montant) VALUES ({}) ON CONFLICT DO NOTHING"
    ).format(sql.SQL(", ").join(sql.Placeholder() for _ in range(5)))

    with conn.cursor() as cursor:
        execute_batch(cursor, insert_query, values)
    conn.commit()
