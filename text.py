# For doing substitution on text
import re

# For removing weird characthers that sometimes exist in text scraped from the internet
import unicodedata

# For counting and finding the most frequently used words when generating tag
from collections import Counter


# Function for taking in text from article (or basically any source) and outputting a list of words cleaned for punctuation, sole numbers, double spaces and other things so that it can be used for text analyssis
def clean_text(clear_text):
    # Normalizing the text, to remove weird characthers that sometimes pop up in webarticles
    clean_clear_text = unicodedata.normalize("NFKD", clear_text)
    # Remove line endings
    clean_clear_text = re.sub(r"\n", " ", clean_clear_text)

    return clean_clear_text


def tokenize_text(clean_clear_text):
    # Removing all contractions and "'s" created in english by descriping possession
    clean_clear_text = re.sub(r"(?:\'|’)\S*", "", clean_clear_text)
    # Remove punctuation
    clean_clear_text = re.sub(
        r'\s(?:,|\.|"|\'|\/|\\|:|-)+|(?:,|\.|"|\'|\/|\\|:|-)+\s', " ", clean_clear_text
    )
    clean_clear_text = re.sub(r"(?:\{.*\})|(?:\(\d{1,3}\))", "", clean_clear_text)
    # Remove all "words" where the word doesn't have any letters in it. This will remove "-", "3432" (words consisting purely of letters) and double spaces.
    clean_clear_text = re.sub(r"\s[^a-zA-Z]*\s", " ", clean_clear_text)

    # Converting the cleaned cleartext to a list
    clear_text_list = clean_clear_text.split(" ")

    return clear_text_list


# Function for taking in a list of words, and generating tags based on that. Does this by finding the words that doesn't appear in a wordlist (which means they probably have some technical relevans) and then sort them by how often they're used. The input should be cleaned with cleanText
def generate_tags(clear_text_list):

    # List containing words that doesn't exist in the wordlist
    uncommon_words = list()

    # Generating set of all words in the wordlist
    wordlist = set(line.strip() for line in open("./tools/wordlist.txt", "r"))

    # Find all the words that doesn't exist in the normal english dictionary (since those are the names and special words that we want to use as tags)
    for word in clear_text_list:
        if word.lower() not in wordlist and word != "":
            uncommon_words.append(word)

    # Take the newly found words, sort by them by frequency and take the 10 most used
    words_sorted_by_freq = [word for word in Counter(uncommon_words).most_common(10)]

    # only use those who have 3 mentions or more
    tag_list = list()
    for word_count in words_sorted_by_freq:
        if word_count[1] > 2:
            tag_list.append(word_count[0].capitalize())

    return tag_list


# Function for locating interresting bits and pieces in an article like ip adresses and emails
def locate_objects_of_interrest(clear_text):
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
    for object_name in objects:

        # Sometimes the regex's will return a tuple of the result split up based on the groups in the regex. This will combine each of the, before reuniting them as a list
        result = [
            result if type(result) != tuple else "".join(result)
            for result in objects[object_name]["pattern"].findall(clear_text)
        ]

        if result != []:
            # Removing duplicates from result list by converting it to a set and then back to list
            results[object_name] = {
                "results": list(set(result)),
                "tag": objects[object_name]["tag"],
            }

    return results


# The keyword file should be created like this "(keyword),(keyword),(keyword);(tag);[proximity]", where keyword are the words that are looked for withing [proximity] number of characthers of each side of the first (keyword), and if found the function "locateKeywords" from text will return (tag). [proximity] is optional, and if not specified 30 is the default value
def locate_keywords(keywords, clear_text):

    manual_tags = []
    for keyword_collection in keywords:
        for match in re.finditer(
            keyword_collection["keywords"].pop(0), clear_text.lower()
        ):

            current_pos = [
                match.span()[0] - keyword_collection["proximity"],
                match.span()[1] + keyword_collection["proximity"],
            ]
            scan_results = []

            for keyword in keyword_collection["keywords"]:
                current_pattern = re.compile(keyword)

                scan_results.append(
                    current_pattern.search(
                        clear_text.lower(), current_pos[0], current_pos[1]
                    )
                )

            if not None in scan_results:
                manual_tags.append(keyword_collection["tag"])
                break

    return manual_tags
