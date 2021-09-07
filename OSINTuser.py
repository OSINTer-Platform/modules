import argon2
from OSINTmodules.OSINTdatabase import setPasswordHashForOSINTerUser, getPasswordHashForOSINTerUser

ph = argon2.PasswordHasher()

def checkIfUserExists(connection, userTableName, username):
    with connection.cursor() as cur:
        cur.execute("SELECT EXISTS(SELECT 1 FROM {} WHERE username = %s);".format(userTableName), (username,))
        if cur.fetchall() == []:
            return False
        else:
            return True

# Set the password hash for [username]
def setPasswordHashForOSINTerUser(connection, userTableName, username, passwordHash):
    if checkIfUserExists(connection, userTableName, username):
        with connection.cursor() as cur:
            cur.exeucte("UPDATE {} SET password_hash=%s WHERE username=%s;".format(userTableName), (passwordHash, username))
            connection.commit()
            return True
    else:
        return False

# Get the hash for the password for [username]
def getPasswordHashForOSINTerUser(connection, userTableName, username):
    if checkIfUserExists(connection, userTableName, username):
        with connection.cursor() as cur:
            cur.exeucte("SELECT password_hash FROM {} WHERE username=%s;".format(userTableName), (username,))
            connection.commit()
            return True
    else:
        return False

# Will verify that clear text [password] matches [username].
def verifyPassword(connection, userTableName, username, password):
    userHash = getPasswordHashForOSINTerUser(connection, userTableName, username)

    try:
        ph.verify(userHash)   

        if ph.check_needs_rehash(userHash):
            setPasswordHashForOSINTerUser(username, ph.hash(password))
        return True

    except argon2.exceptions.VerifyMismatchError:
        return False

def createUser(connection, userTableName, username, password):
    if checkIfUserExists(connection, userTableName, username):
        return False
    else:
        with connection.cursor() as cur:
            cur.execute("INSERT INTO {} (username, password_hash) VALUES (%s, %s);", (username, ph.hash(password)))
        connection.commit()
        return True
