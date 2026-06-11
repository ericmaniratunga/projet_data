import os
import sys
import matplotlib.pyplot as plt
import pandas as pd
import psycopg2

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import DB_CONFIG


QUERY = """
    SELECT p.nom, SUM(f.montant) AS ca_total
    FROM warehouse.fait_ventes f
    JOIN warehouse.dim_produit p ON f.produit_key = p.id
    GROUP BY p.nom
    ORDER BY ca_total DESC
"""


def load_sales_by_product() -> pd.DataFrame:
    """Charge le chiffre d'affaires total par produit depuis PostgreSQL."""
    with psycopg2.connect(**DB_CONFIG) as conn:
        return pd.read_sql(QUERY, conn)


def show_chart(df: pd.DataFrame) -> None:
    """Affiche le graphique du chiffre d'affaires par produit."""
    if df.empty:
        raise ValueError(
            "Aucune donnee trouvee dans warehouse.fait_ventes pour afficher le graphique."
        )

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(df["nom"], df["ca_total"], color="darkorange")

    ax.set_title("Chiffre d'affaires par produit", fontsize=14)
    ax.set_xlabel("Produit")
    ax.set_ylabel("Montant (EUR)")
    ax.set_ylim(0, df["ca_total"].max() * 1.2)
    ax.bar_label(bars, labels=[f"{value:.0f} EUR" for value in df["ca_total"]], padding=3)
    ax.tick_params(axis="x", labelrotation=30)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    sales_by_product = load_sales_by_product()
    show_chart(sales_by_product)
