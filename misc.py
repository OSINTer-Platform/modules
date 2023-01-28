import os
import re
from typing import TypedDict


def create_folder(folder_name: str) -> None:
    folder_path = os.path.normcase("./" + folder_name)

    if not os.path.isdir(folder_path):
        try:
            os.mkdir(folder_path, mode=0o750)
        except:
            # This shoudln't ever be reached, as it would imply that the folder doesn't exist, but the script also is unable to create it. Could possibly be missing read permissions if the scripts catches this exception
            raise Exception(f"The folder {folder_name} couldn't be created, exiting")
    else:
        try:
            os.chmod(folder_path, 0o750)
        except:
            raise Exception(
                f"Failed to set the 750 permissions on {folder_name}, either remove the folder or set the right perms yourself and try again."
            )


def check_if_valid_url(url: str) -> bool:
    if re.match(r"https?:\/\/.*\..*", url):
        return True
    else:
        return False


# Function for intellegently adding the domain to a relative path on website depending on if the domain is already there
def cat_url(root_url: str, relative_path: str) -> str:
    if check_if_valid_url(relative_path):
        return relative_path
    else:
        return root_url[:-1] + relative_path


# The keyword file should be created like this "(keyword),(keyword),(keyword);(tag);[proximity]", where keyword are the words that are looked for withing [proximity] number of characthers of each side of the first (keyword), and if found the function "locateKeywords" from text will return (tag). [proximity] is optional, and if not specified 30 is the default value


class Keywords(TypedDict, total=False):
    keywords: list[str]
    tag: str
    proximity: int


def decode_keywords_file(file_path) -> list[Keywords]:
    keywords = []
    with open(file_path, "r") as keyword_file:
        for line in keyword_file.readlines():
            try:
                keyword_details = line.strip().split(";")
                keyword_collection: Keywords = {}
                keyword_collection["keywords"] = keyword_details[0].lower().split(",")
                keyword_collection["tag"] = keyword_details[1]
                if len(keyword_details) == 3:
                    keyword_collection["proximity"] = int(keyword_details[2])
                else:
                    keyword_collection["proximity"] = 30
            except:
                continue

            keywords.append(keyword_collection)
    return keywords
