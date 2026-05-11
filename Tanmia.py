import pandas as pd
import requests
import os
import zipfile
import io
import tempfile
import pytesseract
from PIL import Image
import fitz  # PyMuPDF
from docx import Document
from bs4 import BeautifulSoup as bs
import PyPDF2
from datetime import datetime, timedelta
import re
import unicodedata
import time

# --- CONFIG ---
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
OCR_LANGS = "ara+fra+eng"  # Arabic, French, English
BASE_URL = "https://tanmia.ma/appels-doffres/"
MONTHS_FR = ["janvier","février","mars","avril","mai","juin","juillet",
             "août","septembre","octobre","novembre","décembre"]

# --- DATE CONFIG ---
today = datetime.now() - timedelta(days=1)
TARGET_DATE_STR = f"{today.day} {MONTHS_FR[today.month-1]} {today.year}"
print(f"📅 Target date: {TARGET_DATE_STR}")

# --- HELPER FUNCTIONS ---

def clean_text(text):
    """Clean and normalize extracted text."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

def extract_text_with_ocr(file_bytes, filename=""):
    """OCR using PyMuPDF and Tesseract."""
    print(f"🔍 [OCR] Starting OCR on {os.path.basename(filename)} ...")
    text = ""
    try:
        pdf_doc = fitz.open(stream=file_bytes, filetype="pdf")
        for i, page in enumerate(pdf_doc):
            print(f"🧠 [OCR] Processing page {i+1}/{len(pdf_doc)} ...")
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            page_text = pytesseract.image_to_string(img, lang=OCR_LANGS)
            page_text = clean_text(page_text)
            text += f"\n\n[OCR PAGE {i+1}/{len(pdf_doc)}]\n{page_text}"
        print(f"✅ [OCR] Finished OCR ({len(text)} chars)")
    except Exception as e:
        text = f"[OCR failed: {e}]"
        print(f"❌ [OCR] Error on {filename}: {e}")
    return text

def extract_text_from_pdf(file_bytes, filename=""):
    """Extract text from PDF, fallback to OCR."""
    print(f"📄 [PDF] Extracting from {os.path.basename(filename)} ...")
    text = ""
    try:
        with io.BytesIO(file_bytes) as pdf_stream:
            reader = PyPDF2.PdfReader(pdf_stream)
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                page_text = clean_text(page_text)
                if page_text:
                    text += f"\n\n[PDF PAGE {i+1}/{len(reader.pages)}]\n{page_text}"
    except Exception as e:
        print(f"❌ [PDF] Error: {e}")

    if not text.strip():
        print(f"⚠️ No text found, switching to OCR...")
        text = extract_text_with_ocr(file_bytes, filename)
    else:
        print(f"✅ PDF text extraction complete ({len(text)} chars)")
    return text

def extract_text_from_docx(file_bytes, filename=""):
    print(f"📝 [DOCX] Extracting from {os.path.basename(filename)} ...")
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            tmp.write(file_bytes)
            tmp.flush()
            doc = Document(tmp.name)
            text = "\n".join([clean_text(p.text) for p in doc.paragraphs if p.text.strip()])
        print(f"✅ DOCX extracted ({len(text)} chars)")
        return text
    except Exception as e:
        print(f"❌ DOCX error: {e}")
        return ""

def extract_text_from_xlsx(file_bytes, filename=""):
    print(f"📊 [XLSX] Extracting from {os.path.basename(filename)} ...")
    try:
        with io.BytesIO(file_bytes) as f:
            df = pd.read_excel(f)
            text = clean_text(df.to_string(index=False))
        print(f"✅ XLSX extracted ({len(text)} chars)")
        return text
    except Exception as e:
        print(f"❌ XLSX error: {e}")
        return ""

def extract_text_from_csv(file_bytes, filename=""):
    print(f"📈 [CSV] Extracting from {os.path.basename(filename)} ...")
    try:
        with io.BytesIO(file_bytes) as f:
            df = pd.read_csv(f)
            text = clean_text(df.to_string(index=False))
        print(f"✅ CSV extracted ({len(text)} chars)")
        return text
    except Exception as e:
        print(f"❌ CSV error: {e}")
        return ""

def extract_text_from_zip(file_bytes, filename=""):
    print(f"📦 [ZIP] Extracting files from {os.path.basename(filename)} ...")
    text = ""
    try:
        with io.BytesIO(file_bytes) as zf:
            with zipfile.ZipFile(zf, "r") as zip_ref:
                for name in zip_ref.namelist():
                    if name.endswith(('.pdf','.docx','.doc','.csv','.xlsx','.txt')):
                        print(f"   🔹 Found inside ZIP: {name}")
                        with zip_ref.open(name) as f:
                            inner_bytes = f.read()
                            inner_text = extract_text_by_type(inner_bytes, name)
                            text += f"\n\n===== From {name} =====\n{inner_text}\n"
        print(f"✅ ZIP extraction complete")
    except Exception as e:
        print(f"❌ ZIP error: {e}")
    return text

def extract_text_by_type(file_bytes, filename):
    filename = filename.lower()
    if filename.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes, filename)
    elif filename.endswith(".docx"):
        return extract_text_from_docx(file_bytes, filename)
    elif filename.endswith(".xlsx"):
        return extract_text_from_xlsx(file_bytes, filename)
    elif filename.endswith(".csv"):
        return extract_text_from_csv(file_bytes, filename)
    elif filename.endswith(".zip"):
        return extract_text_from_zip(file_bytes, filename)
    elif filename.endswith(".txt"):
        text = clean_text(file_bytes.decode("utf-8", errors="ignore"))
        print(f"📃 TXT extracted ({len(text)} chars)")
        return text
    else:
        print(f"⚠️ Unsupported type: {filename}")
        return ""

# --- SCRAPER ---
results = []

for page_num in range(1, 6):
    page_url = f"{BASE_URL}{page_num}/"
    print(f"\n🌍 Scraping page {page_num}: {page_url}")
    
    resp = requests.get(page_url)
    if resp.status_code != 200:
        print("❌ Failed to load page.")
        break

    soup = bs(resp.text, "html.parser")
    articles = soup.find_all("article", class_="elementor-post")
    stop_scraping = False

    for article in articles:
        date_tag = article.find("span", class_="elementor-post-date")
        if not date_tag:
            continue
        post_date = date_tag.text.strip()
        print(f"📅 Found post date: {post_date}")

        if post_date != TARGET_DATE_STR:
            print(f"🛑 Post not from target date, stopping.")
            stop_scraping = True
            break

        title_tag = article.find("h3", class_="elementor-post__title")
        if not title_tag or not title_tag.a:
            continue
        article_url = title_tag.a["href"]
        print(f"🔗 Visiting: {article_url}")

        article_resp = requests.get(article_url)
        if article_resp.status_code != 200:
            continue

        article_soup = bs(article_resp.text, "html.parser")
        title = article_soup.find("h1").text.strip() if article_soup.find("h1") else "Untitled"
        attachments = [a["href"] for a in article_soup.select(".post-attachments a[href]")]
        results.append({"Title": title, "URL": article_url, "Attachments": attachments})

    if stop_scraping:
        break

df = pd.DataFrame(results)
print("\n✅ Scraping complete!")

excluded_words = [
    "construction", "installation", "travaux",
    "fourniture", "achat", "equipement", "supply", "acquisition", "nettoyage"
]

# --- DOWNLOAD & EXTRACT WITH DETAILED STEPS ---
extracted_texts = []

for idx, row in df.iterrows():
    print(f"\n📄 Processing tender {idx+1}/{len(df)}: {row['Title']}")
    combined_text = ""

    for url in row["Attachments"]:
        print(f"\n⬇️ Step 1: Downloading attachment: {url}")
        try:
            r = requests.get(url)
            if r.status_code == 200:
                file_bytes = r.content
                print(f"✅ Step 2: Download complete ({len(file_bytes)} bytes)")

                file_type = url.split('.')[-1].lower()
                print(f"🔍 Step 3: Detected file type: {file_type}")

                print(f"📝 Step 4: Extracting text ...")
                text = extract_text_by_type(file_bytes, url)
                print(f"✅ Step 4 complete ({len(text)} chars extracted)")

                if not text.strip() and file_type == "pdf":
                    print(f"⚠️ Step 5: Empty PDF, applying OCR fallback...")
                    text = extract_text_with_ocr(file_bytes, url)
                    print(f"✅ Step 5 complete (OCR extracted {len(text)} chars)")

                print(f"🔧 Step 6: Cleaning text ...")
                text = clean_text(text)
                print(f"✅ Step 6 complete ({len(text)} chars after cleaning)")

                combined_text += f"\n\n--- From {os.path.basename(url)} ---\n{text}\n"
            else:
                print(f"⚠️ Step 2: Failed to download ({r.status_code})")
        except Exception as e:
            print(f"❌ Step 2: Error downloading {url}: {e}")

    print(f"🗂 Step 7: Appending extracted text to list")
    extracted_texts.append(combined_text)
    print(f"✅ Step 7 complete for tender {idx+1}")

print("\n📌 Step 8: Adding extracted text as new column in DataFrame")
df["Extracted_Text"] = extracted_texts

# ✅ FILTER AFTER ADDING 'Extracted_Text'
#if not df.empty:
   # df_filtered = df[~df["Title"].str.lower().str.contains("|".join(excluded_words), na=False)].reset_index(drop=True)
#else:
    #df_filtered = df

print(f"✅ Found {len(df)} relevant tenders after filtering.")
print("\n✅ All done! DataFrame ready.")

# --- WEBHOOK SENDING (OPTIMIZED FOR SLOW AI) ---
WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")

if WEBHOOK_URL:
    for idx, row in df.iterrows():
        print(f"\n🚀 Sending row {idx+1}/{len(df)}: {row['Title']}")
        
        payload = {
            "Title": row["Title"],
            "URL": row["URL"],
            "Attachments": row["Attachments"],
            "Extracted_Text": row["Extracted_Text"]
        }

        try:
            # -------------------------------------------------------------
            # CHANGED: Timeout increased to 600s (10 mins) for slow Ollama
            # -------------------------------------------------------------
            response = requests.post(WEBHOOK_URL, json=payload, timeout=600)
            
            if response.status_code == 200:
                print(f"✅ Row {idx+1} sent successfully.")
            else:
                print(f"⚠️ Row {idx+1} sent, but webhook returned status {response.status_code}")
        
        except requests.exceptions.ReadTimeout:
            # -------------------------------------------------------------
            # NEW: Handle timeout specifically without crashing
            # -------------------------------------------------------------
            print(f"⚠️ TIMEOUT: Row {idx+1} took > 600s. AI is likely still processing. Moving to next row.")
            
        except requests.exceptions.ConnectionError:
            print(f"❌ Connection Error sending row {idx+1}: Could not reach n8n server.")
            
        except Exception as e:
            print(f"❌ General Error sending row {idx+1}: {e}")

        time.sleep(1)
    
    print("\n✅ All rows processed (sent or timed out safely)!")
else:
    print("\n⚠️ No N8N_WEBHOOK_URL found in environment variables. Skipping webhook.")
