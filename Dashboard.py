import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from datetime import datetime, timedelta
from supabase import create_client

# ============================================
# 1. CONFIGURATION ET RÉFÉRENCE TEMPORELLE
# ============================================
st.set_page_config(page_title="AO Strategic Monitoring", layout="wide")

TODAY = datetime.today().date()
YESTERDAY = TODAY - timedelta(days=1)
URGENT_DEADLINE = TODAY + timedelta(days=3)

# ============================================
# 2. CSS PERSONNALISÉ
# ============================================
st.markdown("""
    <style>
    .stApp { background-color: #0F172A; color: #F1F5F9; }

    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background-color: transparent;
        margin-bottom: 10px;
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
    .stTabs [data-baseweb="tab--active"] {
        background-color: #EF4444 !important;
        color: #FFFFFF !important;
        border: 1px solid #EF4444 !important;
    }
    
    .main-title { font-size: 2.2rem; font-weight: 800; color: #FFFFFF; margin-bottom: 10px; }
    .intro-container {
        background: #1E293B;
        padding: 15px;
        border-radius: 12px;
        border-left: 5px solid #EF4444;
        margin-bottom: 20px;
    }

    /* Style pour les widgets de filtrage */
    .stMultiSelect [data-baseweb="tag"] {
        background-color: #EF4444 !important;
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

        # === NEW: CLEANING EMPTY ROWS ===
        # 1. Remove rows where the 'Title' column is missing (NaN)
        df = df.dropna(subset=['Title', 'Client'], how='all')
        
        # 2. Remove rows where the 'Title' is literally the string "EMPTY" or just whitespace
        df = df[df['Title'].astype(str).str.strip().str.upper() != "EMPTY"]
        df = df[df['Title'].astype(str).str.strip() != ""]
        # ================================

        df['pub_dt'] = clean_date_series(df['Date de publication'])
        df['lim_dt'] = clean_date_series(df['Date de limite'])
        df['Tags'] = df['Tags'].fillna('Non classé')
        df['Localisation'] = df['Localisation'].fillna('Maroc')
        return df
    except Exception as e:
        st.error(f"Erreur Supabase : {e}")
        return pd.DataFrame()
        
df_raw = get_data()
# Sort by publication date (newest first)
df_raw = df_raw.sort_values(
    by='pub_dt',
    ascending=False,
    na_position='last'
)

# ============================================
# 4. FONCTION DE FILTRAGE STREAMLIT
# ============================================
def apply_filters(df, key_prefix):
    col1, col2 = st.columns(2)
    
    # Extraire les domaines uniques (gestion des tags multiples séparés par des virgules)
    all_tags = set()
    for t in df['Tags'].unique():
        for tag in str(t).split(','):
            all_tags.add(tag.strip())
    
    with col1:
        selected_tags = st.multiselect(
            "🔍 Filtrer par Domaine", 
            options=sorted(list(all_tags)),
            key=f"{key_prefix}_tags"
        )
    
    with col2:
        selected_loc = st.multiselect(
            "📍 Filtrer par Lieu", 
            options=sorted(df['Localisation'].unique().tolist()),
            key=f"{key_prefix}_loc"
        )
    
    # Logique de filtrage
    filtered_df = df.copy()
    if selected_tags:
        # On garde la ligne si au moins un des tags sélectionnés est présent
        pattern = '|'.join(selected_tags)
        filtered_df = filtered_df[filtered_df['Tags'].str.contains(pattern, case=False, na=False)]
    
    if selected_loc:
        filtered_df = filtered_df[filtered_df['Localisation'].isin(selected_loc)]
        
    return filtered_df

# ============================================
# 5. GÉNÉRATION DU TABLEAU HTML
# ============================================
def build_html_table(data_df):
    if data_df.empty:
        return "<div style='color:#94A3B8; text-align:center; padding:50px; font-family:sans-serif; background:#1E293B; border-radius:12px;'>Aucune opportunité ne correspond à vos filtres.</div>"

    table_rows = ""
    for idx, row in data_df.iterrows():
        def val(col):
            v = row.get(col, "-")
            return v if pd.notna(v) and str(v).lower() != "nan" else "-"

        client, title, pub, lim = val('Client'), val('Title'), val('Date de publication'), val('Date de limite')
        budget, caution, loc, tags, desc, url = val('Budget'), val('Caution'), val('Localisation'), val('Tags'), val('Description Technique'), val('URL')
        link = url if str(url).startswith('http') else f"https://{url}" if url != "-" else "#"

        table_rows += f"""
        <tr onclick="toggleDetails({idx})" style="cursor: pointer;">
            <td><span class="tag-badge">{tags}</span></td>
            <td class="primary-col"><span class="expand-icon">▶</span> {title}</td>
            <td class="muted">{client}</td>
            <td class="muted">{loc}</td>
            <td class="muted">{pub}</td>
            <td class="urgent">{lim}</td>
            <td class="success">{budget}</td>
            <td class="muted">{caution}</td>
        </tr>
        <tr id="details-{idx}" class="details-row" style="display: none;">
            <td colspan="8">
                <div class="expanded-content">
                    <div class="expanded-section"><span class="label">📌 Descriptif</span><div class="content-text">{title}</div></div>
                    <div class="expanded-section"><span class="label">🛠️ Analyse Technique (IA)</span><div class="content-text">{desc}</div></div>
                    <div style="margin-top:20px;"><a class="btn-link" href="{link}" target="_blank">Ouvrir le document source 🔗</a></div>
                </div>
            </td>
        </tr>
        """

    return f"""
    <style>
        body {{ background-color: #0F172A; color: #F1F5F9; font-family: 'Inter', sans-serif; margin: 0; padding: 0; overflow-y: auto; }}
        .saas-table {{ width: 100%; border-collapse: collapse; background-color: #1E293B; table-layout: fixed; }}
        .saas-table thead th {{ position: sticky; top: 0; background-color: #111827; z-index: 10; text-align: left; padding: 12px 10px; color: #94A3B8; font-size: 9px; text-transform: uppercase; border-bottom: 2px solid #475569; }}
        .saas-table td {{ padding: 10px; border-bottom: 1px solid #334155; font-size: 11px; color: #CBD5E1; vertical-align: top; word-wrap: break-word; }}
        .saas-table tr:hover {{ background-color: #26334D; }}
        
        th:nth-child(1), td:nth-child(1) {{ width: 110px; }}
        th:nth-child(2), td:nth-child(2) {{ width: 220px; }}
        th:nth-child(3), td:nth-child(3) {{ width: 140px; }}
        th:nth-child(4), td:nth-child(4) {{ width: 100px; }}
        th:nth-child(5), td:nth-child(5) {{ width: 75px; }}
        th:nth-child(6), td:nth-child(6) {{ width: 75px; }}
        th:nth-child(7), td:nth-child(7) {{ width: 100px; }}
        th:nth-child(8), td:nth-child(8) {{ width: 70px; }}

        .tag-badge {{ background: #0F172A; color: #EF4444; padding: 2px 5px; border-radius: 4px; font-size: 9px; font-weight: bold; border: 1px solid #EF4444; display: inline-block; }}
        .expand-icon {{ color: #EF4444; font-size: 8px; margin-right: 3px; }}
        .urgent {{ color: #F87171; font-weight: bold; }}
        .success {{ color: #10B981; font-weight: bold; }}
        .muted {{ color: #94A3B8; font-size: 10.5px; }}
        .expanded-content {{ padding: 20px 30px; border-left: 4px solid #EF4444; background: #111827; }}
        .label {{ color: #94A3B8; text-transform: uppercase; font-size: 9px; font-weight: bold; }}
        .content-text {{ font-size: 12.5px; margin-top: 5px; color: #E2E8F0; line-height: 1.5; white-space: normal; }}
        .btn-link {{ background-color: #EF4444; color: white !important; padding: 8px 16px; border-radius: 5px; text-decoration: none; font-size: 11px; font-weight: bold; display: inline-block; }}
    </style>
    <table class="saas-table">
        <thead><tr><th>Domaines</th><th>Titre</th><th>Acheteur</th><th>Lieu</th><th>Pub.</th><th>Échéance</th><th>Budget</th><th>Caution</th></tr></thead>
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
# 6. INTERFACE PRINCIPALE
# ============================================
st.markdown('<h1 class="main-title">📊 Intelligence & Veille Appels d\'Offres</h1>', unsafe_allow_html=True)

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
    st.warning("Aucune donnée trouvée dans Supabase.")
else:
    # Définition des sous-ensembles
    df_nouveaux_base = df_raw[df_raw['pub_dt'] == YESTERDAY]
    df_urgent_base = df_raw[(df_raw['lim_dt'].notna()) & (df_raw['lim_dt'] >= TODAY) & (df_raw['lim_dt'] <= URGENT_DEADLINE)]

    tab1, tab2, tab3 = st.tabs([
        f"📋 Tous ({len(df_raw)})", 
        f"✨ Nouveaux ({len(df_nouveaux_base)})", 
        f"🔥 Urgent ({len(df_urgent_base)})"
    ])

    with tab1:
        f_df1 = apply_filters(df_raw, "all")
        components.html(build_html_table(f_df1), height=800, scrolling=True)

    with tab2:
        f_df2 = apply_filters(df_nouveaux_base, "new")
        components.html(build_html_table(f_df2), height=800, scrolling=True)

    with tab3:
        f_df3 = apply_filters(df_urgent_base, "urgent")
        components.html(build_html_table(f_df3), height=800, scrolling=True)

# ============================================
# 7. FOOTER CONTACT
# ============================================
st.markdown("""
    <style>
    .footer-contact {
        background-color: #1E293B;
        padding: 25px;
        border-radius: 12px;
        text-align: center;
        margin-top: 50px;
        border: 1px solid #334155;
    }
    .contact-button {
        display: inline-block;
        background-color: #3B82F6;
        color: white !important;
        padding: 10px 20px;
        border-radius: 8px;
        text-decoration: none;
        font-weight: bold;
        margin-top: 15px;
        transition: background-color 0.3s;
    }
    .contact-button:hover {
        background-color: #2563EB;
    }
    </style>
""", unsafe_allow_html=True)

# 2. Your corrected Markdown
st.markdown(f"""
    <div class="footer-contact">
        <h3 style="color:white; margin-top:0; margin-bottom:10px;">🚀 Vous voulez plus d'automatisations IA ?</h3>
        <p style="color:#94A3B8; font-size:0.95rem; margin-bottom:15px;">
            Besoin d'un outil sur mesure ou d'une extraction de données complexe ?
        </p>
        <a href="mailto:anaslachhab666@gmail.com" class="contact-button">Me contacter par Email</a>
    </div>
    <div style="text-align: center; padding: 20px 0;">
        <small style="color: #475569;">© 2026 Anas Lachhab</small>
    </div>
""", unsafe_allow_html=True)
