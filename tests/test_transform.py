import pandas as pd

from src.transform import add_montant, build_dimensions, build_fact_sales


def test_add_montant_and_build_dimensions():
    data = {
        "client_id": [1, 2],
        "nom": ["Alice", "Bob"],
        "ville": ["Paris", "Lyon"],
        "produit_id": [10, 20],
        "produit_nom": ["Produit A", "Produit B"],
        "prix": [100.0, 200.0],
        "date_commande": ["2024-01-01", "2024-02-01"],
        "quantite": [2, 3],
    }

    df = pd.DataFrame(data)
    df = add_montant(df)
    assert df.loc[0, "montant"] == 200.0
    assert df.loc[1, "montant"] == 600.0

    dimensions = build_dimensions(df)
    assert len(dimensions["clients"]) == 2
    assert len(dimensions["produits"]) == 2
    assert len(dimensions["temps"]) == 2
    assert "mois" in dimensions["temps"].columns
    assert "annee" in dimensions["temps"].columns

    fact_sales = build_fact_sales(df)
    assert len(fact_sales) == 2
    assert fact_sales.loc[0, "client_id"] == 1
    assert fact_sales.loc[0, "produit_id"] == 10
    assert fact_sales.loc[0, "quantite"] == 2
    assert fact_sales.loc[0, "montant"] == 200.0
