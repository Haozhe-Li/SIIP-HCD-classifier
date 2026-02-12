import asyncio
import os
from d1_client import AsyncD1Client
from typing import Optional

ACCOUNT_ID = os.getenv("D1_ACCOUNT_ID")
API_TOKEN = os.getenv("D1_API_TOKEN")
DATABASE_ID = os.getenv("D1_DATABASE_ID")
client = AsyncD1Client(account_id=ACCOUNT_ID, api_token=API_TOKEN)

async def fetch_unlabeld_activity() -> Optional[dict]:
    """
    Return 1 unlabeled activity. If there are no unlabeled activities, return None.
    Returns a dictionary with 'rowid' and 'Activity' fields.
    """
    # Query for activities where HCD_Space is NULL or empty
    sql = """
        SELECT rowid, Activity 
        FROM labels
        WHERE HCD_Space IS NULL OR HCD_Space = '' 
        LIMIT 1
    """
    
    try:
        # list db first
        result = await client.query_db(db_id=DATABASE_ID, sql=sql)
        # print(result)
        
        if result.success and result.results:
            # Return the first unlabeled activity
            activity_data = result.results[0].get("results")[0]
            print(activity_data)
            return {
                "rowid": activity_data.get("rowid"),
                "Activity": activity_data.get("Activity")
            }
        return None
    except Exception as e:
        print(f"Error fetching unlabeled activity: {e}")
        return None

async def label_activity(
    activity_id: int, 
    HCD_Space: str, 
    HCD_Subspace: str, 
    reason: str, 
    annotator: str
) -> bool:
    """
    Label the activity with the given ID with the provided HCD space, subspace, reason, and annotator.
    Returns True if successful, False otherwise.
    """
    sql = """
        UPDATE labels
        SET HCD_Space = ?, HCD_Subspace = ?, Reason = ?, Annotator = ?
        WHERE rowid = ?
    """
    
    params = [HCD_Space, HCD_Subspace, reason, annotator, activity_id]
    
    try:
        result = await client.query_db(db_id=DATABASE_ID, sql=sql, params=params)
        return result.success
    except Exception as e:
        print(f"Error labeling activity: {e}")
        return False