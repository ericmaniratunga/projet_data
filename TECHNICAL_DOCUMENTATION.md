# Documentation technique du projet ETL

## 1. Objectif du projet

Ce projet implémente un pipeline ETL simple en Python pour extraire des données transactionnelles depuis une base PostgreSQL, les transformer en dimensions et faits, puis charger ces sorties dans un entrepôt de données (`warehouse`).

Le cheminement théorique est :
- `Extract` : extraction SQL depuis le schéma source `oltp`
- `Transform` : calculs et construction des dimensions et de la table de faits
- `Load` : insertion dans les tables du schéma `warehouse`


## 2. Architecture logicielle

### 2.1. Entrée du pipeline

- `main.py`
  - Exécute la fonction `run_etl()` définie dans `src/etl.py`.

- `etl.py` (racine)
  - Charge la configuration depuis `config.py`.
  - Ouvre une connexion PostgreSQL via `src.utils.connect_db()`.
  - Extrait les données, transforme le `DataFrame`, construit les dimensions et la table de faits.
  - Charge chaque dimension puis la table de faits.

### 2.2. Configuration

- `config.py`
  - Utilise `python-dotenv` pour charger les paramètres de connexion PostgreSQL à partir du fichier `.env` situé à la racine.
  - Expose `DB_CONFIG` avec les clés `host`, `database`, `user`, `password`.
  - Définit `ETL_QUERY` : la requête SQL source qui fusionne les tables `commande_details`, `commandes`, `clients` et `produits`.

### 2.3. Extraction

- `src/extract.py`
  - Fonction `extract_data(conn, query)`.
  - Exécute la requête SQL via `pandas.read_sql()`.
  - Retourne un `DataFrame` pandas contenant les colonnes extraites.

### 2.4. Transformation

- `src/transform.py`

Fonctions :
- `add_montant(df)`
  - Calcule une colonne `montant` comme le produit de `quantite` par `prix`.
- `build_dimensions(df)`
  - Construit trois `DataFrame` de dimensions :
    - `clients` : colonnes `client_id`, `nom`, `ville`
    - `produits` : colonnes `produit_id`, `nom`, `prix` (renommage de `produit_nom`)
    - `temps` : colonnes `date_jour`, `mois`, `annee`
  - Les dimensions sont dédupliquées avec `drop_duplicates()`.
  - La dimension `temps` est construite depuis `date_commande` en utilisant `pd.to_datetime()`.
- `build_fact_sales(df)`
  - Crée la table de faits `fait_ventes` avec les colonnes sources suivantes :
    - `client_id`
    - `produit_id`
    - `date_jour` (date extraite de `date_commande`)
    - `quantite`
    - `montant`

### 2.5. Chargement

- `src/load.py`

Fonctions :
- `load_table(conn, table_name, dataframe, column_mapping)`
  - Charge un `DataFrame` dans une table cible PostgreSQL.
  - Utilise `execute_batch()` pour insérer les lignes avec `ON CONFLICT DO NOTHING`.
  - Reçoit un `column_mapping` permettant de mapper les colonnes du `DataFrame` vers les colonnes cibles.

- `load_fact_sales(conn, fact_df)`
  - Charge la table de faits `warehouse.fait_ventes`.
  - Récupère les mappages de clés naturelles vers clés surrogates pour chaque dimension :
    - `warehouse.dim_client` sur `client_id`
    - `warehouse.dim_produit` sur `produit_id`
    - `warehouse.dim_temps` sur `date_jour`
  - Mappe les clés naturelles vers `client_key`, `produit_key`, `temps_key`.
  - Vérifie qu’aucune clé n’est manquante avant la charge.
  - Insère les faits avec `ON CONFLICT DO NOTHING`.

- `_load_dimension_key_map(conn, table_name, natural_key)`
  - Interroge une dimension pour retourner un dictionnaire `valeur_naturelle -> id_surogate`.

- `_to_native(value)`
  - Convertit certains types pandas en valeurs Python natives avant insertion.

### 2.6. Utilitaires

- `src/utils.py`
  - Fonction `connect_db(db_config)` qui ouvre une connexion PostgreSQL via `psycopg2.connect(**db_config)`.


## 3. Modèle de données attendu

### 3.1. Source (schéma `oltp`)

La requête SQL source attend les tables suivantes :
- `oltp.commande_details` : contient `commande_id`, `produit_id`, `quantite`
- `oltp.commandes` : contient `id`, `client_id`, `date_commande`
- `oltp.clients` : contient `id`, `nom`, `ville`
- `oltp.produits` : contient `id`, `nom`, `prix`

