import os
import json
from supabase import create_client, Client
from openai import OpenAI

# Configuration
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_SERVICE_KEY")
OR_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# Initialize Clients
supabase: Client = create_client(URL, KEY)
# Pointing OpenAI client to OpenRouter
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OR_API_KEY,
)

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
        # Using MiniMax M2.5 (Free version)
        # Change to "minimax/minimax-m2.5" if you want the paid, higher-limit version
        response = client.chat.completions.create(
            model="minimax/minimax-m2.5:free",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        # Parse the JSON response
        content = response.choices[0].message.content
        return json.loads(content)
        
    except Exception as e:
        print(f"AI Error for MiniMax: {e}")
        return None

def main():
    # Get all rows from raw table (Limit 100 for batch processing)
    try:
        response = (
            supabase
            .table("Tenders Raw Data")
            .select("*")
            .limit(100)
            .execute()
        )
        records = response.data
    except Exception as e:
        print(f"Supabase Fetch Error: {e}")
        return

    if not records:
        print("No documents found in 'Tenders Raw Data'.")
        return

    for record in records:
        print(f"--- Processing ID: {record['id']} ---")

        extracted = get_ai_extraction(
            record.get("Extracted_Text", "")
        )

        if extracted:
            # Map extracted JSON to your Supabase schema
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
                print(f"Successfully cleaned: {structured_data['Title']}")
            except Exception as e:
                print(f"Supabase Insert Error: {e}")

        else:
            print(f"Failed to extract data for ID {record['id']}")

if __name__ == "__main__":
    main()
