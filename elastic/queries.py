from abc import ABC, abstractmethod

from collections.abc import Set
from dataclasses import dataclass
from datetime import datetime
from typing import (
    Any,
    ClassVar,
    Literal,
    TypedDict,
)

class SemanticSearchField(TypedDict):
    field: str
    nested_path: str | None
    boost: int

@dataclass
class SearchQuery(ABC):
    limit: int = 10_000

    sort_by: str | None = None
    sort_order: Literal["desc", "asc"] = "desc"

    search_term: str | None = None

    date_field: str | None = None

    first_date: datetime | None = None
    last_date: datetime | None = None

    ids: Set[str] | None = None

    highlight: bool = False
    highlight_symbol: str = "**"

    custom_exclude_fields: list[str] | None = None
    aggregations: dict[str, Any] | None = None

    search_fields: ClassVar[list[tuple[str, int]]] = []
    essential_fields: ClassVar[list[str]] = []
    exclude_fields: ClassVar[list[str]] = []
    semantic_fields: ClassVar[list[SemanticSearchField]] = []

    @abstractmethod
    def generate_es_query(
        self, elser_id: str | None, completeness: bool | list[str]
    ) -> dict[str, Any]:
        if self.aggregations and (self.limit < 1 or self.limit > 10000):
            raise Exception("Aggregations are not allowed with large searches")

        query: dict[str, Any] = {
            "size": self.limit,
            "sort": ["_doc"],
            "query": {"bool": {"filter": [], "should": [], "must_not": []}},
        }

        if self.custom_exclude_fields:
            query["source_excludes"] = self.exclude_fields + self.custom_exclude_fields
        else:
            query["source_excludes"] = self.exclude_fields

        if self.highlight:
            query["highlight"] = {
                "pre_tags": [self.highlight_symbol],
                "post_tags": [self.highlight_symbol],
                "fields": {field_type[0]: {} for field_type in self.search_fields},
            }

        if completeness is False:
            query["source_includes"] = self.essential_fields
        elif isinstance(completeness, list):
            query["source_includes"] = completeness

        if self.search_term:
            query["sort"].insert(0, "_score")

            if self.search_fields:
                query["query"]["bool"]["should"].append({
                    "multi_match": {
                        "query": self.search_term,
                        "fields": [
                            f"{field[0]}^{field[1]}" for field in self.search_fields
                        ],
                    }
                })

            if self.semantic_fields and elser_id:
                for field in self.semantic_fields:
                    semantic_query = {
                        "text_expansion": {
                            field["field"]: {
                                "model_id": elser_id,
                                "model_text": self.search_term,
                                "boost": field["boost"],
                            }
                        }
                    }

                    if field["nested_path"]:
                        semantic_query = {
                            "nested": {
                                "path": field["nested_path"],
                                "query": semantic_query,
                            }
                        }

                    query["query"]["bool"]["should"].append(semantic_query)

        if self.sort_by:
            query["sort"].insert(0, {self.sort_by: self.sort_order})

        if self.ids:
            query["query"]["bool"]["filter"].append({"terms": {"_id": list(self.ids)}})

        # This check forces elasticsearch to return no results, in case the ids param is set, but empty, as this would indicate the user was querying an empty set of articles and thus expecting no articles in return
        elif isinstance(self.ids, Set) and len(self.ids) == 0:
            query["query"]["bool"]["filter"].append(
                {"terms": {"_id": ["THIS_ID_DOES_NOT_EXIST"]}}
            )

        if self.date_field:
            if self.first_date or self.last_date:
                query["query"]["bool"]["filter"].append(
                    {"range": {self.date_field: {}}}
                )

            if self.first_date:
                query["query"]["bool"]["filter"][-1]["range"][self.date_field][
                    "gte"
                ] = self.first_date.isoformat()

            if self.last_date:
                query["query"]["bool"]["filter"][-1]["range"][self.date_field][
                    "lte"
                ] = self.last_date.isoformat()

        if self.aggregations:
            query["aggs"] = self.aggregations

        return query