Colonnes extraites par `ETL_QUERY` :
- `client_id`
- `nom`
- `ville`
- `produit_id`
- `produit_nom`
- `prix`
- `date_commande`
- `quantite`

### 3.2. Entrepôt (schéma `warehouse`)

Tables principales souhaitées :
- `warehouse.dim_client`
  - `id` (clé surrogate)
  - `client_id` (clé naturelle)
  - `nom`
  - `ville`
- `warehouse.dim_produit`
  - `id` (clé surrogate)
  - `produit_id` (clé naturelle)
  - `nom`
  - `prix`
- `warehouse.dim_temps`
  - `id` (clé surrogate)
  - `date_jour` (clé naturelle)
  - `mois`
  - `annee`
- `warehouse.fait_ventes`
  - `client_key`
  - `produit_key`
  - `temps_key`
  - `quantite`
  - `montant`


## 4. Comportement du pipeline

### 4.1. Idempotence partielle

- Les insertions de dimensions et de faits utilisent `ON CONFLICT DO NOTHING`, ce qui rend les charges réexécutables sans dupliquer les mêmes lignes si les contraintes uniques existent.

### 4.2. Résolution des dimensions

- Les faits ne sont chargés que si les dimensions sont déjà présentes dans `warehouse.dim_client`, `warehouse.dim_produit` et `warehouse.dim_temps`.
- Toute ligne dont une dimension ne peut pas être résolue déclenche une erreur `ValueError` et interrompt le chargement des faits.

### 4.3. Gestion des dates

- Les dates sont converties avec `pd.to_datetime(..., errors="coerce")`.
- Si une date est invalide, la conversion produit `NaT`, ce qui peut conduire à des clés manquantes lors du chargement du fait.


## 5. Tests unitaires

- `tests/test_transform.py`
  - Vérifie le calcul de la colonne `montant`.
  - Vérifie la création des dimensions `clients`, `produits`, `temps`.
  - Vérifie la construction de la table de faits `build_fact_sales()`.

Ce jeu de tests couvre la logique de transformation et la bonne normalisation des colonnes sources.


## 6. Flux détaillé des données : exemple concret

### 6.1. Données sources extraites

La requête `ETL_QUERY` fusionne quatre tables OLTP :

```sql
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
```

#### Sources et colonnes extraites

| Table source | Colonne | Signification |
|---|---|---|
| `oltp.clients` | `id` → `client_id` | Identifiant unique du client |
| `oltp.clients` | `nom` | Nom du client |
| `oltp.clients` | `ville` | Ville du client |
| `oltp.produits` | `id` → `produit_id` | Identifiant unique du produit |
| `oltp.produits` | `nom` → `produit_nom` | Nom du produit |
| `oltp.produits` | `prix` | Prix unitaire du produit |
| `oltp.commandes` | `date_commande` | Date de la commande |
| `oltp.commande_details` | `quantite` | Quantité vendue |

#### Exemple réel de données brutes extraites (du dump de base)

À partir des données PostgreSQL réelles :
- `oltp.clients` : 3 clients (Eric, Alice, Jean)
- `oltp.produits` : 3 produits (Ordinateur 800€, Souris 20€, Clavier 30€)
- `oltp.commandes` : 2 commandes (Eric le 01/06/2026, Alice le 02/06/2026)
- `oltp.commande_details` : 3 lignes de détail

Résultat de la requête `ETL_QUERY` :
```
client_id | nom    | ville      | produit_id | produit_nom  | prix  | date_commande | quantite
----------|--------|------------|------------|--------------|-------|---------------|----------
1         | Eric   | Bujumbura  | 1          | Ordinateur   | 800.0 | 2026-06-01    | 2
1         | Eric   | Bujumbura  | 2          | Souris       | 20.0  | 2026-06-01    | 3
2         | Alice  | Gitega     | 3          | Clavier      | 30.0  | 2026-06-02    | 5
```

### 6.2. Étape 1 : Calcul du montant (transformation simple)

**Fonction** : `add_montant(df)`

**Opération** :
```python
df["montant"] = df["quantite"] * df["prix"]
```

**Résultat avec données réelles** :
```
client_id | nom    | prix  | quantite | montant
----------|--------|-------|----------|--------
1         | Eric   | 800.0 | 2        | 1600.0
1         | Eric   | 20.0  | 3        | 60.0
2         | Alice  | 30.0  | 5        | 150.0
```

