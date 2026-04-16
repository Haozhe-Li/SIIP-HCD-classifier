import sqlite3

conn = sqlite3.connect(':memory:')
cursor = conn.cursor()

cursor.execute('''CREATE TABLE labels (rowid INTEGER PRIMARY KEY, Activity TEXT, HCD_Space TEXT)''')
cursor.execute('''INSERT INTO labels (Activity, HCD_Space) VALUES ('A1', 'Space1')''')
cursor.execute('''INSERT INTO labels (Activity, HCD_Space) VALUES ('A2', 'Space2')''')
# Second annotation for A1
cursor.execute('''INSERT INTO labels (Activity, HCD_Space) VALUES ('A1', 'Space1_2')''')
# Unlabeled
cursor.execute('''INSERT INTO labels (Activity, HCD_Space) VALUES ('A3', NULL)''')

TARGET_ANNOTATIONS = 2

sql_fetch = f"""
    SELECT MIN(rowid) as rowid, Activity 
    FROM labels
    GROUP BY Activity
    HAVING SUM(CASE WHEN HCD_Space IS NOT NULL AND HCD_Space != '' THEN 1 ELSE 0 END) < {TARGET_ANNOTATIONS}
"""
cursor.execute(sql_fetch)
print("FETCH:", cursor.fetchall())

sql_stats = f"""
    WITH ActivityCounts AS (
        SELECT 
            Activity,
            SUM(CASE WHEN HCD_Space IS NOT NULL AND HCD_Space != '' THEN 1 ELSE 0 END) as label_count
        FROM labels
        GROUP BY Activity
    )
    SELECT 
        COUNT(*) * {TARGET_ANNOTATIONS} as total,
        SUM(CASE WHEN label_count >= {TARGET_ANNOTATIONS} THEN {TARGET_ANNOTATIONS} ELSE label_count END) as labeled
    FROM ActivityCounts
"""
cursor.execute(sql_stats)
row = cursor.fetchone()
print(f"STATS: Total: {row[0]}, Labeled: {row[1]}, Unlabeled: {row[0] - row[1]}")

conn.close()
