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



# Will mark or "unmark" an article for the [osinter_user] based on whether [add] is true or false. articleTableName is the name of the table storing the articles (used for verifying that there exists a table with that name) and userTableName is the name of the table holding the user and their saved articles. Column is the name of the column which holds the marked articles of that type, so this is what differentiates whether the system for example saves the article or markes it as read.
def markArticle(osinter_user, column, articleID, add):

    conn = sqlite3.connect(DBName)
    cur = conn.cursor

    cur.execute(f"SELECT EXISTS(SELECT 1 FROM {userTable} WHERE username = ?);", (osinter_user,))
    if cur.fetchall() == []:
        return "User does not seem to exist"
    else:
        if add:
            # Combines the array from the DB with the new ID, and takes all the uniqe entries from that so that duplicates are avoided
            cur.execute(f"UPDATE {userTable} SET {column} = ({column} || ?) WHERE username = ?", ("|" + str(articleID)), osinter_user)
        else:
            cur.execute(f"UPDATE {userTable} SET {column} = REPLACE({column}, ?, '') WHERE username = ?", ("|" + str(articleID)))

    conn.commit()
    conn.close()

    return True
