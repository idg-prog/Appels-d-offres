import os
import time
import re
import shutil
import zipfile
import subprocess
import traceback
import unicodedata
import pandas as pd
from datetime import datetime, timedelta

# PDF / OCR / DOC
import fitz  # PyMuPDF
from pdf2image import convert_from_path
import pytesseract
import docx

# Selenium
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager


# -----------------------------
# CONFIGURATION
# -----------------------------
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
driver.set_page_load_timeout(90)

PDF_PAGE_LIMIT = 15
yesterday = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")

EXCLUDED_KEYWORDS = [
    "construction", "travaux", "réhabilitation", "infrastructure",
    "aménagement", "voirie", "route", "autoroute", "pont",
    "conduite", "canalisation", "raccordement", "réseau", "adduction",
    "assainissement", "électrique", "électrification",
    "fourniture", "achat", "acquisition", "livraison", "matériel",
    "nettoyage", "lot", "génie civil", "bâtiment", "plomberie",
    "géotechnique", "topographique", "hydraulique", "étude de sol",
]


# -----------------------------
# HELPERS
# -----------------------------
def clean_text(text):
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return "\n".join(lines)


def extract_text_from_pdf(file_path):
    text = ""
    try:
        doc = fitz.open(file_path)
        for i in range(min(len(doc), PDF_PAGE_LIMIT)):
            text += doc[i].get_text("text") + "\n"
        doc.close()
        print(f"   📄 PyMuPDF: {len(text.strip())} chars — {os.path.basename(file_path)}")
    except Exception as e:
        print(f"   ⚠️ PyMuPDF failed: {e}")

    if len(text.strip()) < 100:
        print(f"   🔍 Switching to OCR...")
        try:
            pages = convert_from_path(file_path, last_page=PDF_PAGE_LIMIT, dpi=200)
            ocr = ""
            for p in pages:
                ocr += pytesseract.image_to_string(p, lang="fra+ara+eng") + "\n"
            text = ocr
            print(f"   📄 OCR: {len(text.strip())} chars")
        except Exception as e:
            print(f"   ❌ OCR failed: {e}")

    return clean_text(text)


def extract_text_from_docx(file_path):
    try:
        doc = docx.Document(file_path)
        text = clean_text("\n".join(p.text for p in doc.paragraphs))
        print(f"   📄 DOCX: {len(text)} chars — {os.path.basename(file_path)}")
        return text
    except Exception as e:
        print(f"   ❌ DOCX failed: {e}")
        return ""


def extract_text_from_doc(file_path):
    try:
        proc = subprocess.Popen(["antiword", file_path], stdout=subprocess.PIPE)
        out, _ = proc.communicate()
        text = clean_text(out.decode("utf-8", errors="ignore"))
        print(f"   📄 DOC: {len(text)} chars — {os.path.basename(file_path)}")
        return text
    except Exception as e:
        print(f"   ❌ DOC failed: {e}")
        return ""


def extract_from_zip(file_path):
    try:
        out_dir = os.path.splitext(file_path)[0]
        os.makedirs(out_dir, exist_ok=True)
        with zipfile.ZipFile(file_path, "r") as z:
            z.extractall(out_dir)
        return out_dir
    except Exception as e:
        print(f"   ❌ ZIP failed: {e}")
        return None


