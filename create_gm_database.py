import sqlite3
from pathlib import Path

DBFILE = Path(__file__).with_name("gmsystem.db")
SQLFILE = Path(__file__).with_name("gm_schema_and_data_extended.sql")

if not SQLFILE.exists():
    raise FileNotFoundError(f"Nie znaleziono pliku SQL: {SQLFILE}")

sql_text = SQLFILE.read_text(encoding="utf-8")

with sqlite3.connect(DBFILE) as conn:
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(sql_text)

    tables = [row[0] for row in conn.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)]

    print("Tabele:", ", ".join(tables))

    for table in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {count}")

print(f"Utworzono bazę: {DBFILE}")