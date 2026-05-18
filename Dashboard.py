import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from supabase import create_client

# ============================================
# 1. CONFIGURATION
# ============================================
st.set_page_config(page_title="AO Monitoring", layout="wide")

@st.cache_data(ttl=600)
def get_data():
    try:
        client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_SERVICE_KEY"])
        response = client.table("Tenders Clean Data").select("*").execute()
        df = pd.DataFrame(response.data)
        return df.fillna("-")
    except:
        return pd.DataFrame()

df = get_data()

# ============================================
# 2. CONSTRUCTION DU CODE HTML COMPLET (CSS + TABLE)
# ============================================
# On prépare tout le code dans une seule variable string
table_rows = ""
for _, row in df.iterrows():
    client = str(row.get('Client', '-'))
    title = str(row.get('Title', '-'))
    pub = str(row.get('Date de publication', '-'))
    lim = str(row.get('Date de limite', '-'))
    budget = str(row.get('Budget', '-'))
    caution = str(row.get('Caution', '-'))
    url = str(row.get('URL', '#'))
    
    # Nettoyage URL
    link = url if url.startswith('http') else f"https://{url}"
    initial = client[0] if client != "-" else "?"
    title_short = (title[:85] + '...') if len(title) > 85 else title

    table_rows += f"""
    <tr>
        <td><div class="logo-badge">{initial}</div>{client}</td>
        <td class="title-cell">{title_short}</td>
        <td class="muted">{pub}</td>
        <td class="urgent">{lim}</td>
        <td class="success">{budget}</td>
        <td>{caution}</td>
        <td><a class="btn-link" href="{link}" target="_blank">Ouvrir</a></td>
    </tr>
    """

full_html = f"""
<style>
    body {{
        background-color: #0F172A;
        color: #F1F5F9;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        margin: 0;
        padding: 20px;
    }}
    .saas-table {{
        width: 100%;
        border-collapse: collapse;
        background-color: #1E293B;
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #334155;
    }}
    .saas-table thead {{
        background-color: #111827;
        border-bottom: 2px solid #475569;
    }}
    .saas-table th {{
        text-align: left;
        padding: 18px 15px;
        color: #94A3B8;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}
    .saas-table td {{
        padding: 16px 15px;
        border-bottom: 1px solid #334155;
        font-size: 14px;
        color: #CBD5E1;
    }}
    .saas-table tr:hover {{ background-color: #26334D; }}
    
    .logo-badge {{
        width: 30px; height: 30px; border-radius: 6px;
        background: #475569; display: inline-flex;
        align-items: center; justify-content: center;
        font-weight: bold; margin-right: 12px; color: white;
    }}
    .title-cell {{ font-weight: 600; color: #F8FAFC; }}
    .muted {{ color: #94A3B8; }}
    .urgent {{ color: #F87171; font-weight: bold; }}
    .success {{ color: #10B981; font-weight: bold; }}
    
    .btn-link {{
        background-color: #EF4444;
        color: white !important;
        padding: 8px 14px;
        border-radius: 6px;
        text-decoration: none;
        font-size: 12px;
        font-weight: bold;
    }}
</style>

<table class="saas-table">
    <thead>
        <tr>
            <th>Acheteur / Client</th>
            <th>Titre du Marché</th>
            <th>Publication</th>
            <th>Échéance</th>
            <th>Budget</th>
            <th>Caution</th>
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
st.markdown('<h1 style="color:white; font-size: 2.2rem; font-weight:800;">📊 Suivi Centralisé des Appels d\'Offres</h1>', unsafe_allow_html=True)
st.markdown('<p style="color:#94A3B8; font-size:1.1rem; margin-bottom:30px;">Bienvenue sur votre interface de veille. Consultez les détails financiers et les échéances de soumission.</p>', unsafe_allow_html=True)

if df.empty:
    st.warning("Aucune donnée disponible.")
else:
    # On utilise COMPONENTS.HTML pour un rendu garanti
    # On ajuste la hauteur en fonction du nombre de lignes (50px par ligne environ)
    calc_height = min(len(df) * 65 + 100, 800)
    components.html(full_html, height=calc_height, scrolling=True)

st.markdown("<center><small style='color: #475569;'>Données synchronisées via Supabase</small></center>", unsafe_allow_html=True)
