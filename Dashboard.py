import streamlit as st
import pandas as pd
from supabase import create_client
import os

# ============================================
# PAGE CONFIG
# ============================================

st.set_page_config(
    page_title="Appels d'Offres Dashboard",
    page_icon="📊",
    layout="wide"
)

# ============================================
# SUPABASE CONNECTION
# ============================================


SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_SERVICE_KEY"]

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

# ============================================
# LOAD DATA
# ============================================

@st.cache_data(ttl=300)
def load_data():

    response = (
        supabase
        .table("Tenders Clean Data")
        .select("*")
        .execute()
    )

    data = response.data

    if not data:
        return pd.DataFrame()

    return pd.DataFrame(data)

df = load_data()

# ============================================
# HEADER
# ============================================

st.title("📑 Dashboard Appels d'Offres")
st.markdown("Visualisation intelligente des appels d'offres")

# ============================================
# EMPTY CHECK
# ============================================

if df.empty:
    st.warning("Aucune donnée trouvée dans la table 'Tenders Clean Data'")
    st.stop()

# ============================================
# CLEAN DATA
# ============================================

df.fillna("", inplace=True)

# ============================================
# SIDEBAR FILTERS
# ============================================

st.sidebar.header("🔎 Filtres")

# Client filter
clients = sorted(df["Client"].dropna().unique())

selected_client = st.sidebar.multiselect(
    "Client",
    clients
)

# Localisation filter
localisations = sorted(df["Localisation"].dropna().unique())

selected_localisation = st.sidebar.multiselect(
    "Localisation",
    localisations
)

# Search filter
search_text = st.sidebar.text_input(
    "Recherche par mot clé"
)

# ============================================
# APPLY FILTERS
# ============================================

filtered_df = df.copy()

if selected_client:
    filtered_df = filtered_df[
        filtered_df["Client"].isin(selected_client)
    ]

if selected_localisation:
    filtered_df = filtered_df[
        filtered_df["Localisation"].isin(selected_localisation)
    ]

if search_text:

    filtered_df = filtered_df[
        filtered_df.astype(str)
        .apply(
            lambda row: row.str.contains(
                search_text,
                case=False,
                na=False
            ).any(),
            axis=1
        )
    ]

# ============================================
# KPI METRICS
# ============================================

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Total Appels d'Offres",
        len(filtered_df)
    )

with col2:
    st.metric(
        "Clients",
        filtered_df["Client"].nunique()
    )

with col3:
    st.metric(
        "Villes",
        filtered_df["Localisation"].nunique()
    )

st.divider()

# ============================================
# TABLE VIEW
# ============================================

st.subheader("📋 Liste des Appels d'Offres")

display_columns = [
    "Title",
    "Client",
    "Localisation",
    "Date de publication",
    "Date de limite",
    "Budget",
    "Caution"
]

existing_columns = [
    col for col in display_columns
    if col in filtered_df.columns
]

st.dataframe(
    filtered_df[existing_columns],
    use_container_width=True,
    height=500
)

# ============================================
# DETAILED VIEW
# ============================================

st.divider()

st.subheader("📄 Détails")

titles = filtered_df["Title"].tolist()

selected_title = st.selectbox(
    "Choisir un appel d'offres",
    titles
)

if selected_title:

    selected_row = filtered_df[
        filtered_df["Title"] == selected_title
    ].iloc[0]

    st.markdown(f"## {selected_row.get('Title', '')}")

    col1, col2 = st.columns(2)

    with col1:
        st.write("### Informations")

        st.write(
            f"**Client :** {selected_row.get('Client', '')}"
        )

        st.write(
            f"**Localisation :** {selected_row.get('Localisation', '')}"
        )

        st.write(
            f"**Date de publication :** {selected_row.get('Date de publication', '')}"
        )

        st.write(
            f"**Date limite :** {selected_row.get('Date de limite', '')}"
        )

    with col2:

        st.write("### Financier")

        st.write(
            f"**Budget :** {selected_row.get('Budget', '')}"
        )

        st.write(
            f"**Caution :** {selected_row.get('Caution', '')}"
        )

    st.divider()

    st.write("### 🛠️ Description Technique")

    st.write(
        selected_row.get("Description Technique", "")
    )

    st.divider()

    url = selected_row.get("URL", "")

    if url:
        st.link_button(
            "🔗 Ouvrir le document",
            url
        )

# ============================================
# DOWNLOAD CSV
# ============================================

st.divider()

csv = filtered_df.to_csv(index=False).encode("utf-8")

st.download_button(
    "⬇️ Télécharger CSV",
    csv,
    "appels_offres.csv",
    "text/csv"
)