**Nettoyage à ce stade** : aucun (juste un calcul)
- Eric a acheté 2 Ordinateurs : 2 × 800 = 1600€
- Eric a acheté 3 Souris : 3 × 20 = 60€
- Alice a acheté 5 Claviers : 5 × 30 = 150€

### 6.3. Étape 2 : Construction des dimensions (dédupplication)

**Fonction** : `build_dimensions(df)`

#### 2.1. Dimension `clients`

**Extraction** : colonnes `client_id`, `nom`, `ville`
**Nettoyage** : `drop_duplicates()` supprime les doublons

Dans notre cas, le DataFrame de faits ne contient que les clients qui ont des commandes :
```
Avant dédupplication (du DataFrame des ventes) :
client_id | nom    | ville
----------|--------|----------
1         | Eric   | Bujumbura
1         | Eric   | Bujumbura    ← doublon (client 1 a 2 articles)
2         | Alice  | Gitega

Après dédupplication :
client_id | nom    | ville
----------|--------|----------
1         | Eric   | Bujumbura
2         | Alice  | Gitega
```

**Chargé dans la warehouse** :
```
id | client_id | nom    | ville
---|-----------|--------|----------
19 | 1         | Eric   | Bujumbura
20 | 2         | Alice  | Gitega
```

*Note : Jean (client_id=3) n'apparaît pas car il n'a pas de commandes.*

#### 2.2. Dimension `produits`

**Extraction** : colonnes `produit_id`, `produit_nom` (renommée en `nom`), `prix`
**Nettoyage** : `drop_duplicates()`

```
Avant dédupplication :
produit_id | nom          | prix
-----------|--------------|-------
1          | Ordinateur   | 800.0
2          | Souris       | 20.0
3          | Clavier      | 30.0

Après dédupplication :
produit_id | nom          | prix
-----------|--------------|-------
1          | Ordinateur   | 800.0
2          | Souris       | 20.0
3          | Clavier      | 30.0
```

**Chargé dans la warehouse** :
```
id | produit_id | nom          | prix
---|------------|--------------|-------
28 | 1          | Ordinateur   | 800.0
29 | 2          | Souris       | 20.0
30 | 3          | Clavier      | 30.0
```

#### 2.3. Dimension `temps`

**Extraction** : colonne `date_commande`
**Transformation** :
- Conversion de la date avec `pd.to_datetime(...)`
- Renommage en `date_jour`
- Création des colonnes `mois` et `annee`
- `drop_duplicates()`

```
Avant traitement :
date_commande
-----------
2026-06-01
2026-06-01    ← doublon (2 articles pour Eric ce jour)
2026-06-02

Après traitement :
date_jour  | mois | annee
-----------|------|-------
2026-06-01 | 6    | 2026
2026-06-02 | 6    | 2026
```

**Chargé dans la warehouse** :
```
id | date_jour  | mois | annee
---|------------|------|-------
19 | 2026-06-01 | 6    | 2026
20 | 2026-06-02 | 6    | 2026
```

**Nettoyage à ce stade** :
- Suppression des doublons
- Extraction du mois et de l'année à partir de la date

### 6.4. Étape 3 : Construction de la table de faits

**Fonction** : `build_fact_sales(df)`

**Sélection** : colonnes `client_id`, `produit_id`, `date_jour`, `quantite`, `montant`

**Avant chargement** (après avoir calculé `montant` et conservé toutes les lignes) :
```
client_id | produit_id | date_jour  | quantite | montant
----------|------------|------------|----------|--------
1         | 1          | 2026-06-01 | 2        | 1600.0
1         | 2          | 2026-06-01 | 3        | 60.0
2         | 3          | 2026-06-02 | 5        | 150.0
```

**Point important** : la table de faits CONSERVE toutes les lignes (une ligne = une transaction).

**Grain de la table de faits** (avec données réelles) :
- Row 1 : Eric a commandé 2 Ordinateurs le 01/06/2026 pour 1600€
- Row 2 : Eric a commandé 3 Souris le 01/06/2026 pour 60€
- Row 3 : Alice a commandé 5 Claviers le 02/06/2026 pour 150€

### 6.5. Étape 4 : Résolution des clés et chargement dans le warehouse

**Fonction** : `load_fact_sales(conn, fact_df)`

#### Étape 4a : Récupération des mappages surrogates

La fonction interroge les dimensions déjà chargées pour obtenir les correspondances :

