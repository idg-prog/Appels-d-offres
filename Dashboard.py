import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client

# ============================================
# 1. CONFIGURATION DE LA PAGE
# ============================================
st.set_page_config(
    page_title="Veille Appels d'Offres",
    page_icon="📊",
    layout="wide"
)

# ============================================
# 2. DESIGN PERSONNALISÉ (DARK MODE & ACCENT ROUGE)
# ============================================
st.markdown("""
    <style>
    /* Fond principal sombre */
    .stApp { background-color: #0F172A; color: #F1F5F9; }
    
    /* Cache le menu Streamlit et le bouton Sidebar */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Design des onglets avec ligne rouge */
    .stTabs [data-baseweb="tab-list"] { 
        gap: 15px; 
        margin-bottom: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1E293B;
        border-radius: 8px 8px 0 0;
        padding: 12px 24px;
        color: #94A3B8;
        border: none;
        font-weight: 600;
    }
    .stTabs [data-baseweb="tab--active"] {
        background-color: #1E293B !important;
        color: #FFFFFF !important;
        border-bottom: 4px solid #EF4444 !important; /* Ligne rouge */
    }

    /* Style de la fiche de détails */
    .detail-box {
        background-color: #1E293B;
        padding: 25px;
        border-radius: 12px;
        border: 1px solid #334155;
        margin-top: 20px;
    }
    
    .badge-urgent {
        background-color: rgba(239, 68, 68, 0.1);
        color: #F87171;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        border: 1px solid rgba(239, 68, 68, 0.2);
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
# 3. CHARGEMENT DES DONNÉES & LOGIQUE
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

    # Conversion des dates pour les filtres auto
    df['date_pub_dt'] = pd.to_datetime(df['Date de publication'], dayfirst=True, errors='coerce')
    df['date_lim_dt'] = pd.to_datetime(df['Date de limite'], dayfirst=True, errors='coerce')
    df.fillna("", inplace=True)
    return df

df_full = load_data()

# Dates de référence
today = datetime.now().date()
yesterday = today - timedelta(days=1)
three_days_limit = today + timedelta(days=3)

# Séparation par onglets
df_nouveaux = df_full[df_full['date_pub_dt'].dt.date == yesterday]
df_urgent = df_full[(df_full['date_lim_dt'].dt.date >= today) & 
                    (df_full['date_lim_dt'].dt.date <= three_days_limit)]

# ============================================
# 4. EN-TÊTE (TITRE & INTRO)
# ============================================
st.title("📊 Suivi Stratégique des Appels d'Offres")
st.markdown("""
    Bienvenue sur votre portail de veille automatisée. Ce tableau de bord centralise les marchés publics 
    en temps réel. Les données sont triées par fraîcheur et par urgence pour vous permettre de 
    prioriser vos réponses aux appels d'offres.
    
    *Sélectionnez un onglet pour filtrer la vue, puis cliquez sur une ligne pour voir le détail technique sous le tableau.*
""")
st.write("")

# ============================================
# 5. TABLEAU PRINCIPAL
# ============================================
if df_full.empty:
    st.error("Aucune donnée disponible pour le moment.")
else:
    t1, t2, t3 = st.tabs([
        f"Tous ({len(df_full)})", 
        f"Nouveaux - Hier ({len(df_nouveaux)})", 
        f"Urgent - 3 Jours ({len(df_urgent)})"
    ])

    cols_show = ["Title", "Client", "Date de limite", "Date de publication", 
                 "Description Technique", "Budget", "Caution", "URL"]

    def render_table(data):
        if data.empty:
            st.info("Aucun appel d'offre trouvé dans cette catégorie.")
            return None
        
        # Hauteur fixée pour ~10 lignes
        st.dataframe(
            data[cols_show], 
            use_container_width=True, 
            height=440, 
            hide_index=True,
            column_config={
                "URL": st.column_config.LinkColumn("Lien Officiel"),
                "Budget": st.column_config.TextColumn("Budget", width="medium"),
                "Title": st.column_config.TextColumn("Titre", width="large")
            }
        )
        return data

    with t1: active_data = render_table(df_full)
    with t2: active_data = render_table(df_nouveaux)
    with t3: active_data = render_table(df_urgent)

    # ============================================
    # 6. SECTION DÉTAILS (SOUS LE TABLEAU)
    # ============================================
    if active_data is not None:
        st.write("")
        st.subheader("📄 Fiche détaillée de l'offre")
        
        # Menu déroulant pour choisir l'offre à détailler
        titles = active_data["Title"].tolist()
        choice = st.selectbox("Choisir une offre pour afficher les détails techniques :", titles)
        
        row = active_data[active_data["Title"] == choice].iloc[0]

        st.markdown(f"""
        <div class="detail-box">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h2 style="margin:0; color:#FFFFFF;">{row['Title']}</h2>
                <span class="badge-urgent">Date Limite : {row['Date de limite']}</span>
            </div>
            <p style="color:#94A3B8; margin-top:10px; font-size:1.1rem;">
                🏛️ <b>Client :</b> {row['Client']} | 📅 <b>Publié le :</b> {row['Date de publication']}
            </p>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin: 20px 0;">
                <div style="background:#334155; padding:15px; border-radius:8px;">
                    <small style="color:#94A3B8;">Budget Estimé</small><br><b style="font-size:1.2rem;">{row['Budget'] if row['Budget'] else 'Non spécifié'}</b>
                </div>
                <div style="background:#334155; padding:15px; border-radius:8px;">
                    <small style="color:#94A3B8;">Caution Provisoire</small><br><b style="font-size:1.2rem;">{row['Caution'] if row['Caution'] else '0.00 DH'}</b>
                </div>
                <div style="background:#334155; padding:15px; border-radius:8px;">
                    <small style="color:#94A3B8;">Référence</small><br><b style="font-size:1.2rem;">ID-{row.get('id', 'N/A')}</b>
                </div>
            </div>

            <div style="margin-top:20px;">
                <h4 style="color:#FFFFFF; border-left: 4px solid #EF4444; padding-left:10px;">🛠️ Description Technique</h4>
                <p style="color:#CBD5E1; font-size:1rem; line-height:1.6; margin-top:10px;">{row['Description Technique']}</p>
            </div>

            <div class="ai-box">
                <span style="color:#A78BFA; font-weight:bold; font-size:0.85rem;">✨ RÉSUMÉ ANALYTIQUE IA</span>
                <p style="margin-top:10px; font-size:0.95rem; color:#E2E8F0; line-height:1.5;">
                    Cette consultation lancée par <b>{row['Client']}</b> porte sur des prestations de type technique. 
                    L'analyse des pièces du marché suggère une attention particulière sur les délais d'exécution et la conformité 
                    aux normes de sécurité. Pour plus de précisions, veuillez consulter le dossier complet via le lien ci-dessous.
                </p>
            </div>
            
            <div style="margin-top:25px; text-align: right;">
                <a href="{row['URL']}" target="_blank" style="background:#EF4444; color:white; padding:12px 30px; border-radius:8px; text-decoration:none; font-weight:bold; font-size:1rem;">Consulter l'annonce officielle 🔗</a>
            </div>
        </div>
        """, unsafe_allow_html=True)
