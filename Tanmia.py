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
from datetime import datetime, timedelta
import re
import unicodedata
import json
import ollama

# --- CONFIGURATION ---
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
OCR_LANGS = "ara+fra+eng"
BASE_URL = "https://tanmia.ma/appels-doffres/"

# ✅ FIX #1: Model name matches what GitHub Action pulls (qwen2.5)
MODEL_NAME = "qwen2.5"

MONTHS_FR = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre"
]

# --- DATE HANDLING ---
today = datetime.now() - timedelta(days=1)
TARGET_DATE_STR = f"{today.day} {MONTHS_FR[today.month - 1]} {today.year}"
print(f"📅 Target date for scraping: {TARGET_DATE_STR}")


# --- TEXT CLEANING ---

def clean_text(text):
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


# --- TEXT EXTRACTION ---

def extract_text_by_type(file_bytes, filename):
    """
    Extract text from PDF or DOCX files.
    For PDFs: tries PyPDF2 first, then falls back to OCR via PyMuPDF + Tesseract.
    """
    fname = filename.lower().split("?")[0]  # Strip query params from URL filenames
    text = ""

    try:
        if fname.endswith(".pdf"):
            # --- Step 1: Try direct text extraction ---
            try:
                with io.BytesIO(file_bytes) as pdf_stream:
                    reader = PyPDF2.PdfReader(pdf_stream)
                    for page in reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text

                print(f"📄 PyPDF2 extracted {len(text)} chars from {filename}")
            except Exception as e:
                print(f"⚠️ PyPDF2 failed on {filename}: {e}")

            # --- Step 2: OCR fallback if text is too short (scanned PDF) ---
            if len(text.strip()) < 100:
                print(f"🔍 Text too short ({len(text.strip())} chars), switching to OCR for {filename}...")
                try:
                    pdf_doc = fitz.open(stream=file_bytes, filetype="pdf")
                    ocr_text = ""
                    for page_num, page in enumerate(pdf_doc):
                        pix = page.get_pixmap(dpi=300)
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        page_ocr = pytesseract.image_to_string(img, lang=OCR_LANGS)
                        ocr_text += page_ocr
                        print(f"   OCR page {page_num + 1}: {len(page_ocr)} chars")
                    text = ocr_text
                    print(f"📄 OCR extracted {len(text)} chars total from {filename}")
                except Exception as e:
                    print(f"❌ OCR failed on {filename}: {e}")

        elif fname.endswith(".docx"):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                    tmp.write(file_bytes)
                    tmp.flush()
                    doc = Document(tmp.name)
                    text = "\n".join([p.text for p in doc.paragraphs])
                    print(f"📄 DOCX extracted {len(text)} chars from {filename}")
            except Exception as e:
                print(f"❌ DOCX extraction failed on {filename}: {e}")

        else:
            print(f"⚠️ Unsupported file type: {filename}")

    except Exception as e:
        print(f"❌ General extraction error on {filename}: {e}")

    return clean_text(text)


# --- AI ANALYSIS ---

def parse_ai_response(content):
    """
    ✅ FIX #3: Robust multiline parser using regex instead of line-by-line splitting.
    Handles bold markers, dashes, and values that span multiple lines.
    """
    data = {}
    target_keys = ["CLIENT", "VILLE", "BUDGET", "CAUTION", "DATE LIMITE", "SECTEUR", "WHAT", "HOW"]

    # Strip markdown bold/italic markers
    content_clean = re.sub(r'[*_]', '', content)

    for i, key in enumerate(target_keys):
        # Build a lookahead that stops at the next key or end of string
        next_keys = target_keys[i + 1:]
        if next_keys:
            lookahead = r'(?=' + '|'.join(re.escape(k) for k in next_keys) + r'\s*:|\Z)'
        else:
            lookahead = r'(?=\Z)'

        pattern = rf'{re.escape(key)}\s*:\s*(.*?){lookahead}'
        match = re.search(pattern, content_clean, re.IGNORECASE | re.DOTALL)
        if match:
            value = match.group(1).strip()
            # Clean up: remove leading dashes, extra newlines
            value = re.sub(r'^[-–—\s]+', '', value)
            value = re.sub(r'\n+', ' ', value).strip()
            if value and value.upper() not in ("N/A", "NON DISPONIBLE", ""):
                data[key] = value

    return data