```python
# Avec les données réelles du dump :
client_map = _load_dimension_key_map(conn, "warehouse.dim_client", "client_id")
# Résultat : {1: 19, 2: 20}  (client_id → id surrogate)

produit_map = _load_dimension_key_map(conn, "warehouse.dim_produit", "produit_id")
# Résultat : {1: 28, 2: 29, 3: 30}  (produit_id → id surrogate)

temps_map = _load_dimension_key_map(conn, "warehouse.dim_temps", "date_jour")
# Résultat : {2026-06-01: 19, 2026-06-02: 20}  (date_jour → id surrogate)
```

#### Étape 4b : Remplacement des clés naturelles par clés surrogates

La fonction mappe chaque colonne naturelle vers sa clé surrogate :

```python
fact["client_key"] = fact["client_id"].map(client_map)
# 1 → 19, 2 → 20

fact["produit_key"] = fact["produit_id"].map(produit_map)
# 1 → 28, 2 → 29, 3 → 30

fact["temps_key"] = fact["date_jour"].map(temps_map)
# 2026-06-01 → 19, 2026-06-02 → 20
```

#### Étape 4c : Sélection pour chargement

La fonction ne conserve que les colonnes finales :

```
client_key | produit_key | temps_key | quantite | montant
-----------|-------------|-----------|----------|--------
19         | 28          | 19        | 2        | 1600.0
19         | 29          | 19        | 3        | 60.0
20         | 30          | 20        | 5        | 150.0
```

#### Étape 4d : Insertion dans le warehouse

```sql
INSERT INTO warehouse.fait_ventes (client_key, produit_key, temps_key, quantite, montant) 
VALUES (19, 28, 19, 2, 1600.0)
       (19, 29, 19, 3, 60.0)
       (20, 30, 20, 5, 150.0)
ON CONFLICT DO NOTHING;
```

**Résultat final dans la warehouse** :
```
id | client_key | produit_key | temps_key | quantite | montant
---|------------|-------------|-----------|----------|--------
13 | 19         | 28          | 19        | 2        | 1600.00
14 | 19         | 29          | 19        | 3        | 60.00
15 | 20         | 30          | 20        | 5        | 150.00
```

**Vérification** :
- Ligne 13 : Eric (key=19) × Ordinateur (key=28) × 2026-06-01 (key=19) = 2 unités × 1600€
- Ligne 14 : Eric (key=19) × Souris (key=29) × 2026-06-01 (key=19) = 3 unités × 60€
- Ligne 15 : Alice (key=20) × Clavier (key=30) × 2026-06-02 (key=20) = 5 unités × 150€

### 6.8. Diagramme synthétique du flux avec données réelles

```
OLTP (SOURCE)
=============

oltp.clients           oltp.produits         oltp.commandes        oltp.commande_details
(id, nom, ville)       (id, nom, prix)       (id, client_id, date) (id, commande_id, produit_id, quantite)
1  Eric, Bujumbura     1  Ordinateur, 800    1  client=1, 01/06    1  cmd=1, prod=1, qty=2
2  Alice, Gitega       2  Souris, 20         2  client=2, 02/06    2  cmd=1, prod=2, qty=3
3  Jean, Ngozi         3  Clavier, 30                              3  cmd=2, prod=3, qty=5

                             ↓ ETL_QUERY (JOIN)

DataFrame extrait (8 colonnes, 3 lignes)
========================================
client_id | nom   | ville     | produit_id | produit_nom  | prix | date_commande | quantite
1         | Eric  | Bujumbura | 1          | Ordinateur   | 800  | 2026-06-01    | 2
1         | Eric  | Bujumbura | 2          | Souris       | 20   | 2026-06-01    | 3
2         | Alice | Gitega    | 3          | Clavier      | 30   | 2026-06-02    | 5

                        ↓ Transform

Étape 1 : add_montant()
=======================
Ajoute colonne montant = quantite × prix

        ↓ Étape 2 : build_dimensions()
        ↓ (déduplique et normalise)

DIMENSIONS (warehouse)
======================

dim_client              dim_produit              dim_temps
id | client_id         id | produit_id           id | date_jour
19 | 1                 28 | 1                    19 | 2026-06-01
20 | 2                 29 | 2                    20 | 2026-06-02
   (pas Jean=3)        30 | 3

        ↓ Étape 3 : build_fact_sales()
        ↓ (sélectionne colonnes pour faits)

Table de faits (avant résolution de clés)
==========================================
client_id | produit_id | date_jour  | quantite | montant
1         | 1          | 2026-06-01 | 2        | 1600.0
1         | 2          | 2026-06-01 | 3        | 60.0
2         | 3          | 2026-06-02 | 5        | 150.0

                        ↓ Load

Étape 4a-4b : Résolution de clés
=================================
Mappe chaque clé naturelle vers clé surrogate :
client_id 1 → 19, 2 → 20
produit_id 1 → 28, 2 → 29, 3 → 30
date_jour 2026-06-01 → 19, 2026-06-02 → 20

Étape 4d : Chargement final
============================

FAIT_VENTES (warehouse)
id | client_key | produit_key | temps_key | quantite | montant
13 | 19         | 28          | 19        | 2        | 1600.00
14 | 19         | 29          | 19        | 3        | 60.00
15 | 20         | 30          | 20        | 5        | 150.00
```

