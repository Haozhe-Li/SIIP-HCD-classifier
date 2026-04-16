import asyncio
from database.db import client, DATABASE_ID, fetch_unlabeld_activity

async def main():
    print("Checking...")
    res = await fetch_unlabeld_activity()
    print("RES:", res)
    
    count_sql = "SELECT COUNT(*) as count FROM labels WHERE HCD_Space IS NULL OR HCD_Space = '';"
    res2 = await client.query_db(db_id=DATABASE_ID, sql=count_sql)
    print("COUNT:", res2.results)

asyncio.run(main())
