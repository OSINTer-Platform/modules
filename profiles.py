# Used for listing files in directory
import os

# Used for handling relative paths
from pathlib import Path

import json

# Function for reading all profile files and returning the content in a list if profile_name is left empty, returning the contents of one profile if it isn't or simply just return the names of the available profile if profile_name is left empty and just_names is set to true
def get_profiles(profile_name="", just_names=False):

    profile_path = "./profiles/profiles/"

    if profile_name == "":
        # Listing all the profiles by getting the OS indepentent path to profiles folder and listing files in it, and then only choosing those files that end in a .profile
        profile_files = [
            x for x in os.listdir(path=Path(profile_path)) if ".profile" in x
        ]

        if just_names and profile_name == "":
            # Remember to remove the .profile extension
            return [x[:-8] for x in profile_files]

        # List for holding the information from all the files, so they only have to be read one
        profiles = list()

        # Reading all the different profile files and storing the contents in just created list
        for profile in profile_files:

            # Stripping any potential trailing or leading newlines
            profiles.append(
                json.loads(Path(profile_path + profile).read_text().strip())
            )

        return profiles
    else:
        return json.loads(
            Path(profile_path + profile_name + ".profile").read_text().strip()
        )


def collect_website_details(es_client):
    db_stored_profiles = es_client.get_source_category_list_from_db()

    profiles = get_profiles()

    # The final list of all the website information
    details = {}

    for profile in profiles:

        if profile["source"]["profile_name"] in db_stored_profiles:
            image_url = profile["source"]["image_url"]

            details[profile["source"]["profile_name"]] = {
                "name": profile["source"]["name"],
                "image": image_url,
                "url": profile["source"]["address"],
            }

    return {source: details[source] for source in sorted(details)}