def clear_downloads():
    for item in os.listdir(download_dir):
        path = os.path.join(download_dir, item)
        try:
            if os.path.isfile(path):
                os.unlink(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
        except:
            pass


def wait_for_download(timeout=20):
    for _ in range(timeout):
        files = [f for f in os.listdir(download_dir) if not f.endswith(".crdownload")]
        if files:
            time.sleep(2)
            return os.path.join(download_dir, files[0])
        time.sleep(1)
    print("   ⚠️ Download timed out.")
    return None


def safe_get(url, retries=2):
    for attempt in range(1, retries + 1):
        try:
            driver.get(url)
            return True
        except TimeoutException:
            print(f"   ⚠️ Page load timeout (attempt {attempt}/{retries})")
            if attempt < retries:
                time.sleep(3)
    return False


def extract_all_files(downloaded_path):
    """Walk a downloaded file or zip and extract all text."""
    paths = []
    if downloaded_path.endswith(".zip"):
        u_dir = extract_from_zip(downloaded_path)
        if u_dir:
            for root, _, files in os.walk(u_dir):
                for f in files:
                    paths.append(os.path.join(root, f))
    else:
        paths.append(downloaded_path)

    parts = []
    for p in paths:
        ext = os.path.splitext(p)[1].lower()
        if ext == ".pdf":
            parts.append(extract_text_from_pdf(p))
        elif ext == ".docx":
            parts.append(extract_text_from_docx(p))
        elif ext == ".doc":
            parts.append(extract_text_from_doc(p))

    return "\n\n".join([t for t in parts if t.strip()])


# -----------------------------
# MAIN SCRAPER
# -----------------------------
all_results = []

try:
    print(f"\n--- Scraping Marchés Publics for {yesterday} ---")

    if not safe_get("https://www.marchespublics.gov.ma/index.php?page=entreprise.EntrepriseAdvancedSearch&searchAnnCons"):
        raise RuntimeError("Could not load search page.")

    # Select Services
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

    # Date filter
    date_input = driver.find_element(
        By.ID, "ctl0_CONTENU_PAGE_AdvancedSearch_dateMiseEnLigneCalculeStart"
    )
    date_input.clear()
    date_input.send_keys(yesterday)
    driver.find_element(By.ID, "ctl0_CONTENU_PAGE_AdvancedSearch_lancerRecherche").click()

    # 500 per page
    wait.until(EC.presence_of_element_located(
        (By.ID, "ctl0_CONTENU_PAGE_resultSearch_listePageSizeTop")
    ))
    Select(driver.find_element(
        By.ID, "ctl0_CONTENU_PAGE_resultSearch_listePageSizeTop"
    )).select_by_value("500")
    time.sleep(3)

    # Collect rows
    rows = driver.find_elements(By.XPATH, '//table[@class="table-results"]/tbody/tr')
    print(f"   Found {len(rows)} total rows")

    data_list = []
    for row in rows:
        try:
            ref   = row.find_element(By.CSS_SELECTOR, '.col-450 .ref').text.strip()
            objet = row.find_element(By.XPATH, './/div[contains(@id,"panelBlocObjet")]').text.replace("Objet : ", "").strip()
            buyer = row.find_element(By.XPATH, './/div[contains(@id,"panelBlocDenomination")]').text.replace("Acheteur public : ", "").strip()
            url   = row.find_element(By.XPATH, './/td[@class="actions"]//a[1]').get_attribute("href")
            data_list.append({"reference": ref, "objet": objet, "acheteur": buyer, "url": url})
        except:
            continue

    df = pd.DataFrame(data_list)
    print(f"   {len(df)} rows scraped")

    # Keyword filter
    excl_pattern = '|'.join(re.escape(k) for k in EXCLUDED_KEYWORDS)
    df = df[~df['objet'].str.lower().str.contains(excl_pattern, na=False)]
    print(f"   {len(df)} rows after keyword filter")

    # Process each tender
    for i, row in df.iterrows():
        print(f"\n📂 [{i+1}/{len(df)}] {row['reference']} — {row['objet'][:60]}")

        if not safe_get(row['url']):
            print("   ❌ Could not load page — saving without document text.")
            all_results.append({
                "Date Publication": yesterday,
                "Reference":        row['reference'],
                "Titre":            row['objet'],
                "Organisme":        row['acheteur'],
                "Texte Extrait":    "",
                "Lien":             row['url'],
            })
            clear_downloads()
            continue

        doc_text = ""

        try:
            # Fill download form
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

            downloaded = wait_for_download(timeout=20)
            if downloaded:
                doc_text = extract_all_files(downloaded)
                print(f"   ✅ Extracted {len(doc_text)} chars total")
            else:
                print("   ⚠️ Nothing downloaded.")

        except Exception as e:
            print(f"   ⚠️ Download/extract error: {e}")

        all_results.append({
            "Date Publication": yesterday,
            "Reference":        row['reference'],
            "Titre":            row['objet'],
            "Organisme":        row['acheteur'],
            "Texte Extrait":    doc_text,
            "Lien":             row['url'],
        })

        clear_downloads()

finally:
    driver.quit()
    print("\n🔒 Browser closed.")

    if all_results:
        df_out = pd.DataFrame(all_results)
        df_out.to_csv("results.csv", index=False, encoding="utf-8-sig")
        print(f"\n✅ Saved {len(df_out)} tenders to results.csv")
    else:
        print(f"\nℹ️ No results for {yesterday}")
