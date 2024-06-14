from __future__ import annotations
from abc import ABC, abstractmethod

from collections.abc import Callable, Generator, Sequence, Set
from dataclasses import dataclass
from datetime import datetime
import logging
from time import sleep
from typing import (
    Any,
    ClassVar,
    Generic,
    Literal,
    Type,
    TypeVar,
    cast,
    overload,
)
from typing_extensions import TypedDict

from elastic_transport import ObjectApiResponse
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from elasticsearch.client import TasksClient

from pydantic import ValidationError

from .objects import (
    BaseArticle,
    BaseCVE,
    BaseCluster,
    FullCVE,
    FullCluster,
    FullArticle,
    BaseDocument,
    FullDocument,
    PartialArticle,
    PartialCVE,
    PartialCluster,
    PartialDocument,
)

logger = logging.getLogger("osinter")


# TODO: Type this function properly
def create_es_conn(
    addresses: str | list[str], verify_certs: bool, cert_path: None | str = None
) -> Elasticsearch:
    if cert_path:
        return Elasticsearch(
            addresses, ca_certs=cert_path, verify_certs=verify_certs, timeout=30
        )
    else:
        return Elasticsearch(addresses, verify_certs=verify_certs, timeout=30)


def return_article_db_conn(
    es_conn: Elasticsearch,
    index_name: str,
    ingest_pipeline: str | None,
    elser_model_id: str | None,
) -> ElasticDB[BaseArticle, PartialArticle, FullArticle, ArticleSearchQuery]:
    return ElasticDB[BaseArticle, PartialArticle, FullArticle, ArticleSearchQuery](
        es_conn=es_conn,
        index_name=index_name,
        ingest_pipeline=ingest_pipeline,
        unique_field="url",
        elser_model_id=elser_model_id,
        document_object_classes={
            "base": BaseArticle,
            "full": FullArticle,
            "partial": PartialArticle,
            "search_query": ArticleSearchQuery,
        },
    )


def return_cluster_db_conn(
    es_conn: Elasticsearch,
    index_name: str,
    ingest_pipeline: str | None,
    elser_model_id: str | None,
) -> ElasticDB[BaseCluster, PartialCluster, FullCluster, ClusterSearchQuery]:
    return ElasticDB[BaseCluster, PartialCluster, FullCluster, ClusterSearchQuery](
        es_conn=es_conn,
        index_name=index_name,
        ingest_pipeline=ingest_pipeline,
        unique_field="nr",
        elser_model_id=elser_model_id,
        document_object_classes={
            "base": BaseCluster,
            "full": FullCluster,
            "partial": PartialCluster,
            "search_query": ClusterSearchQuery,
        },
    )


def return_cve_db_conn(
    es_conn: Elasticsearch,
    index_name: str,
    ingest_pipeline: str | None,
    elser_model_id: str | None,
) -> ElasticDB[BaseCVE, PartialCVE, FullCVE, CVESearchQuery]:
    return ElasticDB[BaseCVE, PartialCVE, FullCVE, CVESearchQuery](
        es_conn=es_conn,
        index_name=index_name,
        ingest_pipeline=ingest_pipeline,
        unique_field="cve",
        elser_model_id=elser_model_id,
        document_object_classes={
            "base": BaseCVE,
            "full": FullCVE,
            "partial": PartialCVE,
            "search_query": CVESearchQuery,
        },
    )


