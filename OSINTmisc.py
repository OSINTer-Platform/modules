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
    debugMessages = True


def printDebug(message, timeStamp=True):
    if debugMessages and timeStamp:
        print(datetime.now().strftime("[%d/%m/%Y-%H:%M:%S]") + " " + message)
    elif debugMessages:
        print(message)

def createNewsSiteFolder(newsSite):
    if not os.path.isdir(Path("./articles/" + newsSite)):
        try:
            os.mkdir(Path("./articles/" + newsSite), mode=0o750)
        except:
            raise Exception("Apparently {} couldn't get the needed folder created for storing MD files, exiting".format(newsSite))
    else:
        try:
            os.chmod(Path("./articles/" + newsSite), 0o750)
        except:
            raise Exception("Failed to set the 750 permissions on articles/{}, either remove the folder or set the right perms yourself and try again.".format(newsSite))

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

# The keyword file should be created like this "(keyword),(keyword),(keyword);(tag);[proximity]", where keyword are the words that are looked for withing [proximity] number of characthers of each side of the first (keyword), and if found the function "locateKeywords" from OSINTtext will return (tag). [proximity] is optional, and if not specified 30 is the default value
def decodeKeywordsFile(filePath):
    keywords = []
    with open(filePath, "r") as keywordFile:
        for line in keywordFile.readlines():
            try:
                keywordDetails = line.strip().split(";")
                keywordCollection = {}
                keywordCollection["keywords"] = keywordDetails[0].lower().split(",")
                keywordCollection["tag"] = keywordDetails[1]
                if len(keywordDetails) == 3:
                    keywordCollection["proximity"] = int(keywordDetails[2])
                else:
                    keywordCollection["proximity"] = 30
            except:
                pass

            keywords.append(keywordCollection)
    return keywords
