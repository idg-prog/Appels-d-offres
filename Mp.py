import os
import time
import re
import shutil
import zipfile
import subprocess
import traceback
import unicodedata
import random
import requests
import pandas as pd
import json
import ollama  # <--- Added
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

# ... (options setup)


# -----------------------------
# CONFIGURATION
# -----------------------------
MODEL_NAME = "qwen2.5" # <--- Qwen 7B for better results
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

# Update this part:
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
wait = WebDriverWait(driver, 25)
driver.set_page_load_timeout(40)

PDF_PAGE_LIMIT = 10

# -----------------------------
# AI ANALYSIS FUNCTION
# -----------------------------
def analyze_with_ollama(tender_title, extracted_text):
    """Sends text to local Qwen 2.5 and parses the result."""
    print(f"🧠 [AI] Analyzing with {MODEL_NAME}...")
    context_text = extracted_text[:10000] # Increased context

    prompt = f"""
    Tu es un Expert Senior en Marchés Publics Marocains.
    Extraits les informations suivantes à partir du texte. Utilise EXACTEMENT ces mots-clés suivis de deux points.

    CLIENT : 
    VILLE : 
    BUDGET : 
    CAUTION : 
    DATE LIMITE : 
    SECTEUR : 
    WHAT : 
    HOW : 

    --- SECTEURS POSSIBLES ---
    Formation & Coaching, Recrutement & RH, Études & Conseil, Audit & Expertise Comptable, Informatique & Digital, Communication & Événementiel, Travaux de Bâtiment, Génie Civil & Routes, Installations Électriques, Plomberie & Chauffage, Achat de Fournitures de Bureau, Mobilier & Aménagement, Matériel Médical, Nettoyage & Gardiennage, Espaces Verts, Transport & Logistique, Restauration & Catering, Maintenance Technique, Énergies Renouvelables, Gardiennage & Sécurité, Archivage.

    --- DOCUMENT ---
    TITRE: {tender_title}
    CONTENU: {context_text}
    """

    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[{'role': 'user', 'content': prompt}]
        )
        content = response['message']['content']
        
        data = {}
        target_keys = ["CLIENT", "VILLE", "BUDGET", "CAUTION", "DATE LIMITE", "SECTEUR", "WHAT", "HOW"]
        
        for line in content.split('\n'):
            clean_line = re.sub(r'[*_\-]', '', line).strip()
            for k in target_keys:
                if clean_line.upper().startswith(k):
                    if ':' in clean_line:
                        _, val = clean_line.split(':', 1)
                        data[k] = val.strip()
        return data
    except Exception as e:
        print(f"❌ AI Error: {e}")
        return {}

# -----------------------------
# EXTRACTION HELPERS (Keep existing)
# -----------------------------
def clean_extracted_text(text):
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    cleaned_lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return "\n".join(cleaned_lines)

def extract_text_from_pdf(file_path):
    text = ""
    try:
        doc = fitz.open(file_path)
        page_count = min(len(doc), PDF_PAGE_LIMIT)
        for i in range(page_count):
            text += doc[i].get_text("text") + "\n"
        doc.close()
    except: pass
    if len(text.strip()) < 50:
        try:
            pages = convert_from_path(file_path, last_page=PDF_PAGE_LIMIT)
            for page_image in pages:
                text += pytesseract.image_to_string(page_image, lang="fra+ara+eng") + "\n"
        except: pass
    return clean_extracted_text(text)

def extract_text_from_docx(file_path):
    try:
        doc = docx.Document(file_path)
        return clean_extracted_text("\n".join(p.text for p in doc.paragraphs))
    except: return ""

def extract_text_from_doc(file_path):
    try:
        process = subprocess.Popen(["antiword", file_path], stdout=subprocess.PIPE)
        stdout, _ = process.communicate()
        return clean_extracted_text(stdout.decode("utf-8", errors="ignore"))
    except: return ""

def extract_from_zip(file_path):
    try:
        extract_to = os.path.splitext(file_path)[0]
        os.makedirs(extract_to, exist_ok=True)
        with zipfile.ZipFile(file_path, "r") as z: z.extractall(extract_to)
        return extract_to
    except: return None

def clear_download_directory():
    for item in os.listdir(download_dir):
        path = os.path.join(download_dir, item)
        if os.path.isfile(path): os.unlink(path)
        elif os.path.isdir(path): shutil.rmtree(path)

def wait_for_download_complete(timeout=120):
    elapsed = 0
    while elapsed < timeout:
        files = [f for f in os.listdir(download_dir) if not f.endswith(".crdownload")]
        if files:
            time.sleep(3) # Wait for file to settle
            return os.path.join(download_dir, files[0])
        time.sleep(1)
        elapsed += 1
    return None

# -----------------------------
# MAIN SCRAPER
# -----------------------------
all_final_results = []

