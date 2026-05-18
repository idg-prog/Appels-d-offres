import streamlit as st
import pandas as pd
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
# 2. DESIGN PERSONNALISÉ (DARK MODE & TABLEAU PROFESSIONNEL)
# ============================================
st.markdown("""
    <style>
    /* Fond principal sombre */
    .stApp { background-color: #0F172A; color: #F1F5F9; }
    
    /* Titre et Intro */
    .main-title { font-size: 2.5rem; font-weight: 800; margin-bottom: 0.5rem; color: #FFFFFF; }
    .intro-text { font-size: 1.1rem; color: #94A3B8; margin-bottom: 2rem; }

    /* Style du Tableau SaaS */
    .saas-table {
        width: 100%;
        border-collapse: collapse;
        background-color: #1E293B;
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #334155;
    }
    .saas-table thead {
        background-color: #0F172A;
        border-bottom: 2px solid #334155;
    }
    .saas-table th {
        text-align: left;
        padding: 18px 15px;
        color: #94A3B8;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .saas-table td {
        padding: 16px 15px;
        border-bottom: 1px solid #334155;
        font-size: 0.9rem;
        color: #CBD5E1;
        vertical-align: middle;
    }
    .saas-table tr:hover {
        background-color: #26334d;
    }

    /* Badge Logo Client */
    .logo-badge {
        width: 32px; height: 32px; border-radius: 6px;
        background: #475569; display: inline-flex;
        align-items: center; justify-content: center;
        font-weight: bold; margin-right: 10px; color: white;
    }

    /* Bouton Lien */
    .btn-link {
        background-color: #EF4444;
        color: white !important;
        padding: 6px 12px;
        border-radius: 6px;
        text-decoration: none;
        font-size: 0.8rem;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# ============================================
# 3. CHARGEMENT DES DONNÉES
# ============================================
@st.cache_resource
def init_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_SERVICE_KEY"])

@st.cache_data(ttl=600)
def get_data():
    client = init_supabase()
    response = client.table("Tenders Clean Data").select("*").execute()
    df = pd.DataFrame(response.data)
    # Nettoyage global pour l'affichage (remplace NaNs par "-")
    return df.fillna("-")

df = get_data()

# ============================================
# 4. EN-TÊTE
# ============================================
st.markdown('<h1 class="main-title">📊 Portail de Veille des Marchés Publics</h1>', unsafe_allow_html=True)
st.markdown("""
    <p class="intro-text">
        Accédez à l'ensemble des appels d'offres en cours. Cette liste centralise les opportunités stratégiques 
        avec les détails de budget, cautions et dates limites pour faciliter votre prise de décision.
    </p>
    """, unsafe_allow_html=True)

# ============================================
# 5. RENDU DU TABLEAU UNIQUE
# ============================================
if df.empty:
    st.warning("Aucune donnée disponible dans la base Supabase.")
else:
    # Construction du tableau en HTML pour un contrôle total du design
    html_table = """
    <table class="saas-table">
        <thead>
            <tr>
                <th>Acheteur / Client</th>
                <th>Titre de l'Appel d'Offre</th>
                <th>Publication</th>
                <th>Date Limite</th>
                <th>Budget (TTC)</th>
                <th>Caution</th>
                <th>Action</th>
            </tr>
        </thead>
        <tbody>
    """

    for _, row in df.iterrows():
        # Génération du logo (première lettre du client)
        client_name = str(row['Client'])
        initial = client_name[0] if client_name and client_name != "-" else "?"
        
        # Tronquer le titre s'il est trop long pour garder le tableau propre
        title_display = str(row['Title'])
        if len(title_display) > 85:
            title_display = title_display[:82] + "..."

        html_table += f"""
        <tr>
            <td>
                <div style="display: flex; align-items: center;">
                    <div class="logo-badge">{initial}</div>
                    <span>{client_name}</span>
                </div>
            </td>
            <td style="font-weight: 600; color: #F8FAFC;">{title_display}</td>
            <td style="color: #94A3B8;">{row['Date de publication']}</td>
            <td style="color: #F87171; font-weight: bold;">{row['Date de limite']}</td>
            <td style="color: #10B981; font-weight: bold;">{row['Budget']}</td>
            <td>{row['Caution']}</td>
            <td>
                <a class="btn-link" href="{row['URL']}" target="_blank">Ouvrir 🔗</a>
            </td>
        </tr>
        """

    html_table += "</tbody></table>"
    
    # Affichage du tableau
    st.markdown(html_table, unsafe_allow_html=True)

# ============================================
# 6. FOOTER
# ============================================
st.markdown("<br><hr><center><small style='color: #475569;'>Mise à jour automatique via Supabase SQL</small></center>", unsafe_allow_html=True)
