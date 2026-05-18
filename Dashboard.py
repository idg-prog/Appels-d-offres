import streamlit as st
import pandas as pd
from supabase import create_client

# ============================================
# 1. PAGE CONFIGURATION
# ============================================
st.set_page_config(
    page_title="Dashboard Appels d'Offres",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# 2. CUSTOM CSS (Match the image design)
# ============================================
st.markdown("""
    <style>
    /* Main app background */
    .stApp {
        background-color: #F9FAFB;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: white !important;
        border-right: 1px solid #E5E7EB;
    }
    
    /* Search bar styling */
    .stTextInput input {
        border-radius: 8px;
    }

    /* Detail Card Styling */
    .detail-container {
        background-color: white;
        padding: 24px;
        border-radius: 12px;
        border: 1px solid #E5E7EB;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    .status-badge {
        background-color: #ECFDF5;
        color: #059669;
        padding: 4px 12px;
        border-radius: 99px;
        font-weight: 600;
        font-size: 0.8rem;
        display: inline-block;
        margin-bottom: 12px;
    }
    
    .ai-box {
        background-color: #F5F3FF;
        border-radius: 8px;
        padding: 16px;
        margin-top: 20px;
        border: 1px solid #DDD6FE;
    }

    .metric-row {
        display: flex;
        justify-content: space-between;
        background: #F9FAFB;
        padding: 12px;
        border-radius: 8px;
        margin: 15px 0;
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border-radius: 4px 4px 0 0;
        padding: 10px 20px;
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
except Exception as e:
    st.error("Connection Error: Please check your Supabase secrets.")
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
    st.button("➕ Nouvelle recherche", use_container_width=True)
    st.markdown("---")
    
    search_query = st.text_input("🔍 Rechercher des appels d'offres...", placeholder="ex: voiture de service")

    with st.expander("📂 Type d'Appel d'offres", expanded=False):
        st.multiselect("Sélectionner", ["National", "International"], key="type_filter")

    with st.expander("🏷️ Catégories", expanded=True):
        if not df.empty and "Category" in df.columns:
            cats = sorted(df["Category"].unique())
        else:
            cats = ["Fournitures", "Travaux", "Services"]
        st.multiselect("Catégories", cats, default=["Fournitures"])

    with st.expander("🏢 Acheteurs", expanded=False):
        clients = sorted(df["Client"].unique()) if not df.empty else []
        selected_clients = st.multiselect("Acheteurs", clients)

    with st.expander("📍 Régions", expanded=False):
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
    st.warning("Aucune donnée disponible avec les filtres actuels.")
else:
    # 2-Column Layout (Table | Details)
    col_table, col_details = st.columns([1.8, 1.2], gap="medium")

    # LEFT COLUMN: The List
    with col_table:
        tab_tout, tab_nouv, tab_vu = st.tabs([f"Tout ({len(filtered_df)})", "Nouveaux", "Déjà vu"])
        
        with tab_tout:
            # We display the table
            # Note: Removed selection_mode to ensure compatibility with older Streamlit versions
            display_df = filtered_df[["Client", "Title", "Date de publication"]].copy()
            display_df.columns = ["Acheteur", "Titre", "Date de publication"]
            
            st.dataframe(
                display_df,
                use_container_width=True,
                height=750,
                hide_index=True
            )

    # RIGHT COLUMN: The Details Card
    with col_details:
        # Title selection to drive the detail view
        st.write("### 📄 Détails de l'offre")
        titles = filtered_df["Title"].tolist()
        target_title = st.selectbox("Sélectionner une offre pour voir les détails :", titles)
        
        # Get data for the selected title
        row = filtered_df[filtered_df["Title"] == target_title].iloc[0]

        # Custom HTML Card to match the image
        st.markdown(f"""
            <div class="detail-container">
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
                    <div style="background: #f0f0f0; width: 48px; height: 48px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 20px;">🏢</div>
                    <div>
                        <div style="font-weight: 700; color: #111827; font-size: 1.1rem;">{row['Client']}</div>
                        <div style="color: #6B7280; font-size: 0.85rem;">Réf: {row.get('Reference', '06/CTAAI/2025')}</div>
                    </div>
                </div>
                
                <h2 style="font-size: 1.3rem; color: #111827; line-height: 1.4; margin-bottom: 15px;">{row['Title']}</h2>
                
                <div class="status-badge">● En cours</div>
                
                <div class="metric-row">
                    <div><small style="color: #6B7280;">💰 Budget</small><br><strong>{row.get('Budget', 'N/A')} Dhs</strong></div>
                    <div><small style="color: #6B7280;">🛡️ Caution</small><br><strong>{row.get('Caution', 'N/A')} Dhs</strong></div>
                </div>
                
                <div style="font-size: 0.9rem; color: #374151; line-height: 1.8;">
                    <p>📅 <b>Publié le :</b> {row.get('Date de publication', 'N/A')}</p>
                    <p>⏰ <b>Date limite :</b> {row.get('Date de limite', 'N/A')}</p>
                    <p>📍 <b>Localisation :</b> {row.get('Localisation', 'Maroc')}</p>
                </div>
                
                <div style="display: flex; gap: 10px; margin-top: 25px;">
                    <a href="#" style="flex: 1; text-align: center; background: #6366F1; color: white; padding: 10px; border-radius: 6px; text-decoration: none; font-weight: 600;">📥 Télécharger</a>
                    <a href="#" style="flex: 1; text-align: center; border: 1px solid #D1D5DB; color: #374151; padding: 10px; border-radius: 6px; text-decoration: none; font-weight: 600;">🚀 Soumission</a>
                </div>

                <div class="ai-box">
                    <div style="display: flex; align-items: center; gap: 6px; color: #7C3AED; font-weight: 700; font-size: 0.8rem; margin-bottom: 8px;">
                        <span>✨ DONNÉES GÉNÉRÉES PAR IA</span>
                    </div>
                    <p style="font-size: 0.85rem; color: #4B5563; line-height: 1.5; margin: 0;">
                        <b>Résumé de l'offre :</b> Cet appel d'offres concerne l'acquisition de matériel spécifique pour le compte de <b>{row['Client']}</b>. 
                        L'objet principal est l'amélioration de la flotte de service avec des spécifications techniques précises.
                    </p>
                </div>
            </div>
        """, unsafe_allow_html=True)

        with st.expander("🛠️ Description Technique"):
            st.write(row.get("Description Technique", "Aucune description technique détaillée disponible."))

# ============================================
# 7. EXPORT FUNCTION
# ============================================
st.sidebar.markdown("---")
if not filtered_df.empty:
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(
        label="📥 Exporter la liste (CSV)",
        data=csv,
        file_name='appels_offres_export.csv',
        mime='text/csv',
        use_container_width=True
    )
