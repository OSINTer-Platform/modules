from __future__ import annotations
from abc import ABC, abstractmethod

from collections.abc import Callable, Generator, Sequence, Set
from dataclasses import dataclass
from datetime import datetime
import logging
from time import sleep
from typing import Any, ClassVar, Generic, Literal, Type, TypeVar, cast, overload
from typing_extensions import TypedDict

from elastic_transport import ObjectApiResponse
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from elasticsearch.client import TasksClient

from pydantic import ValidationError

from .objects import BaseArticle, FullArticle, BaseDocument, FullDocument

logger = logging.getLogger("osinter")


# TODO: Type this function properly
def create_es_conn(
    addresses: str | list[str], cert_path: None | str = None
) -> Elasticsearch:
    if cert_path:
        return Elasticsearch(addresses, ca_certs=cert_path)  # type: ignore
    else:
        return Elasticsearch(addresses, verify_certs=False)  # type: ignore


def return_article_db_conn(
    es_conn: Elasticsearch,
    index_name: str,
    ingest_pipeline: str | None,
    elser_model_id: str | None,
) -> ElasticDB[BaseArticle, FullArticle, ArticleSearchQuery]:
    return ElasticDB[BaseArticle, FullArticle, ArticleSearchQuery](
        es_conn=es_conn,
        index_name=index_name,
        ingest_pipeline=ingest_pipeline,
        unique_field="url",
        elser_model_id=elser_model_id,
        document_object_classes={
            "base": BaseArticle,
            "full": FullArticle,
            "search_query": ArticleSearchQuery,
        },
    )


@dataclass
class SearchQuery(ABC):
    limit: int = 10_000

    sort_by: str | None = None
    sort_order: Literal["desc", "asc"] = "desc"

    search_term: str | None = None
    semantic_search: str | None = None

    first_date: datetime | None = None
    last_date: datetime | None = None

    ids: Set[str] | None = None

    highlight: bool = False
    highlight_symbol: str = "**"

    search_fields: ClassVar[list[tuple[str, int]]] = []
    essential_fields: ClassVar[list[str]] = []
    exclude_fields: ClassVar[list[str]] = ["elastic_ml"]

    @abstractmethod
    def generate_es_query(self, elser_id: str | None, complete: bool) -> dict[str, Any]:
        query: dict[str, Any] = {
            "size": self.limit,
            "sort": ["_doc"],
            "query": {"bool": {"filter": [], "should": []}},
            "source_excludes": self.exclude_fields,
        }

        if self.highlight:
            query["highlight"] = {
                "pre_tags": [self.highlight_symbol],
                "post_tags": [self.highlight_symbol],
                "fields": {field_type[0]: {} for field_type in self.search_fields},
            }

        if not complete:
            query["source"] = self.essential_fields

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

        if self.first_date or self.last_date:
            query["query"]["bool"]["filter"].append({"range": {"publish_date": {}}})

        if self.first_date:
            query["query"]["bool"]["filter"][-1]["range"]["publish_date"][
                "gte"
            ] = self.first_date.isoformat()

        if self.last_date:
            query["query"]["bool"]["filter"][-1]["range"]["publish_date"][
                "lte"
            ] = self.last_date.isoformat()

        return query


@dataclass
class ArticleSearchQuery(SearchQuery):
    sources: Set[str] | None = None
    cluster_id: int | None = None

    search_fields = [("title", 5), ("description", 3), ("content", 1)]
    essential_fields = [
        "title",
        "description",
        "url",
        "image_url",
        "profile",
        "source",
        "publish_date",
        "inserted_at",
    ]

    def generate_es_query(
        self, elser_id: str | None, complete: bool = False
    ) -> dict[str, Any]:
        query = super(ArticleSearchQuery, self).generate_es_query(elser_id, complete)

        if self.sources:
            query["query"]["bool"]["filter"].append(
                {"terms": {"profile": [source.lower() for source in self.sources]}}
            )

        if self.cluster_id:
            query["query"]["bool"]["filter"].append(
                {"term": {"ml.cluster": {"value": self.cluster_id}}}
            )

        return query


@dataclass
class MLArticleSearchQuery(ArticleSearchQuery):
    essential_fields: ClassVar[list[str]] = [
        "title",
        "description",
        "url",
        "image_url",
        "profile",
        "source",
        "publish_date",
        "inserted_at",
        "ml",
    ]


SearchQueryType = TypeVar("SearchQueryType", bound=SearchQuery)


