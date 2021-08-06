# For checking if string matches regex
import re

import os

# For getting the current date and time for logging and verbose output
from datetime import datetime

from pathlib import Path


try:
    # For if the user wants verbose output
    from __main__ import debugMessages
except:
    pass


def printDebug(message, timeStamp=True):
    if debugMessages and timeStamp:
        print(datetime.now().strftime("[%d/%m/%Y-%H:%M:%S]") + " " + message)
    elif debugMessages:
        print(message)

def createNewsSiteFolder(newsSite):
    if not os.path.isdir(Path("./articles/" + newsSite)):
        try:
            os.mkdir(Path("./articles/" + newsSite))
        except:
            raise Exception("Apparently {} couldn't get the needed folder created for storing MD files, exiting".format(newsSite))

def checkIfURL(URL):
    if re.match(r"https?:\/\/.*\..*", URL):
        return True
    else:
        return False

# Function for intellegently adding the domain to a relative path on website depending on if the domain is already there
def catURL(rootURL, relativePath):
    if checkIfURL(relativePath):
        return relativePath
    else:
        return rootURL[:-1] + relativePath

# Function for taking an arbitrary string and convert it into one that can safely be used as a filename and for removing spaces as those can be a headache to deal with
def fileSafeString(unsafeString):
    allowedCharacthers = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
    unsafeString = unsafeString.strip().replace(" ", "-")
    safeString = ''.join(c for c in unsafeString if c in allowedCharacthers)
    return safeString
