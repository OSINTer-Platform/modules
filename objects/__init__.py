from typing_extensions import TypeVar

from .articles import (
    BaseArticle,
    PartialArticle,
    FullArticle,
    MLAttributes,
    MLClassification,
    TagsOfInterest,
    Tags,
    ArticleHighlights,
)
from .clusters import BaseCluster, PartialCluster, FullCluster, ClusterHighlights

from .generic import AbstractDocument, AbstractPartialDocument

BaseDocument = TypeVar("BaseDocument", bound=AbstractDocument)
FullDocument = TypeVar("FullDocument", bound=AbstractDocument)
PartialDocument = TypeVar("PartialDocument", bound=AbstractPartialDocument)

__all__ = [
    "BaseDocument",
    "FullDocument",
    "PartialDocument",
    "AbstractDocument",
    "AbstractPartialDocument",
    "BaseArticle",
    "PartialArticle",
    "FullArticle",
    "MLAttributes",
    "MLClassification",
    "TagsOfInterest",
    "Tags",
    "ArticleHighlights",
    "BaseCluster",
    "PartialCluster",
    "FullCluster",
    "ClusterHighlights",
]