@dataclass
class ClusterSearchQuery(SearchQuery):
    search_fields = [("title", 1), ("description", 1), ("summary", 1)]
    essential_fields = [
        "nr",
        "document_count",
        "title",
        "description",
        "summary",
        "keywords",
    ]

    sort_by: Literal["document_count", "nr", ""] | None = "document_count"  # type: ignore[unused-ignore]

    cluster_nr: int | None = None
    date_field: None = None  # type: ignore[unused-ignore]

    exclude_outliers: bool = True

    def generate_es_query(
        self, elser_id: str | None, completeness: bool | list[str] = False
    ) -> dict[str, Any]:
        query = super(ClusterSearchQuery, self).generate_es_query(None, completeness)

        if self.cluster_nr:
            query["query"]["bool"]["filter"].append(
                {"term": {"nr": {"value": self.cluster_nr}}}
            )

        if self.exclude_outliers:
            query["query"]["bool"]["must_not"] = {"term": {"nr": {"value": -1}}}

        return query


@dataclass
class CVESearchQuery(SearchQuery):
    date_field: Literal["publish_date", "modified_date"] = "publish_date"  # type: ignore[unused-ignore]

    search_fields = [("title", 1), ("description", 1)]
    essential_fields = [
        "cve",
        "document_count",
        "title",
        "description",
        "keywords",
        "publish_date",
        "modified_date",
        "weaknesses",
        "status",
        "cvss2",
        "cvss3",
    ]

    sort_by: Literal["document_count", "cve", "publish_date", "modified_date", ""] | None = "document_count"  # type: ignore[unused-ignore]

    min_doc_count: int | None = None
    cves: Set[str] | None = None

    def generate_es_query(
        self, elser_id: str | None, completeness: bool | list[str] = False
    ) -> dict[str, Any]:
        query = super(CVESearchQuery, self).generate_es_query(None, completeness)

        if self.cves:
            query["query"]["bool"]["filter"].append({"terms": {"cve": list(self.cves)}})

        if self.min_doc_count:
            query["query"]["bool"]["filter"].append(
                {"range": {"document_count": {"gte": self.min_doc_count}}}
            )

        return query


@dataclass
class ArticleSearchQuery(SearchQuery):
    date_field: Literal["publish_date", "inserted_at"] = "publish_date"  # type: ignore[unused-ignore]

    sources: Set[str] | None = None
    exclude_sources: Set[str] | None = None
    cluster_id: str | None = None
    cve: str | None = None

    search_fields = [("title", 1), ("description", 1), ("content", 1)]
    essential_fields = [
        "title",
        "description",
        "url",
        "profile",
        "source",
        "image_url",
        "author",
        "publish_date",
        "inserted_at",
        "tags",
        "similar",
        "summary",
        "ml",
        "read_times",
    ]
    semantic_fields = [
        {
            "field": "embeddings.content_chunks.elser.tokens",
            "nested_path": "embeddings.content_chunks",
            "boost": 1,
        },
        {
            "field": "embeddings.description.elser.tokens",
            "nested_path": None,
            "boost": 1,
        },
        {"field": "embeddings.title.elser.tokens", "nested_path": None, "boost": 1},
    ]
    exclude_fields: ClassVar[list[str]] = ["embeddings"]

    def generate_es_query(
        self, elser_id: str | None, completeness: bool | list[str] = False
    ) -> dict[str, Any]:
        query = super(ArticleSearchQuery, self).generate_es_query(
            elser_id, completeness
        )

        if self.sources:
            query["query"]["bool"]["filter"].append(
                {"terms": {"profile": [source.lower() for source in self.sources]}}
            )

        if self.exclude_sources:
            query["query"]["bool"]["must_not"].append(
                {
                    "terms": {
                        "profile": [source.lower() for source in self.exclude_sources]
                    }
                }
            )

        if self.cluster_id is not None:
            query["query"]["bool"]["filter"].append(
                {"term": {"ml.cluster": {"value": self.cluster_id}}}
            )

        if self.cve is not None:
            query["query"]["bool"]["filter"].append(
                {"term": {"tags.interesting.values": {"value": self.cve}}}
            )

        return query
