from datetime import datetime, timezone
from typing import TypeAlias, TypedDict

from pydantic import BaseModel, HttpUrl



class BaseArticle(BaseModel):
    title: str
    description: str
    url: HttpUrl
    image_url: HttpUrl
    profile: str
    source: str
    publish_date: datetime
    inserted_at: datetime = datetime.now(timezone.utc)
    id: str | None = None


class MLAttributes(TypedDict, total=False):
    similar: list[str]
    cluster: int


class TagsOfInterest(TypedDict):
    results: list[str]
    tag: bool


class Tags(TypedDict, total=False):
    manual: dict[str, list[str]]
    automatic: list[str]
    interresting: dict[str, TagsOfInterest]


class FullArticle(BaseArticle):
    author: str | None = None
    formatted_content: str | None = None
    content: str | None = None
    summary: str | None = None
    tags: Tags = {}
    read_times: int = 0
    ml: MLAttributes | None = None


class BaseTweet(BaseModel):
    twitter_id: str
    content: str

    publish_date: datetime
    inserted_at: datetime = datetime.now(timezone.utc)

    id: str | None = None


class FullTweet(BaseTweet):
    hashtags: list[str] = []
    mentions: list[str] = []

    author_details: dict[str, str] = {}
    OG: dict[str, str] = {}

    read_times: int = 0


OSINTerDocument: TypeAlias = BaseArticle | BaseTweet
