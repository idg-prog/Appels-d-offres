import os
import json
import time
import random
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

# Liste des 20 Domaines (incluant RH et Archivage)
DOMAINS = [
    "Construction & BTP", 
    "Informatique & Digital", 
    "Nettoyage & Gardiennage",
    "Fournitures de Bureau", 
    "Aménagement & Mobilier", 
    "Études & Conseil",
    "Transport & Logistique", 
    "Énergie & Électricité", 
    "Eau & Assainissement",
    "Santé & Médical", 
    "Agriculture & Espaces Verts", 
    "Éducation & Formation",
    "Événementiel & Communication", 
    "Sécurité & Surveillance", 
    "Maintenance & Réparation",
    "Télécommunications", 
    "Ressources Humaines (RH)", 
    "Archivage & Gestion Documentaire",
    "Laboratoire & Analyse", 
    "Industrie & Mécanique"
]

def get_ai_extraction(text, retries=3):
    domains_list = ", ".join(DOMAINS)
    
    prompt = f"""
    Analyse ce document d'appel d'offres public marocain.
    
    Retourne UNIQUEMENT du JSON valide.
    Pas de markdown, pas de ```json.
    
    Champs requis :
    - Title
    - Date_publication
    - Client
    - Localisation
    - Date_limite
    - Budget
    - Caution
    - URL
    - Technical_Description
    - Tags (Choisis les catégories les plus pertinentes UNIQUEMENT dans la liste autorisée ci-dessous. Retourne une liste de strings)

    LISTE AUTORISÉE DES TAGS :
    {domains_list}
    
    TEXTE :
    {text}
    """
    
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model="minimax/minimax-m2.5:free",
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.choices[0].message.content.strip()
            
            if content.startswith("```"):
                content = content.replace("```json", "").replace("```", "").strip()
            
            return json.loads(content)
            
        except RateLimitError:
            wait_time = (2 ** attempt) * 30 + random.uniform(0, 5)
            print(f"⚠️ Limite atteinte. Attente de {int(wait_time)}s...")
            time.sleep(wait_time)
            
        except Exception as e:
            print(f"❌ Erreur IA : {e}")
            return None
    return None

def main():
    response = supabase.table("Tenders Raw Data").select("*").limit(100).execute()
    records = response.data

    if not records:
        print("Aucun document trouvé.")
        return

    processed_count = 0

    for record in records:
        if processed_count > 0:
            time.sleep(random.uniform(3, 6))

        print(f"--- [{processed_count + 1}/100] ID: {record['id']} ---")

        extracted = get_ai_extraction(record.get("Extracted_Text", ""))

        if extracted:
            # Transformation des tags en chaîne de caractères (ou garde en liste selon ta colonne Supabase)
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
                "Tags": tags_string,
                "URL": extracted.get("URL") or record.get("URL")
            }

            try:
                supabase.table("Tenders Clean Data").insert(structured_data).execute()
                print(f"✅ Enregistré : {structured_data['Title']} | Tags : {tags_string}")
                processed_count += 1
            except Exception as e:
                print(f"⚠️ Erreur Insertion Supabase : {e}")
        else:
            print(f"🛑 Échec pour l'ID {record['id']}")

    print(f"\n🎉 Terminé ! {processed_count} lignes traitées.")

if __name__ == "__main__":
    main()
