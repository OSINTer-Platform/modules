import os
from typing_extensions import Literal

from pydantic import BaseModel

PROFILE_PATH = os.path.normcase("./profiles/profiles/")


class ScrapingTargets(BaseModel):
    container_list: str
    link_containers: str
    links: str


class ArticleMeta(BaseModel):
    author: str
    publish_date: str
    title: str
    description: str
    image_url: str


class ArticleContent(BaseModel):
    container: str
    remove: list[str]


class ProfileSource(BaseModel):
    name: str
    profile_name: str
    address: str
    image_url: str
    retrieval_method: Literal["scraping", "dynamic", "rss"]
    news_paths: list[str]
    scraping_targets: ScrapingTargets


class ProfileScraping(BaseModel):
    js_injections: list[str] = []
    meta: ArticleMeta
    content: ArticleContent


class Profile(BaseModel):
    source: ProfileSource
    scraping: ProfileScraping


def list_profiles(complete_file_name: bool = False) -> list[str]:
    if complete_file_name:
        return [x for x in os.listdir(PROFILE_PATH) if ".profile" in x]
    else:
        return [x[:-8] for x in os.listdir(PROFILE_PATH) if ".profile" in x]


def get_profile(specific_profile: str) -> Profile:
    if ".profile" not in specific_profile:
        specific_profile += ".profile"

    with open(os.path.join(PROFILE_PATH, specific_profile)) as f:
        return Profile.model_validate_json(f.read())


def get_profiles() -> list[Profile]:
    profiles: list[Profile] = []

    for profile_name in list_profiles(complete_file_name=True):
        with open(os.path.join(PROFILE_PATH, profile_name)) as f:
            profiles.append(Profile.model_validate_json(f.read().strip()))

    return profiles
