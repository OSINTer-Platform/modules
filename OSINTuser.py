import argon2
import secrets

ph = argon2.PasswordHasher()


class User:
    def __init__(self, username, indexName, esConn):
        self.username = username
        self.indexName = indexName
        self.es = esConn

    def getCurrentUserObject(self):
        return self.es.search(
            index=self.indexName,
            body={"query": {"term": {"username": {"value": self.username}}}},
        )["hits"]["hits"][0]

    def checkIfUserExists(self):
        print(
            "\n\n",
            self.es.search(
                index=self.indexName,
                body={"query": {"term": {"username": {"value": self.username}}}},
            ),
            "\n\n",
        )
        print(self.username)
        return (
            int(
                self.es.search(
                    index=self.indexName,
                    body={"query": {"term": {"username": {"value": self.username}}}},
                )["hits"]["total"]["value"]
            )
            != 0
        )

    def get_id(self):
        if self.checkIfUserExists():
            return self.getCurrentUserObject()["_id"]
        else:
            return False

    # Get the hash for the password for [username]
    def getPasswordHash(self):
        if self.checkIfUserExists():
            return self.getCurrentUserObject()["_source"]["password_hash"]
        else:
            return False

    # Set the password hash for [username]
    def setPasswordHash(self, passwordHash):
        return self.es.update(
            index=self.indexName, id=self.get_id(), doc={"password_hash": passwordHash}
        )

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
            currentUser = self.getCurrentUserObject()
            return {
                tableName: currentUser["_source"][tableName] for tableName in tableNames
            }
        else:
            return {tableName: [] for tableName in tableNames}

    # Will mark or "unmark" an article for the current user based on whether [add] is true or false. articleTableName is the name of the table storing the articles (used for verifying that there exists a table with that name) and userTableName is the name of the table holding the user and their saved articles. Column is the name of the column which holds the marked articles of that type, so this is what differentiates whether the system for example saves the article or markes it as read.
    def markArticle(self, column, articleID, add):
        if self.checkIfUserExists():
            currentUser = self.getCurrentUserObject()
            if add:
                if articleID not in currentUser["_source"][column]:
                    currentUser["_source"][column].append(articleID)
                    self.es.update(
                        index=self.indexName,
                        id=currentUser["_id"],
                        doc={column: currentUser["_source"][column]},
                    )
            else:
                if articleID in currentUser["_source"][column]:
                    currentUser["_source"][column].remove(articleID)
                    self.es.update(
                        index=self.indexName,
                        id=currentUser["_id"],
                        doc={column: currentUser["_source"][column]},
                    )

            return True
        else:
            return False

    # Methods needed by the flask_login plugin
    def is_active(self):
        return True

    def is_authenticated(self):
        return True

    def is_anonymous(self):
        return False


def getUsernameFromID(userID, indexName, esConn):
    esResponse = esConn.get(index=indexName, id=userID, ignore=[404])

    if esResponse["found"]:
        return esResponse["_source"]["username"]
    else:
        False


def createUser(username, password, indexName, esConn):

    if User(username, indexName, esConn).checkIfUserExists():
        return False
    else:
        userObject = {
            "username": username,
            "password_hash": ph.hash(password),
            "read_article_ids": [],
            "saved_article_ids": [],
        }

        esConn.index(index=indexName, document=userObject)

        return True
