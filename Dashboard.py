import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from datetime import datetime, timedelta
from supabase import create_client

# ============================================
# 1. CONFIGURATION ET RÉFÉRENCE TEMPORELLE
# ============================================
st.set_page_config(page_title="AO Strategic Monitoring", layout="wide")

# Date de référence (18 Mai 2026)
TODAY = datetime(2026, 5, 18).date()
YESTERDAY = TODAY - timedelta(days=1)
URGENT_DEADLINE = TODAY + timedelta(days=3)

# ============================================
# 2. CSS PERSONNALISÉ
# ============================================
st.markdown("""
    <style>
    .stApp { background-color: #0F172A; color: #F1F5F9; }

    /* DESIGN DES ONGLETS */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background-color: transparent;
        margin-bottom: 25px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        background-color: #1E293B;
        border-radius: 10px;
        padding: 0px 30px;
        color: #94A3B8;
        border: 1px solid #334155;
        transition: all 0.3s ease;
        font-weight: 600;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #F1F5F9;
        border-color: #EF4444;
    }
    .stTabs [data-baseweb="tab--active"] {
        background-color: #EF4444 !important;
        color: #FFFFFF !important;
        border: 1px solid #EF4444 !important;
        box-shadow: 0 4px 15px rgba(239, 68, 68, 0.4);
    }
    .stTabs [data-baseweb="tab-border"] { display: none; }
    
    /* STYLE DE L'INTRODUCTION */
    .main-title { font-size: 2.5rem; font-weight: 800; color: #FFFFFF; margin-bottom: 10px; }
    .intro-container {
        background: #1E293B;
        padding: 20px;
        border-radius: 12px;
        border-left: 5px solid #EF4444;
        margin-bottom: 30px;
    }
    .intro-text { color: #CBD5E1; font-size: 1.05rem; line-height: 1.6; }

    /* SECTION CONTACT FOOTER */
    .footer-contact {
        background: linear-gradient(135deg, #1E293B 0%, #111827 100%);
        padding: 40px;
        border-radius: 20px;
        border: 1px solid #334155;
        text-align: center;
        margin-top: 50px;
        margin-bottom: 20px;
    }
    .footer-contact h2 { color: white; margin-bottom: 10px; font-size: 1.8rem; }
    .footer-contact p { color: #94A3B8; margin-bottom: 25px; font-size: 1.1rem; }
    .contact-button {
        background-color: #EF4444;
        color: white !important;
        padding: 14px 32px;
        border-radius: 10px;
        text-decoration: none;
        font-weight: bold;
        font-size: 16px;
        display: inline-block;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        box-shadow: 0 4px 15px rgba(239, 68, 68, 0.3);
    }
    .contact-button:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 20px rgba(239, 68, 68, 0.5);
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ============================================
# 3. TRAITEMENT DES DONNÉES
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
        st.error(f"Erreur Supabase : {e}")
        return pd.DataFrame()

df_raw = get_data()

# ============================================
# 4. GÉNÉRATION DU TABLEAU HTML (AVEC TAGS)
# ============================================
def build_html_table(data_df):
    if data_df.empty:
        return "<div style='color:#94A3B8; text-align:center; padding:50px; font-family:sans-serif; background:#1E293B; border-radius:12px;'>Aucune opportunité détectée.</div>"

    table_rows = ""
    for idx, row in data_df.iterrows():
        def val(col):
            v = row.get(col, "-")
            return v if pd.notna(v) and str(v).lower() != "nan" else "-"

        client = val('Client')
        title = val('Title')
        pub = val('Date de publication')
        lim = val('Date de limite')
        budget = val('Budget')
        caution = val('Caution')
        loc = val('Localisation')
        tags = val('Tags')
        desc = val('Description Technique')
        url = val('URL')
        
        link = url if str(url).startswith('http') else f"https://{url}" if url != "-" else "#"

        table_rows += f"""
        <tr onclick="toggleDetails({idx})" style="cursor: pointer;">
            <td class="primary-col">{client}</td>
            <td class="primary-col"><span class="expand-icon">▶</span> {title}</td>
            <td class="tag-cell"><span class="tag-badge">{tags}</span></td>
            <td class="muted">{pub}</td>
            <td class="urgent">{lim}</td>
            <td class="success">{budget}</td>
            <td class="muted">{caution}</td>
            <td class="muted">{loc}</td>
            <td><a class="btn-link" href="{link}" target="_blank">Ouvrir</a></td>
        </tr>
        <tr id="details-{idx}" class="details-row" style="display: none;">
            <td colspan="9">
                <div class="expanded-content">
                    <div class="expanded-section"><span class="label">📌 Analyse du Titre</span><div class="content-text">{title}</div></div>
                    <div class="expanded-section"><span class="label">🏷️ Domaines</span><div class="content-text">{tags}</div></div>
                    <div class="expanded-section"><span class="label">🛠️ Spécifications Techniques</span><div class="content-text">{desc}</div></div>
                    <div style="margin-top:10px;"><a class="btn-link" href="{link}" target="_blank">Accéder au Document Source 🔗</a></div>
                </div>
            </td>
        </tr>
        """

    return f"""
    <style>
        body {{ background-color: #0F172A; color: #F1F5F9; font-family: 'Inter', sans-serif; margin: 0; }}
        
        .saas-table {{ 
            width: 100%; 
            border-collapse: collapse; 
            background-color: #1E293B; 
            table-layout: fixed; 
            border: 1px solid #334155; 
        }}
        
        .saas-table thead th {{ 
            position: sticky; 
            top: 0; 
            background-color: #111827; 
            z-index: 10;
            text-align: left; 
            padding: 18px 15px; 
            color: #94A3B8; 
            font-size: 10px; 
            text-transform: uppercase; 
            letter-spacing: 1px; 
            border-bottom: 2px solid #475569;
        }}
        
        .saas-table td {{ padding: 16px 15px; border-bottom: 1px solid #334155; font-size: 13px; color: #CBD5E1; vertical-align: top; }}
        .saas-table tr:hover {{ background-color: #26334D; }}
        
        .primary-col {{ font-weight: 600; color: #FFFFFF; line-height: 1.4; word-wrap: break-word; white-space: normal; }}
        
        /* Ajustement des largeurs pour inclure la colonne TAGS */
        th:nth-child(1), td:nth-child(1) {{ width: 180px; }} /* Acheteur */
        th:nth-child(2), td:nth-child(2) {{ width: 200px; }} /* Titre */
        th:nth-child(3), td:nth-child(3) {{ width: 150px; }} /* Tags/Domaines */
        th:nth-child(4), td:nth-child(4) {{ width: 90px; }}  /* Pub */
        th:nth-child(5), td:nth-child(5) {{ width: 90px; }}  /* Limite */
        th:nth-child(6), td:nth-child(6) {{ width: 110px; }} /* Budget */
        th:nth-child(7), td:nth-child(7) {{ width: 90px; }}  /* Caution */
        th:nth-child(8), td:nth-child(8) {{ width: 100px; }} /* Lieu */
        th:nth-child(9), td:nth-child(9) {{ width: 80px; }}  /* Action */

        .tag-badge {{
            background: #334155;
            color: #EF4444;
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: bold;
            border: 1px solid #475569;
            display: inline-block;
        }}

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
                <th>Acheteur</th>
                <th>Titre</th>
                <th>Domaines</th>
                <th>Pub.</th>
                <th>Échéance</th>
                <th>Budget</th>
                <th>Caution</th>
                <th>Lieu</th>
                <th>Lien</th>
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
# 5. INTERFACE PRINCIPALE
# ============================================
st.markdown('<h1 class="main-title">Intelligence & Veille Appels d\'Offres</h1>', unsafe_allow_html=True)

st.markdown(f"""
    <div class="intro-container">
        <div class="intro-text">
            Bienvenue sur votre portail de monitoring stratégique. Cette interface centralise l'ensemble des marchés publics 
            détectés. Les opportunités sont automatiquement analysées et classées pour optimiser votre réactivité.
            <br><br>
            🚀 <b>Comment utiliser ce tableau :</b>
            <ul>
                <li>Utilisez les <b>onglets</b> pour filtrer les nouveaux marchés de la veille ou les dossiers urgents.</li>
                <li>Cliquez sur n'importe quelle ligne pour <b>dérouler les détails techniques</b> et le résumé de l'offre.</li>
            </ul>
            <small>Date : {TODAY.strftime("%d/%m/%Y")}</small>
        </div>
    </div>
""", unsafe_allow_html=True)
if df_raw.empty:
    st.warning("Aucune donnée disponible.")
else:
    df_nouveaux = df_raw[df_raw['pub_dt'] == YESTERDAY]
    df_urgent = df_raw[(df_raw['lim_dt'].notna()) & (df_raw['lim_dt'] >= TODAY) & (df_raw['lim_dt'] <= URGENT_DEADLINE)]

    tab1, tab2, tab3 = st.tabs([
        f"📋 Tous ({len(df_raw)})", 
        f"✨ Nouveaux ({len(df_nouveaux)})", 
        f"🔥 Urgent ({len(df_urgent)})"
    ])

    with tab1: components.html(build_html_table(df_raw), height=850, scrolling=True)
    with tab2: components.html(build_html_table(df_nouveaux), height=850, scrolling=True)
    with tab3: components.html(build_html_table(df_urgent), height=850, scrolling=True)

# ============================================
# 6. SECTION CONTACT
# ============================================
st.markdown(f"""
    <div class="footer-contact">
        <h2>🚀 Vous voulez plus d'automatisations IA ?</h2>
        <p>Besoin d'un outil sur mesure, d'extraction de données complexe ou d'agents IA intelligents ?</p>
        <a href="mailto:anaslachhab666@gmail.com" class="contact-button">📩 Me contacter par Email</a>
    </div>
    <center><small style='color: #475569;'>Optimisé pour la prise de décision • © 2026 Strategy Monitor</small></center>
""", unsafe_allow_html=True)
