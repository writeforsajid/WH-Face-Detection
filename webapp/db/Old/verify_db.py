import os, sqlite3

def main():
    db = os.getenv('DB_PATH', './../data/WhiteHouse.db')
    print('DB:', db)
    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [r[0] for r in c.fetchall()]
    print('Tables:', tables)
    if 'roles' in tables:
        c.execute("SELECT role_name, priority FROM roles ORDER BY priority;")
        print('Roles:', c.fetchall())
    if 'guest_auth' in tables:
        c.execute("PRAGMA table_info(guest_auth)")
        print('guest_auth columns:', [tuple(row) for row in c.fetchall()])
    if 'guest_roles' in tables:
        c.execute("PRAGMA table_info(guest_roles)")
        print('guest_roles columns:', [tuple(row) for row in c.fetchall()])
    conn.close()

if __name__ == '__main__':
    main()
