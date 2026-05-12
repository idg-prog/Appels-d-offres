import os
import time
import re
import shutil
import zipfile
import subprocess
import traceback
import unicodedata
import requests
import pandas as pd
import ollama
from datetime import datetime, timedelta

# PDF / OCR / DOC
import fitz  # PyMuPDF
from pdf2image import convert_from_path
from PIL import Image
import pytesseract
import docx

# Selenium
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager


# -----------------------------
# CONFIGURATION
# -----------------------------
MODEL_NAME = "qwen2.5"

print("🚀 Initializing configuration...")
download_dir = os.path.join(os.getcwd(), "downloads_temp")
os.makedirs(download_dir, exist_ok=True)

options = webdriver.ChromeOptions()
options.add_argument("--headless=chrome")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-gpu")

prefs = {
    "download.default_directory": download_dir,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
}
options.add_experimental_option("prefs", prefs)

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
wait = WebDriverWait(driver, 25)

# ✅ FIX #3: Increased page load timeout (was 40s — too low for gov portal)
driver.set_page_load_timeout(90)

PDF_PAGE_LIMIT = 10
yesterday = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")

# ✅ FIX #1: Expanded keyword exclusion list to catch infrastructure/works tenders
EXCLUDED_KEYWORDS = [
    # Civil works
    "construction", "travaux", "réhabilitation", "infrastructure",
    "aménagement", "voirie", "route", "autoroute", "pont",
    # Water / electrical networks
    "conduite", "canalisation", "raccordement", "réseau", "adduction",
    "assainissement", "électrique", "électrification", "ligne haute tension",
    # Supplies / equipment
    "fourniture", "achat", "acquisition", "livraison", "matériel",
    # Cleaning / maintenance of physical assets
    "nettoyage", "entretien", "maintenance des bâtiments",
    # Construction lots
    "lot", "génie civil", "bâtiment", "plomberie",
]


# -----------------------------
# TEXT CLEANING
# -----------------------------
def clean_extracted_text(text):
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    cleaned_lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return "\n".join(cleaned_lines)


# -----------------------------
# EXTRACTION HELPERS
# -----------------------------
def extract_text_from_pdf(file_path):
    text = ""
    try:
        doc = fitz.open(file_path)
        page_count = min(len(doc), PDF_PAGE_LIMIT)
        for i in range(page_count):
            text += doc[i].get_text("text") + "\n"
        doc.close()
        print(f"   📄 PyMuPDF extracted {len(text.strip())} chars from {os.path.basename(file_path)}")
    except Exception as e:
        print(f"   ⚠️ PyMuPDF failed on {os.path.basename(file_path)}: {e}")

    if len(text.strip()) < 100:
        print(f"   🔍 Text too short, switching to OCR for {os.path.basename(file_path)}...")
        try:
            pages = convert_from_path(file_path, last_page=PDF_PAGE_LIMIT, dpi=300)
            ocr_text = ""
            for page_num, page_image in enumerate(pages):
                page_ocr = pytesseract.image_to_string(page_image, lang="fra+ara+eng")
                ocr_text += page_ocr + "\n"
                print(f"      OCR page {page_num + 1}: {len(page_ocr)} chars")
            text = ocr_text
            print(f"   📄 OCR total: {len(text.strip())} chars from {os.path.basename(file_path)}")
        except Exception as e:
            print(f"   ❌ OCR failed on {os.path.basename(file_path)}: {e}")

    return clean_extracted_text(text)


def extract_text_from_docx(file_path):
    try:
        doc = docx.Document(file_path)
        text = clean_extracted_text("\n".join(p.text for p in doc.paragraphs))
        print(f"   📄 DOCX extracted {len(text)} chars from {os.path.basename(file_path)}")
        return text
    except Exception as e:
        print(f"   ❌ DOCX extraction failed on {os.path.basename(file_path)}: {e}")
        return ""


def extract_text_from_doc(file_path):
    try:
        process = subprocess.Popen(["antiword", file_path], stdout=subprocess.PIPE)
        stdout, _ = process.communicate()
        text = clean_extracted_text(stdout.decode("utf-8", errors="ignore"))
        print(f"   📄 DOC extracted {len(text)} chars from {os.path.basename(file_path)}")
        return text
    except Exception as e:
        print(f"   ❌ DOC extraction failed on {os.path.basename(file_path)}: {e}")
        return ""


def extract_from_zip(file_path):
    try:
        extract_to = os.path.splitext(file_path)[0]
        os.makedirs(extract_to, exist_ok=True)
        with zipfile.ZipFile(file_path, "r") as z:
            z.extractall(extract_to)
        return extract_to
    except Exception as e:
        print(f"   ❌ ZIP extraction failed: {e}")
        return None


