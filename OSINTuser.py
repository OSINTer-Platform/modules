import argon2
import secrets

ph = argon2.PasswordHasher()

class User():
    def __init__(self, DBConnection, userTableName, username):
        self.DBConnection = DBConnection
        self.userTableName = userTableName
        self.username = username

    def checkIfUserExists(self):
        with self.DBConnection.cursor() as cur:
            cur.execute("SELECT EXISTS(SELECT 1 FROM {} WHERE username = %s);".format(self.userTableName), (self.username,))
            if cur.fetchall() == []:
                return False
            else:
                cur.execute("SELECT password_hash FROM {} WHERE username = %s;".format(self.userTableName), (self.username,))
                if cur.fetchall() == []:
                    return False
                else:
                    return True

    # Set the password hash for [username]
    def setPasswordHash(self, passwordHash):
        if self.checkIfUserExists():
            with self.DBConnection.cursor() as cur:
                cur.execute("UPDATE {} SET password_hash=%s WHERE username=%s;".format(self.userTableName), (passwordHash, self.username))
                self.DBConnection.commit()
                return True
        else:
            return False

    # Get the hash for the password for [username]
    def getPasswordHash(self):
        if self.checkIfUserExists():
            with self.DBConnection.cursor() as cur:
                cur.execute("SELECT password_hash FROM {} WHERE username=%s;".format(self.userTableName), (self.username,))
                return cur.fetchall()[0][0]
        else:
            return False

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

    def get_id(self):
        if self.checkIfUserExists():
            with self.DBConnection.cursor() as cur:
                cur.execute("SELECT id FROM {} WHERE username=%s;".format(self.userTableName), (self.username,))
                return cur.fetchall()[0][0]
        else:
            return False

    # Methods needed by the flask_login plugin
    def is_active(self):
        return True
    def is_authenticated(self):
        return True
    def is_anonymous(self):
        return False

def createUser(connection, userTableName, username, password):
    if User(connection, userTableName, username).checkIfUserExists():
        return False
    else:
        with connection.cursor() as cur:

            # Will generate ID for the new user, and make sure that it's unique
            while True:
                userID = secrets.token_urlsafe(128)[0:128]
                cur.execute("SELECT EXISTS(SELECT 1 FROM {} WHERE id = %s);".format(userTableName), (userID,))
                if cur.fetchall()[0][0] == False:
                    break

            cur.execute("INSERT INTO {} (username, password_hash, id) VALUES (%s, %s, %s);".format(userTableName), (username, ph.hash(password), userID))
        connection.commit()
        return True