@dataclass
class SearchQuery(ABC):
    limit: int = 10_000

    sort_by: str | None = None
    sort_order: Literal["desc", "asc"] = "desc"

    search_term: str | None = None
    semantic_search: str | None = None

    date_field: str | None = None

    first_date: datetime | None = None
    last_date: datetime | None = None

    ids: Set[str] | None = None

    highlight: bool = False
    highlight_symbol: str = "**"

    custom_exclude_fields: list[str] | None = None

    search_fields: ClassVar[list[tuple[str, int]]] = []
    essential_fields: ClassVar[list[str]] = []
    exclude_fields: ClassVar[list[str]] = ["elastic_ml"]

    @abstractmethod
    def generate_es_query(
        self, elser_id: str | None, completeness: bool | list[str]
    ) -> dict[str, Any]:
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

        if self.search_term or (self.semantic_search and elser_id):
            query["sort"].insert(0, "_score")

        if self.semantic_search and elser_id:
            for field in self.search_fields:
                query["query"]["bool"]["should"].append(
                    {
                        "text_expansion": {
                            f"elastic_ml.{field[0]}_tokens": {
                                "model_text": self.semantic_search,
                                "model_id": elser_id,
                                "boost": field[1] * 3,
                            }
                        }
                    }
                )

        if self.search_term:
            query["query"]["bool"]["must"] = {
                "simple_query_string": {
                    "query": self.search_term,
                    "fields": [
                        f"{field[0]}^{field[1]}" for field in self.search_fields
                    ],
                }
            }

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

        return query


@dataclass
class ClusterSearchQuery(SearchQuery):
    search_fields = [("title", 5), ("description", 3), ("summary", 2)]
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
    semantic_search: None = None  # type: ignore[unused-ignore]
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

    search_fields = [("title", 5), ("description", 3)]
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
        "references",
    ]

    sort_by: Literal["document_count", "cve", "publish_date", "modified_date", ""] | None = "document_count"  # type: ignore[unused-ignore]

    min_doc_count: int | None = None
    cves: Set[str] | None = None
    semantic_search: None = None  # type: ignore[unused-ignore]

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

    search_fields = [("title", 5), ("description", 3), ("content", 1)]
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


SearchQueryType = TypeVar("SearchQueryType", bound=SearchQuery)
AnyDocument = TypeVar("AnyDocument")


class DocumentObjectClasses(
    TypedDict, Generic[BaseDocument, PartialDocument, FullDocument, SearchQueryType]
):
    base: Type[BaseDocument]
    full: Type[FullDocument]
    partial: Type[PartialDocument]
    search_query: Type[SearchQueryType]


