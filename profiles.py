import json
import os
from typing import Any, cast

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
        return cast(dict[str, Any], json.loads(f.read().strip()))


def get_profiles() -> list[dict[str, Any]]:
    profiles = []

    for profile_name in list_profiles(complete_file_name=True):
        with open(os.path.join(PROFILE_PATH, profile_name)) as f:
            profiles.append(json.loads(f.read().strip()))

    return profiles
