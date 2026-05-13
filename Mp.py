import os
import time
import re
import shutil
import zipfile
import subprocess
import traceback
import unicodedata
import random
import pandas as pd
from datetime import datetime, timedelta

# PDF / OCR / DOC
import fitz  # PyMuPDF
from pdf2image import convert_from_path
from PIL import Image
import pytesseract
import docx

# Selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from supabase import create_client, Client

# Replace the Configuration section or add after existing config
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_KEY or not SUPABASE_URL:
    raise ValueError("Please set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)

prefs = {
    "download.default_directory": download_dir,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
}
options.add_experimental_option("prefs", prefs)

service = Service()
driver = webdriver.Chrome(service=service, options=options)
wait = WebDriverWait(driver, 25)
driver.set_page_load_timeout(40)
print("✅ WebDriver initialized.")

PDF_PAGE_LIMIT = 10

# -----------------------------
# HELPER FUNCTIONS
# -----------------------------
def clean_extracted_text(text):
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"Page\s*\d+\s*/\s*\d+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[\u0000-\u001f]+", "", text)
    cleaned_lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    pretty = "\n".join(cleaned_lines)
    pretty = re.sub(r"\n{3,}", "\n\n", pretty)
    return pretty.strip()


def extract_text_from_pdf(file_path):
    text = ""
    try:
        doc = fitz.open(file_path)
        page_count = min(len(doc), PDF_PAGE_LIMIT)
        for i in range(page_count):
            text += doc[i].get_text("text") + "\n"
        doc.close()
    except Exception:
        text = ""
    if len(text.strip()) < 50:
        try:
            pages = convert_from_path(file_path, last_page=PDF_PAGE_LIMIT)
            for page_image in pages:
                text += pytesseract.image_to_string(page_image, lang="fra+ara+eng") + "\n"
        except Exception as e:
            print(f"⚠️ OCR failed for {file_path}: {e}")
    return clean_extracted_text(text)


def extract_text_from_docx(file_path):
    try:
        doc = docx.Document(file_path)
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        return clean_extracted_text(text)
    except Exception:
        return ""


