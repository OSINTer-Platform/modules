from datetime import datetime, timezone
from typing_extensions import Annotated, TypedDict, TypeVar

from pydantic import AwareDatetime, BaseModel, BeforeValidator, Field, HttpUrl
import annotated_types


class MLAttributes(TypedDict, total=False):
    similar: list[str]
    cluster: int


class TagsOfInterest(TypedDict):
    results: list[str]
    tag: bool


class Tags(TypedDict, total=False):
    automatic: list[str]
    interresting: dict[str, TagsOfInterest]


class AbstractDocument(BaseModel):
    id: str | None = None


class BaseArticle(AbstractDocument):
    title: Annotated[
        str, BeforeValidator(lambda x: str.strip((x))), annotated_types.MinLen(3)
    ]
    description: Annotated[
        str, BeforeValidator(lambda x: str.strip((x))), annotated_types.MinLen(10)
    ]
    url: HttpUrl
    image_url: HttpUrl
    profile: str
    source: str
    publish_date: Annotated[datetime, AwareDatetime]
    inserted_at: Annotated[datetime, AwareDatetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    read_times: int = 0


class FullArticle(BaseArticle):
    author: str | None = None
    formatted_content: str
    content: str
    summary: str | None = None
    tags: Tags = {}
    ml: MLAttributes | None = None


BaseDocument = TypeVar("BaseDocument", bound=AbstractDocument)
FullDocument = TypeVar("FullDocument", bound=AbstractDocument)
