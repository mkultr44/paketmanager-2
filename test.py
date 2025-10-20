import sqlite3, datetime, random

conn = sqlite3.connect("pakete.db")
conn.execute("DROP TABLE IF EXISTS pakete")
conn.execute("""
CREATE TABLE pakete(
    id INTEGER PRIMARY KEY,
    code TEXT UNIQUE,
    zone TEXT,
    ts TEXT
)
""")

zones = ["A", "B", "C", "D", "E-1", "E-2", "E-3", "E-4", "F"]
base = datetime.datetime.utcnow()

for i in range(1, 25):
    code = f"0300{random.randint(100000000, 999999999)}{random.randint(10,99)}"
    zone = random.choice(zones)
    ts = (base - datetime.timedelta(days=random.randint(0, 9),
                                    hours=random.randint(0, 12))).isoformat()
    conn.execute("INSERT INTO pakete(code, zone, ts) VALUES (?, ?, ?)", (code, zone, ts))

conn.commit()
conn.close()
print("pakete.db erzeugt.")
