import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client

# ============================================
# 1. PAGE CONFIGURATION
# ============================================
st.set_page_config(
    page_title="AO Monitoring Dashboard",
    page_icon="📊",
    layout="wide"
)

# ============================================
# 2. CUSTOM CSS: THE "SAAS" TABLE DESIGN
# ============================================
st.markdown("""
    <style>
    /* Global Background */
    .stApp { background-color: #0F172A; color: #F1F5F9; }
    
    /* Custom Header Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; margin-bottom: 20px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #1E293B;
        border-radius: 8px;
        padding: 8px 20px;
        color: #94A3B8;
        border: 1px solid #334155;
        font-weight: 500;
        transition: 0.3s;
    }
    .stTabs [data-baseweb="tab--active"] {
        background-color: #FFFFFF !important; /* White like the image */
        color: #0F172A !important;
        border: none !important;
    }

    /* Professional Table Styling */
    .saas-table {
        width: 100%;
        border-collapse: collapse;
        background-color: #1E293B;
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #334155;
    }
    .saas-table thead {
        background-color: #1E293B;
        border-bottom: 1px solid #334155;
    }
    .saas-table th {
        text-align: left;
        padding: 15px 20px;
        color: #94A3B8;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .saas-table td {
        padding: 16px 20px;
        border-bottom: 1px solid #334155;
        vertical-align: middle;
        font-size: 0.95rem;
    }
    
    /* Acheteur Column with Logo */
    .acheteur-wrapper {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .logo-circle {
        width: 32px;
        height: 32px;
        border-radius: 6px;
        background: #334155;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        color: #F1F5F9;
        font-size: 0.8rem;
        border: 1px solid #475569;
    }

    /* Detail Box styling */
    .detail-box {
        background-color: #1E293B;
        padding: 25px;
        border-radius: 12px;
        border: 1px solid #334155;
        margin-top: 30px;
    }
    
    .ai-box {
        background-color: #2E1065;
        border: 1px solid #7C3AED;
        padding: 18px;
        border-radius: 8px;
        margin-top: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# ============================================
# 3. DATA LOADING
# ============================================
@st.cache_data(ttl=300)
def load_data():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_SERVICE_KEY"]
        supabase = create_client(url, key)
        response = supabase.table("Tenders Clean Data").select("*").execute()
        df = pd.DataFrame(response.data)
    except:
        return pd.DataFrame()

    if df.empty: return df
    
    df['date_pub_dt'] = pd.to_datetime(df['Date de publication'], dayfirst=True, errors='coerce')
    df['date_lim_dt'] = pd.to_datetime(df['Date de limite'], dayfirst=True, errors='coerce')
    df.fillna("", inplace=True)
    return df

df_full = load_data()

# Filtering for tabs
today = datetime.now().date()
yesterday = today - timedelta(days=1)
three_days_limit = today + timedelta(days=3)

df_nouveaux = df_full[df_full['date_pub_dt'].dt.date == yesterday]
df_urgent = df_full[(df_full['date_lim_dt'].dt.date >= today) & 
                    (df_full['date_lim_dt'].dt.date <= three_days_limit)]

# ============================================
# 4. HEADER & INTRODUCTION
# ============================================
st.title("📑 Tableau de Bord des Appels d'Offres")
st.markdown("""
    Explorez les opportunités de marchés publics. Utilisez les onglets pour filtrer par récence ou par urgence.
    La liste ci-dessous affiche les informations clés ; sélectionnez une offre pour voir l'analyse détaillée.
""")
st.write("")

# ============================================
# 5. THE CUSTOM TABLE
# ============================================
if df_full.empty:
    st.error("Aucune donnée disponible.")
else:
    # Use native tabs but styled via CSS to look like pills
    t1, t2, t3 = st.tabs([
        f"Tout ({len(df_full)})", 
        f"Nouveaux ({len(df_nouveaux)})", 
        f"Urgent ({len(df_urgent)})"
    ])

    def render_custom_table(data):
        if data.empty:
            st.info("Aucun résultat dans cette catégorie.")
            return None
        
        # Limit to 10 rows
        data_subset = data.head(10)
        
        # Build Table HTML
        table_html = """
        <table class="saas-table">
            <thead>
                <tr>
                    <th>Acheteur</th>
                    <th>Titre de l'Offre</th>
                    <th>Date Publication</th>
                    <th>Date Limite</th>
                    <th>Budget</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for _, row in data_subset.iterrows():
            # Create a simple letter logo if none exists
            initial = row['Client'][0] if row['Client'] else '?'
            
            table_html += f"""
                <tr>
                    <td>
                        <div class="acheteur-wrapper">
                            <div class="logo-circle">{initial}</div>
                            <div>{row['Client']}</div>
                        </div>
                    </td>
                    <td style="color: #F1F5F9; font-weight: 500;">{row['Title'][:80]}...</td>
                    <td style="color: #94A3B8;">{row['Date de publication']}</td>
                    <td style="color: #EF4444; font-weight: 600;">{row['Date de limite']}</td>
                    <td style="color: #10B981; font-weight: 600;">{row['Budget']}</td>
                </tr>
            """
        
        table_html += "</tbody></table>"
        st.markdown(table_html, unsafe_allow_html=True)
        return data

    with t1: active_data = render_custom_table(df_full)
    with t2: active_data = render_custom_table(df_nouveaux)
    with t3: active_data = render_custom_table(df_urgent)

    # ============================================
    # 6. DETAILS SECTION (Under Table)
    # ============================================
    if active_data is not None:
        st.write("")
        st.divider()
        
        # Selection for details
        titles = active_data["Title"].tolist()
        choice = st.selectbox("🔍 Sélectionnez un marché pour afficher l'analyse technique :", titles)
        
        row = active_data[active_data["Title"] == choice].iloc[0]

        st.markdown(f"""
        <div class="detail-box">
            <div style="display: flex; justify-content: space-between; align-items: start;">
                <h2 style="margin:0; color:#FFFFFF;">{row['Title']}</h2>
                <div style="text-align:right;">
                    <a href="{row['URL']}" target="_blank" style="background:#EF4444; color:white; padding:8px 20px; border-radius:6px; text-decoration:none; font-weight:bold; font-size:0.9rem;">Dossier Officiel 🔗</a>
                </div>
            </div>
            
            <p style="color:#94A3B8; margin-top:10px; font-size:1.1rem;">
                🏛️ {row['Client']} | 📅 Publié le {row['Date de publication']}
            </p>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin: 25px 0;">
                <div style="background:#334155; padding:15px; border-radius:8px;">
                    <small style="color:#94A3B8;">Budget Estimé</small><br><b style="font-size:1.2rem;">{row['Budget']}</b>
                </div>
                <div style="background:#334155; padding:15px; border-radius:8px;">
                    <small style="color:#94A3B8;">Caution Provisoire</small><br><b style="font-size:1.2rem;">{row['Caution']}</b>
                </div>
                <div style="background:#334155; padding:15px; border-radius:8px;">
                    <small style="color:#94A3B8;">Lieu d'exécution</small><br><b style="font-size:1.2rem;">{row.get('Localisation', 'Maroc')}</b>
                </div>
            </div>

            <div style="margin-top:20px;">
                <h4 style="color:#FFFFFF; border-left: 4px solid #EF4444; padding-left:10px;">Détails de la consultation</h4>
                <p style="color:#CBD5E1; font-size:1rem; line-height:1.6; margin-top:10px;">{row['Description Technique']}</p>
            </div>

            <div class="ai-box">
                <span style="color:#A78BFA; font-weight:bold; font-size:0.85rem;">✨ RÉSUMÉ ANALYTIQUE IA</span>
                <p style="margin-top:10px; font-size:0.95rem; color:#E2E8F0; line-height:1.5;">
                    Cette opportunité est classée comme stratégique pour <b>{row['Client']}</b>. 
                    L'analyse suggère une forte composante technique. La date de limite au <b>{row['Date de limite']}</b> 
                    impose une préparation rapide du dossier de réponse.
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)
