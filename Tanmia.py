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

# --- CONFIGURATION ---
# Assurez-vous que tesseract est installé dans votre environnement (Codespaces/GitHub Actions)
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
OCR_LANGS = "ara+fra+eng"
BASE_URL = "https://tanmia.ma/appels-doffres/"
MODEL_NAME = "llama3.2"

MONTHS_FR = ["janvier","février","mars","avril","mai","juin","juillet",
             "août","septembre","octobre","novembre","décembre"]

# --- GESTION DES DATES ---
today = datetime.now()
TARGET_DATE_STR = f"{today.day} {MONTHS_FR[today.month-1]} {today.year}"
print(f"📅 Recherche des offres du : {TARGET_DATE_STR}")

# --- FONCTIONS DE NETTOYAGE ET EXTRACTION ---

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
            
            # Si le PDF est vide (image/scan), on lance l'OCR
            if not text.strip():
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
        print(f"❌ Erreur d'extraction sur {filename}: {e}")
    return clean_text(text)

# --- ANALYSE IA (OLLAMA) ---

def analyze_with_ollama(tender_title, extracted_text):
    print(f"🧠 [AI] Analyse détaillée : {tender_title[:50]}...")
    
    # On prend une large portion de texte pour ne pas rater le budget à la fin
    context_text = extracted_text[:8000] 

    prompt = f"""
    Tu es un Expert Senior en Ingénierie des Marchés Publics Marocains.
    Extraits les informations suivantes. Utilise EXACTEMENT les mots-clés suivis de deux points.

    --- RÈGLES D'OR ---
    1. BUDGET : Cherche "MAD", "DH", "TTC", "Estimation" (souvent à la fin du document).
    2. WHAT & HOW : Explique concrètement le QUOI et la MÉTHODOLOGIE imposée.

    --- SECTEURS (Choisis-en UN) ---
    1. Formation & Coaching | 2. Recrutement & RH | 3. Études & Conseil | 4. Audit & Expertise Comptable | 
    5. Informatique & Digital | 6. Communication & Événementiel | 7. Travaux de Bâtiment | 8. Génie Civil & Routes | 
    9. Installations Électriques | 10. Plomberie & Chauffage | 11. Achat de Fournitures de Bureau | 12. Mobilier & Aménagement | 
    13. Matériel Médical | 14. Nettoyage & Gardiennage | 15. Espaces Verts | 16. Transport & Logistique | 
    17. Restauration & Catering | 18. Maintenance Technique | 19. Énergies Renouvelables | 20. Gardiennage & Sécurité | 21. Archivage.

    --- FORMAT DE RÉPONSE ---
    CLIENT : 
    VILLE : 
    BUDGET : 
    CAUTION : 
    DATE LIMITE : 
    SECTEUR : 
    WHAT : 
    HOW : 

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
        
        # Parser robuste pour extraire les données malgré le formatage (gras, tirets, etc.)
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

# --- SCRAPER PRINCIPAL ---

results = []
# On parcourt les 3 premières pages pour être sûr de tout voir
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

        # Filtrage par date (Aujourd'hui)
        if post_date != TARGET_DATE_STR: 
            continue

        title_tag = article.find("h3", class_="elementor-post__title")
        if not title_tag or not title_tag.a: continue
        
        article_url = title_tag.a["href"]
        article_resp = requests.get(article_url)
        if article_resp.status_code != 200: continue

        article_soup = bs(article_resp.text, "html.parser")
        title = article_soup.find("h1").text.strip() if article_soup.find("h1") else "Untitled"
        
        # Récupération des pièces jointes
        attachments = [a["href"] for a in article_soup.select(".post-attachments a[href]")]
        
        full_tender_text = ""
        for att_url in attachments:
            try:
                att_resp = requests.get(att_url)
                if att_resp.status_code == 200:
                    full_tender_text += extract_text_by_type(att_resp.content, att_url) + "\n"
            except: continue

        # Analyse par l'IA
        ai_data = analyze_with_ollama(title, full_tender_text)

        # Construction de la ligne Excel
        results.append({
            "Date de Publication": post_date,
            "Organisme": ai_data.get("CLIENT", "N/A"),
            "Secteur": ai_data.get("SECTEUR", "N/A"),
            "Objet": title,
            "Budget": ai_data.get("BUDGET", "N/A"),
            "Ville": ai_data.get("VILLE", "N/A"),
            "Caution": ai_data.get("CAUTION", "N/A"),
            "Date Limite": ai_data.get("DATE LIMITE", "N/A"),
            "Nature (WHAT)": ai_data.get("WHAT", "N/A"),
            "Méthode (HOW)": ai_data.get("HOW", "N/A"),
            "Lien Article": article_url
        })

# --- SORTIE FINALE ---

df = pd.DataFrame(results)
if not df.empty:
    print(f"\n✅ Extraction terminée ! {len(df)} offres trouvées.")
    # Sauvegarde avec encodage compatible Excel (utf-8-sig)
    df.to_csv("results.csv", index=False, encoding='utf-8-sig')
    print("📂 Fichier 'results.csv' généré.")
else:
    print(f"ℹ️ Aucune offre trouvée pour la date du {TARGET_DATE_STR}.")