### 6.9. Questions-réponses sur le flux réel

**Q : Pourquoi Eric apparaît deux fois dans les faits ?**
R : Car Eric a deux lignes de détail dans sa commande : Ordinateur (2 unités) et Souris (3 unités). La table de faits est au grain transaction, donc chaque ligne de détail = une ligne de faits.

**Q : Où est Jean ?**
R : Jean n'a pas de commandes dans les données source, donc il n'apparaît pas dans les faits ni dans la dimension `dim_client` (elle est construite depuis le DataFrame des ventes).

**Q : Pourquoi les clés surrogates ne sont pas 1, 2, 3 mais 19, 20, 28, 29, 30 ?**
R : Parce que le pipeline a déjà été exécuté plusieurs fois. Les séquences PostgreSQL ont continué à incrémenter. Chaque exécution ajoute de nouvelles lignes (ou les ignore avec `ON CONFLICT DO NOTHING` si la contrainte unique existe).

**Q : Comment savez-vous que Eric (key=19) a commandé dans dim_temps (key=19) ?**
R : C'est une coïncidence dans cet exemple. Les deux ont la même valeur surrogates (19) mais ils sont dans des tables différentes et correspondent à des domaines différents. La liaison se fait par `client_key` et `temps_key` dans la table de faits.

---

## 7. Dashboard interactif dans le navigateur

Le projet inclut un dashboard Dash dans `dashboard.py` qui réunit les quatre rapports principaux au sein d'une seule interface web.

### 7.1. Fonctionnalités du dashboard

- `Chiffre d'affaires par client`
- `Chiffre d'affaires par produit`
- `Évolution des ventes par mois / année`
- `Quantités vendues par produit`

Le dashboard charge les données depuis les tables `warehouse.fait_ventes`, `warehouse.dim_client`, `warehouse.dim_produit` et `warehouse.dim_temps`.

### 7.2. Architecture et exécution

- `dashboard.py` utilise Dash et Plotly pour construire l'interface.
- Les données sont chargées avec quatre requêtes SQL distinctes :
  - `QUERY_CA_CLIENT`
  - `QUERY_CA_PRODUIT`
  - `QUERY_VENTES_MOIS`
  - `QUERY_QUANTITES`
- Les graphiques sont organisés en une grille 2×2, avec deux graphiques sur la première ligne et deux sur la deuxième.

### 7.3. Lancement et adresse d'accès

Exécuter :

```powershell
python dashboard.py
```

Puis ouvrir dans un navigateur :

- `http://127.0.0.1:8050`

Le script affiche également dans la console :

```text
Dashboard disponible sur : http://127.0.0.1:8050
```

### 7.4. Concept de rapport combiné

Ce dashboard combine déjà les quatre rapports existants du projet dans une interface unique :

- synthèse client,
- synthèse produit,
- évolution des ventes dans le temps,
- quantités vendues par produit.

Il permet de visualiser rapidement les principaux indicateurs métier sans lancer quatre scripts distincts.

## 8. Recommandations théoriques pour l'évolution

- Ajouter des tests pour `load_table()` et `load_fact_sales()` avec une base de données de test ou un mock de `psycopg2`.
- Ajouter un suivi des métriques de volume : nombre de lignes extraites, insérées, ignorées.
- Compléter le schéma de l’entrepôt avec les contraintes uniques attendues (`client_id`, `produit_id`, `date_jour`).
- Ajouter un traitement d’erreurs plus fin pour les dates invalides et les enregistrements partiellement incomplets.
- Introduire des logs pour tracer chaque étape du pipeline.
