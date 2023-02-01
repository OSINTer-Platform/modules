from datetime import datetime
from typing import TypedDict, TypeVar

from pydantic import BaseModel, Field, HttpUrl


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


class BaseArticle(BaseModel):
    title: str
    description: str
    url: HttpUrl
    image_url: HttpUrl
    profile: str
    source: str
    publish_date: datetime
    inserted_at: datetime = Field(default_factory=datetime.utcnow)
    read_times: int = 0
    id: str | None = None


class FullArticle(BaseArticle):
    author: str | None = None
    formatted_content: str | None = None
    content: str | None = None
    summary: str | None = None
    tags: Tags = {}
    ml: MLAttributes | None = None


class FullTweet(BaseModel):
    twitter_id: str
    content: str

    publish_date: datetime
    inserted_at: datetime = Field(default_factory=datetime.utcnow)

    read_times: int = 0

    id: str | None = None

    hashtags: list[str] = []
    mentions: list[str] = []

    author_details: dict[str, str] = {}
    OG: dict[str, str] = {}


OSINTerDocument = TypeVar("OSINTerDocument", FullTweet, FullArticle)
