from src.extract import extract_data
from src.load import load_table, load_fact_sales
from src.transform import add_montant, build_dimensions, build_fact_sales
from src.utils import connect_db
from config import DB_CONFIG, ETL_QUERY


def run_etl() -> None:
    """Run the full ETL pipeline from source to warehouse."""
    with connect_db(DB_CONFIG) as conn:
        df = extract_data(conn, ETL_QUERY)
        df = add_montant(df)

        dimensions = build_dimensions(df)
        facts = build_fact_sales(df)

        load_table(
            conn,
            "warehouse.dim_client",
            dimensions["clients"],
            {
                "client_id": "client_id",
                "nom": "nom",
                "ville": "ville",
            },
        )

        load_table(
            conn,
            "warehouse.dim_produit",
            dimensions["produits"],
            {
                "produit_id": "produit_id",
                "nom": "nom",
                "prix": "prix",
            },
        )

        load_table(
            conn,
            "warehouse.dim_temps",
            dimensions["temps"],
            {
                "date_jour": "date_jour",
                "mois": "mois",
                "annee": "annee",
            },
        )

        load_fact_sales(conn, facts)

        print("ETL terminé : dimensions et table de faits chargées dans le data warehouse.")
