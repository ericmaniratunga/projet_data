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
    SELECT p.nom, SUM(f.quantite) AS quantite_totale
    FROM warehouse.fait_ventes f
    JOIN warehouse.dim_produit p ON f.produit_key = p.id
    GROUP BY p.nom
    ORDER BY quantite_totale DESC
"""


def load_quantity_by_product() -> pd.DataFrame:
    """Charge les quantites vendues par produit depuis PostgreSQL."""
    with psycopg2.connect(**DB_CONFIG) as conn:
        return pd.read_sql(QUERY, conn)


def show_chart(df: pd.DataFrame) -> None:
    """Affiche le graphique des quantites vendues par produit."""
    if df.empty:
        raise ValueError(
            "Aucune donnee trouvee dans warehouse.fait_ventes pour afficher le graphique."
        )

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(df["nom"], df["quantite_totale"], color="mediumpurple")

    ax.set_title("Quantites vendues par produit", fontsize=14)
    ax.set_xlabel("Produit")
    ax.set_ylabel("Quantite (unites)")
    ax.set_ylim(0, df["quantite_totale"].max() * 1.2)
    ax.bar_label(bars, labels=[f"{int(v)} unites" for v in df["quantite_totale"]], padding=3)
    ax.tick_params(axis="x", labelrotation=30)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    quantity_by_product = load_quantity_by_product()
    show_chart(quantity_by_product)
