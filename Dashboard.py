import streamlit as st
import pandas as pd
from supabase import create_client

# ============================================
# 1. PAGE CONFIGURATION
# ============================================
st.set_page_config(
    page_title="Appels d'Offres - Monitoring",
    page_icon="🇲🇦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# 2. ADVANCED DARK SAAS CSS
# ============================================
st.markdown("""
    <style>
    /* Main Background */
    .stApp {
        background-color: #0F172A;
        color: #F1F5F9;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #1E293B !important;
        border-right: 1px solid #334155;
    }

    /* Tabs Styling (Matching the white buttons in your image but for Dark Mode) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 40px;
        background-color: #1E293B;
        border-radius: 8px;
        padding: 0 20px;
        color: #94A3B8;
        border: 1px solid #334155;
    }
    .stTabs [data-baseweb="tab--active"] {
        background-color: #334155 !important;
        color: #FFFFFF !important;
        border-bottom: none !important;
    }

    /* The Detail Card (Right Panel) */
    .detail-card {
        background-color: #1E293B;
        padding: 24px;
        border-radius: 12px;
        border: 1px solid #334155;
        position: sticky;
        top: 20px;
    }
    
    .status-pill {
        background-color: rgba(34, 197, 94, 0.1);
        color: #4ADE80;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        border: 1px solid rgba(34, 197, 94, 0.2);
    }
    
    .ai-summary-box {
        background-color: #2E1065; /* Deep Purple like image */
        border: 1px solid #7C3AED;
        padding: 16px;
        border-radius: 8px;
        margin-top: 20px;
    }

    /* Custom metrics layout */
    .metric-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
        margin: 20px 0;
    }
    .metric-item {
        background: #0F172A;
        padding: 10px;
        border-radius: 6px;
        border: 1px solid #334155;
    }

    /* Table headers */
    .stDataFrame {
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# ============================================
# 3. DATA CONNECTION
# ============================================
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_SERVICE_KEY"])

supabase = init_connection()

@st.cache_data(ttl=300)
def load_data():
    response = supabase.table("Tenders Clean Data").select("*").execute()
    data = response.data
    df = pd.DataFrame(data) if data else pd.DataFrame()
    if not df.empty:
        # Match your SQL columns
        df.fillna("", inplace=True)
    return df

df = load_data()

# ============================================
# 4. SIDEBAR FILTERS
# ============================================
with st.sidebar:
    st.button("➕ Nouvelle recherche", use_container_width=True)
    st.markdown("---")
    
    q = st.text_input("🔍 Rechercher des appels d'offres...", placeholder="ex: Maintenance")

    with st.expander("📂 Type d'Appel d'offres"):
        st.multiselect("Sélectionner", ["National", "International"])

    with st.expander("🏢 Acheteurs", expanded=True):
        clients = sorted(df["Client"].unique()) if not df.empty else []
        sel_clients = st.multiselect("Filtrer par acheteur", clients)

    with st.expander("📍 Régions"):
        locs = sorted(df["Localisation"].unique()) if not df.empty else []
        sel_locs = st.multiselect("Filtrer par ville", locs)

# ============================================
# 5. FILTERING LOGIC
# ============================================
filtered_df = df.copy()
if not filtered_df.empty:
    if sel_clients:
        filtered_df = filtered_df[filtered_df["Client"].isin(sel_clients)]
    if sel_locs:
        filtered_df = filtered_df[filtered_df["Localisation"].isin(sel_locs)]
    if q:
        filtered_df = filtered_df[filtered_df.apply(lambda row: row.astype(str).str.contains(q, case=False).any(), axis=1)]

# ============================================
# 6. MAIN LAYOUT (Tabs + Table + Details)
# ============================================
col_main, col_side = st.columns([2, 1.2], gap="medium")

with col_main:
    # Tabs like the image: Tout, Nouveaux, Déjà vu
    t1, t2, t3 = st.tabs([f"Tout ({len(filtered_df)})", f"Nouveaux ({len(filtered_df)//2})", "Déjà vu (0)"])
    
    with t1:
        # We use a selectbox to drive the detail view because row-clicks 
        # are not supported in all Streamlit versions yet
        st.write("### 📋 Liste des marchés")
        
        # Displaying the clean table
        display_cols = ["Client", "Title", "Date de publication"]
        nice_df = filtered_df[display_cols].copy()
        nice_df.columns = ["Acheteur", "Titre", "Date de publication"]
        
        st.dataframe(nice_df, use_container_width=True, height=650, hide_index=True)

with col_side:
    st.markdown("### 📄 Détails de l'appel d'offre")
    
    if not filtered_df.empty:
        # Selectbox to pick which tender to view (replaces the click interaction)
        selected_title = st.selectbox("Sélectionner pour voir les détails :", filtered_df["Title"].tolist())
        row = filtered_df[filtered_df["Title"] == selected_title].iloc[0]
        
        # UI Detail Card
        st.markdown(f"""
            <div class="detail-card">
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
                    <div style="background: #334155; width: 45px; height: 45px; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-weight: bold; color: white;">
                        {row['Client'][0] if row['Client'] else 'A'}
                    </div>
                    <div>
                        <strong style="font-size: 1.1rem;">{row['Client']}</strong><br>
                        <span style="color: #64748B; font-size: 0.8rem;">REF: AO-{row.get('id', '001')}</span>
                    </div>
                </div>
                
                <h2 style="font-size: 1.25rem; line-height: 1.4; margin-bottom: 15px;">{row['Title']}</h2>
                
                <div class="status-pill">● En cours</div>
                
                <div class="metric-grid">
                    <div class="metric-item">
                        <small style="color: #64748B;">💰 Budget</small><br>
                        <strong style="font-size: 1rem;">{row.get('Budget', 'N/A')}</strong>
                    </div>
                    <div class="metric-item">
                        <small style="color: #64748B;">🛡️ Caution</small><br>
                        <strong style="font-size: 1rem;">{row.get('Caution', 'N/A')}</strong>
                    </div>
                </div>

                <div style="font-size: 0.9rem; color: #94A3B8; margin-bottom: 20px;">
                    <p>📅 <b>Publié :</b> {row.get('Date de publication', 'N/A')}</p>
                    <p>⏰ <b>Limite :</b> {row.get('Date de limite', 'N/A')}</p>
                    <p>📍 <b>Lieu :</b> {row.get('Localisation', 'Maroc')}</p>
                </div>
                
                <div style="display: flex; gap: 10px;">
                    <button style="flex: 1; padding: 10px; border-radius: 6px; border: 1px solid #475569; background: #1E293B; color: white; cursor: pointer;">📥 Télécharger</button>
                    <button style="flex: 1; padding: 10px; border-radius: 6px; border: none; background: #6366F1; color: white; font-weight: bold; cursor: pointer;">🚀 Soumission</button>
                </div>

                <div class="ai-summary-box">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                        <span style="font-size: 0.75rem; font-weight: bold; color: #A78BFA;">AI</span>
                        <span style="font-size: 0.75rem; color: #A78BFA; opacity: 0.8;">Données générées par IA</span>
                    </div>
                    <p style="font-size: 0.85rem; color: #E2E8F0; line-height: 1.5; margin: 0;">
                        <b>Résumé de l'offre :</b> Cet appel d'offres concerne {row['Title']}. 
                        L'exécution est prévue pour la région de <b>{row['Localisation']}</b> avec des critères techniques spécifiques mentionnés dans le DCE.
                    </p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        with st.expander("🛠️ Description Technique"):
            st.write(row.get("Description Technique", "Aucune description supplémentaire."))

# ============================================
# 7. EXPORT
# ============================================
st.sidebar.markdown("---")
if not filtered_df.empty:
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button("⬇️ Exporter (CSV)", csv, "marches_publics.csv", "text/csv", use_container_width=True)
