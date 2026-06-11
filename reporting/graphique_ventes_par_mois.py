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
    SELECT t.annee, t.mois, SUM(f.montant) AS ca_total
    FROM warehouse.fait_ventes f
    JOIN warehouse.dim_temps t ON f.temps_key = t.id
    GROUP BY t.annee, t.mois
    ORDER BY t.annee, t.mois
"""


def load_sales_by_month() -> pd.DataFrame:
    """Charge l'evolution des ventes par mois/annee depuis PostgreSQL."""
    with psycopg2.connect(**DB_CONFIG) as conn:
        df = pd.read_sql(QUERY, conn)
    # Construit une colonne label lisible "MM/YYYY"
    df["periode"] = df["mois"].astype(str).str.zfill(2) + "/" + df["annee"].astype(str)
    return df


def show_chart(df: pd.DataFrame) -> None:
    """Affiche le graphique d'evolution des ventes par mois/annee."""
    if df.empty:
        raise ValueError(
            "Aucune donnee trouvee dans warehouse.fait_ventes pour afficher le graphique."
        )

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(df["periode"], df["ca_total"], marker="o", color="seagreen", linewidth=2, markersize=7)

    for x, y in zip(df["periode"], df["ca_total"]):
        ax.annotate(f"{y:.0f} EUR", (x, y), textcoords="offset points", xytext=(0, 10),
                    ha="center", fontsize=9)

    ax.set_title("Evolution des ventes par mois / annee", fontsize=14)
    ax.set_xlabel("Periode")
    ax.set_ylabel("Montant (EUR)")
    ax.set_ylim(0, df["ca_total"].max() * 1.3)
    ax.tick_params(axis="x", labelrotation=30)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    sales_by_month = load_sales_by_month()
    show_chart(sales_by_month)
