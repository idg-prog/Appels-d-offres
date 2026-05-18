import streamlit as st
import pandas as pd
from supabase import create_client

# ============================================
# 1. CONFIGURATION
# ============================================
st.set_page_config(page_title="AO Monitoring", layout="wide")

# ============================================
# 2. DESIGN CSS (DARK SAAS PROFESSIONNEL)
# ============================================
st.markdown("""
    <style>
    .stApp { background-color: #0F172A; color: #F1F5F9; }
    
    .main-title { font-size: 2.2rem; font-weight: 800; color: #FFFFFF; margin-bottom: 5px; }
    .intro-text { color: #94A3B8; margin-bottom: 30px; font-size: 1.1rem; }

    /* Conteneur pour le défilement horizontal */
    .table-container {
        width: 100%;
        overflow-x: auto;
        border-radius: 12px;
        border: 1px solid #334155;
    }

    .saas-table {
        width: 100%;
        border-collapse: collapse;
        background-color: #1E293B;
        min-width: 1100px; /* Force la largeur pour éviter l'écrasement */
    }

    .saas-table thead {
        background-color: #111827;
        border-bottom: 2px solid #475569;
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

    .saas-table tr:hover { background-color: #26334D; }

    .logo-badge {
        width: 30px; height: 30px; border-radius: 6px;
        background: #475569; display: inline-flex;
        align-items: center; justify-content: center;
        font-weight: bold; margin-right: 12px; color: white;
    }

    .btn-link {
        background-color: #EF4444;
        color: white !important;
        padding: 8px 14px;
        border-radius: 6px;
        text-decoration: none;
        font-size: 0.8rem;
        font-weight: bold;
        display: inline-block;
    }
    </style>
    """, unsafe_allow_html=True)

# ============================================
# 3. CHARGEMENT DES DONNÉES
# ============================================
@st.cache_data(ttl=600)
def get_data():
    try:
        client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_SERVICE_KEY"])
        response = client.table("Tenders Clean Data").select("*").execute()
        return pd.DataFrame(response.data)
    except:
        return pd.DataFrame()

df = get_data()

# ============================================
# 4. EN-TÊTE
# ============================================
st.markdown('<h1 class="main-title">📊 Suivi Centralisé des Appels d\'Offres</h1>', unsafe_allow_html=True)
st.markdown('<p class="intro-text">Plateforme de veille stratégique. Consultez les détails financiers et les échéances de soumission des derniers marchés publics.</p>', unsafe_allow_html=True)

# ============================================
# 5. CONSTRUCTION DU TABLEAU HTML
# ============================================
if df.empty:
    st.warning("Aucune donnée disponible.")
else:
    # --- DÉBUT DU TABLEAU ---
    html_code = """
    <div class="table-container">
        <table class="saas-table">
            <thead>
                <tr>
                    <th style="width: 200px;">Acheteur / Client</th>
                    <th style="width: 400px;">Titre du Marché</th>
                    <th>Publication</th>
                    <th>Échéance</th>
                    <th>Budget</th>
                    <th>Caution</th>
                    <th>Lien</th>
                </tr>
            </thead>
            <tbody>
    """

    for _, row in df.iterrows():
        # Nettoyage des valeurs 'nan' de Pandas
        def clean(val):
            return str(val) if pd.notna(val) and str(val).lower() != "nan" else "-"

        client = clean(row.get('Client'))
        title = clean(row.get('Title'))
        pub = clean(row.get('Date de publication'))
        lim = clean(row.get('Date de limite'))
        budget = clean(row.get('Budget'))
        caution = clean(row.get('Caution'))
        url = clean(row.get('URL'))

        # Fix pour les liens sans protocole
        link_url = url if url.startswith('http') else f"https://{url}" if url != "-" else "#"

        initial = client[0] if client != "-" else "?"
        title_short = (title[:85] + '...') if len(title) > 85 else title

        html_code += f"""
            <tr>
                <td>
                    <div style="display: flex; align-items: center;">
                        <div class="logo-badge">{initial}</div>
                        <span>{client}</span>
                    </div>
                </td>
                <td style="font-weight: 600; color: #F8FAFC;">{title_short}</td>
                <td style="color: #94A3B8;">{pub}</td>
                <td style="color: #F87171; font-weight: bold;">{lim}</td>
                <td style="color: #10B981; font-weight: bold;">{budget}</td>
                <td>{caution}</td>
                <td><a class="btn-link" href="{link_url}" target="_blank">Ouvrir 🔗</a></td>
            </tr>
        """

    html_code += """
            </tbody>
        </table>
    </div>
    """

    # Rendu final
    st.markdown(html_code, unsafe_allow_html=True)

# ============================================
# 6. FOOTER
# ============================================
st.markdown("<br><center><small style='color: #475569;'>Mise à jour automatique • Supabase SQL</small></center>", unsafe_allow_html=True)
