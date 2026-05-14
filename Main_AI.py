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

def get_ai_extraction(text, retries=3):
    prompt = f"""
    Analyze this Moroccan public procurement document.
    
    Return ONLY valid JSON.
    Do not use markdown.
    Do not use ```json.
    Do not add explanations.
    
    Required fields:
    - Title
    - Date_publication
    - Client
    - Localisation
    - Date_limite
    - Budget
    - Caution
    - URL
    - Technical_Description
    
    TEXT:
    {text}
    """
    
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model="minimax/minimax-m2.5:free",
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.choices[0].message.content
            content = content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                content = content.replace("json", "", 1).strip()
            
            return json.loads(content)
            
        except RateLimitError:
            # Exponential backoff: wait longer each time it fails
            wait_time = (2 ** attempt) * 30 + random.uniform(0, 5)
            print(f"⚠️ Rate limit hit. Waiting {int(wait_time)}s before retry...")
            time.sleep(wait_time)
            
        except Exception as e:
            print(f"❌ AI Error: {e}")
            return None
    return None

def main():
    # 1. Fetch data
    response = supabase.table("Tenders Raw Data").select("*").limit(100).execute()
    records = response.data

    if not records:
        print("No documents found.")
        return

    processed_count = 0

    for record in records:
        # 2. Add a mandatory cooldown between rows (Approx 15-20 requests per minute)
        # This keeps you safe from the "Minute" limit
        if processed_count > 0:
            pause = random.uniform(3, 6) # Wait 3 to 6 seconds
            time.sleep(pause)

        print(f"--- [{processed_count + 1}/100] Processing ID: {record['id']} ---")

        extracted = get_ai_extraction(record.get("Extracted_Text", ""))

        if extracted:
            structured_data = {
                "Title": extracted.get("Title"),
                "Date de publication": extracted.get("Date_publication"),
                "Client": extracted.get("Client"),
                "Localisation": extracted.get("Localisation"),
                "Date de limite": extracted.get("Date_limite"),
                "Budget": extracted.get("Budget"),
                "Caution": extracted.get("Caution"),
                "Description Technique": extracted.get("Technical_Description"),
                "URL": extracted.get("URL") or record.get("URL")
            }

            try:
                supabase.table("Tenders Clean Data").insert(structured_data).execute()
                print(f"✅ Saved: {structured_data['Title']}")
                processed_count += 1
            except Exception as e:
                print(f"⚠️ Supabase Insert Error: {e}")
        else:
            print(f"🛑 Skipped ID {record['id']} after failed retries.")

    print(f"\n🎉 Finished! Processed {processed_count} rows.")

if __name__ == "__main__":
    main()
