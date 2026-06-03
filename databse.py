import os
from supabase import create_client

# --- Configuration ---
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_SERVICE_KEY")

supabase = create_client(URL, KEY)

# =====================================================
# 1. DELETE ALL ROWS FROM "Tenders Raw Data"
# =====================================================

def clear_raw_data():
    supabase.table("Tenders Raw Data") \
        .delete() \
        .neq("id", 0) \
        .execute()

    print("Tenders Raw Data cleared.")


# =====================================================
# 2. REMOVE DUPLICATES FROM "Tenders Clean Data"
#    based on Title
# =====================================================

def remove_duplicate_titles():
    response = (
        supabase.table("Tenders Clean Data")
        .select("*")
        .execute()
    )

    rows = response.data

    seen_titles = set()
    duplicate_ids = []

    for row in rows:
        title = (row.get("Title") or "").strip().lower()

        if title in seen_titles:
            duplicate_ids.append(row["id"])
        else:
            seen_titles.add(title)

    if duplicate_ids:
        (
            supabase.table("Tenders Clean Data")
            .delete()
            .in_("id", duplicate_ids)
            .execute()
        )

        print(f"Deleted {len(duplicate_ids)} duplicate rows.")
    else:
        print("No duplicate titles found.")


# =====================================================
# RUN
# =====================================================

if __name__ == "__main__":
    clear_raw_data()
    remove_duplicate_titles()