class ElasticDB(Generic[BaseDocument, PartialDocument, FullDocument, SearchQueryType]):
    def __init__(
        self,
        *,
        es_conn: Elasticsearch,
        index_name: str,
        ingest_pipeline: str | None,
        elser_model_id: str | None,
        unique_field: str,
        document_object_classes: DocumentObjectClasses[
            BaseDocument, PartialDocument, FullDocument, SearchQueryType
        ],
    ):
        self.es: Elasticsearch = es_conn
        self.index_name: str = index_name
        self.ingest_pipeline = ingest_pipeline
        self.unique_field: str = unique_field

        self.elser_model_id = elser_model_id

        self.document_object_class: DocumentObjectClasses[
            BaseDocument, PartialDocument, FullDocument, SearchQueryType
        ] = document_object_classes

    # Checking if the document is already stored in the es db using the URL as that is probably not going to change and is uniqe
    def exists_in_db(self, token: str) -> bool:
        return (
            int(
                self.es.search(
                    index=self.index_name,
                    query={"term": {self.unique_field: {"value": token}}},
                )["hits"]["total"]["value"]
            )
            != 0
        )

    def _process_search_results(
        self,
        hits: list[dict[str, Any]],
        convert: Callable[[dict[str, Any]], AnyDocument],
    ) -> tuple[list[AnyDocument], list[dict[str, Any]]]:
        for result in hits:
            if "highlight" in result and len(result) > 0:
                result["_source"]["highlights"] = {}
                for field_type in result["highlight"].keys():
                    result["_source"]["highlights"][field_type] = result["highlight"][
                        field_type
                    ]

        valid_docs: list[AnyDocument] = []
        invalid_docs: list[dict[str, Any]] = []

        for hit in hits:
            try:
                valid_docs.append(convert({"id": hit["_id"], **hit["_source"]}))
            except ValidationError as e:
                logger.error(
                    f'Encountered problem with article with ID "{hit["_id"]}" and title "{hit["_source"]["title"]}", skipping for now. Error: {e}'
                )

                invalid_docs.append(hit)

        return valid_docs, invalid_docs

    def _query_large(
        self,
        query: dict[str, Any],
        *,
        batch_size: int = 10_000,
        pit_keep_alive: str = "1m",
    ) -> Generator[list[dict[str, Any]], None, None]:
        pit_id: str = self.es.open_point_in_time(
            index=self.index_name, keep_alive=pit_keep_alive
        )["id"]

        search_after: Any = None
        prior_limit: int = query["size"]

        while True:
            query["size"] = (
                batch_size
                if prior_limit >= batch_size or prior_limit == 0
                else prior_limit
            )

            search_results: ObjectApiResponse[Any] = self.es.search(
                **query,
                pit={"id": pit_id, "keep_alive": pit_keep_alive},
                search_after=search_after,
            )

            yield search_results["hits"]["hits"]

            if len(search_results["hits"]["hits"]) < batch_size:
                break

            search_after = search_results["hits"]["hits"][-1]["sort"]
            pit_id = search_results["pit_id"]

            if prior_limit > 0:
                prior_limit -= batch_size

    @overload
    def query_documents(
        self, search_q: SearchQueryType | None, completeness: Literal[False]
    ) -> tuple[list[BaseDocument], list[dict[str, Any]]]: ...

    @overload
    def query_documents(
        self, search_q: SearchQueryType | None, completeness: Literal[True]
    ) -> tuple[list[FullDocument], list[dict[str, Any]]]: ...

    @overload
    def query_documents(
        self, search_q: SearchQueryType | None, completeness: bool
    ) -> tuple[
        list[BaseDocument] | list[FullDocument],
        list[dict[str, Any]],
    ]: ...

    @overload
    def query_documents(
        self, search_q: SearchQueryType | None, completeness: list[str]
    ) -> tuple[list[PartialDocument], list[dict[str, Any]]]: ...

    @overload
    def query_documents(
        self, search_q: SearchQueryType | None, completeness: bool | list[str]
    ) -> tuple[
        list[BaseDocument] | list[PartialDocument] | list[FullDocument],
        list[dict[str, Any]],
    ]: ...

    def query_documents(
        self,
        search_q: SearchQueryType | None,
        completeness: bool | list[str],
    ) -> tuple[
        list[BaseDocument] | list[PartialDocument] | list[FullDocument],
        list[dict[str, Any]],
    ]:
        if not search_q:
            search_q = self.document_object_class["search_query"]()

        hits: list[dict[str, Any]] = []

        if search_q.limit <= 10_000 and search_q.limit != 0:
            hits = self.es.search(
                **search_q.generate_es_query(self.elser_model_id, completeness),
                index=self.index_name,
            )["hits"]["hits"]

        else:
            for hit_batch in self._query_large(
                search_q.generate_es_query(self.elser_model_id, completeness)
            ):
                hits.extend(hit_batch)

        if completeness is False:
            return self._process_search_results(
                hits,
                lambda data: self.document_object_class["base"].model_validate(data),
            )
        elif completeness is True:
            return self._process_search_results(
                hits,
                lambda data: self.document_object_class["full"].model_validate(data),
            )  # pyright: ignore
        elif isinstance(completeness, list):
            return self._process_search_results(
                hits,
                lambda data: self.document_object_class["partial"].model_validate(
                    data, context={"fields_to_validate": completeness}
                ),  # pyright: ignore
            )
        else:
            raise NotImplemented

    def scroll_documents(
        self,
        search_q: SearchQueryType | None,
        pit_keep_alive: str = "3m",
        batch_size: int = 10_000,
    ) -> Generator[list[FullDocument], None, None]:
        if not search_q:
            search_q = self.document_object_class["search_query"](limit=0)

        for hits in self._query_large(
            search_q.generate_es_query(self.elser_model_id, True),
            pit_keep_alive=pit_keep_alive,
            batch_size=batch_size,
        ):
            yield self._process_search_results(
                hits,
                lambda data: self.document_object_class["full"].model_validate(data),
            )[0]

    def query_all_documents(self) -> list[FullDocument]:
        return self.query_documents(
            self.document_object_class["search_query"](limit=0), True
        )[0]

    def filter_document_list(self, document_attribute_list: Sequence[str]) -> list[str]:
        filtered_document_list = []
        for attr in document_attribute_list:
            if not self.exists_in_db(attr):
                filtered_document_list.append(attr)

        return filtered_document_list

    # If there's more than 10.000 unique values, then this function will only get the first 10.000
    def get_unique_values(self, field_name: str) -> dict[str, int]:
        unique_vals = self.es.search(
            size=0,
            aggs={"unique_fields": {"terms": {"field": field_name, "size": 10_000}}},
        )["aggregations"]["unique_fields"]["buckets"]

        return {
            unique_val["key"]: unique_val["doc_count"] for unique_val in unique_vals
        }

    def update_documents(
        self,
        documents: Sequence[BaseDocument | FullDocument],
        fields: list[str] | None = None,
        use_pipeline: bool = False,
    ) -> int:
        def convert_documents(
            documents: Sequence[BaseDocument | FullDocument],
        ) -> Generator[dict[str, Any], None, None]:
            for document in documents:
                operation: dict[str, Any] = {
                    "_op_type": "update",
                    "_index": self.index_name,
                    "doc": document.model_dump(
                        exclude={"highlights"}, exclude_none=True, mode="json"
                    ),
                }

                operation["_id"] = operation["doc"].pop("id")

                if fields:
                    operation["doc"] = {
                        field: operation["doc"][field] for field in fields
                    }

                if self.ingest_pipeline and use_pipeline:
                    operation["pipeline"] = self.ingest_pipeline

                yield operation

        return bulk(self.es, convert_documents(documents))[0]

    def save_documents(
        self,
        document_objects: Sequence[BaseDocument | FullDocument],
        bypass_pipeline: bool = False,
        chunk_size: int = 50,
    ) -> int:
        def convert_documents(
            documents: Sequence[BaseDocument | FullDocument],
        ) -> Generator[dict[str, Any], None, None]:
            for document in documents:
                operation: dict[str, Any] = {
                    "_index": self.index_name,
                    "_source": document.model_dump(
                        exclude={"highlights"}, exclude_none=True, mode="json"
                    ),
                }

                if self.ingest_pipeline and not bypass_pipeline:
                    operation["pipeline"] = self.ingest_pipeline

                operation["_id"] = operation["_source"].pop("id")

                yield operation

        return bulk(
            self.es, convert_documents(document_objects), chunk_size=chunk_size
        )[0]

    def save_document(self, document_object: BaseDocument | FullDocument) -> str:
        document_dict: dict[str, Any] = document_object.model_dump(
            exclude={"highlights"}, exclude_none=True, mode="json"
        )

        document_id = document_dict.pop("id")
        response = self.es.index(
            index=self.index_name,
            pipeline=self.ingest_pipeline,
            document=document_dict,
            id=document_id,
        )["_id"]

        return cast(str, response)

    def delete_document(self, ids: Set[str]) -> int:
        def gen_actions(ids: Set[str]) -> Generator[dict[str, Any], None, None]:
            for id in ids:
                yield {
                    "_op_type": "delete",
                    "_index": self.index_name,
                    "_id": id,
                }

        return bulk(self.es, gen_actions(ids))[0]

    def increment_read_counter(self, document_id: str) -> None:
        increment_script = {"source": "ctx._source.read_times += 1", "lang": "painless"}
        self.es.update(index=self.index_name, id=document_id, script=increment_script)

    def await_task(
        self,
        task_id: str,
        status_field: str,
        status_message_formatter: Callable[[dict[str, Any]], str],
    ) -> None:
        logger.info(f'Awaiting task "{task_id}"')
        last_status: Any = None

        task_client = TasksClient(self.es)

        try:
            while True:
                sleep(2)

                r = task_client.get(task_id=task_id)

                if r["task"]["status"][status_field] == last_status:
                    continue

                last_status = r["task"]["status"][status_field]

                logger.info(status_message_formatter(r["task"]["status"]))

                if r["completed"]:
                    break
        except KeyboardInterrupt:
            answer = ""

            while True:
                answer = input(
                    f'Terminating waiting on task "{task_id}", do you also want to cancel the task itself? (y/n): '
                ).lower()

                if answer == "y" or answer == "n":
                    break

            if answer == "y":
                logger.info("Cancelling task")
                task_client.cancel(task_id=task_id)

        r = task_client.get(task_id=task_id)
        run_time = r["task"]["running_time_in_nanos"] / 1_000_000_000

        logger.info(
            " ".join(
                [
                    f"Task is {'cancelled' if r['task']['cancelled'] else 'completed' if r['completed'] else 'still running'}.",
                    f"It has run for {run_time} seconds",
                ]
            )
        )


