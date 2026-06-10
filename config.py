import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
root = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=root / ".env")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_DATABASE", "data_lab"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "12345"),
}

ETL_QUERY = """
SELECT
    c.id AS client_id,
    c.nom,
    c.ville,
    p.id AS produit_id,
    p.nom AS produit_nom,
    p.prix,
    co.date_commande,
    cd.quantite
FROM oltp.commande_details cd
JOIN oltp.commandes co ON cd.commande_id = co.id
JOIN oltp.clients c ON co.client_id = c.id
JOIN oltp.produits p ON cd.produit_id = p.id
"""
