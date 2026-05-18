import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from datetime import datetime, timedelta
from supabase import create_client

# ============================================
# 1. CONFIGURATION ET RÉFÉRENCE TEMPORELLE
# ============================================
st.set_page_config(page_title="AO Monitoring Pro", layout="wide")

# Date de référence basée sur le contexte (18 Mai 2026)
TODAY = datetime(2026, 5, 18).date()
YESTERDAY = TODAY - timedelta(days=1)
URGENT_DEADLINE = TODAY + timedelta(days=3)

# ============================================
# 2. CHARGEMENT ET TRAITEMENT DES DONNÉES
# ============================================
def clean_date_series(s):
    """Nettoyage des formats de dates variés (français/anglais/ISO)"""
    s = s.astype(str).str.lower()
    s = s.str.replace('juin', 'june').str.replace('mai', 'may')
    s = s.str.split(' à').str[0].str.strip()
    return pd.to_datetime(s, errors='coerce', dayfirst=True).dt.date

@st.cache_data(ttl=600)
def get_data():
    try:
        client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_SERVICE_KEY"])
        response = client.table("Tenders Clean Data").select("*").execute()
        df = pd.DataFrame(response.data)
        
        # Création de colonnes de dates techniques pour le filtrage
        df['pub_dt'] = clean_date_series(df['Date de publication'])
        df['lim_dt'] = clean_date_series(df['Date de limite'])
        
        return df.fillna("-")
    except Exception as e:
        st.error(f"Erreur de connexion : {e}")
        return pd.DataFrame()

df = get_data()

# ============================================
# 3. LOGIQUE DE GÉNÉRATION DU TABLEAU HTML
# ============================================
def build_html_table(data_df):
    if data_df.empty:
        return "<div style='color:#94A3B8; text-align:center; padding:50px;'>Aucun appel d'offre dans cette catégorie.</div>"

    table_rows = ""
    # On utilise l'index réel du dataframe pour garantir l'unicité des IDs JS
    for idx, row in data_df.iterrows():
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
        <tr onclick="toggleDetails({idx})" style="cursor: pointer;">
            <td class="primary-col">{client}</td>
            <td class="primary-col title-cell"><span class="expand-icon">▶</span> {title}</td>
            <td class="muted">{pub}</td>
            <td class="urgent">{lim}</td>
            <td class="success">{budget}</td>
            <td class="muted">{caution}</td>
            <td class="muted">{loc}</td>
            <td><a class="btn-link" href="{link}" target="_blank">Ouvrir</a></td>
        </tr>
        <tr id="details-{idx}" class="details-row" style="display: none;">
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

    return f"""
    <style>
        body {{ background-color: #0F172A; color: #F1F5F9; font-family: sans-serif; margin: 0; }}
        .saas-table {{ width: 100%; border-collapse: collapse; background-color: #1E293B; table-layout: fixed; border: 1px solid #334155; }}
        .saas-table thead {{ background-color: #111827; border-bottom: 2px solid #475569; }}
        .saas-table th {{ text-align: left; padding: 15px; color: #94A3B8; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; }}
        .saas-table td {{ padding: 16px 15px; border-bottom: 1px solid #334155; font-size: 13px; color: #CBD5E1; vertical-align: top; }}
        .saas-table tr:hover {{ background-color: #26334D; }}
        .primary-col {{ font-weight: 600; color: #FFFFFF; line-height: 1.4; word-wrap: break-word; white-space: normal; }}
        th:nth-child(1), td:nth-child(1) {{ width: 220px; }}
        th:nth-child(2), td:nth-child(2) {{ width: 220px; }}
        th:nth-child(3), td:nth-child(3) {{ width: 100px; }}
        th:nth-child(4), td:nth-child(4) {{ width: 100px; }}
        th:nth-child(5), td:nth-child(5) {{ width: 130px; }}
        th:nth-child(6), td:nth-child(6) {{ width: 100px; }}
        th:nth-child(7), td:nth-child(7) {{ width: 120px; }}
        th:nth-child(8), td:nth-child(8) {{ width: 90px; }}
        .expand-icon {{ color: #EF4444; font-size: 9px; margin-right: 4px; }}
        .urgent {{ color: #F87171; font-weight: bold; }}
        .success {{ color: #10B981; font-weight: bold; }}
        .muted {{ color: #94A3B8; font-size: 12px; }}
        .details-row {{ background-color: #111827 !important; }}
        .expanded-content {{ padding: 25px; border-left: 4px solid #EF4444; }}
        .label {{ color: #94A3B8; text-transform: uppercase; font-size: 10px; font-weight: bold; }}
        .content-text {{ font-size: 14px; margin-top: 5px; color: #E2E8F0; line-height: 1.6; }}
        .btn-link {{ background-color: #EF4444; color: white !important; padding: 6px 12px; border-radius: 6px; text-decoration: none; font-size: 11px; font-weight: bold; display: inline-block; }}
    </style>
    <table class="saas-table">
        <thead>
            <tr>
                <th>Acheteur</th><th>Titre du Marché</th><th>Publication</th><th>Échéance</th><th>Budget</th><th>Caution</th><th>Lieu</th><th>Action</th>
            </tr>
        </thead>
        <tbody>{table_rows}</tbody>
    </table>
    <script>
    function toggleDetails(id) {{
        var element = document.getElementById('details-' + id);
        element.style.display = (element.style.display === 'none') ? 'table-row' : 'none';
    }}
    </script>
    """

# ============================================
# 4. INTERFACE STREAMLIT AVEC ONGLETS
# ============================================
st.markdown('<h1 style="color:white; font-size: 2.2rem; font-weight:800; margin-bottom:0;">📊 Suivi des Appels d\'Offres</h1>', unsafe_allow_html=True)
st.markdown(f'<p style="color:#94A3B8; font-size:1.1rem; margin-top:10px;">Date actuelle : <b>{TODAY.strftime("%d/%m/%Y")}</b>. Cliquez sur une ligne pour voir les détails.</p>', unsafe_allow_html=True)

if df.empty:
    st.warning("Aucune donnée disponible.")
else:
    # Filtrage des données pour les onglets
    df_nouveaux = df[df['pub_dt'] == YESTERDAY]
    df_urgent = df[(df['lim_dt'].notna()) & (df['lim_dt'] >= TODAY) & (df['lim_dt'] <= URGENT_DEADLINE)]

    # Création des onglets Streamlit
    tab1, tab2, tab3 = st.tabs([
        f"Tous ({len(df)})", 
        f"Nouveaux - Hier ({len(df_nouveaux)})", 
        f"Urgent - 3 jours ({len(df_urgent)})"
    ])

    with tab1:
        html_all = build_html_table(df)
        components.html(html_all, height=900, scrolling=True)

    with tab2:
        html_new = build_html_table(df_nouveaux)
        components.html(html_new, height=900, scrolling=True)

    with tab3:
        html_urgent = build_html_table(df_urgent)
        components.html(html_urgent, height=900, scrolling=True)

st.markdown("<center><small style='color: #475569;'>Mise à jour automatique • Supabase SQL</small></center>", unsafe_allow_html=True)
