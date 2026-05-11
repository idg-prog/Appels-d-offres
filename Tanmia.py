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

def extract_text_by_type(file_bytes, filename):
    fname = filename.lower()
    text = ""
    try:
        if fname.endswith(".pdf"):
            with io.BytesIO(file_bytes) as pdf_stream:
                reader = PyPDF2.PdfReader(pdf_stream)
                for page in reader.pages:
                    text += page.extract_text() or ""
            if not text.strip():
                # OCR Fallback
                pdf_doc = fitz.open(stream=file_bytes, filetype="pdf")
                for page in pdf_doc:
                    pix = page.get_pixmap(dpi=300)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    text += pytesseract.image_to_string(img, lang=OCR_LANGS)
        elif fname.endswith(".docx"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                tmp.write(file_bytes)
                tmp.flush()
                doc = Document(tmp.name)
                text = "\n".join([p.text for p in doc.paragraphs])
    except Exception as e:
        print(f"❌ Extraction error on {filename}: {e}")
    return clean_text(text)

# --- OLLAMA INTEGRATION (FIXED PROMPT) ---

def analyze_with_ollama(tender_title, extracted_text):
    """Refined prompt to ensure budget is captured correctly."""
    print(f"🧠 [AI] Analyzing: {tender_title[:50]}...")
    
    # Increase context slightly to 7000 to ensure we reach the 'Budget' section at the end
    context_text = extracted_text[:7000] 

    prompt = f"""
    Tu es un Expert Senior en Ingénierie des Marchés Publics Marocains. Ton rôle est d'extraire une fiche technique décisionnelle à partir de documents complexes.
    
    --- RÈGLES D'OR ---
    1. ANALYSE FINANCIÈRE : Priorité absolue sur le BUDGET. Cherche "MAD", "DH", "TTC", "Estimation". Vérifie les sections "Traitement économique" ou "Dispositions financières".
    2. ANALYSE OPÉRATIONNELLE : Explique le WHAT (Quoi) et le HOW (Comment : méthodologie, livrables, approche).
    
    --- CLASSIFICATION PAR SECTEUR ---
    Tu dois impérativement classer l'offre dans l'UN de ces 20 secteurs :
    1. Formation & Coaching | 2. Recrutement & RH | 3. Études & Conseil | 4. Audit & Expertise Comptable | 5. Informatique & Digital | 6. Communication & Événementiel | 7. Travaux de Bâtiment | 8. Génie Civil & Routes | 9. Installations Électriques | 10. Plomberie & Chauffage | 11. Achat de Fournitures de Bureau | 12. Mobilier & Aménagement | 13. Matériel Médical | 14. Nettoyage & Gardiennage | 15. Espaces Verts | 16. Transport & Logistique | 17. Restauration & Catering | 18. Maintenance Technique | 19. Énergies Renouvelables | 20. Gardiennage & Sécurité | 21. Archivage.
    
    --- FORMAT DE SORTIE IMPÉRATIF ---
    
    CLIENT : [Nom de l'organisme]
    VILLE : [Ville et Région]
    BUDGET : [Valeur exacte 'Non mentionnée' ]
    CAUTION : [Montant ou 'Non mentionnée']
    DATE LIMITE : [Date et Heure]
    
    SECTEUR : [Choisis parmi la liste des 21 secteurs ci-dessus]
    
    CE QU'ILS VEULENT (WHAT) : 
    [Minimum 2 phrases : Objectif concret, quantités, volume, nature de la mission.]
    
    COMMENT ILS LE VEULENT (HOW) : 
    [Minimum 2 phrases : Méthodologie imposée, livrables attendus, approche technique, contraintes de réalisation.]
    ---------------------------------------------------------

    DOCUMENT :
    TITRE: {tender_title}
    CONTENU DU DOCUMENT:
    {context_text}
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
        return {"client": "N/A", "ville": "N/A", "budget": "N/A", "caution": "N/A", "date_limite": "N/A", "what_they_want": "N/A"}

# --- SCRAPER ---

results = []
for page_num in range(1, 3): 
    page_url = f"{BASE_URL}{page_num}/"
    resp = requests.get(page_url)
    if resp.status_code != 200: break

    soup = bs(resp.text, "html.parser")
    articles = soup.find_all("article", class_="elementor-post")

    for article in articles:
        date_tag = article.find("span", class_="elementor-post-date")
        if not date_tag: continue
        post_date = date_tag.text.strip()

        if post_date != TARGET_DATE_STR: continue

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

        ai_data = analyze_with_ollama(title, full_tender_text)

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

df = pd.DataFrame(results)
if not df.empty:
    print("\n✅ Extraction Finished!")
    print(df[['object', 'budget', 'client']]) # Preview key columns
    df.to_csv("results.csv", index=False, encoding='utf-8-sig')
else:
    print(f"No results for {TARGET_DATE_STR}")
