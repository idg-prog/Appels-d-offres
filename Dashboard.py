import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client

# ============================================
# 1. CONFIGURATION ET CONNEXION
# ============================================
st.set_page_config(page_title="AO Monitoring", layout="wide")

# Date de référence pour le test (18 Mai 2026)
# En production, utilisez : TODAY = datetime.now().date()
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
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #1E293B; border-radius: 8px; padding: 8px 20px;
        color: #94A3B8; border: 1px solid #334155;
    }
    .stTabs [data-baseweb="tab--active"] {
        background-color: #FFFFFF !important; color: #0F172A !important; border: none !important;
    }
    .saas-table { width: 100%; border-collapse: collapse; background-color: #1E293B; border-radius: 12px; overflow: hidden; }
    .saas-table th { text-align: left; padding: 15px 20px; color: #94A3B8; font-size: 0.8rem; text-transform: uppercase; border-bottom: 1px solid #334155; }
    .saas-table td { padding: 14px 20px; border-bottom: 1px solid #334155; font-size: 0.9rem; }
    .logo-circle { width: 30px; height: 30px; border-radius: 6px; background: #475569; display: inline-flex; align-items: center; justify-content: center; font-weight: bold; margin-right: 10px; color: white; }
    .detail-box { background-color: #1E293B; padding: 25px; border-radius: 12px; border: 1px solid #334155; margin-top: 20px; }
    .ai-box { background-color: #2E1065; border: 1px solid #7C3AED; padding: 15px; border-radius: 8px; margin-top: 15px; }
    </style>
    """, unsafe_allow_html=True)

# ============================================
# 3. TRAITEMENT DES DONNÉES
# ============================================
def clean_date_series(s):
    """Transforme une série de texte en objets date proprement"""
    s = s.astype(str).str.lower().str.replace('juin', 'june').str.replace('mai', 'may')
    s = s.str.split(' à').str[0].str.strip()
    return pd.to_datetime(s, errors='coerce', dayfirst=True).dt.date

@st.cache_data(ttl=600)
def get_data():
    client = init_supabase()
    response = client.table("Tenders Clean Data").select("*").execute()
    df = pd.DataFrame(response.data)
    
    if df.empty:
        return df

    # Colonnes techniques pour le filtrage (Gardent le type Date ou NaT)
    df['pub_dt'] = clean_date_series(df['Date de publication'])
    df['lim_dt'] = clean_date_series(df['Date de limite'])
    
    # On ne fait SURTOUT PAS fillna("") ici pour éviter l'erreur de type
    return df

df = get_data()

# Filtrage sécurisé (les NaT sont ignorés automatiquement dans la comparaison)
yesterday = TODAY - timedelta(days=1)
three_days_limit = TODAY + timedelta(days=3)

df_tout = df
df_nouveaux = df[df['pub_dt'] == yesterday]
df_urgent = df[(df['lim_dt'].notna()) & (df['lim_dt'] >= TODAY) & (df['lim_dt'] <= three_days_limit)]

# ============================================
# 4. INTERFACE
# ============================================
st.title("📊 Suivi des Appels d'Offres")

t1, t2, t3 = st.tabs([f"Tout ({len(df_tout)})", f"Nouveaux ({len(df_nouveaux)})", f"Urgent ({len(df_urgent)})"])

def render_table(data_df):
    if data_df.empty:
        st.info("Aucun résultat pour le moment.")
        return None
    
    html = """<table class="saas-table">
    <thead><tr><th>Acheteur</th><th>Titre</th><th>Publication</th><th>Limite</th><th>Budget</th></tr></thead>
    <tbody>"""
    
    for _, row in data_df.head(15).iterrows():
        # Gestion sécurisée des valeurs vides pour l'affichage
        buyer = str(row['Client']) if pd.notna(row['Client']) else ""
        init = buyer[0] if buyer else "?"
        budget = str(row['Budget']) if pd.notna(row['Budget']) else "-"
        date_pub = str(row['Date de publication']) if pd.notna(row['Date de publication']) else "-"
        date_lim = str(row['Date de limite']) if pd.notna(row['Date de limite']) else "-"
        
        html += f"""
        <tr>
            <td><div class="logo-circle">{init}</div>{buyer}</td>
            <td style="font-weight:500;">{str(row['Title'])[:75]}...</td>
            <td style="color:#94A3B8;">{date_pub}</td>
            <td style="color:#EF4444; font-weight:600;">{date_lim}</td>
            <td style="color:#10B981; font-weight:600;">{budget}</td>
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
    
    # Remplissage des champs vides juste pour l'affichage du bloc détail
    item = item.fillna("Non spécifié")

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
                Analyse IA : Ce marché pour <b>{item['Client']}</b> présente des exigences spécifiques. 
                Veuillez préparer votre réponse avant le {item['Date de limite']}.
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
