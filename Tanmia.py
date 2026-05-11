import pandas as pd
import requests
import os
import io
import tempfile
import pytesseract
from PIL import Image
import fitz  # PyMuPDF
from docx import Document
from bs4 import BeautifulSoup as bs
import PyPDF2
from datetime import datetime
import re
import unicodedata
import json
import ollama

# --- CONFIG ---
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
OCR_LANGS = "ara+fra+eng"
BASE_URL = "https://tanmia.ma/appels-doffres/"
MODEL_NAME = "llama3.2"

MONTHS_FR = ["janvier","février","mars","avril","mai","juin","juillet",
             "août","septembre","octobre","novembre","décembre"]

# --- DATE CONFIG ---
# REMOVED: - timedelta(days=1) to target TODAY
today = datetime.now()
TARGET_DATE_STR = f"{today.day} {MONTHS_FR[today.month-1]} {today.year}"
print(f"📅 Target date for scraping: {TARGET_DATE_STR}")

# --- HELPER FUNCTIONS ---

def clean_text(text):
    if not text: return ""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

def extract_text_with_ocr(file_bytes, filename=""):
    text = ""
    try:
        pdf_doc = fitz.open(stream=file_bytes, filetype="pdf")
        for page in pdf_doc:
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            page_text = pytesseract.image_to_string(img, lang=OCR_LANGS)
            text += f"\n{page_text}"
    except Exception as e:
        print(f"❌ [OCR Error]: {e}")
    return clean_text(text)

def extract_text_from_pdf(file_bytes, filename=""):
    text = ""
    try:
        with io.BytesIO(file_bytes) as pdf_stream:
            reader = PyPDF2.PdfReader(pdf_stream)
            for page in reader.pages:
                text += page.extract_text() or ""
    except:
        pass
    if not text.strip():
        return extract_text_with_ocr(file_bytes, filename)
    return clean_text(text)

def extract_text_by_type(file_bytes, filename):
    fname = filename.lower()
    if fname.endswith(".pdf"): return extract_text_from_pdf(file_bytes, filename)
    if fname.endswith(".docx"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            tmp.write(file_bytes)
            tmp.flush()
            doc = Document(tmp.name)
            return clean_text("\n".join([p.text for p in doc.paragraphs]))
    return ""

# --- OLLAMA INTEGRATION ---

def analyze_with_ollama(tender_title, extracted_text):
    """Uses the official ollama library for structured extraction."""
    print(f"🧠 [AI] Analyzing: {tender_title[:50]}...")
    context_text = extracted_text[:5000] # Stay within context limits

    prompt = f"""
    Tu es un expert en appels d'offres. Analyse le texte suivant et extrais :
    - client: L'organisme qui lance l'offre.
    - ville: Localisation.
    - budget: Montant estimé en DH (sinon 'Non mentionné').
    - caution: La caution provisoire en DH.
    - date_limite: Date de dépôt des offres.
    - what_they_want: Un résumé d'une phrase de la prestation.

    RETOURNE UNIQUEMENT UN OBJET JSON.
    TITRE: {tender_title}
    TEXTE: {context_text}
    """

    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[{'role': 'user', 'content': prompt}],
            format='json'
        )
        return json.loads(response['message']['content'])
    except Exception as e:
        print(f"❌ AI Error: {e}")
        return {
            "client": "N/A", "ville": "N/A", "budget": "N/A", 
            "caution": "N/A", "date_limite": "N/A", "what_they_want": "N/A"
        }

# --- SCRAPER ---

results = []
# Searching first 3 pages to ensure we catch all of today's posts
for page_num in range(1, 4): 
    page_url = f"{BASE_URL}{page_num}/"
    resp = requests.get(page_url)
    if resp.status_code != 200: break

    soup = bs(resp.text, "html.parser")
    articles = soup.find_all("article", class_="elementor-post")

    for article in articles:
        date_tag = article.find("span", class_="elementor-post-date")
        if not date_tag: continue
        post_date = date_tag.text.strip()

        # Only process if it matches today
        if post_date != TARGET_DATE_STR: 
            continue

        title_tag = article.find("h3", class_="elementor-post__title")
        if not title_tag or not title_tag.a: continue
        
        article_url = title_tag.a["href"]
        article_resp = requests.get(article_url)
        if article_resp.status_code != 200: continue

        article_soup = bs(article_resp.text, "html.parser")
        title = article_soup.find("h1").text.strip() if article_soup.find("h1") else "Untitled"
        attachments = [a["href"] for a in article_soup.select(".post-attachments a[href]")]
        
        full_tender_text = ""
        for att_url in attachments:
            try:
                att_resp = requests.get(att_url)
                if att_resp.status_code == 200:
                    full_tender_text += extract_text_by_type(att_resp.content, att_url) + "\n"
            except:
                continue

        # Process with AI
        ai_data = analyze_with_ollama(title, full_tender_text)

        # Build Final Data Row
        results.append({
            "object": title,
            "link": article_url,
            "date limite": ai_data.get("date_limite"),
            "date de publication": post_date,
            "ville": ai_data.get("ville"),
            "client": ai_data.get("client"),
            "budget": ai_data.get("budget"),
            "caution": ai_data.get("caution"),
            "what they want": ai_data.get("what_they_want")
        })

# --- FINAL OUTPUT ---
df = pd.DataFrame(results)
if not df.empty:
    print("\n✅ Processing Complete!")
    print(df.head())
    df.to_csv("results.csv", index=False, encoding='utf-8-sig')
else:
    print(f"\nℹ️ No offers found for {TARGET_DATE_STR} yet.")
