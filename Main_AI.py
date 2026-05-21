import os
import json
import time
import random
import re
import logging
from supabase import create_client, Client
from openai import OpenAI, RateLimitError
from datetime import datetime, timedelta

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
TODAY = datetime.today().date()
YESTERDAY = TODAY - timedelta(days=1)

# --- Configuration & Environment Check ---
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_SERVICE_KEY")
OR_API_KEY = os.environ.get("OPENROUTER_API_KEY")

if not all([URL, KEY, OR_API_KEY]):
    logger.error("Missing environment variables! Check SUPABASE_URL, SUPABASE_SERVICE_KEY, and OPENROUTER_API_KEY.")
    exit(1)

supabase: Client = create_client(URL, KEY)
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OR_API_KEY,
)

DOMAINS = [
    "Construction & BTP", "Informatique & Digital", "Nettoyage & Gardiennage",
    "Fournitures de Bureau", "Aménagement & Mobilier", "Études & Conseil",
    "Transport & Logistique", "Énergie & Électricité", "Eau & Assainissement",
    "Santé & Médical", "Agriculture & Espaces Verts", "Éducation & Formation",
    "Événementiel & Communication", "Sécurité & Surveillance", "Maintenance & Réparation",
    "Télécommunications", "Ressources Humaines & Recrutement", "Archivage & Gestion Documentaire",
    "Laboratoire & Analyse", "Industrie & Mécanique"
]

def clean_json_response(raw_content):
    """
    Extracts JSON from the AI response even if it includes conversational text or markdown.
    """
    try:
        # 1. Use Regex to find the first '{' and last '}'
        match = re.search(r'(\{.*\})', raw_content, re.DOTALL)
        if match:
            json_str = match.group(1)
            # 2. Remove potential control characters that break json.loads
            json_str = re.sub(r'[\x00-\x1F\x7F]', '', json_str)
            return json.loads(json_str)
        return None
    except Exception as e:
        logger.warning(f"Failed to parse JSON: {e}")
        return None

def get_ai_extraction(text, retries=3):
    if not text or len(text.strip()) < 20:
        return None

    domains_str = ", ".join(DOMAINS)
    prompt = f"""
    Analyse ce document d'appel d'offres marocain.
    
    RÈGLES DE FORMATAGE STRICTES :
    1. Dates : Format DD/MM/YYYY uniquement. Convertis les noms de mois (ex: 'Juin' -> '06').
    2. Budget & Caution : "Nombre Devise" uniquement (ex: "150000 MAD"). Pas de "TTC", pas de phrases.
    3. Tags : Choisis EXACTEMENT 1 catégorie dans cette liste : [{domains_str}]
    4. Localisation : "Ville, Maroc". Si la ville est inconnue, écris "Maroc".
    5. Langue : TOUT le contenu doit être en Français.
    
    LIRE LE TEXT EXTRAIT ET RETOURNE UNIQUEMENT CES INFORMATIONS EN OBJET JSON :
    {{
        "Title": "...",
        "Date_publication": "...",
        "Client": "...",
        "Localisation": "...",
        "Date_limite": "...",
        "Budget": "...",
        "Caution": "...",
        "URL": "...",
        "Technical_Description": "...",
        "Tags": ["..."]
    }}

    TEXTE :
    {text}
    """
    
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model="minimax/minimax-m2.5:free",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1 # Low temperature for more consistent formatting
            )
            
            raw_content = response.choices[0].message.content
            extracted_data = clean_json_response(raw_content)
            
            if extracted_data:
                # Basic validation: ensure keys exist
                required_keys = ["Title", "Tags", "Budget"]
                if all(k in extracted_data for k in required_keys):
                    return extracted_data
            
            logger.info(f"Attempt {attempt + 1}: AI returned invalid JSON. Retrying...")
            
        except RateLimitError:
            wait = (attempt + 1) * 40
            logger.warning(f"Rate limited. Waiting {wait}s...")
            time.sleep(wait)
        except Exception as e:
            logger.error(f"AI Error on attempt {attempt}: {e}")
            time.sleep(2)
            
    return None

def main():
    # 1. Fetch only 100 rows that HAVEN'T been processed yet
    # (Assuming you add a 'Processed' boolean column in 'Tenders Raw Data')
    # If you don't have that column, this will just fetch the first 100.
    try:
        response = supabase.table("Tenders Raw Data").select("*").limit(100).execute()
        records = response.data
    except Exception as e:
        logger.error(f"Supabase Fetch Error: {e}")
        return

    if not records:
        logger.info("No documents found.")
        return

    processed_count = 0

    for record in records:
        # Mandatory cooldown for OpenRouter free tier
        if processed_count > 0:
            time.sleep(random.uniform(4, 7))

        rec_id = record.get('id')
        logger.info(f"--- Processing Record {rec_id} ({processed_count + 1}/100) ---")

        raw_text = record.get("Extracted_Text", "")
        extracted = get_ai_extraction(raw_text)

        if extracted:
            # Map and sanitize
            tags = extracted.get("Tags", [])
            tags_string = ", ".join(tags) if isinstance(tags, list) else str(tags)

            structured_data = {
                "Title": extracted.get("Title", "Sans titre"),
                "Date de publication": YESTERDAY.strftime("%d/%m/%Y"),
                "Client": extracted.get("Client"),
                "Localisation": extracted.get("Localisation"),
                "Date de limite": extracted.get("Date_limite"),
                "Budget": extracted.get("Budget"),
                "Caution": extracted.get("Caution"),
                "Description Technique": extracted.get("Technical_Description"),
                "URL": extracted.get("URL") or record.get("URL"),
                "Tags": tags_string
            }

            try:
                # Insert data
                supabase.table("Tenders Clean Data").insert(structured_data).execute()
                
                # OPTIONAL: Mark raw row as processed so you don't do it again
                # supabase.table("Tenders Raw Data").update({"Processed": True}).eq("id", rec_id).execute()
                
                logger.info(f"✅ Successfully saved: {structured_data['Title'][:50]}...")
                processed_count += 1
            except Exception as e:
                logger.error(f"❌ Supabase Insert Error for ID {rec_id}: {e}")
        else:
            logger.error(f"🛑 Failed to extract data for ID {rec_id} after retries.")

    logger.info(f"🎉 Process finished. Total processed: {processed_count}")

if __name__ == "__main__":
    main()
