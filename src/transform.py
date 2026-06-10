import pandas as pd


def add_montant(df: pd.DataFrame) -> pd.DataFrame:
    """Add a montant column to the extracted order dataset."""
    transformed = df.copy()
    transformed["montant"] = transformed["quantite"] * transformed["prix"]
    return transformed


def build_dimensions(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Build dataframes for the warehouse dimension tables."""
    clients = (
        df[["client_id", "nom", "ville"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )

    produits = (
        df[["produit_id", "produit_nom", "prix"]]
        .drop_duplicates()
        .rename(columns={"produit_nom": "nom"})
        .reset_index(drop=True)
    )

    temps = (
        pd.to_datetime(df["date_commande"], errors="coerce")
        .drop_duplicates()
        .rename("date_jour")
        .to_frame()
    )
    temps["mois"] = temps["date_jour"].dt.month
    temps["annee"] = temps["date_jour"].dt.year

    return {
        "clients": clients,
        "produits": produits,
        "temps": temps,
    }


def build_fact_sales(df: pd.DataFrame) -> pd.DataFrame:
    """Build the sales fact table from the transformed dataset."""
    fact = df.copy()
    fact["date_jour"] = pd.to_datetime(fact["date_commande"], errors="coerce").dt.date
    return fact[["client_id", "produit_id", "date_jour", "quantite", "montant"]]
