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
from datetime import datetime, timedelta
import re
import unicodedata
from supabase import create_client, Client
import openpyxl


# --- CONFIG ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
if not SUPABASE_KEY:
    raise ValueError("Please set the SUPABASE_SERVICE_KEY environment variable.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# --- CONFIG ---
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
OCR_LANGS = "ara+fra+eng"
BASE_URL = "https://tanmia.ma/appels-doffres/"
MONTHS_FR = ["janvier","février","mars","avril","mai","juin","juillet",
             "août","septembre","octobre","novembre","décembre"]

# --- DATE CONFIG ---
# Target is yesterday's date
today_dt = datetime.now() - timedelta(days=1)
TARGET_DATE_STR = f"{today_dt.day} {MONTHS_FR[today_dt.month-1]} {today_dt.year}"
print(f"📅 Target date for scraping: {TARGET_DATE_STR}")

def clean_text(text):
    """Clean and normalize extracted text."""
    if not text: return ""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r'\n\s*\n+', '\n\n', text) # Remove excessive newlines
    text = re.sub(r'[ \t]+', ' ', text)     # Remove excessive tabs/spaces
    return text.strip()

def extract_text_by_type(file_bytes, filename):
    """Extract text from PDF (with OCR fallback), DOCX, or ZIP."""
    fname = filename.lower().split("?")[0]
    text = ""
    
    try:
        if fname.endswith(".pdf"):
            # fitz (PyMuPDF) is much better at extracting full document text than PyPDF2
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for page in doc:
                text += page.get_text()
            
            # If extraction yields almost nothing, it's a scanned image PDF
            if len(text.strip()) < 200:
                print(f"🔍 [OCR] Low text count ({len(text)}), starting OCR for {filename}...")
                text = ""
                for i, page in enumerate(doc):
                    pix = page.get_pixmap(dpi=300)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    page_text = pytesseract.image_to_string(img, lang=OCR_LANGS)
                    text += f"\n[Page {i+1}]\n{page_text}"
            doc.close()

        elif fname.endswith(".docx"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                tmp.write(file_bytes)
                tmp.flush()
                doc_docx = Document(tmp.name)
                text = "\n".join([p.text for p in doc_docx.paragraphs])
            os.unlink(tmp.name)

        elif fname.endswith(".zip"):
            with io.BytesIO(file_bytes) as zf:
                with zipfile.ZipFile(zf, "r") as zip_ref:
                    for name in zip_ref.namelist():
                        if name.endswith(('.pdf','.docx')):
                            with zip_ref.open(name) as f:
                                text += f"\n--- File inside ZIP: {name} ---\n{extract_text_by_type(f.read(), name)}"
    except Exception as e:
        print(f"❌ Error extracting {filename}: {e}")
        
    return clean_text(text)

# --- MAIN SCRAPER ---
results = []

# Scrape the first 3 pages of the archive
for page_num in range(1, 4):
    page_url = f"{BASE_URL}{page_num}/"
    print(f"\n🌍 Scraping page {page_num}...")
    
    try:
        resp = requests.get(page_url, timeout=30)
        soup = bs(resp.text, "html.parser")
        articles = soup.find_all("article", class_="elementor-post")
        
        for article in articles:
            date_tag = article.find("span", class_="elementor-post-date")
            if not date_tag: continue
            
            post_date = date_tag.text.strip()
            
            # Only process if it matches yesterday's date
            if post_date != TARGET_DATE_STR:
                continue
            
            title_tag = article.find("h3", class_="elementor-post__title")
            article_url = title_tag.a["href"]
            print(f"✅ Match Found: {title_tag.text.strip()}")

            # Visit the individual article page
            art_resp = requests.get(article_url, timeout=30)
            art_soup = bs(art_resp.text, "html.parser")
            
            # Find download links
            attachments = [a["href"] for a in art_soup.select(".post-attachments a[href]")]
            if not attachments:
                # Secondary check for direct PDF links in the text
                attachments = [a["href"] for a in art_soup.find_all("a", href=True) if ".pdf" in a["href"].lower()]

            full_extracted_text = ""
            for att_url in attachments:
                print(f"  ⬇️ Downloading attachment: {os.path.basename(att_url)}")
                try:
                    att_r = requests.get(att_url, timeout=60)
                    if att_r.status_code == 200:
                        full_extracted_text += extract_text_by_type(att_r.content, att_url) + "\n\n"
                except Exception as e:
                    print(f"  ⚠️ Failed to download {att_url}: {e}")

            results.append({
                "Date": post_date,
                "Title": title_tag.text.strip(),
                "URL": article_url,
                "Extracted_Text": full_extracted_text
            })
            
    except Exception as e:
        print(f"⚠️ Network error on page {page_num}: {e}")

# --- FINAL STEP: SAVE TO CSV ---
df = pd.DataFrame(results)

if not df.empty:
    # utf-8-sig ensures Arabic and French characters work in Excel
    df.to_csv("results.csv", index=False, encoding="utf-8-sig")
    print(f"\n💾 SUCCESS: Saved {len(df)} offers to 'results.csv'")
else:
    print("\nℹ️ No offers found for the target date. Creating empty file.")
    pd.DataFrame(columns=["Date", "Title", "URL", "Extracted_Text"]).to_csv("results.csv", index=False)