ES_INDEX_CONFIGS: dict[str, dict[str, dict[str, Any]]] = {
    "ELASTICSEARCH_ARTICLE_INDEX": {
        "properties": {
            "title": {"type": "text"},
            "description": {"type": "text"},
            "content": {"type": "text"},
            "formatted_content": {"type": "text"},
            "url": {"type": "keyword"},
            "profile": {"type": "keyword"},
            "source": {"type": "keyword"},
            "image_url": {"type": "keyword"},
            "author": {"type": "keyword"},
            "inserted_at": {"type": "date"},
            "publish_date": {"type": "date"},
            "read_times": {"type": "unsigned_long"},
            "tags": {
                "type": "object",
                "properties": {
                    "interesting": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "keyword"},
                            "values": {"type": "keyword"},
                        },
                    },
                    "automatic": {"type": "keyword"},
                },
            },
            "similar": {"type": "keyword"},
            "ml": {
                "type": "object",
                "properties": {
                    "cluster": {"type": "keyword"},
                    "coordinates": {"type": "float"},
                    "labels": {"type": "keyword"},
                    "incident": {"type": "integer"}
                },
            },
        },
    },
    "ELASTICSEARCH_CLUSTER_INDEX": {
        "properties": {
            "nr": {"type": "integer"},
            "document_count": {"type": "integer"},
            "title": {"type": "text"},
            "description": {"type": "text"},
            "summary": {"type": "text"},
            "keywords": {"type": "keyword"},
            "documents": {"type": "keyword"},
            "dating": {"type": "date"},
        },
    },
    "ELASTICSEARCH_CVE_INDEX": {
        "properties": {
            "cve": {"type": "keyword"},
            "document_count": {"type": "integer"},
            "title": {"type": "text"},
            "description": {"type": "text"},
            "publish_date": {"type": "date"},
            "modified_date": {"type": "date"},
            "weaknesses": {"type": "keyword"},
            "status": {"type": "keyword"},
            "cvss2": {
                "type": "object",
                "properties": {
                    "source": {"type": "keyword"},
                    "base_severity": {"type": "keyword"},
                    "exploitability_score": {"type": "half_float"},
                    "impact_score": {"type": "half_float"},
                    "ac_insuf_info": {"type": "boolean"},
                    "obtain_all_privilege": {"type": "boolean"},
                    "obtain_user_privilege": {"type": "boolean"},
                    "obtain_other_privilege": {"type": "boolean"},
                    "user_interaction_required": {"type": "boolean"},
                    "cvss_data": {
                        "type": "object",
                        "properties": {
                            "version": {"type": "keyword"},
                            "vector_string": {"type": "keyword"},
                            "access_vector": {"type": "keyword"},
                            "access_complexity": {"type": "keyword"},
                            "authentication": {"type": "keyword"},
                            "confidentiality_impact": {"type": "keyword"},
                            "integrity_impact": {"type": "keyword"},
                            "availability_impact": {"type": "keyword"},
                            "base_score": {"type": "half_float"},
                        },
                    },
                },
            },
            "cvss3": {
                "type": "object",
                "properties": {
                    "source": {"type": "keyword"},
                    "exploitability_score": {"type": "half_float"},
                    "impact_score": {"type": "half_float"},
                    "cvss_data": {
                        "type": "object",
                        "properties": {
                            "version": {"type": "keyword"},
                            "vector_string": {"type": "keyword"},
                            "attack_vector": {"type": "keyword"},
                            "attack_complexity": {"type": "keyword"},
                            "privileges_required": {"type": "keyword"},
                            "user_interaction": {"type": "keyword"},
                            "scope": {"type": "keyword"},
                            "confidentiality_impact": {"type": "keyword"},
                            "integrity_impact": {"type": "keyword"},
                            "availability_impact": {"type": "keyword"},
                            "base_score": {"type": "half_float"},
                            "base_severity": {"type": "keyword"},
                        },
                    },
                },
            },
            "references": {
                "type": "object",
                "properties": {
                    "url": {"type": "keyword"},
                    "source": {"type": "keyword"},
                    "tags": {"type": "keyword"},
                },
            },
            "keywords": {"type": "keyword"},
            "documents": {"type": "keyword"},
            "dating": {"type": "date"},
        },
    },
}


