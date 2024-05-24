from datetime import datetime, timezone
from typing import Literal
from typing_extensions import Annotated

from pydantic import (
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    Field,
    HttpUrl,
)
import annotated_types

from .generic import AbstractDocument, AbstractPartialDocument


class MLClassification(BaseModel):
    incident: bool = False


class MLAttributes(BaseModel):
    cluster: str = ""
    coordinates: tuple[float, float] = (0, 0)
    labels: list[str] = []
    incident: int = 0
    classification: MLClassification = MLClassification()


class TagsOfInterest(BaseModel):
    name: str
    values: list[str]


class Tags(BaseModel):
    automatic: list[str]
    interesting: list[TagsOfInterest]


class ArticleHighlights(BaseModel):
    title: list[str] | None = None
    description: list[str] | None = None
    content: list[str] | None = None


class BaseArticle(AbstractDocument):
    title: Annotated[
        str, BeforeValidator(lambda x: str.strip((x))), annotated_types.MinLen(3)
    ]
    description: Annotated[
        str, BeforeValidator(lambda x: str.strip((x))), annotated_types.MinLen(10)
    ]
    url: Annotated[str, HttpUrl]
    image_url: Annotated[str, HttpUrl] | Literal[""]
    profile: str
    source: str
    author: str | None = None
    publish_date: Annotated[datetime, AwareDatetime]
    inserted_at: Annotated[datetime, AwareDatetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    read_times: int = 0
    similar: list[str] = []
    ml: MLAttributes = MLAttributes(
        cluster="", coordinates=(0.0, 0.0), labels=[], incident=0
    )
    tags: Tags = Tags(automatic=[], interesting=[])
    summary: str | None = None
    highlights: ArticleHighlights | None = None


class FullArticle(BaseArticle):
    formatted_content: Annotated[str, annotated_types.MinLen(10)]
    content: Annotated[str, annotated_types.MinLen(10)]


class PartialArticle(AbstractDocument, AbstractPartialDocument):
    title: (
        Annotated[
            str, BeforeValidator(lambda x: str.strip((x))), annotated_types.MinLen(3)
        ]
        | None
    ) = None
    description: (
        Annotated[
            str, BeforeValidator(lambda x: str.strip((x))), annotated_types.MinLen(10)
        ]
        | None
    ) = None
    url: Annotated[str, HttpUrl] | None = None
    image_url: Annotated[str, HttpUrl] | Literal[""] | None = None
    profile: str | None = None
    source: str | None = None
    author: str | None = None
    publish_date: Annotated[datetime, AwareDatetime] | None = None
    inserted_at: Annotated[datetime, AwareDatetime] | None = None
    read_times: int | None = None
    similar: list[str] | None = None
    ml: MLAttributes | None = None
    tags: Tags | None = None

    formatted_content: Annotated[str, annotated_types.MinLen(10)] | None = None
    content: Annotated[str, annotated_types.MinLen(10)] | None = None
    summary: str | None = None