def clear_download_directory():
    for item in os.listdir(download_dir):
        path = os.path.join(download_dir, item)
        try:
            if os.path.isfile(path):
                os.unlink(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
        except Exception as e:
            print(f"   ⚠️ Could not delete {path}: {e}")


# ✅ FIX #2: Reduced timeout from 120s to 45s so script doesn't block too long
def wait_for_download_complete(timeout=45):
    elapsed = 0
    while elapsed < timeout:
        files = [f for f in os.listdir(download_dir) if not f.endswith(".crdownload")]
        if files:
            time.sleep(3)  # Wait for file to fully settle
            return os.path.join(download_dir, files[0])
        time.sleep(1)
        elapsed += 1
    print("   ⚠️ Download timed out.")
    return None


# -----------------------------
# AI RESPONSE PARSER
# -----------------------------
def parse_ai_response(content):
    """
    Robust multiline parser using regex with DOTALL.
    Handles bold markers, dashes, and values spanning multiple lines.
    """
    data = {}
    target_keys = ["CLIENT", "VILLE", "BUDGET", "CAUTION", "DATE LIMITE", "SECTEUR", "WHAT", "HOW"]

    content_clean = re.sub(r'[*_]', '', content)

    for i, key in enumerate(target_keys):
        next_keys = target_keys[i + 1:]
        if next_keys:
            lookahead = r'(?=' + '|'.join(re.escape(k) for k in next_keys) + r'\s*:|\Z)'
        else:
            lookahead = r'(?=\Z)'

        pattern = rf'{re.escape(key)}\s*:\s*(.*?){lookahead}'
        match = re.search(pattern, content_clean, re.IGNORECASE | re.DOTALL)
        if match:
            value = match.group(1).strip()
            value = re.sub(r'^[-–—\s]+', '', value)
            value = re.sub(r'\n+', ' ', value).strip()
            if value and value.upper() not in ("N/A", "NON DISPONIBLE", ""):
                data[key] = value

    return data


# -----------------------------
# AI ANALYSIS
# -----------------------------
def analyze_with_ollama(tender_title, extracted_text):
    print(f"🧠 [AI] Analyzing: {tender_title[:60]}...")
    print(f"   Input text length: {len(extracted_text)} chars")

    if not extracted_text.strip():
        print("   ⚠️ Empty text passed to AI — skipping analysis.")
        return {}

    context_text = extracted_text[:10000]

    prompt = f"""Tu es un Expert Senior en Marchés Publics Marocains.
Analyse le document ci-dessous et extrais les informations demandées.

--- RÈGLES STRICTES ---
1. Réponds UNIQUEMENT avec les champs listés ci-dessous, un par ligne.
2. Ne mets aucun texte avant ou après les champs.
3. Si une information n'est pas trouvée, écris N/A.
4. BUDGET : cherche "MAD", "DH", "TTC", "Estimation", "budget", "coût", "montant" (souvent à la fin du document).
5. DATE LIMITE : cherche "date limite", "délai", "soumission", "dépôt", "offres".
6. CAUTION : cherche "cautionnement", "garantie", "caution", "dépôt de garantie".
7. CLIENT : cherche le nom de l'organisme, maître d'ouvrage, institution, ONG ou entreprise commanditaire.
8. VILLE : cherche la ville ou région concernée par le marché.
9. SECTEUR : choisis UN secteur parmi la liste.
10. WHAT : décris concrètement l'objet du marché (ce qui est demandé).
11. HOW : décris la méthodologie imposée ou attendue.

--- SECTEURS DISPONIBLES ---
Formation & Coaching, Recrutement & RH, Études & Conseil, Audit & Expertise Comptable, Informatique & Digital, Communication & Événementiel, Travaux de Bâtiment, Génie Civil & Routes, Installations Électriques, Plomberie & Chauffage, Achat de Fournitures de Bureau, Mobilier & Aménagement, Matériel Médical, Nettoyage & Gardiennage, Espaces Verts, Transport & Logistique, Restauration & Catering, Maintenance Technique, Énergies Renouvelables, Gardiennage & Sécurité, Archivage.

--- FORMAT DE RÉPONSE (respecte exactement ces clés) ---
CLIENT : 
VILLE : 
BUDGET : 
CAUTION : 
DATE LIMITE : 
SECTEUR : 
WHAT : 
HOW : 

--- DOCUMENT À ANALYSER ---
TITRE: {tender_title}

CONTENU:
{context_text}
"""

    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[{'role': 'user', 'content': prompt}],
            options={"temperature": 0.1}
        )
        raw_content = response['message']['content']
        print(f"   Raw AI response preview:\n{raw_content[:600]}\n{'---' * 20}")

        data = parse_ai_response(raw_content)
        print(f"   Parsed fields: {list(data.keys())}")
        return data

    except Exception as e:
        print(f"❌ AI Error: {e}")
        return {}


