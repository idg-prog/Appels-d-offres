import os
import json
from supabase import create_client, Client
import ollama

# Supabase Connection
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(URL, KEY)

def get_ai_extraction(text):
    prompt = f"""
    Analyze this Moroccan public procurement document. 
    Extract the details and return ONLY a valid JSON object.
    
    REQUIRED FIELDS:
    - Title: Main subject/title of the tender.
    - Date_publication: Publication date.
    - Client: The issuing entity.
    - Localisation: City or region.
    - Date_limite: Deadline date.
    - Budget: Estimated cost.
    - Caution: Provisional guarantee amount.
    - URL: Source link if found.
    - Technical_Description: Detailed summary including: 
        1. What is the job offer?
        2. Methodology required.
        3. Type of consultants/experts needed.

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
    # 1. Get up to 100 unprocessed rows from raw table
    # Replace 'Tenders Raw Data' with your actual raw data table name
    response = supabase.table("Tenders Raw Data").select("*").eq("processed", False).limit(100).execute()
    records = response.data

    if not records:
        print("No new documents to process.")
        return

    for record in records:
        print(f"Processing Raw ID: {record['id']}...")
        
        extracted = get_ai_extraction(record.get('extracted_text', ''))

        if extracted:
            # 2. Insert into your structured table using exact column names from image
            structured_data = {
                "Title": extracted.get("Title"),
                "Date de publication": extracted.get("Date_publication"),
                "Client": extracted.get("Client"),
                "Localisation": extracted.get("Localisation"),
                "Date de limite": extracted.get("Date_limite"),
                "Budget": extracted.get("Budget"),
                "Caution": extracted.get("Caution"),
                "Description Technique": extracted.get("Technical_Description"),
                "URL": extracted.get("URL") or record.get("url")
            }
            
            # Replace 'Tenders Clean Data' with your actual output table name
            supabase.table("Tenders Clean Data").insert(structured_data).execute()

            # 3. Mark raw data as processed
            supabase.table("Tenders Raw Data").update({"processed": True}).eq("id", record["id"]).execute()
            print(f"Successfully processed: {extracted.get('Title')}")
        else:
            print(f"Failed to process ID {record['id']}")

if __name__ == "__main__":
    main()
