# For checking if string matches regex
import re

import os
from pathlib import Path

def createFolder(folderName):
    if not os.path.isdir(Path("./" + folderName)):
        try:
            os.mkdir(Path("./" + folderName), mode=0o750)
        except:
            # This shoudln't ever be reached, as it would imply that the folder doesn't exist, but the script also is unable to create it. Could possibly be missing read permissions if the scripts catches this exception
            raise Exception(
                "The folder {} couldn't be created, exiting".format(folderName)
            )
    else:
        try:
            os.chmod(Path("./" + folderName), 0o750)
        except:
            raise Exception(
                "Failed to set the 750 permissions on {}, either remove the folder or set the right perms yourself and try again.".format(
                    folderName
                )
            )


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


# The keyword file should be created like this "(keyword),(keyword),(keyword);(tag);[proximity]", where keyword are the words that are looked for withing [proximity] number of characthers of each side of the first (keyword), and if found the function "locateKeywords" from text will return (tag). [proximity] is optional, and if not specified 30 is the default value
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
