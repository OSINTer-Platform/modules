import json
import os
from typing import Any


PROFILE_PATH = os.path.normcase("./profiles/profiles/")


def list_profiles(complete_file_name: bool = False) -> list[str]:
    if complete_file_name:
        return [x for x in os.listdir(PROFILE_PATH) if ".profile" in x]
    else:
        return [x[:-8] for x in os.listdir(PROFILE_PATH) if ".profile" in x]


def get_profile(specific_profile: str) -> dict[str, Any]:
    if ".profile" not in specific_profile:
        specific_profile += ".profile"

    with open(os.path.join(PROFILE_PATH, specific_profile)) as f:
        return json.loads(f.read().strip())


def get_profiles() -> list[dict[str, Any]]:

    profiles = []

    for profile_name in list_profiles(complete_file_name=True):

        with open(os.path.join(PROFILE_PATH, profile_name)) as f:
            profiles.append(json.loads(f.read().strip()))

    return profiles


def collect_website_details(es_client) -> dict[str, dict[str, str]]:
    db_stored_profiles = list(es_client.get_unique_values())

    profiles = sorted(
        get_profiles(), key=lambda profile: profile["source"]["profile_name"]
    )

    details = {}

    for profile in profiles:

        if (profile_name := profile["source"]["profile_name"]) in db_stored_profiles:
            image_url = profile["source"]["image_url"]

            details[profile_name] = {
                "name": profile["source"]["name"],
                "image": image_url,
                "url": profile["source"]["address"],
            }

    return details
