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
# 2. CONSTRUCTION DU HTML / CSS / JS
# ============================================
table_rows = ""

for i, row in df.iterrows():
    client = str(row.get('Client', '-'))
    title = str(row.get('Title', '-'))
    pub = str(row.get('Date de publication', '-'))
    lim = str(row.get('Date de limite', '-'))
    budget = str(row.get('Budget', '-'))
    caution = str(row.get('Caution', '-'))
    loc = str(row.get('Localisation', '-'))
    desc = str(row.get('Description Technique', '-'))
    url = str(row.get('URL', '#'))
    
    link = url if url.startswith('http') else f"https://{url}"

    table_rows += f"""
    <tr onclick="toggleDetails({i})" style="cursor: pointer;">
        <td class="primary-col">{client}</td>
        <td class="primary-col title-cell">
            <span class="expand-icon">▶</span> {title}
        </td>
        <td class="muted">{pub}</td>
        <td class="urgent">{lim}</td>
        <td class="success">{budget}</td>
        <td class="muted">{caution}</td>
        <td class="muted">{loc}</td>
        <td><a class="btn-link" href="{link}" target="_blank">Ouvrir 🔗</a></td>
    </tr>
    <tr id="details-{i}" class="details-row" style="display: none;">
        <td colspan="8">
            <div class="expanded-content">
                <div class="expanded-section">
                    <span class="label">📌 Titre intégral</span><br>
                    <div class="content-text">{title}</div>
                </div>
                <div class="expanded-section">
                    <span class="label">🛠️ Description Technique détaillée</span><br>
                    <div class="content-text">{desc}</div>
                </div>
                <div style="margin-top:10px;">
                    <a class="btn-link" href="{link}" target="_blank">Accéder au document officiel 🔗</a>
                </div>
            </div>
        </td>
    </tr>
    """

full_html = f"""
<style>
    body {{
        background-color: #0F172A;
        color: #F1F5F9;
        font-family: 'Inter', system-ui, sans-serif;
        margin: 0; padding: 10px;
    }}
    .saas-table {{
        width: 100%;
        border-collapse: collapse;
        background-color: #1E293B;
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #334155;
        table-layout: fixed; /* Indispensable pour contrôler précisément les largeurs */
    }}
    .saas-table thead {{
        background-color: #111827;
        border-bottom: 2px solid #475569;
    }}
    .saas-table th {{
        text-align: left;
        padding: 15px;
        color: #94A3B8;
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}
    .saas-table td {{
        padding: 16px 15px;
        border-bottom: 1px solid #334155;
        font-size: 13px;
        color: #CBD5E1;
        vertical-align: top; /* Pour l'effet 'tall' */
    }}
    .saas-table tr:hover {{ background-color: #26334D; }}

    /* Colonnes Principales (Acheteur & Titre) */
    .primary-col {{
        font-weight: 600;
        color: #FFFFFF;
        line-height: 1.4;
        word-wrap: break-word;
        white-space: normal; /* Autorise le retour à la ligne pour l'effet 'tall' */
    }}

    /* Ajustement des largeurs pour l'effet 'small' horizontalement */
    th:nth-child(1), td:nth-child(1) {{ width: 220px; }} /* Acheteur */
    th:nth-child(2), td:nth-child(2) {{ width: 220px; }} /* Titre (étroit comme l'acheteur) */
    th:nth-child(3), td:nth-child(3) {{ width: 100px; }} /* Publication */
    th:nth-child(4), td:nth-child(4) {{ width: 100px; }} /* Échéance */
    th:nth-child(5), td:nth-child(5) {{ width: 130px; }} /* Budget */
    th:nth-child(6), td:nth-child(6) {{ width: 100px; }} /* Caution */
    th:nth-child(7), td:nth-child(7) {{ width: 120px; }} /* Lieu */
    th:nth-child(8), td:nth-child(8) {{ width: 90px; }}  /* Action */

    .expand-icon {{
        color: #EF4444;
        font-size: 9px;
        margin-right: 4px;
        vertical-align: middle;
    }}

    .urgent {{ color: #F87171; font-weight: bold; }}
    .success {{ color: #10B981; font-weight: bold; }}
    .muted {{ color: #94A3B8; font-size: 12px; }}
    
    .details-row {{ background-color: #111827 !important; }}
    .expanded-content {{
        padding: 25px;
        color: #F1F5F9;
        line-height: 1.6;
        border-left: 4px solid #EF4444;
    }}
    .expanded-section {{ margin-bottom: 20px; }}
    .label {{
        color: #94A3B8;
        text-transform: uppercase;
        font-size: 10px;
        font-weight: bold;
        letter-spacing: 1px;
    }}
    .content-text {{
        font-size: 14px;
        margin-top: 5px;
        color: #E2E8F0;
    }}

    .btn-link {{
        background-color: #EF4444;
        color: white !important;
        padding: 6px 12px;
        border-radius: 6px;
        text-decoration: none;
        font-size: 11px;
        font-weight: bold;
        display: inline-block;
        text-align: center;
    }}
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
            <th>Action</th>
        </tr>
    </thead>
    <tbody>
        {table_rows}
    </tbody>
</table>

<script>
function toggleDetails(id) {{
    var element = document.getElementById('details-' + id);
    if (element.style.display === 'none') {{
        element.style.display = 'table-row';
    }} else {{
        element.style.display = 'none';
    }}
}}
</script>
"""

# ============================================
# 3. INTERFACE STREAMLIT
# ============================================
st.markdown('<h1 style="color:white; font-size: 2.2rem; font-weight:800; margin-bottom:0;">📊 Suivi des Appels d\'Offres</h1>', unsafe_allow_html=True)
st.markdown("""
    <p style="color:#94A3B8; font-size:1.1rem; margin-top:10px;">
        💡 <b>Astuce :</b> Cliquez sur n'importe quelle ligne pour dérouler la <b>description technique complète</b>.
    </p>
""", unsafe_allow_html=True)

if df.empty:
    st.warning("Aucune donnée disponible.")
else:
    # On utilise 900px pour laisser de la place aux lignes déployées
    components.html(full_html, height=900, scrolling=True)

st.markdown("<center><small style='color: #475569;'>Synchronisation en temps réel • Supabase SQL</small></center>", unsafe_allow_html=True)