class SearchTemplate(TypedDict):
    script: dict[Literal["source"], str]
    dictionary: dict[
        Literal["properties"], dict[str, bool | dict[str, dict[str, str] | str]]
    ]


ES_SEARCH_APPLICATIONS: dict[
    Literal["ARTICLES"], dict[Literal["template"], SearchTemplate]
] = {
    "ARTICLES": {
        "template": {
            "script": {
                "source": """{
    "query": {
        "bool": {
            "should": [
                {{#semantic_search}}
                    {
                        "text_expansion": {
                        "elastic_ml.title_tokens": {
                            "model_text": "{{semantic_search}}",
                            "model_id": "{{elser_model}}{{^elser_model}}.elser_model_2{{/elser_model}}",
                            "boost": 15
                        }
                        }
                    },
                    {
                        "text_expansion": {
                        "elastic_ml.description_tokens": {
                            "model_text": "{{semantic_search}}",
                            "model_id": "{{elser_model}}{{^elser_model}}.elser_model_2{{/elser_model}}",
                            "boost": 9
                        }
                        }
                    },
                    {
                        "text_expansion": {
                        "elastic_ml.content_tokens": {
                            "model_text": "{{semantic_search}}",
                            "model_id": "{{elser_model}}{{^elser_model}}.elser_model_2{{/elser_model}}",
                            "boost": 15
                        }
                        }
                    }
                {{/semantic_search}}
            ],
            "must": [
                {{#search_term}}
                    {
                        "simple_query_string": {
                            "query": "{{search_term}}",
                            "fields": [
                                "title^5",
                                "description^3",
                                "content^1"
                            ]
                        }
                    }
                {{/search_term}}
            ],
            "filter": [
                {{#filters}}
                    {{#toJson}}.{{/toJson}},
                {{/filters}}
                {{#ids.0}}
                    {
                        "terms": {
                            "_id": {{#toJson}}ids{{/toJson}}
                        }
                    },
                {{/ids.0}}

                {{#sources.0}}
                    {
                        "terms": {
                            "profile": {{#toJson}}sources{{/toJson}}
                        }
                    },
                {{/sources.0}}

                {{#cluster_id}}
                    {
                        "term": {
                            "ml.cluster": "{{cluster_id}}"
                        }
                    },
                {{/cluster_id}}

                {
                    "range": {
                        "publish_date": {
                            {{#first_date}}
                                "gte": "{{first_date}}"
                            {{/first_date}}

                            {{#first_date}}
                                {{#last_date}}
                                    ,
                                {{/last_date}}
                            {{/first_date}}

                            {{#last_date}}
                                "lte": "{{last_date}}"
                            {{/last_date}}
                        }
                    }
                }
            ]
        }
    },
    {{#highlight}}
        "highlight": {
            "pre_tags": ["{{highlight_symbol}}{{^highlight_symbol}}**{{/highlight_symbol}}"],
            "post_tags": ["{{highlight_symbol}}{{^highlight_symbol}}**{{/highlight_symbol}}"],
            "fields": {
                "title": {},
                "description": {},
                "content": {}
            }
        },
    {{/highlight}}

    "_source": {
        {{#include_fields.0}}
            "includes": {{#toJson}}include_fields{{/toJson}},
        {{/include_fields.0}}

        {{#exclude_fields.0}}
            "excludes": [{{#exclude_fields}}"{{.}}", {{/exclude_fields}} "elastic_ml"]
        {{/exclude_fields.0}}

        {{^exclude_fields}}
            "excludes": ["elastic_ml"]
        {{/exclude_fields}}
    },

    {{#sort.0}}
        "sort": {{#toJson}}sort{{/toJson}},
    {{/sort.0}}
    {{^sort.0}}
        "sort": [
            {{#sort_by}}
                {"{{sort_by}}": "{{sort_order}}{{^sort_order}}desc{{/sort_order}}"},
            {{/sort_by}}

            {{#semantic_search}}
                {"_score": "desc"},
            {{/semantic_search}}
            {{^semantic_search}}
                {{#search_term}}
                    {"_score": "desc"},
                {{/search_term}}
            {{/semantic_search}}

            {{#sort_tiebreaker}}
                "url",
            {{/sort_tiebreaker}}
            "_doc"
        ],
    {{/sort.0}}

    {{#search_after.0}}
        "search_after": {{#toJson}}search_after{{/toJson}},
    {{/search_after.0}}

    {{#aggregations}}
        "aggregations": {{#toJson}}aggregations{{/toJson}},
    {{/aggregations}}

    "from": "{{from}}{{^from}}0{{/from}}",
    "size": "{{limit}}{{^limit}}10{{/limit}}",
    "track_total_hits": "{{track_total}}{{^track_total}}false{{/track_total}}"
}"""
            },
            "dictionary": {
                "properties": {
                    "highlight_symbol": {"type": "string"},
                    "elser_model": {"type": "string"},
                    "semantic_search": {"type": "string"},
                    "search_term": {"type": "string"},
                    "cluster_id": {"type": "string"},
                    "first_date": {"type": "string"},
                    "last_date": {"type": "string"},
                    "sort_by": {"type": "string"},
                    "sort_order": {"type": "string"},
                    "ids": {"type": "array", "items": {"type": "string"}},
                    "sources": {"type": "array", "items": {"type": "string"}},
                    "include_fields": {"type": "array", "items": {"type": "string"}},
                    "exclude_fields": {"type": "array", "items": {"type": "string"}},
                    "filters": {"type": "array", "items": {"type": "object"}},
                    "sort": {"type": "array", "items": {"type": "object"}},
                    "search_after": {"type": "array"},
                    "from": {"type": "integer"},
                    "limit": {"type": "integer"},
                    "highlight": {"type": "boolean"},
                    "track_total": {"type": "boolean"},
                    "sort_tiebreaker": {"type": "boolean"},
                    "additionalProperties": False,
                }
            },
        }
    }
}
