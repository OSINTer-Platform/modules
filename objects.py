from datetime import datetime, timezone
from typing_extensions import Annotated, TypedDict, TypeVar

from pydantic import AwareDatetime, BaseModel, BeforeValidator, Field, HttpUrl
import annotated_types


class MLAttributes(TypedDict, total=False):
    similar: list[str]
    cluster: int
    coordinates: tuple[float, float]


class Tags(TypedDict):
    automatic: list[str]
    interresting: dict[str, list[str]]


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

class MLArticle(BaseArticle):
    ml: MLAttributes = {"similar": [], "cluster": -1, "coordinates": (0., 0.)}


class FullArticle(MLArticle):
    author: str | None = None
    formatted_content: Annotated[str, annotated_types.MinLen(10)]
    content: Annotated[str, annotated_types.MinLen(10)]
    summary: str | None = None
    tags: Tags = {"automatic": [], "interresting": {}}


BaseDocument = TypeVar("BaseDocument", bound=AbstractDocument)
FullDocument = TypeVar("FullDocument", bound=AbstractDocument)