try:
    print("\n--- Starting scraping Portails Marches Publics ---")
    driver.get("https://www.marchespublics.gov.ma/index.php?page=entreprise.EntrepriseAdvancedSearch&searchAnnCons")
    
    # Select Services
    wait.until(EC.element_to_be_clickable((By.ID, "ctl0_CONTENU_PAGE_AdvancedSearch_domaineActivite_linkDisplay"))).click()
    wait.until(lambda d: len(d.window_handles) > 1)
    driver.switch_to.window(driver.window_handles[-1])
    wait.until(EC.element_to_be_clickable((By.ID, "ctl0_CONTENU_PAGE_repeaterCategorie_ctl2_idCategorie"))).click()
    driver.find_element(By.ID, "ctl0_CONTENU_PAGE_validateButton").click()
    driver.switch_to.window(driver.window_handles[0])

    # Yesterday's date
    date_input = driver.find_element(By.ID, "ctl0_CONTENU_PAGE_AdvancedSearch_dateMiseEnLigneCalculeStart")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
    date_input.clear()
    date_input.send_keys(yesterday)
    driver.find_element(By.ID, "ctl0_CONTENU_PAGE_AdvancedSearch_lancerRecherche").click()
    
    # 500 Results per page
    wait.until(EC.presence_of_element_located((By.ID, "ctl0_CONTENU_PAGE_resultSearch_listePageSizeTop")))
    Select(driver.find_element(By.ID, "ctl0_CONTENU_PAGE_resultSearch_listePageSizeTop")).select_by_value("500")
    time.sleep(3)

    rows = driver.find_elements(By.XPATH, '//table[@class="table-results"]/tbody/tr')
    data_list = []
    for row in rows:
        try:
            ref = row.find_element(By.CSS_SELECTOR, '.col-450 .ref').text
            objet = row.find_element(By.XPATH, './/div[contains(@id,"panelBlocObjet")]').text.replace("Objet : ", "")
            buyer = row.find_element(By.XPATH, './/div[contains(@id,"panelBlocDenomination")]').text.replace("Acheteur public : ", "")
            url = row.find_element(By.XPATH, './/td[@class="actions"]//a[1]').get_attribute("href")
            data_list.append({"reference": ref, "objet": objet, "acheteur": buyer, "url": url})
        except: continue

    df = pd.DataFrame(data_list)
    # Filter keywords
    excluded = ["construction", "travaux", "fourniture", "achat", "nettoyage"]
    df = df[~df['objet'].str.lower().str.contains('|'.join(excluded), na=False)]

    # Download & Analyze
    for idx, row in df.iterrows():
        print(f"\n📂 [{idx+1}/{len(df)}] AO: {row['reference']}")
        driver.get(row['url'])
        merged_text = ""
        
        try:
            # Download Logic
            wait.until(EC.element_to_be_clickable((By.ID, "ctl0_CONTENU_PAGE_linkDownloadDce"))).click()
            wait.until(EC.presence_of_element_located((By.ID, "ctl0_CONTENU_PAGE_EntrepriseFormulaireDemande_nom"))).send_keys("Lachhab")
            driver.find_element(By.ID, "ctl0_CONTENU_PAGE_EntrepriseFormulaireDemande_prenom").send_keys("Anas")
            driver.find_element(By.ID, "ctl0_CONTENU_PAGE_EntrepriseFormulaireDemande_email").send_keys("anas@example.com")
            driver.find_element(By.ID, "ctl0_CONTENU_PAGE_EntrepriseFormulaireDemande_accepterConditions").click()
            driver.find_element(By.ID, "ctl0_CONTENU_PAGE_validateButton").click()
            wait.until(EC.element_to_be_clickable((By.ID, "ctl0_CONTENU_PAGE_EntrepriseDownloadDce_completeDownload"))).click()
            
            downloaded = wait_for_download_complete()
            if downloaded:
                paths = []
                if downloaded.endswith(".zip"):
                    u_dir = extract_from_zip(downloaded)
                    if u_dir:
                        for r, _, f_list in os.walk(u_dir):
                            for f in f_list: paths.append(os.path.join(r, f))
                else: paths.append(downloaded)

                extracted_parts = []
                for p in paths:
                    ext = os.path.splitext(p)[1].lower()
                    if ext == ".pdf": extracted_parts.append(extract_text_from_pdf(p))
                    elif ext == ".docx": extracted_parts.append(extract_text_from_docx(p))
                
                merged_text = "\n\n".join(extracted_parts)

            # AI Analysis
            ai_info = analyze_with_ollama(row['objet'], merged_text)

            # Final Row Construction
            all_final_results.append({
                "Date Publication": yesterday,
                "Reference": row['reference'],
                "Organisme": ai_info.get("CLIENT", row['acheteur']),
                "Secteur": ai_info.get("SECTEUR", "N/A"),
                "Objet": row['objet'],
                "Budget": ai_info.get("BUDGET", "N/A"),
                "Ville": ai_info.get("VILLE", "N/A"),
                "Caution": ai_info.get("CAUTION", "N/A"),
                "Date Limite": ai_info.get("DATE LIMITE", "N/A"),
                "Nature (WHAT)": ai_info.get("WHAT", "N/A"),
                "Methode (HOW)": ai_info.get("HOW", "N/A"),
                "Lien AO": row['url']
            })

        except Exception as e:
            print(f"⚠️ Failed processing: {e}")
        
        clear_download_directory()

finally:
    if all_final_results:
        df_out = pd.DataFrame(all_final_results)
        df_out.to_csv("tender_results_summary.csv", index=False, encoding="utf-8-sig")
        print(f"\n✅ SUCCESS: Saved {len(df_out)} analysis to tender_results_summary.csv")
    driver.quit()
