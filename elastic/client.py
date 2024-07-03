from collections.abc import Callable, Generator, Sequence, Set
from dataclasses import dataclass
import functools
import itertools
import logging
from time import sleep
from typing import (
    Any,
    Generic,
    Literal,
    Type,
    TypeVar,
    cast,
    overload,
)
from typing_extensions import TypedDict
import multiprocessing

from elastic_transport import ObjectApiResponse
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from elasticsearch.client import TasksClient

from pydantic import ValidationError

from ..objects import BaseDocument, FullDocument, PartialDocument, AbstractDocument
from .queries import SearchQuery

logger = logging.getLogger("osinter")

AnyDocument = TypeVar("AnyDocument")
SearchQueryType = TypeVar("SearchQueryType", bound=SearchQuery)


class DocumentObjectClasses(
    TypedDict, Generic[BaseDocument, PartialDocument, FullDocument, SearchQueryType]
):
    base: Type[BaseDocument]
    full: Type[FullDocument]
    partial: Type[PartialDocument]
    search_query: Type[SearchQueryType]


# The function assigned to call needs to be global in order for the multiprocessing to work
@dataclass
class PrePipeline:
    name: str
    call: Callable[[dict[str, Any]], dict[str, Any]]
    requires_elser: bool
    requires_pipeline: bool


# Needs to be global to allow pickling for multiprocessing
def create_document_operation(
    document: AbstractDocument,
    index_name: str,
    elser_model_id: str | None,
    pipeline: str | None,
    pre_pipelines: list[PrePipeline] | None,
) -> dict[str, Any]:
    def run_pre_pipeline(doc: dict[str, Any], pipeline: PrePipeline) -> dict[str, Any]:
        if pipeline.requires_elser and not elser_model_id:
            return doc
        if pipeline.requires_pipeline and not pipeline:
            return doc

        return pipeline.call(doc)

    doc = document.model_dump(exclude={"highlights"}, exclude_none=True, mode="json")

    if pre_pipelines:
        for pre_pipeline in pre_pipelines:
            doc = run_pre_pipeline(doc, pre_pipeline)

    operation: dict[str, Any] = {
        "_index": index_name,
        "_source": doc,
    }

    operation["_id"] = operation["_source"].pop("id")

    if pipeline:
        operation["pipeline"] = pipeline

    return operation


