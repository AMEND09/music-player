import sqlite3

try:
    with sqlite3.connect("sql.db") as conn:
        print(f"opened db with version {sqlite3.sqlite_version}")
        cursor = conn.cursor()
        create_table_query = '''
        CREATE TABLE IF NOT EXISTS Students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER,
            email TEXT
        );
        '''
        cursor.execute(create_table_query)
        conn.commit()
        
        insert_query = """
        INSERT INTO Students (name, age, email)
        VALUES (?, ?, ?);
        """

        #to execute many at once, use python executemany() cursor.executemany(insert_query, [list of data])
        conn.commit()

        print("success")
except sqlite3.OperationalError as e:
    print("failed", e)
