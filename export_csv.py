import asyncio
import csv
from dotenv import load_dotenv
from database.db import client, DATABASE_ID

load_dotenv()

async def fetch_all_labeled_activities() -> list[dict]:
    sql = """
        SELECT rowid, Activity, HCD_Space, HCD_Subspace, Reason, Annotator
        FROM labels
        WHERE HCD_Space IS NOT NULL AND HCD_Space != ''
        ORDER BY rowid ASC
    """
    try:
        result = await client.query_db(db_id=DATABASE_ID, sql=sql)
        if result.success and result.results:
            return result.results[0].get("results", [])
    except Exception as e:
        print(f"Error fetching activities: {e}")
    return []

async def main():
    print("Fetching all labeled data from D1...")
    rows = await fetch_all_labeled_activities()

    if not rows:
        print("No labeled data found!")
        return

    print(f"Fetched {len(rows)} labeled rows.")

    filename = "all_annotated_data.csv"
    with open(filename, "w", newline="", encoding="utf-8") as f:
        if len(rows) > 0:
            fieldnames = ["rowid", "Activity", "HCD_Space", "HCD_Subspace", "Reason", "Annotator"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    print(f"Data successfully saved to {filename}")

if __name__ == "__main__":
    asyncio.run(main())