def analyze_with_ollama(tender_title, extracted_text):
    print(f"\n🧠 [AI] Analyzing: {tender_title[:60]}...")
    print(f"   Input text length: {len(extracted_text)} chars")

    if not extracted_text.strip():
        print("⚠️ Empty text passed to AI — skipping analysis.")
        return {}

    # Use up to 10000 chars to maximize info available to the model
    context_text = extracted_text[:10000]

    prompt = f"""Tu es un Expert Senior en Ingénierie des Marchés Publics Marocains.
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
1. Formation & Coaching | 2. Recrutement & RH | 3. Études & Conseil | 4. Audit & Expertise Comptable |
5. Informatique & Digital | 6. Communication & Événementiel | 7. Travaux de Bâtiment | 8. Génie Civil & Routes |
9. Installations Électriques | 10. Plomberie & Chauffage | 11. Achat de Fournitures de Bureau | 12. Mobilier & Aménagement |
13. Matériel Médical | 14. Nettoyage & Gardiennage | 15. Espaces Verts | 16. Transport & Logistique |
17. Restauration & Catering | 18. Maintenance Technique | 19. Énergies Renouvelables | 20. Gardiennage & Sécurité | 21. Archivage.

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
            options={"temperature": 0.1}  # Low temp for factual extraction
        )
        raw_content = response['message']['content']
        print(f"   Raw AI response preview:\n{raw_content[:600]}\n{'---'*20}")

        data = parse_ai_response(raw_content)
        print(f"   Parsed fields: {list(data.keys())}")
        return data

    except Exception as e:
        print(f"❌ AI Error: {e}")
        return {}


# --- ARTICLE BODY FALLBACK ---

def extract_article_body(article_soup):
    """
    ✅ FIX #4: Fallback — extract visible text from the article body
    in case no PDF attachments are found or they fail to download.
    """
    text = ""
    # Try common Elementor content containers
    selectors = [
        "div.elementor-widget-theme-post-content",
        "div.elementor-widget-text-editor",
        "div.entry-content",
        "div.post-content",
        "article",
    ]
    for sel in selectors:
        el = article_soup.select_one(sel)
        if el:
            text = el.get_text(separator="\n")
            if len(text.strip()) > 100:
                print(f"   Article body fallback: {len(text)} chars from '{sel}'")
                break
    return clean_text(text)


# --- MAIN SCRAPER ---

results = []

for page_num in range(1, 4):
    page_url = f"{BASE_URL}{page_num}/"
    print(f"\n🌐 Scraping page {page_num}: {page_url}")

    try:
        resp = requests.get(page_url, timeout=30)
    except Exception as e:
        print(f"❌ Failed to fetch page {page_num}: {e}")
        break

    if resp.status_code != 200:
        print(f"⚠️ Page {page_num} returned status {resp.status_code}, stopping.")
        break

    soup = bs(resp.text, "html.parser")
    articles = soup.find_all("article", class_="elementor-post")
    print(f"   Found {len(articles)} articles on page {page_num}")

    found_on_page = 0

    for article in articles:
        # --- Date filter ---
        date_tag = article.find("span", class_="elementor-post-date")
        if not date_tag:
            continue
        post_date = date_tag.text.strip()

        if post_date != TARGET_DATE_STR:
            continue

        found_on_page += 1
        print(f"\n✅ Match found: {post_date}")

        # --- Get article URL ---
        title_tag = article.find("h3", class_="elementor-post__title")
        if not title_tag or not title_tag.a:
            continue

        article_url = title_tag.a["href"]
        print(f"   URL: {article_url}")

        try:
            article_resp = requests.get(article_url, timeout=30)
        except Exception as e:
            print(f"❌ Failed to fetch article: {e}")
            continue

        if article_resp.status_code != 200:
            continue

        article_soup = bs(article_resp.text, "html.parser")

        # --- Title ---
        h1 = article_soup.find("h1")
        title = h1.text.strip() if h1 else title_tag.get_text(strip=True)
        print(f"   Title: {title[:80]}")

        # --- Collect text from attachments ---
        full_tender_text = ""

        attachments = [
            a["href"] for a in article_soup.select(".post-attachments a[href]")
        ]

        # ✅ Also try generic links ending with .pdf or .docx inside the article
        if not attachments:
            attachments = [
                a["href"] for a in article_soup.find_all("a", href=True)
                if a["href"].lower().split("?")[0].endswith((".pdf", ".docx"))
            ]

        print(f"   Attachments found: {len(attachments)}")

        for att_url in attachments:
            print(f"   Downloading: {att_url[:80]}")
            try:
                att_resp = requests.get(att_url, timeout=60)
                if att_resp.status_code == 200:
                    extracted = extract_text_by_type(att_resp.content, att_url)
                    full_tender_text += extracted + "\n"
                else:
                    print(f"   ⚠️ Attachment returned status {att_resp.status_code}")
            except Exception as e:
                print(f"   ❌ Attachment download error: {e}")
                continue

        # ✅ FIX #4: If no text from attachments, fall back to article body
        if len(full_tender_text.strip()) < 100:
            print("   ⚠️ No usable text from attachments — using article body fallback.")
            full_tender_text = extract_article_body(article_soup)

        print(f"   Total text for AI: {len(full_tender_text)} chars")

        # --- AI Analysis ---
        ai_data = analyze_with_ollama(title, full_tender_text)

        # --- Build result row ---
        results.append({
            "Date de Publication": post_date,
            "Organisme":           ai_data.get("CLIENT",      "N/A"),
            "Secteur":             ai_data.get("SECTEUR",     "N/A"),
            "Objet":               title,
            "Budget":              ai_data.get("BUDGET",      "N/A"),
            "Ville":               ai_data.get("VILLE",       "N/A"),
            "Caution":             ai_data.get("CAUTION",     "N/A"),
            "Date Limite":         ai_data.get("DATE LIMITE", "N/A"),
            "Nature (WHAT)":       ai_data.get("WHAT",        "N/A"),
            "Méthode (HOW)":       ai_data.get("HOW",         "N/A"),
            "Lien Article":        article_url,
        })

    print(f"   → {found_on_page} offers matched date '{TARGET_DATE_STR}' on page {page_num}")

    # If no matches on this page and we're past page 1, stop early
    if found_on_page == 0 and page_num > 1:
        print("   No more matching dates found, stopping pagination.")
        break


# --- OUTPUT ---

df = pd.DataFrame(results)

if not df.empty:
    print(f"\n✅ Done! {len(df)} offer(s) found.")
    df.to_csv("results.csv", index=False, encoding="utf-8-sig")
    print("📂 Saved to 'results.csv'")
    print(df.to_string())
else:
    print(f"\nℹ️ No offers found for date: {TARGET_DATE_STR}")
