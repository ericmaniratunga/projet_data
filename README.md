# Projet ETL - Instructions

Ce dépôt contient un pipeline ETL simple (Extract → Transform → Load) utilisant PostgreSQL et pandas.

## Fichiers importants

- `config.py` : charge la configuration depuis les variables d'environnement via `python-dotenv`.
- `etl.py` : point d'entrée du pipeline, exécute `src.etl.run_etl()`.
- `src/` : code du pipeline
  - `src/extract.py` : extraction SQL → DataFrame
  - `src/transform.py` : transformations et construction des dimensions/faits
  - `src/load.py` : chargement des dimensions et de la table de faits
  - `src/utils.py` : utilitaires (connexion DB)
- `tests/test_transform.py` : tests unitaires pour les transformations
- `.env` : fichier local contenant les variables d'environnement (NE PAS COMMIT)
- `.gitignore` : ignore `.env`, l'environnement virtuel et fichiers temporaires

## Variables d'environnement

Copie le fichier `.env` (déjà présent pour référence) et modifie si nécessaire :

```
DB_HOST=localhost
DB_DATABASE=data_lab
DB_USER=postgres
DB_PASSWORD=12345
```

Le projet utilise `python-dotenv` pour charger ces variables depuis la racine du projet.

## Installation

Active ton venv, puis installe les dépendances :

```powershell
# depuis la racine du projet
.venv\Scripts\Activate.ps1  # (ou source .venv/bin/activate sur Unix)
python -m pip install -r requirements.txt
```

## Exécution

Lancer le pipeline ETL :

```powershell
python etl.py
```

Exécuter les tests unitaires :

```powershell
python -m pytest tests/test_transform.py
```

## Schéma attendu (rappels)

- Dimensions : `warehouse.dim_client`, `warehouse.dim_produit`, `warehouse.dim_temps`
  - Les dimensions doivent contenir une colonne `id` (clé surrogate) et une colonne naturelle (`client_id`, `produit_id`, `date_jour`).
- Table de faits : `warehouse.fait_ventes`
  - Colonnes attendues chargées par le pipeline : `client_key`, `produit_key`, `temps_key`, `quantite`, `montant`.

## Conseils

- Ne pousse pas `.env` dans le dépôt — il est listé dans `.gitignore`.
- Si les clés de dimensions ne sont pas présentes dans les tables `dim_*`, le pipeline lèvera une erreur et arrêtera le chargement des faits.

---

Si tu veux, je peux :
- ajouter un script SQL d'exemple pour créer les tables `warehouse.*` au format attendu, ou
- ajouter des logs plus détaillés et des métriques pour suivre les volumes chargés.
