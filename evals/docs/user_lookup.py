import sqlite3


def find_user(db_path, name):
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT id, email FROM users WHERE name = '" + name + "'").fetchall()
    except:
        return None
    return rows[0]
