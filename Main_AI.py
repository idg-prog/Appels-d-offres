import os
import json
import time
from supabase import create_client, Client
import ollama

# Supabase Connection
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(URL, KEY)

def get_ai_extraction(text):
    prompt = f"""
    Analyze this Moroccan public procurement document. 
    Extract the details and return ONLY a valid JSON object.
    
    REQUIRED FIELDS:
    - objet: Title of the tender.
    - url: Source link.
    - client: The issuing entity.
    - locations: List of cities/regions.
    - date_de_limite: Deadline.
    - date_publication: Publication date.
    - budget: Total estimate.
    - caution: Provisional deposit.
    - job_offers: What is the job?
    - methodologie: How they want it done.
    - type_de_consultants: Required experts.

    TEXT:
    {text}
    """
    
    try:
        response = ollama.chat(
            model='qwen2.5:7b',
            messages=[{'role': 'user', 'content': prompt}],
            format='json'
        )
        return json.loads(response['message']['content'])
    except Exception as e:
        print(f"AI Error: {e}")
        return None

def main():
    # 1. Get unprocessed rows from raw table
    response = supabase.table("Tenders Raw Data").select("*").eq("processed", False).limit(100).execute()
    records = response.data

    if not records:
        print("All documents already processed.")
        return

    for record in records:
        print(f"Processing Raw ID: {record['id']}...")
        
        extracted = get_ai_extraction(record.get('extracted_text', ''))

        if extracted:
            # 2. Insert into structured table
            structured_data = {
                "raw_id": record["id"],
                "objet": extracted.get("objet"),
                "url": extracted.get("url") or record.get("url"),
                "client": extracted.get("client"),
                "locations": extracted.get("locations"),
                "date_limite": extracted.get("date_de_limite"),
                "date_publication": extracted.get("date_publication"),
                "budget": extracted.get("budget"),
                "caution": extracted.get("caution"),
                "job_offers": extracted.get("job_offers"),
                "methodologie": extracted.get("methodologie"),
                "consultants": extracted.get("type_de_consultants")
            }
            
            supabase.table("Tenders Clean Data").insert(structured_data).execute()

            # 3. Mark raw data as processed
            supabase.table("Tenders Raw Data").update({"processed": True}).eq("id", record["id"]).execute()
            print(f"Successfully moved {record['id']} to structured table.")
        else:
            print(f"Failed to process {record['id']}")

if __name__ == "__main__":
    main()
