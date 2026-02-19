import asyncio
import os
from d1_client import AsyncD1Client
from dotenv import load_dotenv

load_dotenv()

ACCOUNT_ID = os.getenv("D1_ACCOUNT_ID")
API_TOKEN = os.getenv("D1_API_TOKEN")
DATABASE_ID = os.getenv("D1_DATABASE_ID")

client = AsyncD1Client(account_id=ACCOUNT_ID, api_token=API_TOKEN)


def generate_suffix(index):
    if index < 26:
        return chr(97 + index)

    first = chr(97 + (index // 26) - 1)
    second = chr(97 + (index % 26))
    return f"{first}{second}"


async def insert_records(count=100):
    print(f"Inserting {count} test records...")

    success = 0
    failed = 0

    for i in range(count):
        activity = f"test activity {generate_suffix(i)}"
        sql = 'INSERT INTO "main"."labels" ("Activity") VALUES(?)'

        try:
            result = await client.query_db(
                db_id=DATABASE_ID, sql=sql, params=[activity]
            )

            if result.success:
                success += 1
                print(f"✓ [{success}/{count}] {activity}")
            else:
                failed += 1
                print(f"✗ Failed: {activity}")

        except Exception as e:
            failed += 1
            print(f"✗ Error: {activity} - {e}")

    print(f"\nDone: {success} succeeded, {failed} failed")


async def main():
    if not all([ACCOUNT_ID, API_TOKEN, DATABASE_ID]):
        print("Error: Missing environment variables")
        print("Required: D1_ACCOUNT_ID, D1_API_TOKEN, D1_DATABASE_ID")
        return

    await insert_records(100)


if __name__ == "__main__":
    asyncio.run(main())
