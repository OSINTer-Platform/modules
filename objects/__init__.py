from typing_extensions import TypeVar

from .articles import (
    AbstractArticle,
    BaseArticle,
    PartialArticle,
    FullArticle,
    MLAttributes,
    MLClassification,
    TagsOfInterest,
    Tags,
    ArticleHighlights,
)
from .clusters import (
    AbstractCluster,
    BaseCluster,
    PartialCluster,
    FullCluster,
    ClusterHighlights,
)
from .cves import (
    AbstractCVE,
    BaseCVE,
    PartialCVE,
    FullCVE,
    CVEReference,
    CVEHighlights,
    CVSS2Data,
    CVSS3Data,
    CVSS2,
    CVSS3,
)

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
    "AbstractArticle",
    "AbstractCluster",
    "AbstractCVE",
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
    "BaseCVE",
    "PartialCVE",
    "FullCVE",
    "CVEHighlights",
    "CVEReference",
    "CVSS2Data",
    "CVSS3Data",
    "CVSS2",
    "CVSS3",
]
