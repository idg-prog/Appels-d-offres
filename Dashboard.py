import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# ============================================
# 1. PAGE CONFIGURATION
# ============================================
st.set_page_config(
    page_title="AO Monitoring Dashboard",
    page_icon="📊",
    layout="wide"
)

# ============================================
# 2. DARK THEME CSS (With Red Tab Underline)
# ============================================
st.markdown("""
    <style>
    .stApp { background-color: #0F172A; color: #F1F5F9; }
    
    /* Custom Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #1E293B !important;
        border-right: 1px solid #334155;
    }

    /* Tab Design - Red Underline like the image */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; background-color: transparent; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #1E293B;
        border-radius: 8px 8px 0 0;
        padding: 0 30px;
        color: #94A3B8;
        border: none;
    }
    .stTabs [data-baseweb="tab--active"] {
        background-color: #1E293B !important;
        color: #FFFFFF !important;
        border-bottom: 3px solid #EF4444 !important; /* Red underline */
    }

    /* Detail Box styling */
    .detail-box {
        background-color: #1E293B;
        padding: 25px;
        border-radius: 12px;
        border: 1px solid #334155;
        margin-top: 20px;
    }
    
    .status-pill {
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
# 3. DATA PROCESSING
# ============================================
@st.cache_data
def load_data():
    # Replace this with your Supabase call or CSV upload
    # For this demo, I'm assuming you are loading the CSV data provided
    df = pd.read_csv("data.csv") # Ensure your file is named data.csv or link to Supabase
    
    # Standardize Dates for filtering
    df['date_pub_dt'] = pd.to_datetime(df['Date de publication'], dayfirst=True, errors='coerce')
    df['date_limite_dt'] = pd.to_datetime(df['Date de limite'], dayfirst=True, errors='coerce')
    
    df.fillna("", inplace=True)
    return df

df = load_data()

# ============================================
# 4. TAB LOGIC
# ============================================
# Logic for "Yesterday" and "3 days left"
today = datetime.now().date()
yesterday = today - timedelta(days=1)
three_days_from_now = today + timedelta(days=3)

# Filter 1: Nouveaux (Published yesterday)
df_nouveaux = df[df['date_pub_dt'].dt.date == yesterday]

# Filter 2: Urgent (Limite in less than 3 days)
# Note: only includes future dates
df_urgent = df[(df['date_limite_dt'].dt.date >= today) & 
               (df['date_limite_dt'].dt.date <= three_days_from_now)]

# ============================================
# 5. SIDEBAR FILTERS
# ============================================
with st.sidebar:
    st.title("🔎 Filtres")
    search = st.text_input("Recherche par mot clé")
    
    clients = sorted(df["Client"].unique())
    sel_client = st.multiselect("Acheteurs", clients)

# Applying sidebar filters to the global pool
if search:
    df = df[df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
if sel_client:
    df = df[df["Client"].isin(sel_client)]

# ============================================
# 6. MAIN LAYOUT
# ============================================

# Tabs display
t1, t2, t3 = st.tabs([
    f"Tous ({len(df)})", 
    f"Nouveaux ({len(df_nouveaux)})", 
    f"Urgent - 3 jours ({len(df_urgent)})"
])

def render_table(data):
    if data.empty:
        st.info("Aucun appel d'offre trouvé pour cette catégorie.")
        return None
    
    # Define columns to show in the table
    cols_to_display = [
        "Title", "Client", "Date de limite", "Date de publication", 
        "Description Technique", "Budget", "Caution", "URL"
    ]
    
    # Configure 10 rows height (~400px is roughly 10 rows in Streamlit)
    selected_event = st.dataframe(
        data[cols_to_display],
        use_container_width=True,
        height=450, 
        hide_index=True,
        column_config={
            "URL": st.column_config.LinkColumn("Lien"),
            "Description Technique": st.column_config.TextColumn("Description", width="large")
        }
    )
    return data

# Handle which dataset to show based on tab
with t1:
    active_df = render_table(df)
with t2:
    active_df = render_table(df_nouveaux)
with t3:
    active_df = render_table(df_urgent)

# ============================================
# 7. DETAILS SECTION (Under the table)
# ============================================
st.markdown("---")

if active_df is not None and not active_df.empty:
    # Use a selectbox to pick the specific AO to see details for
    ao_titles = active_df["Title"].tolist()
    selection = st.selectbox("Sélectionnez un appel d'offre pour voir l'analyse complète :", ao_titles)
    
    row = active_df[active_df["Title"] == selection].iloc[0]

    # Detailed Layout
    st.markdown(f"""
        <div class="detail-box">
            <div style="display: flex; justify-content: space-between; align-items: start;">
                <h2 style="margin:0; color: #F8FAFC;">{row['Title']}</h2>
                <span class="status-pill">Fin dans { (pd.to_datetime(row['Date de limite'], errors='coerce') - datetime.now()).days if row['Date de limite'] else '?' } jours</span>
            </div>
            <p style="color: #94A3B8; font-size: 1.1rem; margin-top: 5px;">🏢 {row['Client']} |
