import sqlite3
import os

userTable = "users"
DBName = "./osinter_users.db"

def initiateUserTable():
    if os.path.exists(DBName):
        os.remove(DBName)

    conn = sqlite3.connect(DBName)
    cur = conn.cursor()

    cur.execute(''' CREATE TABLE users
                (   username text NOT NULL PRIMARY KEY,
                    saved_article_ids text,
                    read_article_ids text,
                    password_hash text NOT NULL,
                    id text NOT NULL    )
                ''')

    conn.commit()
    conn.close()
