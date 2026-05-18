import streamlit as st
import pandas as pd
from supabase import create_client

# ============================================
# 1. CONFIGURATION DE LA PAGE
# ============================================
st.set_page_config(
    page_title="Veille Marchés Publics",
    page_icon="📊",
    layout="wide"
)

# ============================================
# 2. DESIGN PERSONNALISÉ
# ============================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Syne:wght@700;800&family=Inter:wght@400;500;600&display=swap');

    /* ── Base ─────────────────────────────── */
    html, body, .stApp {
        background-color: #07090F !important;
        color: #CBD5E1;
        font-family: 'Inter', sans-serif;
    }

    /* Hide Streamlit chrome */
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding: 2rem 2.5rem 4rem !important; max-width: 1600px; }

    /* ── Header ───────────────────────────── */
    .portal-header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        margin-bottom: 2.5rem;
        padding-bottom: 1.5rem;
        border-bottom: 1px solid #1E293B;
    }
    .portal-title {
        font-family: 'Syne', sans-serif;
        font-size: 2.2rem;
        font-weight: 800;
        color: #F8FAFC;
        letter-spacing: -0.5px;
        margin: 0;
    }
    .portal-title span { color: #EF4444; }
    .portal-subtitle {
        font-size: 0.9rem;
        color: #475569;
        margin-top: 0.35rem;
        font-family: 'IBM Plex Mono', monospace;
    }
    .badge-count {
        background: #EF4444;
        color: white;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.75rem;
        font-weight: 600;
        padding: 4px 12px;
        border-radius: 99px;
        margin-top: 0.5rem;
        display: inline-block;
    }

    /* ── Filter bar ───────────────────────── */
    .filter-bar {
        display: flex;
        gap: 1rem;
        margin-bottom: 1.5rem;
        flex-wrap: wrap;
    }

    /* Override Streamlit input styles */
    .stTextInput > div > div > input {
        background-color: #0F172A !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        color: #CBD5E1 !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.9rem !important;
    }
    .stTextInput > div > div > input::placeholder { color: #475569 !important; }
    .stTextInput > div > div > input:focus {
        border-color: #EF4444 !important;
        box-shadow: 0 0 0 2px rgba(239,68,68,0.15) !important;
    }
    .stSelectbox > div > div {
        background-color: #0F172A !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        color: #CBD5E1 !important;
    }
    label { color: #94A3B8 !important; font-size: 0.8rem !important; }

    /* ── Table wrapper ────────────────────── */
    .table-wrapper {
        overflow-x: auto;
        border-radius: 12px;
        border: 1px solid #1E293B;
        background: #0D1424;
    }

    /* ── Main Table ───────────────────────── */
    .saas-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.875rem;
    }
    .saas-table thead {
        position: sticky;
        top: 0;
        z-index: 10;
        background: #07090F;
        border-bottom: 1px solid #1E293B;
    }
    .saas-table th {
        text-align: left;
        padding: 14px 16px;
        color: #475569;
        font-size: 0.7rem;
        font-family: 'IBM Plex Mono', monospace;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        white-space: nowrap;
        font-weight: 600;
    }
    .saas-table td {
        padding: 14px 16px;
        border-bottom: 1px solid #111827;
        color: #94A3B8;
        vertical-align: middle;
        line-height: 1.4;
    }
    .saas-table tbody tr:last-child td { border-bottom: none; }
    .saas-table tbody tr {
        transition: background 0.15s ease;
    }
    .saas-table tbody tr:hover td {
        background: #111827;
        color: #CBD5E1;
    }

    /* ── Cell styles ──────────────────────── */
    .cell-client {
        display: flex;
        align-items: center;
        gap: 10px;
        min-width: 180px;
        max-width: 220px;
    }
    .logo-badge {
        width: 30px;
        height: 30px;
        border-radius: 7px;
        background: linear-gradient(135deg, #1E40AF, #3B82F6);
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 0.75rem;
        color: white;
        flex-shrink: 0;
        font-family: 'IBM Plex Mono', monospace;
    }
    .client-name {
        font-size: 0.8rem;
        color: #94A3B8;
        line-height: 1.3;
        word-break: break-word;
    }

    .cell-title {
        font-weight: 600;
        color: #E2E8F0 !important;
        max-width: 340px;
        min-width: 200px;
        line-height: 1.4;
    }

    .cell-date-pub {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.78rem;
        color: #475569 !important;
        white-space: nowrap;
    }
    .cell-date-limit {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.78rem;
        color: #EF4444 !important;
        font-weight: 600;
        white-space: nowrap;
    }
    .cell-budget {
        color: #10B981 !important;
        font-weight: 600;
        max-width: 200px;
        min-width: 120px;
        font-size: 0.82rem;
    }
    .cell-caution {
        font-size: 0.78rem;
        color: #64748B !important;
        max-width: 140px;
        min-width: 90px;
    }

    .btn-link {
        display: inline-block;
        background: #EF4444;
        color: white !important;
        padding: 5px 12px;
        border-radius: 6px;
        text-decoration: none !important;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.3px;
        white-space: nowrap;
        transition: background 0.15s ease, transform 0.1s ease;
        font-family: 'Inter', sans-serif;
    }
    .btn-link:hover {
        background: #DC2626 !important;
        color: white !important;
        transform: translateY(-1px);
    }
    .btn-disabled {
        display: inline-block;
        background: #1E293B;
        color: #475569 !important;
        padding: 5px 12px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        white-space: nowrap;
        cursor: not-allowed;
        font-family: 'Inter', sans-serif;
    }

    /* ── Footer ───────────────────────────── */
    .portal-footer {
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid #1E293B;
        text-align: center;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.72rem;
        color: #334155;
    }

    /* ── Stats bar ────────────────────────── */
    .stats-row {
        display: flex;
        gap: 1rem;
        margin-bottom: 1.5rem;
        flex-wrap: wrap;
    }
    .stat-card {
        background: #0F172A;
        border: 1px solid #1E293B;
        border-radius: 10px;
        padding: 12px 20px;
        min-width: 160px;
    }
    .stat-label {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.65rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #475569;
        margin-bottom: 4px;
    }
    .stat-value {
        font-family: 'Syne', sans-serif;
        font-size: 1.4rem;
        font-weight: 800;
        color: #F8FAFC;
    }
    .stat-value.red { color: #EF4444; }
    .stat-value.green { color: #10B981; }
    </style>
    """, unsafe_allow_html=True)


# ============================================
# 3. CHARGEMENT DES DONNÉES
# ============================================
@st.cache_resource
def init_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SERVICE_KEY"]
    )

@st.cache_data(ttl=600)
def get_data():
    client = init_supabase()
    response = client.table("Tenders Clean Data").select("*").execute()
    df = pd.DataFrame(response.data)
    return df.fillna("-")

df = get_data()


# ============================================
# 4. EN-TÊTE
# ============================================
st.markdown("""
    <div class="portal-header">
        <div>
            <h1 class="portal-title">📊 Veille <span>Marchés Publics</span></h1>
            <p class="portal-subtitle">Portail centralisé des appels d'offres — Maroc</p>
        </div>
    </div>
""", unsafe_allow_html=True)


# ============================================
# 5. FILTRES
# ============================================
col1, col2, col3 = st.columns([3, 2, 2])

with col1:
    search_query = st.text_input("🔍 Rechercher", placeholder="Mot-clé, client, titre...")
with col2:
    # Build unique client list for dropdown
    clients = sorted(df['Client'].dropna().unique().tolist()) if not df.empty else []
    clients = [c for c in clients if c != "-"]
    client_filter = st.selectbox("🏢 Filtrer par client", ["Tous"] + clients)
with col3:
    sort_options = {
        "Date limite (proche)": ("Date de limite", True),
        "Date limite (lointaine)": ("Date de limite", False),
        "Budget (décroissant)": ("Budget", False),
        "Client (A→Z)": ("Client", True),
    }
    sort_choice = st.selectbox("↕️ Trier par", list(sort_options.keys()))


# ============================================
# 6. FILTRAGE & TRI
# ============================================
def is_valid_url(url: str) -> bool:
    """Return True if the URL looks like a real link."""
    if not url or url in ("-", "Non mentionné", "Non spécifié"):
        return False
    return url.startswith("http") or url.startswith("www.")

def fix_url(url: str) -> str:
    """Ensure URL has a scheme."""
    if url.startswith("www."):
        return "https://" + url
    return url

filtered = df.copy()

# Keyword search across Client + Title
if search_query.strip():
    q = search_query.strip().lower()
    mask = (
        filtered['Client'].str.lower().str.contains(q, na=False) |
        filtered['Title'].str.lower().str.contains(q, na=False)
    )
    filtered = filtered[mask]

# Client filter
if client_filter != "Tous":
    filtered = filtered[filtered['Client'] == client_filter]

# Sorting (best-effort — dates are strings so alphabetical sort is approximate)
sort_col, sort_asc = sort_options[sort_choice]
if sort_col in filtered.columns:
    filtered = filtered.sort_values(by=sort_col, ascending=sort_asc, na_position='last')


# ============================================
# 7. STATS BAR
# ============================================
total = len(filtered)
# Count rows where budget is a real value (not "-")
budgeted = filtered[filtered['Budget'].str.strip() != "-"].shape[0] if not filtered.empty else 0

st.markdown(f"""
    <div class="stats-row">
        <div class="stat-card">
            <div class="stat-label">Appels d'offres</div>
            <div class="stat-value">{total}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Avec budget</div>
            <div class="stat-value green">{budgeted}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Sans budget spécifié</div>
            <div class="stat-value red">{total - budgeted}</div>
        </div>
    </div>
""", unsafe_allow_html=True)


# ============================================
# 8. TABLEAU
# ============================================
if filtered.empty:
    st.info("Aucun résultat ne correspond à votre recherche.")
else:
    def truncate(text: str, length: int) -> str:
        text = str(text)
        return text[:length] + "…" if len(text) > length else text

    rows_html = ""
    for _, row in filtered.iterrows():
        client_name = str(row.get('Client', '-'))
        initial = client_name[0].upper() if client_name and client_name not in ("-", "?") else "?"

        title_display   = truncate(row.get('Title', '-'), 100)
        date_pub        = str(row.get('Date de publication', '-'))
        date_limit      = str(row.get('Date de limite', '-'))
        budget          = truncate(row.get('Budget', '-'), 60)
        caution         = truncate(row.get('Caution', '-'), 40)
        url_raw         = str(row.get('URL', '-'))

        if is_valid_url(url_raw):
            action_html = f'<a class="btn-link" href="{fix_url(url_raw)}" target="_blank" rel="noopener">Ouvrir 🔗</a>'
        else:
            action_html = '<span class="btn-disabled">N/A</span>'

        rows_html += f"""
        <tr>
            <td>
                <div class="cell-client">
                    <div class="logo-badge">{initial}</div>
                    <span class="client-name">{client_name}</span>
                </div>
            </td>
            <td class="cell-title">{title_display}</td>
            <td class="cell-date-pub">{date_pub}</td>
            <td class="cell-date-limit">{date_limit}</td>
            <td class="cell-budget">{budget}</td>
            <td class="cell-caution">{caution}</td>
            <td>{action_html}</td>
        </tr>
        """

    table_html = f"""
    <div class="table-wrapper">
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
                {rows_html}
            </tbody>
        </table>
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)


# ============================================
# 9. FOOTER
# ============================================
st.markdown("""
    <div class="portal-footer">
        ⚡ Mise à jour automatique via Supabase · Données en temps réel
    </div>
""", unsafe_allow_html=True)
