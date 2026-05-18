import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from datetime import datetime, timedelta
from supabase import create_client

# ============================================
# 1. CONFIGURATION ET RÉFÉRENCE TEMPORELLE
# ============================================
st.set_page_config(page_title="AO Monitoring Pro", layout="wide")

TODAY = datetime(2026, 5, 18).date()
YESTERDAY = TODAY - timedelta(days=1)
URGENT_DEADLINE = TODAY + timedelta(days=3)

# ============================================
# 2. CSS PERSONNALISÉ POUR LES ONGLETS (TABS)
# ============================================
st.markdown("""
    <style>
    /* Fond principal */
    .stApp { background-color: #0F172A; color: #F1F5F9; }

    /* --- DESIGN DES ONGLETS --- */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background-color: transparent;
        margin-bottom: 20px;
    }

    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: #1E293B;
        border-radius: 8px;
        padding: 0px 25px;
        color: #94A3B8;
        border: 1px solid #334155;
        transition: all 0.3s ease;
        font-weight: 600;
    }

    /* Onglet au survol */
    .stTabs [data-baseweb="tab"]:hover {
        color: #F1F5F9;
        border-color: #EF4444;
        background-color: #26334D;
    }

    /* Onglet Actif */
    .stTabs [data-baseweb="tab--active"] {
        background-color: #EF4444 !important; /* Rouge pour l'actif */
        color: #FFFFFF !important;
        border: 1px solid #EF4444 !important;
        box-shadow: 0 4px 15px rgba(239, 68, 68, 0.3);
    }

    /* Enlever la ligne de bordure par défaut de Streamlit sous les onglets */
    .stTabs [data-baseweb="tab-border"] {
        display: none;
    }
    
    /* Titres */
    .main-title { font-size: 2.2rem; font-weight: 800; color: #FFFFFF; margin-bottom: 5px; }
    .intro-text { color: #94A3B8; margin-bottom: 25px; font-size: 1.1rem; }
    </style>
    """, unsafe_allow_html=True)

# ============================================
# 3. CHARGEMENT ET TRAITEMENT DES DONNÉES
# ============================================
def clean_date_series(s):
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
        if df.empty: return df
        df['pub_dt'] = clean_date_series(df['Date de publication'])
        df['lim_dt'] = clean_date_series(df['Date de limite'])
        return df
    except Exception as e:
        st.error(f"Erreur : {e}")
        return pd.DataFrame()

df_raw = get_data()

# ============================================
# 4. GÉNÉRATION DU TABLEAU HTML
# ============================================
def build_html_table(data_df):
    if data_df.empty:
        return "<div style='color:#94A3B8; text-align:center; padding:50px; font-family:sans-serif; background:#1E293B; border-radius:12px;'>Aucun appel d'offre trouvé.</div>"

    table_rows = ""
    for idx, row in data_df.iterrows():
        def val(col):
            v = row.get(col, "-")
            return v if pd.notna(v) and str(v).lower() != "nan" else "-"

        client, title, pub, lim = val('Client'), val('Title'), val('Date de publication'), val('Date de limite')
        budget, caution, loc, desc, url = val('Budget'), val('Caution'), val('Localisation'), val('Description Technique'), val('URL')
        
        link = url if str(url).startswith('http') else f"https://{url}" if url != "-" else "#"
        title_short = (title[:85] + '...') if len(title) > 85 else title

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
                    <div class="expanded-section"><span class="label">📌 Titre intégral</span><div class="content-text">{title}</div></div>
                    <div class="expanded-section"><span class="label">🛠️ Description Technique</span><div class="content-text">{desc}</div></div>
                    <div style="margin-top:10px;"><a class="btn-link" href="{link}" target="_blank">Document Officiel 🔗</a></div>
                </div>
            </td>
        </tr>
        """

    return f"""
    <style>
        body {{ background-color: #0F172A; color: #F1F5F9; font-family: 'Inter', sans-serif; margin: 0; }}
        .saas-table {{ width: 100%; border-collapse: collapse; background-color: #1E293B; table-layout: fixed; border: 1px solid #334155; border-radius: 12px; overflow: hidden; }}
        .saas-table thead {{ background-color: #111827; border-bottom: 2px solid #475569; }}
        .saas-table th {{ text-align: left; padding: 15px; color: #94A3B8; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; }}
        .saas-table td {{ padding: 16px 15px; border-bottom: 1px solid #334155; font-size: 13px; color: #CBD5E1; vertical-align: top; }}
        .saas-table tr:hover {{ background-color: #26334D; }}
        .primary-col {{ font-weight: 600; color: #FFFFFF; line-height: 1.4; word-wrap: break-word; white-space: normal; }}
        th:nth-child(1), td:nth-child(1) {{ width: 220px; }}
        th:nth-child(2), td:nth-child(2) {{ width: 220px; }}
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
        <thead><tr><th>Acheteur</th><th>Titre du Marché</th><th>Publication</th><th>Échéance</th><th>Budget</th><th>Caution</th><th>Lieu</th><th>Action</th></tr></thead>
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
# 5. INTERFACE PRINCIPALE
# ============================================
st.markdown('<h1 class="main-title">📊 Suivi des Appels d\'Offres</h1>', unsafe_allow_html=True)
st.markdown(f'<p class="intro-text">💡 <b>Astuce :</b> Cliquez sur une ligne pour dérouler les détails complets. (Date : {TODAY.strftime("%d/%m/%Y")})</p>', unsafe_allow_html=True)

if df_raw.empty:
    st.warning("Aucune donnée disponible.")
else:
    # Filtrage
    df_nouveaux = df_raw[df_raw['pub_dt'] == YESTERDAY]
    df_urgent = df_raw[(df_raw['lim_dt'].notna()) & (df_raw['lim_dt'] >= TODAY) & (df_raw['lim_dt'] <= URGENT_DEADLINE)]

    # Création des onglets stylisés
    tab1, tab2, tab3 = st.tabs([
        f"📋 Tous ({len(df_raw)})", 
        f"✨ Nouveaux ({len(df_nouveaux)})", 
        f"🔥 Urgent ({len(df_urgent)})"
    ])

    with tab1:
        components.html(build_html_table(df_raw), height=850, scrolling=True)

    with tab2:
        components.html(build_html_table(df_nouveaux), height=850, scrolling=True)

    with tab3:
        components.html(build_html_table(df_urgent), height=850, scrolling=True)

st.markdown("<center><small style='color: #475569;'>Synchronisé avec Supabase • 2026 Strategy</small></center>", unsafe_allow_html=True)
