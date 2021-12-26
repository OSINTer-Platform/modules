import argon2
import secrets
import sqlite3

userTable = "users"
DBName = "./osinter_users.db"

ph = argon2.PasswordHasher()

class User():
    def __init__(self, username):
        self.conn = sqlite3.connect(DBName)
        self.username = username

    def checkIfUserExists(self):
        cur = self.conn.cursor()

        cur.execute(f"SELECT EXISTS(SELECT 1 FROM {userTable} WHERE username = ?);", (self.username,))

        exists = bool(cur.fetchone()[0])
        cur.close()

        return exists

    # Set the password hash for [username]
    def setPasswordHash(self, passwordHash):
        cur = self.conn.cursor()
        cur.execute(f"UPDATE {userTable} SET password_hash=? WHERE username=?;", (passwordHash, self.username))
        self.conn.commit()
        cur.close()

    # Get the hash for the password for [username]
    def getPasswordHash(self):
        if self.checkIfUserExists():
            cur = self.conn.cursor()
            cur.execute(f"SELECT password_hash FROM {userTable} WHERE username=?;", (self.username,))
            return cur.fetchone()[0]
        else:
            return False

    def changePassword(self, password):
        if self.checkIfUserExists():
            self.setPasswordHash(ph.hash(password))

    # Will verify that clear text [password] matches the one for the current user
    def verifyPassword(self, password):
        if not self.checkIfUserExists():
            return False
        else:
            userHash = self.getPasswordHash()

            try:
                ph.verify(userHash, password)

                if ph.check_needs_rehash(userHash):
                    self.setPasswordHash(ph.hash(password))
                return True

            except argon2.exceptions.VerifyMismatchError:
                return False

    def getMarkedArticles(self, tableNames=["saved_article_ids", "read_article_ids"]):
        if self.checkIfUserExists():
            cur = self.conn.cursor()

            DBResults = {}
            for tableName in tableNames:
                cur.execute(f"SELECT {tableName} FROM {userTable} WHERE username=?;", (self.username,))

                currentResults = cur.fetchone()[0].split("~")
                currentResults.pop(0)
                DBResults[tableName] = currentResults if currentResults else []

            cur.close()
            return DBResults
        else:
            return { tableName:[] for tableName in tableNames}

    # Will mark or "unmark" an article for the current user based on whether [add] is true or false. articleTableName is the name of the table storing the articles (used for verifying that there exists a table with that name) and userTableName is the name of the table holding the user and their saved articles. Column is the name of the column which holds the marked articles of that type, so this is what differentiates whether the system for example saves the article or markes it as read.
    def markArticle(self, column, articleID, add):

        if self.checkIfUserExists():
            cur = self.conn.cursor()
            if add:
                # Combines the array from the DB with the new ID, and takes all the uniqe entries from that so that duplicates are avoided
                cur.execute(f"UPDATE {userTable} SET {column} = ({column} || ?) WHERE username = ?", ("~" + str(articleID), self.username))
            else:
                cur.execute(f"UPDATE {userTable} SET {column} = REPLACE({column}, ?, '') WHERE username = ?", ("~" + str(articleID), self.username))

            self.conn.commit()
            cur.close()
            return True
        else:
            return False


    def get_id(self):
        if self.checkIfUserExists():
            cur = self.conn.cursor()
            cur.execute(f"SELECT id FROM {userTable} WHERE username=?;", (self.username,))
            return cur.fetchone()[0]
        else:
            return False

    # Methods needed by the flask_login plugin
    def is_active(self):
        return True
    def is_authenticated(self):
        return True
    def is_anonymous(self):
        return False

def getUsernameFromID(userID):
    conn = sqlite3.connect(DBName)
    cur = conn.cursor()

    cur.execute(f"SELECT username FROM {userTable} WHERE id = ?;", (userID,))
    username = cur.fetchone()

    conn.close()

    if username == None:
        return False
    else:
        return username[0]

def getSavedArticles(username):
    conn = sqlite3.connect(DBName)
    cur = conn.cursor()

    cur.execute(f"SELECT saved_article_ids FROM {userTable} WHERE username = ?", (username,))

    savedArticleIDs = cur.fetchone()

    conn.close()

    if savedArticleIDs == None:
        return []
    else:
        return savedArticleIDs[0].split("~")

def createUser(username, password):
    conn = sqlite3.connect(DBName)

    if User(username).checkIfUserExists():
        conn.close()
        return False
    else:
        cur = conn.cursor()
        # Will generate ID for the new user, and make sure that it's unique
        while True:
            userID = secrets.token_urlsafe(128)[0:128]
            cur.execute(f"SELECT EXISTS (SELECT 1 FROM {userTable} WHERE id = ?);", (userID,))
            if cur.fetchone()[0] == 0:
                break

        cur.execute(f"INSERT INTO {userTable} (username, password_hash, id) VALUES (?, ?, ?);", (username, ph.hash(password), userID))

        conn.commit()
        conn.close()

        return True
