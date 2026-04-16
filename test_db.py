import asyncio
from database.db import client, DATABASE_ID

async def main():
    res = await client.query_db(db_id=DATABASE_ID, sql="PRAGMA table_info(labels);")
    print(res.results)

asyncio.run(main())
