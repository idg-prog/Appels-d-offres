import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from supabase import create_client

# ============================================
# 1. CONFIGURATION
# ============================================
st.set_page_config(page_title="AO Dashboard Pro", layout="wide")

@st.cache_data(ttl=600)
def get_data():
    try:
        client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_SERVICE_KEY"])
        response = client.table("Tenders Clean Data").select("*").execute()
        df = pd.DataFrame(response.data)
        return df.fillna("-")
    except Exception as e:
        st.error(f"Erreur Supabase: {e}")
        return pd.DataFrame()

df = get_data()

# ============================================
# 2. CONSTRUCTION DU HTML / CSS
# ============================================
table_rows = ""

for _, row in df.iterrows():
    # Extraction des données
    client = str(row.get('Client', '-'))
    title = str(row.get('Title', '-'))
    pub = str(row.get('Date de publication', '-'))
    lim = str(row.get('Date de limite', '-'))
    budget = str(row.get('Budget', '-'))
    caution = str(row.get('Caution', '-'))
    loc = str(row.get('Localisation', '-'))
    desc = str(row.get('Description Technique', '-'))
    url = str(row.get('URL', '#'))
    
    # Nettoyage et formatage
    link = url if url.startswith('http') else f"https://{url}"
    initial = client[0] if client != "-" else "?"
    
    # Tronquer les textes longs pour le tableau
    title_short = (title[:60] + '...') if len(title) > 60 else title
    desc_short = (desc[:100] + '...') if len(desc) > 100 else desc

    table_rows += f"""
    <tr>
        <td><div class="logo-badge">{initial}</div><span class="client-name">{client}</span></td>
        <td class="title-cell">{title_short}</td>
        <td class="muted">{pub}</td>
        <td class="urgent">{lim}</td>
        <td class="success">{budget}</td>
        <td>{caution}</td>
        <td>{loc}</td>
        <td class="desc-cell" title="{desc}">{desc_short}</td>
        <td><a class="btn-link" href="{link}" target="_blank">Ouvrir 🔗</a></td>
    </tr>
    """

full_html = f"""
<style>
    body {{
        background-color: #0F172A;
        color: #F1F5F9;
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
        margin: 0;
        padding: 10px;
    }}
    .saas-table {{
        width: 100%;
        border-collapse: collapse;
        background-color: #1E293B;
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #334155;
        table-layout: fixed; /* Pour contrôler la largeur des colonnes */
    }}
    .saas-table thead {{
        background-color: #111827;
        border-bottom: 2px solid #475569;
    }}
    .saas-table th {{
        text-align: left;
        padding: 15px;
        color: #94A3B8;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    .saas-table td {{
        padding: 12px 15px;
        border-bottom: 1px solid #334155;
        font-size: 13px;
        color: #CBD5E1;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .saas-table tr:hover {{ background-color: #26334D; }}
    
    /* Colonnes spécifiques */
    .logo-badge {{
        width: 28px; height: 28px; border-radius: 6px;
        background: #475569; display: inline-flex;
        align-items: center; justify-content: center;
        font-weight: bold; margin-right: 10px; color: white;
    }}
    .client-name {{ font-weight: 500; }}
    .title-cell {{ font-weight: 600; color: #F8FAFC; white-space: normal; line-height: 1.3; }}
    .desc-cell {{ color: #94A3B8; font-size: 12px; white-space: normal; }}
    .muted {{ color: #94A3B8; }}
    .urgent {{ color: #F87171; font-weight: bold; }}
    .success {{ color: #10B981; font-weight: bold; }}
    
    .btn-link {{
        background-color: #EF4444;
        color: white !important;
        padding: 6px 12px;
        border-radius: 6px;
        text-decoration: none;
        font-size: 11px;
        font-weight: bold;
        display: inline-block;
    }}

    /* Définition des largeurs de colonnes */
    th:nth-child(1), td:nth-child(1) {{ width: 180px; }} /* Client */
    th:nth-child(2), td:nth-child(2) {{ width: 220px; }} /* Titre */
    th:nth-child(3), td:nth-child(3) {{ width: 100px; }} /* Publication */
    th:nth-child(4), td:nth-child(4) {{ width: 110px; }} /* Limite */
    th:nth-child(5), td:nth-child(5) {{ width: 120px; }} /* Budget */
    th:nth-child(6), td:nth-child(6) {{ width: 100px; }} /* Caution */
    th:nth-child(7), td:nth-child(7) {{ width: 120px; }} /* Localisation */
    th:nth-child(8), td:nth-child(8) {{ width: 200px; }} /* Description */
    th:nth-child(9), td:nth-child(9) {{ width: 80px; }}  /* Action */
</style>

<table class="saas-table">
    <thead>
        <tr>
            <th>Acheteur</th>
            <th>Titre du Marché</th>
            <th>Publication</th>
            <th>Échéance</th>
            <th>Budget</th>
            <th>Caution</th>
            <th>Lieu</th>
            <th>Description</th>
            <th>Action</th>
        </tr>
    </thead>
    <tbody>
        {table_rows}
    </tbody>
</table>
"""

# ============================================
# 3. INTERFACE STREAMLIT
# ============================================
st.markdown('<h1 style="color:white; font-size: 2.2rem; font-weight:800; margin-bottom:0;">📊 Dashboard de Veille Appels d\'Offres</h1>', unsafe_allow_html=True)
st.markdown('<p style="color:#94A3B8; font-size:1.1rem; margin-bottom:25px;">Interface centralisée pour le suivi des marchés publics. Les données incluent les détails techniques et financiers complets.</p>', unsafe_allow_html=True)

if df.empty:
    st.warning("Aucune donnée trouvée dans Supabase.")
else:
    # On affiche le composant HTML avec une hauteur fixe et scroll
    components.html(full_html, height=800, scrolling=True)

st.markdown("<center><small style='color: #475569;'>Base de données synchronisée en temps réel via Supabase SQL</small></center>", unsafe_allow_html=True)
