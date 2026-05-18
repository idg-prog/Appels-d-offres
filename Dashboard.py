import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client

# ============================================
# 1. CONFIGURATION ET CONNEXION
# ============================================
st.set_page_config(page_title="AO Monitoring", layout="wide")

# Simulation de la date système (18 Mai 2026)
TODAY = datetime(2026, 5, 18).date() 

@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)

# ============================================
# 2. DESIGN CSS (DARK SAAS)
# ============================================
st.markdown("""
    <style>
    .stApp { background-color: #0F172A; color: #F1F5F9; }
    
    /* Onglets style "Pills" blancs */
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
        background: #475569; display: inline-flex;
        align-items: center; justify-content: center;
        font-weight: bold; margin-right: 10px; color: white;
    }

    .detail-box {
        background-color: #1E293B; padding: 25px;
        border-radius: 12px; border: 1px solid #334155; margin-top: 20px;
    }
    .ai-box {
        background-color: #2E1065; border: 1px solid #7C3AED;
        padding: 15px; border-radius: 8px; margin-top: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

# ============================================
# 3. TRAITEMENT DES DONNÉES
# ============================================
def clean_date(date_str):
    if not date_str or str(date_str).lower() in ["nan", "none", ""]: return None
    date_str = str(date_str).lower().replace('juin', 'june').replace('mai', 'may')
    formats = ['%d/%m/%Y', '%Y-%m-%d', '%d %B %Y', '%d %b %Y']
    for fmt in formats:
        try: return datetime.strptime(date_str.split(' à')[0].strip(), fmt).date()
        except: continue
    return None

@st.cache_data(ttl=600)
def get_data():
    client = init_supabase()
    response = client.table("Tenders Clean Data").select("*").execute()
    df = pd.DataFrame(response.data)
    
    if df.empty:
        return df

    # Conversion des colonnes de dates pour les filtres
    df['pub_dt'] = df['Date de publication'].apply(clean_date)
    df['lim_dt'] = df['Date de limite'].apply(clean_date)
    
    # Remplacement sécurisé des NaN par du texte vide (évite le TypeError)
    for col in df.columns:
        df[col] = df[col].astype(object).fillna("")
        
    return df

try:
    df = get_data()
except Exception as e:
    st.error(f"Erreur de chargement : {e}")
    st.stop()

# Filtres temporels
yesterday = TODAY - timedelta(days=1)
three_days_limit = TODAY + timedelta(days=3)

df_tout = df
# On utilise .apply car après fillna(""), ce sont des objets
df_nouveaux = df[df['pub_dt'] == yesterday]
df_urgent = df[(df['lim_dt'] != "") & (df['lim_dt'] >= TODAY) & (df['lim_dt'] <= three_days_limit)]

# ============================================
# 4. INTERFACE
# ============================================
st.title("📊 Suivi des Appels d'Offres")
st.markdown("Consultez les dernières opportunités de marchés publics extraites en temps réel.")

t1, t2, t3 = st.tabs([f"Tout ({len(df_tout)})", f"Nouveaux ({len(df_nouveaux)})", f"Urgent ({len(df_urgent)})"])

def render_table(data_df):
    if data_df.empty:
        st.info("Aucun résultat pour le moment.")
        return None
    
    html = """<table class="saas-table">
    <thead><tr><th>Acheteur</th><th>Titre</th><th>Publication</th><th>Limite</th><th>Budget</th></tr></thead>
    <tbody>"""
    
    for _, row in data_df.head(10).iterrows():
        client_name = str(row['Client'])
        init = client_name[0] if client_name else "?"
        html += f"""
        <tr>
            <td><div class="logo-circle">{init}</div>{client_name}</td>
            <td style="font-weight:500;">{str(row['Title'])[:75]}...</td>
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
# 5. DÉTAILS
# ============================================
if current_view is not None and not current_view.empty:
    st.write("")
    selected_title = st.selectbox("🔍 Analyse détaillée de l'offre :", current_view['Title'].tolist())
    item = current_view[current_view['Title'] == selected_title].iloc[0]
    
    st.markdown(f"""
    <div class="detail-box">
        <div style="display: flex; justify-content: space-between; align-items: start;">
            <h2 style="margin:0; color:#FFF;">{item['Title']}</h2>
            <a href="{item['URL']}" target="_blank" style="background:#EF4444; color:white; padding:8px 18px; border-radius:6px; text-decoration:none; font-weight:bold; font-size:0.9rem;">Consulter le document 🔗</a>
        </div>
        <p style="color:#94A3B8; margin-top:8px; font-size:1.1rem;">🏛️ {item['Client']} | 📍 {item['Localisation']}</p>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; margin: 20px 0;">
            <div style="background:#334155; padding:15px; border-radius:8px;"><small style="color:#94A3B8;">Budget</small><br><b style="font-size:1.1rem;">{item['Budget']}</b></div>
            <div style="background:#334155; padding:15px; border-radius:8px;"><small style="color:#94A3B8;">Caution</small><br><b style="font-size:1.1rem;">{item['Caution']}</b></div>
            <div style="background:#334155; padding:15px; border-radius:8px;"><small style="color:#94A3B8;">Date Limite</small><br><b style="font-size:1.1rem;">{item['Date de limite']}</b></div>
        </div>

        <h4 style="color:#FFF; border-left: 4px solid #EF4444; padding-left:12px; margin-bottom:10px;">Description Technique</h4>
        <p style="color:#CBD5E1; line-height:1.6; font-size:0.95rem;">{item['Description Technique']}</p>

        <div class="ai-box">
            <span style="color:#A78BFA; font-weight:bold; font-size:0.8rem;">✨ RÉSUMÉ ANALYTIQUE IA</span>
            <p style="margin-top:10px; font-size:0.92rem; color:#E2E8F0; line-height:1.5;">
                Analyse en cours pour le compte de <b>{item['Client']}</b>. Ce marché présente des spécifications techniques 
                importantes. Assurez-vous de soumettre votre dossier avant le {item['Date de limite']}.
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
