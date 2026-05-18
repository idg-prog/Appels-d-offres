import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client

# ============================================
# 1. PAGE CONFIGURATION
# ============================================
st.set_page_config(
    page_title="AO Dashboard",
    page_icon="📊",
    layout="wide"
)

# ============================================
# 2. SEPARATED CSS (Fixes the SyntaxError)
# ============================================
st.markdown("""
    <style>
    .stApp { background-color: #0F172A; color: #F1F5F9; }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #1E293B !important;
        border-right: 1px solid #334155;
    }

    /* Tabs with Red Underline */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #1E293B;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        color: #94A3B8;
        border: none;
    }
    .stTabs [data-baseweb="tab--active"] {
        background-color: #1E293B !important;
        color: #FFFFFF !important;
        border-bottom: 3px solid #EF4444 !important;
    }

    /* Details Panel Styling */
    .detail-box {
        background-color: #1E293B;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #334155;
        margin-top: 10px;
    }
    
    .urgent-pill {
        background-color: rgba(239, 68, 68, 0.1);
        color: #F87171;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        border: 1px solid rgba(239, 68, 68, 0.2);
    }
    
    .ai-summary {
        background-color: #2E1065;
        border: 1px solid #7C3AED;
        padding: 15px;
        border-radius: 8px;
        margin-top: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

# ============================================
# 3. DATA LOADING & TAB LOGIC
# ============================================
@st.cache_data(ttl=300)
def load_data():
    # Attempt connection to Supabase (using your secrets)
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_SERVICE_KEY"]
        supabase = create_client(url, key)
        response = supabase.table("Tenders Clean Data").select("*").execute()
        df = pd.DataFrame(response.data)
    except:
        # Fallback if Supabase fails (optional: remove this in production)
        st.warning("Connexion Supabase échouée, vérifiez vos secrets.")
        return pd.DataFrame()

    if df.empty: return df

    # Convert dates for filtering
    # We use dayfirst=True because Moroccan dates are usually DD/MM/YYYY
    df['date_pub_dt'] = pd.to_datetime(df['Date de publication'], dayfirst=True, errors='coerce')
    df['date_lim_dt'] = pd.to_datetime(df['Date de limite'], dayfirst=True, errors='coerce')
    df.fillna("", inplace=True)
    return df

df_full = load_data()

if df_full.empty:
    st.error("Aucune donnée trouvée.")
    st.stop()

# --- Tab Filtering Logic ---
today = datetime.now().date()
yesterday = today - timedelta(days=1)
three_days_limit = today + timedelta(days=3)

# 1. Nouveaux: Published yesterday
df_nouveaux = df_full[df_full['date_pub_dt'].dt.date == yesterday]

# 2. Urgent: Deadline in next 3 days
df_urgent = df_full[(df_full['date_lim_dt'].dt.date >= today) & 
                    (df_full['date_lim_dt'].dt.date <= three_days_limit)]

# ============================================
# 4. SIDEBAR
# ============================================
with st.sidebar:
    st.title("🔎 Filtres")
    search = st.text_input("Mots clés (Titre, Client...)")
    clients_list = sorted(df_full["Client"].unique())
    sel_clients = st.multiselect("Filtrer par Acheteur", clients_list)

# Global filtering based on Sidebar
def apply_sidebar(d):
    if search:
        d = d[d.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
    if sel_clients:
        d = d[d["Client"].isin(sel_clients)]
    return d

# ============================================
# 5. MAIN TABS & TABLE
# ============================================
t1, t2, t3 = st.tabs([
    f"Tous ({len(apply_sidebar(df_full))})", 
    f"Nouveaux ({len(apply_sidebar(df_nouveaux))})", 
    f"Urgent - 3 jours ({len(apply_sidebar(df_urgent))})"
])

# Define exact columns requested
cols_show = ["Title", "Client", "Date de limite", "Date de publication", 
             "Description Technique", "Budget", "Caution", "URL"]

# Function to render table
def show_table(data):
    filtered = apply_sidebar(data)
    if filtered.empty:
        st.info("Aucun résultat.")
        return None
    
    # height=450 is roughly 10 rows in Streamlit
    st.dataframe(
        filtered[cols_show], 
        use_container_width=True, 
        height=450, 
        hide_index=True,
        column_config={"URL": st.column_config.LinkColumn("Lien Document")}
    )
    return filtered

with t1: active_data = show_table(df_full)
with t2: active_data = show_table(df_nouveaux)
with t3: active_data = show_table(df_urgent)

# ============================================
# 6. DETAILS SECTION (Under Table)
# ============================================
if active_data is not None:
    st.divider()
    
    # Dropdown to select which AO to see in detail
    titles = active_data["Title"].tolist()
    choice = st.selectbox("👉 Sélectionnez un appel d'offre pour voir les détails :", titles)
    
    row = active_data[active_data["Title"] == choice].iloc[0]

    # Display using f-string but NO CSS INSIDE to avoid SyntaxError
    st.markdown(f"""
    <div class="detail-box">
        <div style="display: flex; justify-content: space-between;">
            <h2 style="margin:0;">{row['Title']}</h2>
            <span class="urgent-pill">ID: {row.get('id','--')}</span>
        </div>
        <p style="color:#94A3B8; margin-top:5px;"><b>Acheteur:</b> {row['Client']} | <b>Publication:</b> {row['Date de publication']}</p>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; margin: 15px 0;">
            <div style="background:#334155; padding:10px; border-radius:8px;">
                <small style="color:#94A3B8;">Budget</small><br><b>{row['Budget']}</b>
            </div>
            <div style="background:#334155; padding:10px; border-radius:8px;">
                <small style="color:#94A3B8;">Caution</small><br><b>{row['Caution']}</b>
            </div>
            <div style="background:#334155; padding:10px; border-radius:8px;">
                <small style="color:#94A3B8;">Date Limite</small><br><b>{row['Date de limite']}</b>
            </div>
        </div>

        <div>
            <h4>🛠️ Description Technique</h4>
            <p style="color:#CBD5E1; font-size:0.95rem; line-height:1.5;">{row['Description Technique']}</p>
        </div>

        <div class="ai-summary">
            <span style="color:#A78BFA; font-weight:bold; font-size:0.8rem;">✨ RÉSUMÉ ANALYTIQUE IA</span>
            <p style="margin-top:8px; font-size:0.9rem;">
                Le marché lancé par <b>{row['Client']}</b> concerne principalement {row['Title'][:50]}... 
                Les exigences techniques soulignent l'importance de la conformité aux normes en vigueur. 
                Vérifiez le document officiel via le lien ci-dessous avant le <b>{row['Date de limite']}</b>.
            </p>
        </div>
        
        <div style="margin-top:20px;">
            <a href="{row['URL']}" target="_blank" style="background:#EF4444; color:white; padding:8px 20px; border-radius:5px; text-decoration:none; font-weight:bold;">Ouvrir l'annonce officielle 🔗</a>
        </div>
    </div>
    """, unsafe_allow_html=True)
