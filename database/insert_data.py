from __future__ import annotations

import asyncio

from database.db import DATABASE_ID, client


async def ainsert_activities(activities: list[str]) -> int:
	"""
	Insert non-empty activities into labels table.

	Returns:
		int: number of successfully inserted rows.
	"""
	if not DATABASE_ID:
		raise ValueError("Missing D1_DATABASE_ID in environment.")

	inserted = 0
	sql = 'INSERT INTO "main"."labels" ("Activity") VALUES(?)'

	for activity in activities:
		cleaned = " ".join(activity.split()).strip()
		if not cleaned:
			continue

		try:
			result = await client.query_db(db_id=DATABASE_ID, sql=sql, params=[cleaned])
		except Exception:
			continue

		if result.success:
			inserted += 1

	return inserted


def insert_activities(activities: list[str]) -> int:
	"""Sync wrapper for bulk activity insertion."""
	try:
		asyncio.get_running_loop()
	except RuntimeError:
		return asyncio.run(ainsert_activities(activities))

	raise RuntimeError(
		"insert_activities cannot be called from a running event loop. "
		"Use ainsert_activities instead."
	)
