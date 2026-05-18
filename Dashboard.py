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

    # On crée une ligne principale et une ligne de détails cachée
    table_rows += f"""
    <tr onclick="toggleDetails({i})" style="cursor: pointer;">
        <td class="client-column">{client}</td>
        <td class="title-column"><div class="truncate">{title}</div></td>
        <td>{pub}</td>
        <td class="urgent">{lim}</td>
        <td class="success">{budget}</td>
        <td>{caution}</td>
        <td>{loc}</td>
        <td><a class="btn-link" href="{link}" target="_blank">Ouvrir 🔗</a></td>
    </tr>
    <tr id="details-{i}" class="details-row" style="display: none;">
        <td colspan="8">
            <div class="expanded-content">
                <div class="expanded-section">
                    <strong>📌 Titre complet :</strong><br>{title}
                </div>
                <div class="expanded-section">
                    <strong>🏢 Acheteur :</strong> {client}
                </div>
                <div class="expanded-section">
                    <strong>🛠️ Description Technique complète :</strong><br>{desc}
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
    }}
    .saas-table td {{
        padding: 14px 15px;
        border-bottom: 1px solid #334155;
        font-size: 13px;
        color: #CBD5E1;
    }}
    .saas-table tr:hover {{ background-color: #26334D; }}

    /* Troncature pour la vue compacte */
    .truncate {{
        max-width: 300px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}

    .client-column {{ font-weight: 500; color: #F1F5F9; width: 200px; }}
    .title-column {{ font-weight: 600; color: #FFFFFF; }}
    .urgent {{ color: #F87171; font-weight: bold; }}
    .success {{ color: #10B981; font-weight: bold; }}
    
    /* Style du contenu étendu */
    .details-row {{
        background-color: #111827 !important;
    }}
    .expanded-content {{
        padding: 20px;
        color: #F1F5F9;
        line-height: 1.6;
        border-left: 4px solid #EF4444;
    }}
    .expanded-section {{
        margin-bottom: 15px;
        font-size: 14px;
    }}
    .expanded-section strong {{
        color: #94A3B8;
        text-transform: uppercase;
        font-size: 11px;
    }}

    .btn-link {{
        background-color: #EF4444;
        color: white !important;
        padding: 6px 12px;
        border-radius: 6px;
        text-decoration: none;
        font-size: 11px;
        font-weight: bold;
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
st.markdown('<h1 style="color:white; font-size: 2.2rem; font-weight:800; margin-bottom:0;">📊 Dashboard Appels d\'Offres Interactif</h1>', unsafe_allow_html=True)
st.markdown('<p style="color:#94A3B8; font-size:1.1rem; margin-bottom:25px;">Cliquez sur n\'importe quelle ligne pour dérouler les détails complets (Description, Titre entier, etc.).</p>', unsafe_allow_html=True)

if df.empty:
    st.warning("Aucune donnée disponible.")
else:
    # On ajuste la hauteur du composant pour laisser de la place au déploiement
    components.html(full_html, height=800, scrolling=True)

st.markdown("<center><small style='color: #475569;'>Base de données synchronisée en temps réel • Supabase SQL</small></center>", unsafe_allow_html=True)
