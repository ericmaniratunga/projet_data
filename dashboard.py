import os
import sys
import psycopg2
import pandas as pd
from dash import Dash, html, dcc
import plotly.graph_objects as go

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import DB_CONFIG


# ─────────────────────────────────────────────
# Requêtes SQL
# ─────────────────────────────────────────────

QUERY_CA_CLIENT = """
    SELECT c.nom, SUM(f.montant) AS ca_total
    FROM warehouse.fait_ventes f
    JOIN warehouse.dim_client c ON f.client_key = c.id
    GROUP BY c.nom
    ORDER BY ca_total DESC
"""

QUERY_CA_PRODUIT = """
    SELECT p.nom, SUM(f.montant) AS ca_total
    FROM warehouse.fait_ventes f
    JOIN warehouse.dim_produit p ON f.produit_key = p.id
    GROUP BY p.nom
    ORDER BY ca_total DESC
"""

QUERY_VENTES_MOIS = """
    SELECT t.annee, t.mois, SUM(f.montant) AS ca_total
    FROM warehouse.fait_ventes f
    JOIN warehouse.dim_temps t ON f.temps_key = t.id
    GROUP BY t.annee, t.mois
    ORDER BY t.annee, t.mois
"""

QUERY_QUANTITES = """
    SELECT p.nom, SUM(f.quantite) AS quantite_totale
    FROM warehouse.fait_ventes f
    JOIN warehouse.dim_produit p ON f.produit_key = p.id
    GROUP BY p.nom
    ORDER BY quantite_totale DESC
"""


# ─────────────────────────────────────────────
# Chargement des données
# ─────────────────────────────────────────────

def load_data():
    with psycopg2.connect(**DB_CONFIG) as conn:
        df_ca_client  = pd.read_sql(QUERY_CA_CLIENT, conn)
        df_ca_produit = pd.read_sql(QUERY_CA_PRODUIT, conn)
        df_mois       = pd.read_sql(QUERY_VENTES_MOIS, conn)
        df_quantites  = pd.read_sql(QUERY_QUANTITES, conn)

    df_mois["periode"] = (
        df_mois["mois"].astype(str).str.zfill(2) + "/" + df_mois["annee"].astype(str)
    )
    return df_ca_client, df_ca_produit, df_mois, df_quantites


# ─────────────────────────────────────────────
# Construction des figures Plotly
# ─────────────────────────────────────────────

def make_fig_ca_client(df):
    fig = go.Figure(go.Bar(
        x=df["nom"],
        y=df["ca_total"],
        marker_color="steelblue",
        text=[f"{v:.0f} EUR" for v in df["ca_total"]],
        textposition="outside",
    ))
    fig.update_layout(
        title="Chiffre d'affaires par client",
        xaxis_title="Client",
        yaxis_title="Montant (EUR)",
        yaxis=dict(range=[0, df["ca_total"].max() * 1.25]),
        plot_bgcolor="white",
    )
    return fig


def make_fig_ca_produit(df):
    fig = go.Figure(go.Bar(
        x=df["nom"],
        y=df["ca_total"],
        marker_color="darkorange",
        text=[f"{v:.0f} EUR" for v in df["ca_total"]],
        textposition="outside",
    ))
    fig.update_layout(
        title="Chiffre d'affaires par produit",
        xaxis_title="Produit",
        yaxis_title="Montant (EUR)",
        yaxis=dict(range=[0, df["ca_total"].max() * 1.25]),
        plot_bgcolor="white",
    )
    return fig


def make_fig_ventes_mois(df):
    fig = go.Figure(go.Scatter(
        x=df["periode"],
        y=df["ca_total"],
        mode="lines+markers+text",
        line=dict(color="seagreen", width=2),
        marker=dict(size=8),
        text=[f"{v:.0f} EUR" for v in df["ca_total"]],
        textposition="top center",
    ))
    fig.update_layout(
        title="Évolution des ventes par mois / année",
        xaxis_title="Période",
        yaxis_title="Montant (EUR)",
        yaxis=dict(range=[0, df["ca_total"].max() * 1.35]),
        plot_bgcolor="white",
    )
    return fig


def make_fig_quantites(df):
    fig = go.Figure(go.Bar(
        x=df["nom"],
        y=df["quantite_totale"],
        marker_color="mediumpurple",
        text=[f"{int(v)} unités" for v in df["quantite_totale"]],
        textposition="outside",
    ))
    fig.update_layout(
        title="Quantités vendues par produit",
        xaxis_title="Produit",
        yaxis_title="Quantité (unités)",
        yaxis=dict(range=[0, df["quantite_totale"].max() * 1.25]),
        plot_bgcolor="white",
    )
    return fig


# ─────────────────────────────────────────────
# Application Dash
# ─────────────────────────────────────────────

def build_app():
    df_ca_client, df_ca_produit, df_mois, df_quantites = load_data()

    app = Dash(__name__)
    app.title = "Dashboard ETL - Ventes"

    app.layout = html.Div(
        style={"fontFamily": "Arial, sans-serif", "backgroundColor": "#f4f6f9", "padding": "20px"},
        children=[

            # ── Titre principal ──
            html.H1(
                "📊 Dashboard des Ventes",
                style={"textAlign": "center", "color": "#2c3e50", "marginBottom": "30px"}
            ),

            # ── Ligne 1 : CA client + CA produit ──
            html.Div(
                style={"display": "flex", "gap": "20px", "marginBottom": "20px"},
                children=[
                    html.Div(
                        dcc.Graph(figure=make_fig_ca_client(df_ca_client)),
                        style={"flex": "1", "backgroundColor": "white",
                               "borderRadius": "8px", "padding": "10px",
                               "boxShadow": "0 2px 6px rgba(0,0,0,0.1)"}
                    ),
                    html.Div(
                        dcc.Graph(figure=make_fig_ca_produit(df_ca_produit)),
                        style={"flex": "1", "backgroundColor": "white",
                               "borderRadius": "8px", "padding": "10px",
                               "boxShadow": "0 2px 6px rgba(0,0,0,0.1)"}
                    ),
                ]
            ),

            # ── Ligne 2 : Évolution mois + Quantités ──
            html.Div(
                style={"display": "flex", "gap": "20px"},
                children=[
                    html.Div(
                        dcc.Graph(figure=make_fig_ventes_mois(df_mois)),
                        style={"flex": "1", "backgroundColor": "white",
                               "borderRadius": "8px", "padding": "10px",
                               "boxShadow": "0 2px 6px rgba(0,0,0,0.1)"}
                    ),
                    html.Div(
                        dcc.Graph(figure=make_fig_quantites(df_quantites)),
                        style={"flex": "1", "backgroundColor": "white",
                               "borderRadius": "8px", "padding": "10px",
                               "boxShadow": "0 2px 6px rgba(0,0,0,0.1)"}
                    ),
                ]
            ),
        ]
    )
    return app


# ─────────────────────────────────────────────
# Point d'entrée
# ─────────────────────────────────────────────

if __name__ == "__main__":
    app = build_app()
    print("Dashboard disponible sur : http://127.0.0.1:8050")
    app.run(debug=True)
