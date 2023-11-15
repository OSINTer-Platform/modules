from datetime import datetime, timezone
from typing_extensions import Annotated, TypedDict, TypeVar

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


class MLAttributes(TypedDict):
    cluster: int
    coordinates: tuple[float, float]


class TagsOfInterrest(TypedDict):
    name: str
    values: list[str]


class Tags(TypedDict):
    automatic: list[str]
    interresting: list[TagsOfInterrest]


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
    ml: MLAttributes = {"cluster": -1, "coordinates": (0.0, 0.0)}
    tags: Tags = {"automatic": [], "interresting": []}
    summary: str | None = None


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


class BaseCluster(AbstractDocument):
    nr: int
    document_count: int

    title: str
    description: str
    summary: str

    keywords: list[str]


class FullCluster(BaseCluster):
    representative_documents: list[str]
    documents: set[str]
    dating: set[Annotated[datetime, AwareDatetime]]


class PartialCluster(AbstractDocument, AbstractPartialDocument):
    nr: int | None = None
    document_count: int | None = None

    title: str | None = None
    description: str | None = None
    summary: str | None = None

    keywords: list[str] | None = None

    representative_documents: list[str] | None = None
    documents: set[str] | None = None
    dating: set[Annotated[datetime, AwareDatetime]] | None = None


BaseDocument = TypeVar("BaseDocument", bound=AbstractDocument)
FullDocument = TypeVar("FullDocument", bound=AbstractDocument)
PartialDocument = TypeVar("PartialDocument", bound=AbstractPartialDocument)
