# For doing substitution on text
import re

# For removing weird characthers that sometimes exist in text scraped from the internet
import unicodedata

# For counting and finding the most frequently used words when generating tag
from collections import Counter


# Function for taking in text from article (or basically any source) and outputting a list of words cleaned for punctuation, sole numbers, double spaces and other things so that it can be used for text analyssis
def cleanText(clearText):
    # Normalizing the text, to remove weird characthers that sometimes pop up in webarticles
    cleanClearText = unicodedata.normalize("NFKD", clearText)
    # Remove line endings
    cleanClearText = re.sub(r"\n", " ", cleanClearText)

    return cleanClearText


def tokenizeText(cleanClearText):
    # Removing all contractions and "'s" created in english by descriping possession
    cleanClearText = re.sub(r"(?:\'|’)\S*", "", cleanClearText)
    # Remove punctuation
    cleanClearText = re.sub(
        r'\s(?:,|\.|"|\'|\/|\\|:|-)+|(?:,|\.|"|\'|\/|\\|:|-)+\s', " ", cleanClearText
    )
    cleanClearText = re.sub(r"(?:\{.*\})|(?:\(\d{1,3}\))", "", cleanClearText)
    # Remove all "words" where the word doesn't have any letters in it. This will remove "-", "3432" (words consisting purely of letters) and double spaces.
    cleanClearText = re.sub(r"\s[^a-zA-Z]*\s", " ", cleanClearText)

    # Converting the cleaned cleartext to a list
    clearTextList = cleanClearText.split(" ")

    return clearTextList


# Function for taking in a list of words, and generating tags based on that. Does this by finding the words that doesn't appear in a wordlist (which means they probably have some technical relevans) and then sort them by how often they're used. The input should be cleaned with cleanText
def generateTags(clearTextList):

    # List containing words that doesn't exist in the wordlist
    uncommonWords = list()

    # Generating set of all words in the wordlist
    wordlist = set(line.strip() for line in open("./tools/wordlist.txt", "r"))

    # Find all the words that doesn't exist in the normal english dictionary (since those are the names and special words that we want to use as tags)
    for word in clearTextList:
        if word.lower() not in wordlist and word != "":
            uncommonWords.append(word)

    # Take the newly found words, sort by them by frequency and take the 10 most used
    sortedByFreq = [word for word in Counter(uncommonWords).most_common(10)]

    # only use those who have 3 mentions or more
    tagList = list()
    for wordCount in sortedByFreq:
        if wordCount[1] > 2:
            tagList.append(wordCount[0].capitalize())

    return tagList


# Function for locating interresting bits and pieces in an article like ip adresses and emails
def locateObjectsOfInterrest(clearText):
    objects = {
        "ipv4-adresses": {
            "pattern": re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"),
            "tag": False,
        },
        "ipv6-adresses": {
            "pattern": re.compile(
                r"\b(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))\b"
            ),
            "tag": False,
        },
        "email-adresses": {
            "pattern": re.compile(
                r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b"
            ),
            "tag": False,
        },
        "urls": {
            "pattern": re.compile(r'\b(?:[a-zA-Z]+:\/{1,3}|www\.)[^"\s]+'),
            "tag": False,
        },
        "CVE's": {"pattern": re.compile(r"CVE-\d{4}-\d{4,7}"), "tag": True},
        "MITRE IDs": {
            "pattern": re.compile(r"(?:[TMSGO]|TA)\d{4}\.\d{3}"),
            "tag": True,
        },
        "MD5-hash": {
            "pattern": re.compile(r"\b(?:[a-f0-9]{32}|[A-F0-9]{32})\b"),
            "tag": False,
        },
        "SHA1-hash": {
            "pattern": re.compile(r"\b(?:[a-f0-9]{40}|[A-F0-9]{40})\b"),
            "tag": False,
        },
        "SHA256-hash": {
            "pattern": re.compile(r"\b(?:[a-f0-9]{64}|[A-F0-9]{64})\b"),
            "tag": False,
        },
        "SHA512-hash": {
            "pattern": re.compile(r"\b(?:[a-f0-9]{128}|[A-F0-9]{128})\b"),
            "tag": False,
        },
    }
    results = {}
    for objectName in objects:

        # Sometimes the regex's will return a tuple of the result split up based on the groups in the regex. This will combine each of the, before reuniting them as a list
        result = [
            result if type(result) != tuple else "".join(result)
            for result in objects[objectName]["pattern"].findall(clearText)
        ]

        if result != []:
            # Removing duplicates from result list by converting it to a set and then back to list
            results[objectName] = {
                "results": list(set(result)),
                "tag": objects[objectName]["tag"],
            }

    return results


# The keyword file should be created like this "(keyword),(keyword),(keyword);(tag);[proximity]", where keyword are the words that are looked for withing [proximity] number of characthers of each side of the first (keyword), and if found the function "locateKeywords" from text will return (tag). [proximity] is optional, and if not specified 30 is the default value
def locateKeywords(keywords, clearText):

    manualTags = []
    for keywordCollection in keywords:
        for match in re.finditer(
            keywordCollection["keywords"].pop(0), clearText.lower()
        ):

            currentPos = [
                match.span()[0] - keywordCollection["proximity"],
                match.span()[1] + keywordCollection["proximity"],
            ]
            scanResults = []

            for keyword in keywordCollection["keywords"]:
                currentPattern = re.compile(keyword)

                scanResults.append(
                    currentPattern.search(
                        clearText.lower(), currentPos[0], currentPos[1]
                    )
                )

            if not None in scanResults:
                manualTags.append(keywordCollection["tag"])
                break

    return manualTags
