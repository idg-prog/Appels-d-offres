import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client
import io

# ============================================
# 1. CONFIGURATION
# ============================================
st.set_page_config(page_title="AO Monitoring", layout="wide")

# Simulation de la date système basée sur votre fichier (18 Mai 2026)
# Dans un cas réel, utilisez : TODAY = datetime.now().date()
TODAY = datetime(2026, 5, 18).date() 

# ============================================
# 2. DESIGN CSS (DARK SAAS)
# ============================================
st.markdown("""
    <style>
    .stApp { background-color: #0F172A; color: #F1F5F9; }
    [data-testid="stHeader"] { background: rgba(0,0,0,0); }
    
    /* Onglets style "Pills" blancs comme l'image */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #1E293B;
        border-radius: 8px;
        padding: 8px 20px;
        color: #94A3B8;
        border: 1px solid #334155;
    }
    .stTabs [data-baseweb="tab--active"] {
        background-color: #FFFFFF !important;
        color: #0F172A !important;
        border: none !important;
    }

    /* Table Design */
    .saas-table {
        width: 100%;
        border-collapse: collapse;
        background-color: #1E293B;
        border-radius: 12px;
        overflow: hidden;
        margin-top: 10px;
    }
    .saas-table th {
        text-align: left;
        padding: 15px 20px;
        color: #94A3B8;
        font-size: 0.8rem;
        text-transform: uppercase;
        border-bottom: 1px solid #334155;
    }
    .saas-table td {
        padding: 14px 20px;
        border-bottom: 1px solid #334155;
        font-size: 0.9rem;
    }
    .logo-circle {
        width: 30px; height: 30px; border-radius: 6px;
        background: #334155; display: inline-flex;
        align-items: center; justify-content: center;
        font-weight: bold; margin-right: 10px;
    }

    /* Detail Box */
    .detail-box {
        background-color: #1E293B;
        padding: 25px;
        border-radius: 12px;
        border: 1px solid #334155;
        margin-top: 20px;
    }
    .ai-box {
        background-color: #2E1065;
        border: 1px solid #7C3AED;
        padding: 15px; border-radius: 8px; margin-top: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

# ============================================
# 3. CHARGEMENT ET PARSING DES DATES
# ============================================
def clean_date(date_str):
    if not date_str or str(date_str) == "nan": return None
    date_str = str(date_str).lower().replace('juin', 'june').replace('mai', 'may')
    formats = ['%d/%m/%Y', '%Y-%m-%d', '%d %B %Y', '%d %b %Y']
    for fmt in formats:
        try: return datetime.strptime(date_str.split(' à')[0].strip(), fmt).date()
        except: continue
    return None

@st.cache_data
def get_data():
    # Ici, remplacez par votre appel Supabase
    # df = supabase.table("...").select("*").execute()
    # Pour l'exemple, on charge votre CSV
    data = """id,Title,Date de publication,Client,Localisation,Date de limite,Budget,Caution,Description Technique,URL
5,Creative Hubs Programme - British Council Morocco,,British Council,Morocco,12 June 2026,"£10,000 per year (up to £30,000 total over 3 years)",,Description hubs...
6,"Achat et Livraison de 4 560 plants d'olivier",,Karama Solidarity Maroc (KSM),Sidi Kacem,21/05/2026,,,"Achat oliviers..."
7,Evaluation finale NAFASS Casablanca,11/05/2026,Association La Bienfaisance,,31/05/2026,100000 MAD TTC,Non mentionné,"Evaluation formation..."
"""
    df = pd.read_csv(io.StringIO(data))
    df['pub_dt'] = df['Date de publication'].apply(clean_date)
    df['lim_dt'] = df['Date de limite'].apply(clean_date)
    df.fillna("", inplace=True)
    return df

df = get_data()

# Logique des filtres temporels
yesterday = TODAY - timedelta(days=1)
three_days_limit = TODAY + timedelta(days=3)

df_tout = df
df_nouveaux = df[df['pub_dt'] == yesterday]
df_urgent = df[(df['lim_dt'] >= TODAY) & (df['lim_dt'] <= three_days_limit)]

# ============================================
# 4. INTERFACE
# ============================================
st.title("📑 Tableau de Bord des Appels d'Offres")
st.markdown("""
    Bienvenue sur votre espace de veille. Ce tableau récapitule les derniers marchés publics détectés. 
    Consultez les onglets pour voir les nouveautés ou les urgences, et sélectionnez une ligne pour le détail.
""")

t1, t2, t3 = st.tabs([f"Tout ({len(df_tout)})", f"Nouveaux ({len(df_nouveaux)})", f"Urgent ({len(df_urgent)})"])

def render_table(data_df):
    if data_df.empty:
        st.info("Aucun résultat pour cette catégorie.")
        return None
    
    html = """<table class="saas-table">
    <thead><tr><th>Acheteur</th><th>Titre</th><th>Publication</th><th>Limite</th><th>Budget</th></tr></thead>
    <tbody>"""
    
    for _, row in data_df.head(10).iterrows():
        init = row['Client'][0] if row['Client'] else "?"
        html += f"""
        <tr>
            <td><div class="logo-circle">{init}</div>{row['Client']}</td>
            <td style="font-weight:500;">{row['Title'][:70]}...</td>
            <td style="color:#94A3B8;">{row['Date de publication']}</td>
            <td style="color:#EF4444; font-weight:600;">{row['Date de limite']}</td>
            <td style="color:#10B981; font-weight:600;">{row['Budget']}</td>
        </tr>"""
    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)
    return data_df

with t1: current_view = render_table(df_tout)
with t2: current_view = render_table(df_nouveaux)
with t3: current_view = render_table(df_urgent)

# ============================================
# 5. DÉTAILS EN DESSOUS
# ============================================
if current_view is not None:
    st.write("")
    selected_title = st.selectbox("👉 Détails techniques de l'offre :", current_view['Title'].tolist())
    item = current_view[current_view['Title'] == selected_title].iloc[0]
    
    st.markdown(f"""
    <div class="detail-box">
        <div style="display: flex; justify-content: space-between; align-items: start;">
            <h2 style="margin:0; color:#FFF;">{item['Title']}</h2>
            <a href="{item['URL']}" target="_blank" style="background:#EF4444; color:white; padding:8px 15px; border-radius:6px; text-decoration:none; font-weight:bold;">Lien Officiel 🔗</a>
        </div>
        <p style="color:#94A3B8; margin-top:8px;">🏛️ {item['Client']} | 📍 {item['Localisation']}</p>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; margin: 20px 0;">
            <div style="background:#334155; padding:12px; border-radius:8px;"><small>Budget</small><br><b>{item['Budget']}</b></div>
            <div style="background:#334155; padding:12px; border-radius:8px;"><small>Caution</small><br><b>{item['Caution']}</b></div>
            <div style="background:#334155; padding:12px; border-radius:8px;"><small>Date Limite</small><br><b>{item['Date de limite']}</b></div>
        </div>

        <h4 style="color:#FFF; border-left: 3px solid #EF4444; padding-left:10px;">Description Technique</h4>
        <p style="color:#CBD5E1; line-height:1.6;">{item['Description Technique']}</p>

        <div class="ai-box">
            <span style="color:#A78BFA; font-weight:bold; font-size:0.8rem;">✨ RÉSUMÉ IA</span>
            <p style="margin-top:8px; font-size:0.9rem; color:#E2E8F0;">
                Opportunité majeure pour <b>{item['Client']}</b>. Le projet nécessite une expertise pointue. 
                Vérifiez l'éligibilité avant le {item['Date de limite']}.
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
