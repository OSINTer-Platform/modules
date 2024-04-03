from datetime import datetime, timezone
from typing_extensions import Annotated, TypeVar

from pydantic import (
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    Field,
    HttpUrl,
    ValidationInfo,
    model_validator,
)
import annotated_types
from pydantic_core import PydanticCustomError

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


class AbstractDocument(BaseModel):
    id: str


class AbstractPartialDocument(BaseModel):
    @model_validator(mode="after")
    def check_required_values(self, info: ValidationInfo) -> "AbstractPartialDocument":
        context = info.context

        if not context:
            raise PydanticCustomError(
                "missing_validation_context",
                "No context was provided for validating partial document",
            )

        try:
            fields_to_validate: None | list["str"] = context.get(
                "fields_to_validate", None
            )
        except AttributeError:
            raise PydanticCustomError(
                "invalid_field_to_validate",
                "The value passed to the field-to-validate context variable should be a dictionary",
            )

        if not fields_to_validate or len(fields_to_validate) < 1:
            raise PydanticCustomError(
                "missing_fields_to_validate",
                "No list of fields to validate was provided",
            )

        for field_name in fields_to_validate:
            if getattr(self, field_name, None) is None:
                raise ValueError(f"Missing value for {field_name}")

        return self


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
    title: Annotated[
        str, BeforeValidator(lambda x: str.strip((x))), annotated_types.MinLen(3)
    ] | None = None
    description: Annotated[
        str, BeforeValidator(lambda x: str.strip((x))), annotated_types.MinLen(10)
    ] | None = None
    url: HttpUrl | None = None
    image_url: HttpUrl | None = None
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


class ClusterHighlights(BaseModel):
    title: list[str] | None = None
    description: list[str] | None = None
    summary: list[str] | None = None


class BaseCluster(AbstractDocument):
    nr: int
    document_count: int

    title: str
    description: str
    summary: str

    keywords: list[str]
    highlights: ClusterHighlights | None = None


class FullCluster(BaseCluster):
    documents: set[str]
    dating: set[Annotated[datetime, AwareDatetime]]


class PartialCluster(AbstractDocument, AbstractPartialDocument):
    nr: int | None = None
    document_count: int | None = None

    title: str | None = None
    description: str | None = None
    summary: str | None = None

    keywords: list[str] | None = None

    documents: set[str] | None = None
    dating: set[Annotated[datetime, AwareDatetime]] | None = None


BaseDocument = TypeVar("BaseDocument", bound=AbstractDocument)
FullDocument = TypeVar("FullDocument", bound=AbstractDocument)
PartialDocument = TypeVar("PartialDocument", bound=AbstractPartialDocument)
