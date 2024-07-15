from datetime import datetime
from typing_extensions import Annotated

from pydantic import (
    AwareDatetime,
    BaseModel,
)

from .generic import AbstractDocument, AbstractPartialDocument


class ClusterHighlights(BaseModel):
    title: list[str] | None = None
    description: list[str] | None = None
    summary: list[str] | None = None


class AbstractCluster(AbstractDocument):
    highlights: ClusterHighlights | None = None


class BaseCluster(AbstractCluster):
    nr: int
    document_count: int

    title: str
    description: str
    summary: str

    keywords: list[str]


class FullCluster(BaseCluster):
    documents: set[str]
    dating: set[Annotated[datetime, AwareDatetime]]


class PartialCluster(AbstractCluster, AbstractPartialDocument):
    nr: int | None = None
    document_count: int | None = None

    title: str | None = None
    description: str | None = None
    summary: str | None = None

    keywords: list[str] | None = None

    documents: set[str] | None = None
    dating: set[Annotated[datetime, AwareDatetime]] | None = None