# Needs to be global to allow pickling for multiprocessing
def create_document_update_operation(
    document: AbstractDocument,
    index_name: str,
    fields: list[str] | None,
    elser_model_id: str | None,
    pipeline: str | None,
    pre_pipelines: list[PrePipeline] | None,
) -> dict[str, Any]:
    operation = create_document_operation(
        document, index_name, elser_model_id, pipeline, pre_pipelines
    )

    operation["_op_type"] = "update"

    operation["doc"] = operation["_source"]
    del operation["_source"]

    if fields:
        operation["doc"] = {field: operation["doc"][field] for field in fields}

    return operation


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
        pre_pipelines: list[PrePipeline] | None = None,
    ):
        self.es: Elasticsearch = es_conn
        self.index_name: str = index_name
        self.ingest_pipeline = ingest_pipeline
        self.unique_field: str = unique_field

        self.elser_model_id = elser_model_id

        self.document_object_class: DocumentObjectClasses[
            BaseDocument, PartialDocument, FullDocument, SearchQueryType
        ] = document_object_classes

        self.pre_pipelines = pre_pipelines if pre_pipelines else []

    def exists_in_db(self, token: str | list[str]) -> list[str]:
        """Returns list of attributes for documents which exists in DB"""

        token_list = token if isinstance(token, list) else [token]

        remote_document_attributes: list[str] = []

        for token_batch in itertools.batched(token_list, 10000):

            search_result = self.es.search(
                index=self.index_name,
                query={"terms": {self.unique_field: token_batch}},
                source_includes=[self.unique_field],
                size=10000,
            )

            remote_document_attributes.extend(
                [
                    result["_source"][self.unique_field]
                    for result in search_result["hits"]["hits"]
                ]
            )

        return remote_document_attributes

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
    ) -> tuple[list[BaseDocument], list[dict[str, Any]], dict[str, Any] | None]: ...

    @overload
    def query_documents(
        self, search_q: SearchQueryType | None, completeness: Literal[True]
    ) -> tuple[list[FullDocument], list[dict[str, Any]], dict[str, Any] | None]: ...

    @overload
    def query_documents(
        self, search_q: SearchQueryType | None, completeness: bool
    ) -> tuple[
        list[BaseDocument] | list[FullDocument],
        list[dict[str, Any]],
        dict[str, Any] | None,
    ]: ...

    @overload
    def query_documents(
        self, search_q: SearchQueryType | None, completeness: list[str]
    ) -> tuple[list[PartialDocument], list[dict[str, Any]], dict[str, Any] | None]: ...

    @overload
    def query_documents(
        self, search_q: SearchQueryType | None, completeness: bool | list[str]
    ) -> tuple[
        list[BaseDocument] | list[PartialDocument] | list[FullDocument],
        list[dict[str, Any]],
        dict[str, Any] | None,
    ]: ...

    def query_documents(
        self,
        search_q: SearchQueryType | None,
        completeness: bool | list[str],
    ) -> tuple[
        list[BaseDocument] | list[PartialDocument] | list[FullDocument],
        list[dict[str, Any]],
        dict[str, Any] | None,
    ]:
        if not search_q:
            search_q = self.document_object_class["search_query"]()

        hits: list[dict[str, Any]] = []
        aggs: dict[str, Any] | None = None

        if search_q.limit <= 10_000 and search_q.limit != 0:
            search = self.es.search(
                **search_q.generate_es_query(self.elser_model_id, completeness),
                index=self.index_name,
            )

            hits = search["hits"]["hits"]

            if "aggregations" in search:
                aggs = search["aggregations"]

        else:
            for hit_batch in self._query_large(
                search_q.generate_es_query(self.elser_model_id, completeness)
            ):
                hits.extend(hit_batch)

        if completeness is False:
            p1: tuple[list[BaseDocument], list[dict[str, Any]]] = (
                self._process_search_results(
                    hits,
                    lambda data: self.document_object_class["base"].model_validate(
                        data
                    ),
                )
            )

            return (p1[0], p1[1], aggs)
        elif completeness is True:
            p2: tuple[list[FullDocument], list[dict[str, Any]]] = (
                self._process_search_results(
                    hits,
                    lambda data: self.document_object_class["full"].model_validate(
                        data
                    ),
                )
            )

            return (p2[0], p2[1], aggs)
        elif isinstance(completeness, list):
            p3: tuple[list[PartialDocument], list[dict[str, Any]]] = (
                self._process_search_results(
                    hits,
                    lambda data: self.document_object_class["partial"].model_validate(
                        data, context={"fields_to_validate": completeness}
                    ),
                )
            )
            return (p3[0], p3[1], aggs)
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

    def filter_document_list(self, document_attribute_list: list[str]) -> list[str]:
        existing_attributes = self.exists_in_db(document_attribute_list)
        return [attr for attr in document_attribute_list if attr in existing_attributes]

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
        documents: Sequence[FullDocument],
        fields: list[str] | None = None,
        use_pipeline: bool = False,
        use_pre_pipelines: bool = False,
        chunk_size: int = 500,
    ) -> int:
        func_call = functools.partial(
            create_document_update_operation,
            index_name=self.index_name,
            fields=fields,
            elser_model_id=self.elser_model_id,
            pipeline=self.ingest_pipeline if use_pipeline else None,
            pre_pipelines=self.pre_pipelines if use_pre_pipelines else None,
        )

        with multiprocessing.Pool(multiprocessing.cpu_count() - 2) as pool:
            operations = pool.imap_unordered(func_call, documents, 2000)
            return bulk(self.es, operations, chunk_size=chunk_size)[0]

    def save_documents(
        self,
        documents: Sequence[FullDocument],
        use_pipeline: bool = True,
        use_pre_pipelines: bool = True,
        chunk_size: int = 5,
    ) -> int:
        func_call = functools.partial(
            create_document_operation,
            index_name=self.index_name,
            elser_model_id=self.elser_model_id,
            pipeline=self.ingest_pipeline if use_pipeline else None,
            pre_pipelines=self.pre_pipelines if use_pre_pipelines else None,
        )

        with multiprocessing.Pool(multiprocessing.cpu_count() - 2) as pool:
            operations = pool.imap_unordered(func_call, documents, 2000)
            return bulk(self.es, operations, chunk_size=chunk_size)[0]

    def save_document(
        self,
        doc: FullDocument,
        use_pipeline: bool = True,
        use_pre_pipelines: bool = True,
    ) -> str:
        operation = create_document_operation(
            doc,
            self.index_name,
            self.elser_model_id,
            self.ingest_pipeline if use_pipeline else None,
            self.pre_pipelines if use_pre_pipelines else None,
        )

        response = self.es.index(
            index=operation["_index"],
            pipeline=operation["pipeline"] if "pipeline" in operation else None,
            document=operation["_source"],
            id=operation["_id"],
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
