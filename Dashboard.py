import streamlit as st
import pandas as pd
from supabase import create_client

# ============================================
# PAGE CONFIG
# ============================================
st.set_page_config(
    page_title="Appels d'Offres Maroc",
    page_icon="🇲🇦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# CUSTOM CSS (To match the modern UI)
# ============================================
st.markdown("""
    <style>
    /* Main background */
    .stApp {
        background-color: #F8F9FA;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: white !important;
        border-right: 1px solid #E0E0E0;
    }
    
    /* Card-like containers */
    div[data-testid="stVerticalBlock"] > div:has(div.stDataFrame) {
        background-color: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    /* Detail Panel Styling */
    .detail-card {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #E0E0E0;
    }
    
    .status-badge {
        background-color: #E8F5E9;
        color: #2E7D32;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.8rem;
    }
    
    .ai-summary {
        background-color: #F3F0FF;
        border-left: 4px solid #7C3AED;
        padding: 15px;
        border-radius: 4px;
        margin-top: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# ============================================
# SUPABASE CONNECTION
# ============================================
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_SERVICE_KEY"])

supabase = init_connection()

@st.cache_data(ttl=300)
def load_data():
    response = supabase.table("Tenders Clean Data").select("*").execute()
    data = response.data
    return pd.DataFrame(data) if data else pd.DataFrame()

df = load_data()
df.fillna("", inplace=True)

# ============================================
# SIDEBAR FILTERS (Left Panel)
# ============================================
with st.sidebar:
    st.image("https://via.placeholder.com/150x50?text=LOGO", width=150) # Replace with your logo
    st.button("➕ Nouvelle recherche", use_container_width=True)
    
    search_text = st.text_input("🔍 Rechercher des appels d'offres...")

    with st.expander("📂 Type d'Appel d'offres", expanded=True):
        types = ["National", "International"]
        st.multiselect("Sélectionner", types, key="filter_type")

    with st.expander("🏷️ Catégories", expanded=True):
        cats = sorted(df["Category"].unique()) if "Category" in df.columns else ["Fournitures", "Travaux", "Services"]
        selected_cat = st.multiselect("Catégories", cats, default=["Fournitures"])

    with st.expander("🏢 Acheteurs"):
        clients = sorted(df["Client"].unique())
        selected_client = st.multiselect("Clients", clients)

    with st.expander("📍 Régions"):
        regions = sorted(df["Localisation"].unique())
        selected_loc = st.multiselect("Localisation", regions)

# ============================================
# FILTER LOGIC
# ============================================
filtered_df = df.copy()
if selected_client:
    filtered_df = filtered_df[filtered_df["Client"].isin(selected_client)]
if selected_loc:
    filtered_df = filtered_df[filtered_df["Localisation"].isin(selected_loc)]
if search_text:
    filtered_df = filtered_df[filtered_df.apply(lambda row: row.astype(str).str.contains(search_text, case=False).any(), axis=1)]

# ============================================
# MAIN LAYOUT (Middle and Right Panels)
# ============================================
col_list, col_details = st.columns([1.8, 1.2], gap="medium")

with col_list:
    # Tabs like in the image
    tab1, tab2, tab3 = st.tabs([f"Tout ({len(filtered_df)})", "Nouveaux", "Déjà vu"])
    
    with tab1:
        # We use st.dataframe with selection mode
        event = st.dataframe(
            filtered_df[["Client", "Title", "Date de publication"]].rename(
                columns={"Client": "Acheteur", "Title": "Titre"}
            ),
            use_container_width=True,
            height=700,
            hide_index=True,
            on_select="rerun",
            selection_mode="single_row"
        )

# ============================================
# DETAIL VIEW (Right Panel)
# ============================================
with col_details:
    # Check if a row is selected
    if len(event.selection.rows) > 0:
        selected_index = event.selection.rows[0]
        row = filtered_df.iloc[selected_index]
        
        # Detail Card UI
        st.markdown(f"""
            <div class="detail-card">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px;">
                    <div style="background: #eee; width: 40px; height: 40px; border-radius: 5px;"></div>
                    <div>
                        <strong style="font-size: 1.1rem;">{row['Client']}</strong><br>
                        <span style="color: gray; font-size: 0.8rem;">REF: {row.get('Reference', 'N/A')}</span>
                    </div>
                </div>
                <h3 style="margin-top: 0;">{row['Title']}</h3>
                <span class="status-badge">● En cours</span>
                <hr>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                    <div><small>💰 Budget</small><br><strong>{row.get('Budget', 'N/A')} Dhs</strong></div>
                    <div><small>🛡️ Caution</small><br><strong>{row.get('Caution', 'N/A')} Dhs</strong></div>
                </div>
                <div style="margin-top:15px;">
                    <p><small>📅 Publié le:</small> {row.get('Date de publication', '')}</p>
                    <p><small>⏰ Date limite:</small> {row.get('Date de limite', '')}</p>
                    <p><small>📍 Lieu:</small> {row.get('Localisation', '')}</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Action Buttons
        c1, c2 = st.columns(2)
        with c1:
            st.button("📥 Télécharger", use_container_width=True)
        with c2:
            st.button("🚀 Soumission", type="primary", use_container_width=True)

        # AI Summary Section
        st.markdown("""
            <div class="ai-summary">
                <small>✨ Données générées par IA</small>
                <p style="margin-top:5px; font-size: 0.9rem;">
                    <strong>Résumé de l'appel d'offre:</strong><br>
                    Cet avis concerne l'acquisition de matériel spécifique pour la région mentionnée. 
                    Les critères incluent une expérience minimale de 3 ans et une conformité aux normes ISO.
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        with st.expander("Détails techniques"):
            st.write(row.get("Description Technique", "Aucune description technique disponible."))

    else:
        st.info("💡 Sélectionnez un appel d'offres dans la liste pour voir les détails.")

# ============================================
# FOOTER / DOWNLOAD
# ============================================
st.sidebar.markdown("---")
if st.sidebar.button("📥 Exporter la liste (CSV)"):
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button("Confirmer le téléchargement", csv, "tenders.csv", "text/csv")