def extract_text_from_doc(file_path):
    try:
        process = subprocess.Popen(["antiword", file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, _ = process.communicate()
        text = stdout.decode("utf-8", errors="ignore")
        return clean_extracted_text(text)
    except Exception as e:
        print(f"⚠️ Antiword failed for {file_path}: {e}")
        return ""


def extract_from_zip(file_path):
    try:
        extract_to = os.path.splitext(file_path)[0]
        os.makedirs(extract_to, exist_ok=True)
        with zipfile.ZipFile(file_path, "r") as zip_ref:
            zip_ref.extractall(extract_to)
        return extract_to
    except Exception as e:
        print(f"⚠️ Failed to unzip {file_path}: {e}")
        return None


def clear_download_directory():
    for item in os.listdir(download_dir):
        path = os.path.join(download_dir, item)
        try:
            if os.path.isfile(path) or os.path.islink(path):
                os.unlink(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
        except Exception as e:
            print(f"⚠️ Failed to delete {path}: {e}")


def wait_for_download_complete(timeout=120):
    elapsed = 0
    stable_count = 0
    last_size = -1

    while elapsed < timeout:
        files = [f for f in os.listdir(download_dir)
                 if not f.endswith(".crdownload") and not f.startswith(".com.google.Chrome.")]
        if files:
            file_path = os.path.join(download_dir, files[0])
            size = os.path.getsize(file_path)
            if size == last_size:
                stable_count += 1
            else:
                stable_count = 0
                last_size = size
            if stable_count >= 3:
                return file_path
        else:
            last_size = -1
            stable_count = 0

        time.sleep(1)
        elapsed += 1

    print("⚠️ Timeout waiting for download to finish.")
    return None


# -----------------------------
# MAIN SCRIPT
# -----------------------------
all_processed_tenders = []

try:
    print("\n--- Starting scraping ---")
    driver.get("https://www.marchespublics.gov.ma/index.php?page=entreprise.EntrepriseAdvancedSearch&searchAnnCons")
    time.sleep(2)

    # Step 1: Open "Définir" popup
    define_btn = wait.until(EC.element_to_be_clickable((By.ID, "ctl0_CONTENU_PAGE_AdvancedSearch_domaineActivite_linkDisplay")))
    define_btn.click()
    wait.until(lambda d: len(d.window_handles) > 1)
    driver.switch_to.window(driver.window_handles[-1])

    # Step 2: Select Services checkbox and validate
    checkbox = wait.until(EC.element_to_be_clickable((By.ID, "ctl0_CONTENU_PAGE_repeaterCategorie_ctl2_idCategorie")))
    checkbox.click()
    validate_btn = wait.until(EC.element_to_be_clickable((By.ID, "ctl0_CONTENU_PAGE_validateButton")))
    validate_btn.click()
    driver.switch_to.window(driver.window_handles[0])
    print("✅ Services selected.")

    # Step 3: Set date filter to yesterday
    date_input = driver.find_element(By.ID, "ctl0_CONTENU_PAGE_AdvancedSearch_dateMiseEnLigneCalculeStart")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
    date_input.clear()
    for char in yesterday:
        date_input.send_keys(char)
        time.sleep(random.uniform(0.05, 0.15))
    search_button = driver.find_element(By.ID, "ctl0_CONTENU_PAGE_AdvancedSearch_lancerRecherche")
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", search_button)
    time.sleep(0.8)
    search_button.click()
    time.sleep(2)

    # Step 4: Set results per page
    wait.until(EC.presence_of_element_located((By.ID, "ctl0_CONTENU_PAGE_resultSearch_listePageSizeTop")))
    Select(driver.find_element(By.ID, "ctl0_CONTENU_PAGE_resultSearch_listePageSizeTop")).select_by_value("500")
    time.sleep(2)

    # Step 5: Scrape table
    rows = driver.find_elements(By.XPATH, '//table[@class="table-results"]/tbody/tr')
    data = []
    for row in rows:
        try:
            ref      = row.find_element(By.CSS_SELECTOR, '.col-450 .ref').text
            objet    = row.find_element(By.XPATH, './/div[contains(@id,"panelBlocObjet")]').text.replace("Objet : ", "")
            buyer    = row.find_element(By.XPATH, './/div[contains(@id,"panelBlocDenomination")]').text.replace("Acheteur public : ", "")
            lieux    = row.find_element(By.XPATH, './/div[contains(@id,"panelBlocLieuxExec")]').text.replace("\n", ", ")
            deadline = row.find_element(By.XPATH, './/td[@headers="cons_dateEnd"]').text.replace("\n", " ")
            url      = row.find_element(By.XPATH, './/td[@class="actions"]//a[1]').get_attribute("href")
            data.append({
                "reference": ref,
                "objet": objet,
                "acheteur": buyer,
                "lieux_execution": lieux,
                "date_limite": deadline,
                "first_button_url": url
            })
        except Exception as e:
            print(f"⚠️ Error extracting row: {e}")

    df = pd.DataFrame(data)

    excluded_words = [
        "construction", "installation", "travaux", "fourniture", "achat",
        "equipement", "supply", "acquisition", "nettoyage", "déchets"
    ]
    df = df[~df['objet'].str.lower().str.contains('|'.join(excluded_words), na=False)]
    print(f"✅ {len(df)} valid tenders after filtering.\n")

    # Step 6: Download and extract loop
    fields = {
        "ctl0_CONTENU_PAGE_EntrepriseFormulaireDemande_nom":    "Lachhab",
        "ctl0_CONTENU_PAGE_EntrepriseFormulaireDemande_prenom": "Anas",
        "ctl0_CONTENU_PAGE_EntrepriseFormulaireDemande_email":  "anas.lachhab@example.com"
    }

    for idx, row in df.iterrows():
        link = row['first_button_url']
        print(f"\n🔗 Processing tender {idx+1}/{len(df)}: {link}")

        try:
            driver.get(link)
        except TimeoutException:
            print(f"⚠️ Timeout loading {link}, retrying...")
            try:
                driver.execute_script("window.stop();")
                driver.execute_script("window.location.href = arguments[0];", link)
            except TimeoutException:
                print(f"❌ Still timed out, skipping this tender.")
                continue

        time.sleep(3)
        merged_text = "No document downloaded"

        try:
            download_link = wait.until(EC.element_to_be_clickable((By.ID, "ctl0_CONTENU_PAGE_linkDownloadDce")))
            driver.execute_script("arguments[0].scrollIntoView(true);", download_link)
            download_link.click()

            for fid, value in fields.items():
                inp = wait.until(EC.presence_of_element_located((By.ID, fid)))
                inp.clear()
                inp.send_keys(value)

            checkbox = driver.find_element(By.ID, "ctl0_CONTENU_PAGE_EntrepriseFormulaireDemande_accepterConditions")
            if not checkbox.is_selected():
                checkbox.click()

            valider_button = wait.until(EC.element_to_be_clickable((By.ID, "ctl0_CONTENU_PAGE_validateButton")))
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", valider_button)
            time.sleep(0.5)
            try:
                valider_button.click()
            except ElementClickInterceptedException:
                driver.execute_script("arguments[0].click();", valider_button)

            final_button = wait.until(EC.element_to_be_clickable((By.ID, "ctl0_CONTENU_PAGE_EntrepriseDownloadDce_completeDownload")))
            driver.execute_script("arguments[0].scrollIntoView(true);", final_button)
            final_button.click()
            print("✅ Download started.")

            downloaded_file = wait_for_download_complete()
            if downloaded_file:
                file_paths = []
                if downloaded_file.lower().endswith(".zip"):
                    unzip_dir = extract_from_zip(downloaded_file)
                    if unzip_dir:
                        for r, _, files in os.walk(unzip_dir):
                            for f in files:
                                file_paths.append(os.path.join(r, f))
                else:
                    file_paths.append(downloaded_file)

                file_paths.sort(key=lambda x: "cps" not in os.path.basename(x).lower())

                texts = []
                for fpath in file_paths:
                    fname = os.path.basename(fpath)
                    ext = os.path.splitext(fname)[1].lower()

                    if ext == ".pdf":
                        text = extract_text_from_pdf(fpath)
                    elif ext == ".docx":
                        text = extract_text_from_docx(fpath)
                    elif ext == ".doc":
                        text = extract_text_from_doc(fpath)
                    else:
                        print(f"SKIPPED UNSUPPORTED: {fname}")
                        continue

                    print(f"EXTRACTED {len(text)} chars from {fname}")

                    if text.strip():
                        texts.append(f"--- FILE: {fname} ---\n{text}")

                merged_text = "\n\n".join(texts) or "No relevant text extracted"
            else:
                print("⚠️ Download failed or timed out.")

        except Exception as e:
            print(f"⚠️ Error processing tender {link}: {e}")
            traceback.print_exc()

        # -----------------------------
        # SAVE RESULT
        # -----------------------------
        tender_payload = row.to_dict()
        tender_payload["merged_text"] = merged_text
        all_processed_tenders.append(tender_payload)

        clear_download_directory()
        time.sleep(random.uniform(2, 4))

finally:
    # -----------------------------
    # SYNC TO SUPABASE (Replaces CSV part)
    # -----------------------------
    if all_processed_tenders:
        print(f"\n📤 Syncing {len(all_processed_tenders)} tenders to Supabase...")
        
        for tender in all_processed_tenders:
            # Prepare the data to match your Supabase columns
            # We map your existing keys to the database columns
            data_to_insert = {
                "Date": tender.get("date_limite"),
                "Title": tender.get("objet"),
                "URL": tender.get("first_button_url"),
                "Extracted_Text": tender.get("merged_text"),
                "Source": "MarchesPublics" # Identifying the origin
            }
            
            try:
                # Use upsert to avoid duplicates if the URL already exists
                supabase.table("Tenders Raw Data").upsert(data_to_insert, on_conflict="URL").execute()
                print(f"✅ Synced: {data_to_insert['Title'][:50]}...")
            except Exception as e:
                print(f"❌ Failed to sync {tender.get('reference')}: {e}")
    else:
        print("ℹ️ No tenders processed to sync.")

    # Cleanup remains the same
    try:
        driver.quit()
    except Exception:
        pass