# -----------------------------
# SAFE NAVIGATION HELPER
# -----------------------------
def safe_get(url, retries=2):
    """
    ✅ FIX #3: Wraps driver.get() to catch TimeoutException without
    killing the entire run. Returns True if navigation succeeded.
    """
    for attempt in range(1, retries + 1):
        try:
            driver.get(url)
            return True
        except TimeoutException:
            print(f"   ⚠️ Page load timed out (attempt {attempt}/{retries}): {url[:80]}")
            if attempt < retries:
                time.sleep(5)
    return False


# -----------------------------
# MAIN SCRAPER
# -----------------------------
all_final_results = []

try:
    print("\n--- Starting scraping: Portail Marchés Publics ---")

    # ✅ FIX #3: Wrap initial navigation too
    if not safe_get("https://www.marchespublics.gov.ma/index.php?page=entreprise.EntrepriseAdvancedSearch&searchAnnCons"):
        raise RuntimeError("Failed to load search page after retries.")

    # Select "Services" activity domain
    wait.until(EC.element_to_be_clickable(
        (By.ID, "ctl0_CONTENU_PAGE_AdvancedSearch_domaineActivite_linkDisplay")
    )).click()
    wait.until(lambda d: len(d.window_handles) > 1)
    driver.switch_to.window(driver.window_handles[-1])
    wait.until(EC.element_to_be_clickable(
        (By.ID, "ctl0_CONTENU_PAGE_repeaterCategorie_ctl2_idCategorie")
    )).click()
    driver.find_element(By.ID, "ctl0_CONTENU_PAGE_validateButton").click()
    driver.switch_to.window(driver.window_handles[0])

    # Set yesterday's date
    date_input = driver.find_element(
        By.ID, "ctl0_CONTENU_PAGE_AdvancedSearch_dateMiseEnLigneCalculeStart"
    )
    date_input.clear()
    date_input.send_keys(yesterday)
    driver.find_element(By.ID, "ctl0_CONTENU_PAGE_AdvancedSearch_lancerRecherche").click()

    # Show 500 results per page
    wait.until(EC.presence_of_element_located(
        (By.ID, "ctl0_CONTENU_PAGE_resultSearch_listePageSizeTop")
    ))
    Select(driver.find_element(
        By.ID, "ctl0_CONTENU_PAGE_resultSearch_listePageSizeTop"
    )).select_by_value("500")
    time.sleep(3)

    # Scrape result rows
    rows = driver.find_elements(By.XPATH, '//table[@class="table-results"]/tbody/tr')
    print(f"   Found {len(rows)} rows in results table")

    data_list = []
    for row in rows:
        try:
            ref   = row.find_element(By.CSS_SELECTOR, '.col-450 .ref').text
            objet = row.find_element(By.XPATH, './/div[contains(@id,"panelBlocObjet")]').text.replace("Objet : ", "")
            buyer = row.find_element(By.XPATH, './/div[contains(@id,"panelBlocDenomination")]').text.replace("Acheteur public : ", "")
            url   = row.find_element(By.XPATH, './/td[@class="actions"]//a[1]').get_attribute("href")
            data_list.append({"reference": ref, "objet": objet, "acheteur": buyer, "url": url})
        except:
            continue

    df = pd.DataFrame(data_list)
    print(f"   Scraped {len(df)} tenders before filtering")

    # ✅ FIX #1: Use expanded exclusion list
    exclusion_pattern = '|'.join(re.escape(k) for k in EXCLUDED_KEYWORDS)
    df = df[~df['objet'].str.lower().str.contains(exclusion_pattern, na=False)]
    print(f"   {len(df)} tenders remaining after keyword filter")

    # Process each tender
    for idx, row in df.iterrows():
        print(f"\n📂 [{idx + 1}/{len(df)}] AO: {row['reference']} — {row['objet'][:60]}")

        # ✅ FIX #3: Safe navigation — skip tender if page won't load
        if not safe_get(row['url']):
            print(f"   ❌ Could not load tender page — saving partial result and skipping.")
            all_final_results.append({
                "Date Publication": yesterday,
                "Reference":        row['reference'],
                "Organisme":        row['acheteur'],
                "Secteur":          "N/A",
                "Objet":            row['objet'],
                "Budget":           "N/A",
                "Ville":            "N/A",
                "Caution":          "N/A",
                "Date Limite":      "N/A",
                "Nature (WHAT)":    "N/A",
                "Methode (HOW)":    "N/A",
                "Lien AO":          row['url'],
            })
            clear_download_directory()
            continue

        merged_text = ""

        try:
            # --- Download DCE ---
            wait.until(EC.element_to_be_clickable(
                (By.ID, "ctl0_CONTENU_PAGE_linkDownloadDce")
            )).click()

            wait.until(EC.presence_of_element_located(
                (By.ID, "ctl0_CONTENU_PAGE_EntrepriseFormulaireDemande_nom")
            )).send_keys("Lachhab")
            driver.find_element(By.ID, "ctl0_CONTENU_PAGE_EntrepriseFormulaireDemande_prenom").send_keys("Anas")
            driver.find_element(By.ID, "ctl0_CONTENU_PAGE_EntrepriseFormulaireDemande_email").send_keys("anas@example.com")
            driver.find_element(By.ID, "ctl0_CONTENU_PAGE_EntrepriseFormulaireDemande_accepterConditions").click()
            driver.find_element(By.ID, "ctl0_CONTENU_PAGE_validateButton").click()
            wait.until(EC.element_to_be_clickable(
                (By.ID, "ctl0_CONTENU_PAGE_EntrepriseDownloadDce_completeDownload")
            )).click()

            # ✅ FIX #2: 45s download timeout (was 120s)
            downloaded = wait_for_download_complete(timeout=45)

            if downloaded:
                paths = []
                if downloaded.endswith(".zip"):
                    u_dir = extract_from_zip(downloaded)
                    if u_dir:
                        for r, _, f_list in os.walk(u_dir):
                            for f in f_list:
                                paths.append(os.path.join(r, f))
                else:
                    paths.append(downloaded)

                print(f"   Files to extract: {[os.path.basename(p) for p in paths]}")

                extracted_parts = []
                for p in paths:
                    ext = os.path.splitext(p)[1].lower()
                    if ext == ".pdf":
                        extracted_parts.append(extract_text_from_pdf(p))
                    elif ext == ".docx":
                        extracted_parts.append(extract_text_from_docx(p))
                    elif ext == ".doc":
                        extracted_parts.append(extract_text_from_doc(p))

                merged_text = "\n\n".join([t for t in extracted_parts if t.strip()])
                print(f"   Total merged text: {len(merged_text)} chars")

            else:
                print("   ⚠️ No file downloaded within timeout.")

            if len(merged_text.strip()) < 50:
                print("   ⚠️ Very little text extracted — AI results may be incomplete.")

            # AI Analysis
            ai_info = analyze_with_ollama(row['objet'], merged_text)

            all_final_results.append({
                "Date Publication": yesterday,
                "Reference":        row['reference'],
                "Organisme":        ai_info.get("CLIENT",      row['acheteur']),
                "Secteur":          ai_info.get("SECTEUR",     "N/A"),
                "Objet":            row['objet'],
                "Budget":           ai_info.get("BUDGET",      "N/A"),
                "Ville":            ai_info.get("VILLE",       "N/A"),
                "Caution":          ai_info.get("CAUTION",     "N/A"),
                "Date Limite":      ai_info.get("DATE LIMITE", "N/A"),
                "Nature (WHAT)":    ai_info.get("WHAT",        "N/A"),
                "Methode (HOW)":    ai_info.get("HOW",         "N/A"),
                "Lien AO":          row['url'],
            })

        except Exception as e:
            print(f"   ⚠️ Failed processing AO {row['reference']}: {e}")
            traceback.print_exc()
            # Save partial row so we don't lose it
            all_final_results.append({
                "Date Publication": yesterday,
                "Reference":        row['reference'],
                "Organisme":        row['acheteur'],
                "Secteur":          "N/A",
                "Objet":            row['objet'],
                "Budget":           "N/A",
                "Ville":            "N/A",
                "Caution":          "N/A",
                "Date Limite":      "N/A",
                "Nature (WHAT)":    "N/A",
                "Methode (HOW)":    "N/A",
                "Lien AO":          row['url'],
            })

        finally:
            clear_download_directory()

finally:
    driver.quit()
    print("\n🔒 Browser closed.")

    if all_final_results:
        df_out = pd.DataFrame(all_final_results)
        df_out.to_csv("tender_results_summary.csv", index=False, encoding="utf-8-sig")
        print(f"\n✅ SUCCESS: Saved {len(df_out)} tenders to tender_results_summary.csv")
        print(df_out.to_string())
    else:
        print(f"\nℹ️ No results to save for date: {yesterday}")
