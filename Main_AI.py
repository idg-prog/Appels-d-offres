import os
import json
import time
import random
import re
from supabase import create_client, Client
from openai import OpenAI, RateLimitError

# Configuration
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_SERVICE_KEY")
OR_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# Initialize Clients
supabase: Client = create_client(URL, KEY)
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OR_API_KEY,
)

# 20 Professional Domains for Tagging
DOMAINS = [
    "Construction & BTP", "Informatique & Digital", "Nettoyage & Gardiennage",
    "Fournitures de Bureau", "Aménagement & Mobilier", "Études & Conseil",
    "Transport & Logistique", "Énergie & Électricité", "Eau & Assainissement",
    "Santé & Médical", "Agriculture & Espaces Verts", "Éducation & Formation",
    "Événementiel & Communication", "Sécurité & Surveillance", "Maintenance & Réparation",
    "Télécommunications", "Ressources Humaines & Recrutement", "Archivage & Gestion Documentaire",
    "Laboratoire & Analyse", "Industrie & Mécanique"
]

def get_ai_extraction(text, retries=3):
    domains_list = ", ".join(DOMAINS)
    
    prompt = f"""
    Analyze this Moroccan public procurement document.
    
    ### FORMATTING RULES:
    1. **Dates**: Always use DD/MM/YYYY. Convert month names to numbers (e.g., 'June' -> '06'). Remove hours (e.g., '10h00').
    2. **Budget & Caution**: Return ONLY "Number Currency". Remove text like "TTC", "per year", or explanations. Example: "150000 MAD".
    3. **Tags**: Select 1 relevant categories from the ALLOWED LIST below.
    4. **Return format**: Valid JSON only. No markdown (no ```).
    5.**Language** : Always the output need to be in French language
    
    REQUIRED FIELDS:
    - Title
    - Date_publication
    - Client
    - Localisation
    - Date_limite
    - Budget
    - Caution
    - URL
    - Technical_Description
    - Tags (List of strings)

    ALLOWED TAGS:
    {domains_list}
    
    TEXT:
    {text}
    """
    
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model="minimax/minimax-m2.5:free",
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.choices[0].message.content.strip()
            
            # Robust JSON cleaning
            if "```" in content:
                content = re.sub(r'```json|```', '', content).strip()
            
            return json.loads(content)
            
        except RateLimitError:
            wait_time = (2 ** attempt) * 30 + random.uniform(0, 5)
            print(f"⚠️ Rate limit. Waiting {int(wait_time)}s...")
            time.sleep(wait_time)
            
        except Exception as e:
            print(f"❌ AI Error: {e}")
            return None
    return None

def main():
    # 1. Fetch data from Raw table
    response = supabase.table("Tenders Raw Data").select("*").limit(100).execute()
    records = response.data

    if not records:
        print("No documents found.")
        return

    processed_count = 0

    for record in records:
        if processed_count > 0:
            time.sleep(random.uniform(3, 6))

        print(f"--- [{processed_count + 1}/100] Processing ID: {record['id']} ---")

        extracted = get_ai_extraction(record.get("Extracted_Text", ""))

        if extracted:
            # Map the English AI keys to your Table Columns
            # Note: Ensure these keys match your exact Supabase column names
            tags = extracted.get("Tags", [])
            tags_string = ", ".join(tags) if isinstance(tags, list) else tags

            structured_data = {
                "Title": extracted.get("Title"),
                "Date de publication": extracted.get("Date_publication"),
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
                supabase.table("Tenders Clean Data").insert(structured_data).execute()
                print(f"✅ Saved: {structured_data['Title']}")
                print(f"   - Budget: {structured_data['Budget']} | Date: {structured_data['Date de limite']}")
                processed_count += 1
            except Exception as e:
                print(f"⚠️ Supabase Insert Error: {e}")
        else:
            print(f"🛑 Skipped ID {record['id']}")

    print(f"\n🎉 Finished! Processed {processed_count} rows.")

if __name__ == "__main__":
    main()
