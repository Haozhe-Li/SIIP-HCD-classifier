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
    sql = """
        SELECT rowid, Activity 
        FROM labels
        WHERE HCD_Space IS NULL OR HCD_Space = '' 
        LIMIT 1
    """

    try:
        result = await client.query_db(db_id=DATABASE_ID, sql=sql)

        if result.success and result.results:
            activity_data = result.results[0].get("results")[0]
            print(activity_data)
            return {
                "rowid": activity_data.get("rowid"),
                "Activity": activity_data.get("Activity"),
            }
        return None
    except Exception as e:
        print(f"Error fetching unlabeled activity: {e}")
        return None


async def label_activity(
    activity_id: int, HCD_Space: str, HCD_Subspace: str, reason: str, annotator: str
) -> dict:
    """
    Label the activity with the given ID.

    If the row is already labeled (HCD_Space already set), a new duplicate row is
    inserted with the same Activity text and immediately labeled.  This prevents
    concurrent annotators from overwriting each other.

    Returns a dict with keys:
        success (bool)      – whether the operation succeeded
        inserted_new (bool) – True when a duplicate row was created
    """
    # ------------------------------------------------------------------ #
    # 1. Check whether this row already has a label                       #
    # ------------------------------------------------------------------ #
    check_sql = """
        SELECT rowid, Activity, HCD_Space
        FROM labels
        WHERE rowid = ?
        LIMIT 1
    """
    try:
        check_result = await client.query_db(
            db_id=DATABASE_ID, sql=check_sql, params=[activity_id]
        )
    except Exception as e:
        print(f"Error checking activity status: {e}")
        return {"success": False, "inserted_new": False}

    rows = []
    if check_result.success and check_result.results:
        rows = check_result.results[0].get("results", [])

    if not rows:
        print(f"Activity {activity_id} not found")
        return {"success": False, "inserted_new": False}

    existing = rows[0]
    already_labeled = bool(existing.get("HCD_Space"))

    # ------------------------------------------------------------------ #
    # 2a. Row is already labeled → insert a new duplicate row             #
    # ------------------------------------------------------------------ #
    if already_labeled:
        activity_text = existing.get("Activity", "")
        insert_sql = """
            INSERT INTO labels (Activity, HCD_Space, HCD_Subspace, Reason, Annotator)
            VALUES (?, ?, ?, ?, ?)
        """
        insert_params = [activity_text, HCD_Space, HCD_Subspace, reason, annotator]
        try:
            insert_result = await client.query_db(
                db_id=DATABASE_ID, sql=insert_sql, params=insert_params
            )
            success = insert_result.success
        except Exception as e:
            print(f"Error inserting duplicate activity row: {e}")
            success = False
        return {"success": success, "inserted_new": True}

    # ------------------------------------------------------------------ #
    # 2b. Row is unlabeled → update it normally                           #
    # ------------------------------------------------------------------ #
    update_sql = """
        UPDATE labels
        SET HCD_Space = ?, HCD_Subspace = ?, Reason = ?, Annotator = ?
        WHERE rowid = ?
    """
    params = [HCD_Space, HCD_Subspace, reason, annotator, activity_id]
    try:
        update_result = await client.query_db(
            db_id=DATABASE_ID, sql=update_sql, params=params
        )
        return {"success": update_result.success, "inserted_new": False}
    except Exception as e:
        print(f"Error labeling activity: {e}")
        return {"success": False, "inserted_new": False}


async def get_activity_annotations() -> list[dict]:
    """
    Return all labeled rows grouped by Activity text.
    Useful for comparing annotations from multiple annotators across all activities.
    """
    sql = """
        SELECT rowid, Activity, HCD_Space, HCD_Subspace, Reason, Annotator
        FROM labels
        WHERE HCD_Space IS NOT NULL
          AND HCD_Space != ''
        ORDER BY Activity ASC, rowid ASC
    """
    try:
        result = await client.query_db(db_id=DATABASE_ID, sql=sql)
        if result.success and result.results:
            return result.results[0].get("results", [])
        return []
    except Exception as e:
        print(f"Error fetching activity annotations: {e}")
        return []
