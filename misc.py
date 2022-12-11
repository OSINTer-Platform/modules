# For checking if string matches regex
import re

import os
from pathlib import Path

# For decompressing the geckodriver that comes compressed in the .tar.gz format when downloading it
import tarfile
import json
import requests


# Mozilla will have an api endpoint giving a lot of information about the latest releases for the geckodriver, from which the url for the linux 64 bit has to be extracted
def extract_driver_url():
    driver_details = json.loads(
        requests.get(
            "https://api.github.com/repos/mozilla/geckodriver/releases/latest"
        ).text
    )

    for platform_release in driver_details["assets"]:
        if platform_release["name"].endswith("linux64.tar.gz"):
            return platform_release["browser_download_url"]


# Downloading and extracting the .tar.gz file the geckodriver is stored in into the tools directory
def download_driver(driver_url):
    driver_contents = requests.get(driver_url, stream=True)
    with tarfile.open(fileobj=driver_contents.raw, mode="r|gz") as driver_file:
        driver_file.extractall(path=Path("./tools/"))


def create_folder(folder_name):
    if not os.path.isdir(Path("./" + folder_name)):
        try:
            os.mkdir(Path("./" + folder_name), mode=0o750)
        except:
            # This shoudln't ever be reached, as it would imply that the folder doesn't exist, but the script also is unable to create it. Could possibly be missing read permissions if the scripts catches this exception
            raise Exception(f"The folder {folder_name} couldn't be created, exiting")
    else:
        try:
            os.chmod(Path("./" + folder_name), 0o750)
        except:
            raise Exception(
                f"Failed to set the 750 permissions on {folder_name}, either remove the folder or set the right perms yourself and try again."
            )


def check_if_valid_url(url):
    if re.match(r"https?:\/\/.*\..*", url):
        return True
    else:
        return False


# Function for intellegently adding the domain to a relative path on website depending on if the domain is already there
def cat_url(root_url, relative_path):
    if check_if_valid_url(relative_path):
        return relative_path
    else:
        return root_url[:-1] + relative_path


# The keyword file should be created like this "(keyword),(keyword),(keyword);(tag);[proximity]", where keyword are the words that are looked for withing [proximity] number of characthers of each side of the first (keyword), and if found the function "locateKeywords" from text will return (tag). [proximity] is optional, and if not specified 30 is the default value
def decode_keywords_file(file_path):
    keywords = []
    with open(file_path, "r") as keyword_file:
        for line in keyword_file.readlines():
            try:
                keyword_details = line.strip().split(";")
                keyword_collection = {}
                keyword_collection["keywords"] = keyword_details[0].lower().split(",")
                keyword_collection["tag"] = keyword_details[1]
                if len(keyword_details) == 3:
                    keyword_collection["proximity"] = int(keyword_details[2])
                else:
                    keyword_collection["proximity"] = 30
            except:
                pass

            keywords.append(keyword_collection)
    return keywords
