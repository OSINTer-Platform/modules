import os
from typing_extensions import Literal

from pydantic import BaseModel

PROFILE_PATH = os.path.normcase("./profiles/profiles/")


class ScrapingTargets(BaseModel):
    container_list: str
    link_containers: str
    links: str


class ElementSelector(BaseModel):
    element: str
    content_field: str


class ArticleMeta(BaseModel):
    author: str | ElementSelector
    publish_date: str | ElementSelector
    title: str | ElementSelector
    description: str | ElementSelector
    image_url: str | ElementSelector


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


def list_profiles(
    complete_file_name: bool = False, include_disabled: bool = False, path: str | None = None
) -> list[str]:
    def is_profile(name: str) -> bool:
        if name.endswith(".profile"):
            return True
        if include_disabled and name.endswith(".disabled"):
            return True

        return False

    def strip_extension(name: str) -> str:
        return name.removesuffix(".profile").removesuffix(".disabled")

    if complete_file_name:
        return [x for x in os.listdir(path if path else PROFILE_PATH) if is_profile(x)]
    else:
        return [strip_extension(x) for x in os.listdir(path if path else PROFILE_PATH) if is_profile(x)]


def get_profile(specific_profile: str, path: str | None = None) -> Profile:
    if not specific_profile.endswith(".profile") and not specific_profile.endswith(
        ".disabled"
    ):
        specific_profile += ".profile"

    with open(os.path.join(path if path else PROFILE_PATH, specific_profile)) as f:
        return Profile.model_validate_json(f.read())


def get_profiles(include_disabled: bool = False, path: str | None = None) -> list[Profile]:
    profiles: list[Profile] = []

    for profile_name in list_profiles(
        complete_file_name=True, include_disabled=include_disabled, path=path
    ):
        with open(os.path.join(path if path else PROFILE_PATH, profile_name)) as f:
            profiles.append(Profile.model_validate_json(f.read().strip()))

    return profiles
