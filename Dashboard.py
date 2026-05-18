import streamlit as st
import pandas as pd
from supabase import create_client

# ============================================
# 1. PAGE CONFIGURATION
# ============================================
st.set_page_config(
    page_title="Appels d'Offres - Dark Mode",
    page_icon="🌙",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# 2. DARK THEME CUSTOM CSS
# ============================================
st.markdown("""
    <style>
    /* Main app background */
    .stApp {
        background-color: #0F172A; /* Deep Dark Blue/Slate */
        color: #F8FAFC;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #1E293B !important;
        border-right: 1px solid #334155;
    }
    
    /* Input fields */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #334155 !important;
        color: white !important;
        border: 1px solid #475569 !important;
    }

    /* Detail Card Styling */
    .detail-container {
        background-color: #1E293B;
        padding: 24px;
        border-radius: 12px;
        border: 1px solid #334155;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    
    .status-badge {
        background-color: rgba(16, 185, 129, 0.1); /* Emerald translucent */
        color: #34D399;
        padding: 4px 12px;
        border-radius: 99px;
        font-weight: 600;
        font-size: 0.8rem;
        display: inline-block;
        margin-bottom: 12px;
        border: 1px solid rgba(16, 185, 129, 0.2);
    }
    
    .ai-box {
        background-color: #2E1065; /* Dark Purple */
        border-radius: 8px;
        padding: 16px;
        margin-top: 20px;
        border: 1px solid #6D28D9;
    }

    .metric-row {
        display: flex;
        justify-content: space-between;
        background: #334155;
        padding: 12px;
        border-radius: 8px;
        margin: 15px 0;
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        color: #94A3B8;
    }
    .stTabs [data-baseweb="tab--active"] {
        color: #818CF8 !important;
        border-bottom-color: #818CF8 !important;
    }

    /* Titles and text colors */
    h1, h2, h3, strong {
        color: #F8FAFC !important;
    }
    small, p {
        color: #94A3B8 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ============================================
# 3. DATA CONNECTION (Supabase)
# ============================================
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_SERVICE_KEY"])

try:
    supabase = init_connection()
except Exception:
    st.error("Connection Error: Check Supabase secrets.")
    st.stop()

@st.cache_data(ttl=300)
def load_data():
    response = supabase.table("Tenders Clean Data").select("*").execute()
    df = pd.DataFrame(response.data) if response.data else pd.DataFrame()
    if not df.empty:
        df.fillna("", inplace=True)
    return df

df = load_data()

# ============================================
# 4. SIDEBAR FILTERS (Left Panel)
# ============================================
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🇲🇦 AO Dashboard</h2>", unsafe_allow_html=True)
    st.button("➕ Nouvelle recherche", use_container_width=True)
    st.markdown("---")
    
    search_query = st.text_input("🔍 Rechercher...", placeholder="ex: voiture de service")

    with st.expander("📂 Type d'Appel d'offres"):
        st.multiselect("Sélectionner", ["National", "International"])

    with st.expander("🏷️ Catégories", expanded=True):
        if not df.empty and "Category" in df.columns:
            cats = sorted(df["Category"].unique())
        else:
            cats = ["Fournitures", "Travaux", "Services"]
        st.multiselect("Catégories", cats, default=["Fournitures"])

    with st.expander("🏢 Acheteurs"):
        clients = sorted(df["Client"].unique()) if not df.empty else []
        selected_clients = st.multiselect("Acheteurs", clients)

    with st.expander("📍 Régions"):
        locs = sorted(df["Localisation"].unique()) if not df.empty else []
        selected_locs = st.multiselect("Localisation", locs)

# ============================================
# 5. FILTER LOGIC
# ============================================
filtered_df = df.copy()
if not filtered_df.empty:
    if selected_clients:
        filtered_df = filtered_df[filtered_df["Client"].isin(selected_clients)]
    if selected_locs:
        filtered_df = filtered_df[filtered_df["Localisation"].isin(selected_locs)]
    if search_query:
        filtered_df = filtered_df[filtered_df.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)]

# ============================================
# 6. MAIN CONTENT LAYOUT
# ============================================
if filtered_df.empty:
    st.info("Aucun résultat. Essayez d'ajuster vos filtres.")
else:
    # 2-Column Layout
    col_table, col_details = st.columns([1.8, 1.2], gap="medium")

    # LEFT COLUMN: Table
    with col_table:
        tabs = st.tabs([f"Tout ({len(filtered_df)})", "Nouveaux", "Déjà vu"])
        with tabs[0]:
            display_df = filtered_df[["Client", "Title", "Date de publication"]].copy()
            display_df.columns = ["Acheteur", "Titre", "Publication"]
            
            # Dataframe styling in dark mode is automatic, but we set height
            st.dataframe(
                display_df,
                use_container_width=True,
                height=700,
                hide_index=True
            )

    # RIGHT COLUMN: Detail Card
    with col_details:
        st.markdown("### 📄 Fiche Détails")
        titles = filtered_df["Title"].tolist()
        target_title = st.selectbox("Choisir une offre :", titles, label_visibility="collapsed")
        
        row = filtered_df[filtered_df["Title"] == target_title].iloc[0]

        # Dark Mode Custom HTML Card
        st.markdown(f"""
            <div class="detail-container">
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
                    <div style="background: #334155; width: 48px; height: 48px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 20px;">🏢</div>
                    <div>
                        <div style="font-weight: 700; color: #F8FAFC; font-size: 1.1rem;">{row['Client']}</div>
                        <div style="color: #94A3B8; font-size: 0.85rem;">Réf: {row.get('Reference', '06/2025')}</div>
                    </div>
                </div>
                
                <h2 style="font-size: 1.3rem; color: #F8FAFC; line-height: 1.4; margin-bottom: 15px;">{row['Title']}</h2>
                
                <div class="status-badge">● En cours</div>
                
                <div class="metric-row">
                    <div><small style="color: #94A3B8;">💰 Budget</small><br><strong style="color:#F8FAFC;">{row.get('Budget', 'N/A')} Dhs</strong></div>
                    <div><small style="color: #94A3B8;">🛡️ Caution</small><br><strong style="color:#F8FAFC;">{row.get('Caution', 'N/A')} Dhs</strong></div>
                </div>
                
                <div style="font-size: 0.9rem; color: #CBD5E1; line-height: 1.8;">
                    <p>📅 <b>Publié le :</b> {row.get('Date de publication', 'N/A')}</p>
                    <p>⏰ <b>Date limite :</b> {row.get('Date de limite', 'N/A')}</p>
                    <p>📍 <b>Localisation :</b> {row.get('Localisation', 'Maroc')}</p>
                </div>
                
                <div style="display: flex; gap: 10px; margin-top: 25px;">
                    <a href="#" style="flex: 1; text-align: center; background: #6366F1; color: white; padding: 10px; border-radius: 6px; text-decoration: none; font-weight: 600;">📥 Télécharger</a>
                    <a href="#" style="flex: 1; text-align: center; border: 1px solid #475569; color: #F8FAFC; padding: 10px; border-radius: 6px; text-decoration: none; font-weight: 600;">🚀 Soumission</a>
                </div>

                <div class="ai-box">
                    <div style="display: flex; align-items: center; gap: 6px; color: #A78BFA; font-weight: 700; font-size: 0.8rem; margin-bottom: 8px;">
                        <span>✨ RÉSUMÉ IA</span>
                    </div>
                    <p style="font-size: 0.85rem; color: #E2E8F0; line-height: 1.5; margin: 0;">
                        L'offre porte sur l'acquisition de solutions pour <b>{row['Client']}</b>. 
                        Exigence principale : conformité technique stricte et délais d'exécution optimisés.
                    </p>
                </div>
            </div>
        """, unsafe_allow_html=True)

        with st.expander("🛠️ Fiche Technique"):
            st.write(row.get("Description Technique", "Détails non disponibles."))

# ============================================
# 7. EXPORT
# ============================================
st.sidebar.markdown("---")
if not filtered_df.empty:
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(
        label="📥 Exporter CSV",
        data=csv,
        file_name='export_dark.csv',
        mime='text/csv',
        use_container_width=True
    )