class DocumentObjectClasses(
    TypedDict, Generic[BaseDocument, FullDocument, SearchQueryType]
):
    base: Type[BaseDocument]
    full: Type[FullDocument]
    search_query: Type[SearchQueryType]


class ElasticDB(Generic[BaseDocument, FullDocument, SearchQueryType]):
    def __init__(
        self,
        *,
        es_conn: Elasticsearch,
        index_name: str,
        ingest_pipeline: str | None,
        elser_model_id: str | None,
        unique_field: str,
        document_object_classes: DocumentObjectClasses[
            BaseDocument, FullDocument, SearchQueryType
        ],
    ):
        self.es: Elasticsearch = es_conn
        self.index_name: str = index_name
        self.ingest_pipeline = ingest_pipeline
        self.unique_field: str = unique_field

        self.elser_model_id = elser_model_id

        self.document_object_class: DocumentObjectClasses[
            BaseDocument, FullDocument, SearchQueryType
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

    def _concat_strings(self, string_list: Sequence[str]) -> str:
        final_string = " ... ".join(string_list)

        if not final_string[0].isupper():
            final_string = "..." + final_string

        if not final_string[-1] in [".", "!", "?"]:
            final_string += "..."

        return final_string

    @overload
    def _process_search_results(
        self, search_results: ObjectApiResponse[Any], complete: Literal[False]
    ) -> tuple[list[BaseDocument], list[dict[str, Any]]]:
        ...

    @overload
    def _process_search_results(
        self, search_results: ObjectApiResponse[Any], complete: Literal[True]
    ) -> tuple[list[FullDocument], list[dict[str, Any]]]:
        ...

    @overload
    def _process_search_results(
        self, search_results: ObjectApiResponse[Any], complete: bool
    ) -> tuple[list[BaseDocument] | list[FullDocument], list[dict[str, Any]]]:
        ...

    def _process_search_results(
        self, search_results: ObjectApiResponse[Any], complete: bool = False
    ) -> tuple[list[BaseDocument] | list[FullDocument], list[dict[str, Any]]]:
        def process_base(
            hits: list[dict[str, Any]]
        ) -> tuple[list[BaseDocument], list[dict[str, Any]]]:
            valid_docs: list[BaseDocument] = []
            invalid_docs: list[dict[str, Any]] = []

            for hit in hits:
                try:
                    current_document = self.document_object_class["base"](
                        id=hit["_id"], **hit["_source"]
                    )
                    valid_docs.append(current_document)
                except ValidationError as e:
                    logger.error(
                        f'Encountered problem with article with ID "{hit["_id"]}" and title "{hit["_source"]["title"]}", skipping for now. Error: {e}'
                    )

                    invalid_docs.append(hit)

            return valid_docs, invalid_docs

        def process_full(
            hits: list[dict[str, Any]]
        ) -> tuple[list[FullDocument], list[dict[str, Any]]]:
            valid_docs: list[FullDocument] = []
            invalid_docs: list[dict[str, Any]] = []

            for hit in hits:
                try:
                    current_document = self.document_object_class["full"](
                        id=hit["_id"], **hit["_source"]
                    )
                    valid_docs.append(current_document)
                except ValidationError as e:
                    logger.error(
                        f'Encountered problem with article with ID "{hit["_id"]}" and title "{hit["_source"]["title"]}", skipping for now. Error: {e}'
                    )

                    invalid_docs.append(hit)

            return valid_docs, invalid_docs

        for result in search_results["hits"]["hits"]:
            if "highlight" in result:
                for field_type in result["highlight"].keys():
                    if field_type not in result["_source"]:
                        continue

                    result["_source"][field_type] = self._concat_strings(
                        result["highlight"][field_type]
                    )

        if complete:
            return process_full(search_results["hits"]["hits"])
        else:
            return process_base(search_results["hits"]["hits"])

    @overload
    def _query_large(
        self, query: dict[str, Any], complete: Literal[False]
    ) -> tuple[list[BaseDocument], list[dict[str, Any]]]:
        ...

    @overload
    def _query_large(
        self, query: dict[str, Any], complete: Literal[True]
    ) -> tuple[list[FullDocument], list[dict[str, Any]]]:
        ...

    @overload
    def _query_large(
        self, query: dict[str, Any], complete: bool
    ) -> tuple[list[BaseDocument] | list[FullDocument], list[dict[str, Any]]]:
        ...

    def _query_large(
        self, query: dict[str, Any], complete: bool
    ) -> tuple[list[BaseDocument] | list[FullDocument], list[dict[str, Any]]]:
        pit_id: str = self.es.open_point_in_time(
            index=self.index_name, keep_alive="1m"
        )["id"]

        search_after: Any = None
        prior_limit: int = query["size"]

        full_documents: list[FullDocument] = []
        base_documents: list[BaseDocument] = []
        invalid_documents: list[dict[str, Any]] = []

        while True:
            query["size"] = (
                10_000 if prior_limit >= 10_000 or prior_limit == 0 else prior_limit
            )

            search_results: ObjectApiResponse[Any] = self.es.search(
                **query,
                pit={"id": pit_id, "keep_alive": "1m"},
                search_after=search_after,
            )

            if complete:
                returned_full_documents = self._process_search_results(
                    search_results, True
                )
                full_documents.extend(returned_full_documents[0])
                invalid_documents.extend(returned_full_documents[1])
            else:
                returned_base_documents = self._process_search_results(
                    search_results, False
                )
                base_documents.extend(returned_base_documents[0])
                invalid_documents.extend(returned_base_documents[1])

            if len(search_results["hits"]["hits"]) < 10_000:
                break

            search_after = search_results["hits"]["hits"][-1]["sort"]
            pit_id = search_results["pit_id"]

            if prior_limit > 0:
                prior_limit -= 10_000

        if complete:
            return full_documents, invalid_documents
        else:
            return base_documents, invalid_documents

    @overload
    def query_documents(
        self, search_q: SearchQueryType | None, complete: Literal[False] = ...
    ) -> list[BaseDocument]:
        ...

    @overload
    def query_documents(
        self, search_q: SearchQueryType | None, complete: Literal[True] = ...
    ) -> list[FullDocument]:
        ...

    @overload
    def query_documents(
        self, search_q: SearchQueryType | None, complete: bool = ...
    ) -> list[BaseDocument] | list[FullDocument]:
        ...

    def query_documents(
        self, search_q: SearchQueryType | None = None, complete: bool = False
    ) -> list[BaseDocument] | list[FullDocument]:
        if not search_q:
            search_q = self.document_object_class["search_query"]()

        if search_q.limit <= 10_000 and search_q.limit != 0:
            search_results = self.es.search(
                **search_q.generate_es_query(self.elser_model_id, complete),
                index=self.index_name,
            )

            return self._process_search_results(search_results, complete)[0]
        else:
            return self._query_large(
                search_q.generate_es_query(self.elser_model_id, complete), complete
            )[0]

    def query_all_documents(self) -> list[FullDocument]:
        return self.query_documents(
            self.document_object_class["search_query"](limit=0), True
        )

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

    def save_documents(
        self, document_objects: Sequence[BaseDocument | FullDocument]
    ) -> int:
        def convert_documents(
            documents: Sequence[BaseDocument | FullDocument],
        ) -> Generator[dict[str, Any], None, None]:
            for document in documents:
                operation: dict[str, Any] = {
                    "_index": self.index_name,
                    "_source": document.model_dump(exclude_none=True, mode="json"),
                }

                if self.ingest_pipeline:
                    operation["pipeline"] = self.ingest_pipeline

                if "id" in operation["_source"]:
                    operation["_id"] = operation["_source"].pop("id")

                yield operation

        return bulk(self.es, convert_documents(document_objects))[0]

    def save_document(self, document_object: BaseDocument | FullDocument) -> str:
        document_dict: dict[str, Any] = document_object.model_dump(
            exclude_none=True, mode="json"
        )

        try:
            document_id = document_dict.pop("id")
            response = self.es.index(
                index=self.index_name,
                pipeline=self.ingest_pipeline,
                document=document_dict,
                id=document_id,
            )["_id"]
        except KeyError:
            response = self.es.index(
                index=self.index_name,
                pipeline=self.ingest_pipeline,
                document=document_dict,
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


ES_INDEX_CONFIGS = {
    "ELASTICSEARCH_ARTICLE_INDEX": {
        "dynamic": "strict",
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
                "enabled": False,
                "properties": {
                    "interresting": {"type": "object", "dynamic": True},
                    "automatic": {"type": "keyword"},
                },
            },
            "ml": {
                "type": "object",
                "properties": {
                    "similar": {"type": "keyword"},
                    "cluster": {"type": "short"},
                    "coordinates": {"type": "float"},
                },
            },
        },
    },
}
