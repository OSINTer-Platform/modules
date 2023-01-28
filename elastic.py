from collections.abc import Generator
from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any, Generic, Literal, Type, cast, overload

from elastic_transport import ObjectApiResponse
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from pydantic import ValidationError

from modules.objects import (
    AllDocuments,
    BaseArticle,
    BaseTweet,
    DocumentBase,
    DocumentFull,
    FullArticle,
    FullTweet,
    OSINTerDocument,
)

logger = logging.getLogger("osinter")


def create_es_conn(addresses, cert_path=None):
    if cert_path:
        return Elasticsearch(addresses, ca_certs=cert_path)
    else:
        return Elasticsearch(addresses, verify_certs=False)


def return_article_db_conn(config_options):
    return ElasticDB[BaseArticle, FullArticle](
        es_conn=config_options.es_conn,
        index_name=config_options.ELASTICSEARCH_ARTICLE_INDEX,
        unique_field="url",
        source_category="profile",
        weighted_search_fields=["title^5", "description^3", "content"],
        document_object_classes=(BaseArticle, FullArticle),
        essential_fields=[
            "title",
            "description",
            "url",
            "image_url",
            "profile",
            "source",
            "publish_date",
            "inserted_at",
        ],
    )


def return_tweet_db_conn(config_options):
    return ElasticDB[BaseTweet, FullTweet](
        es_conn=config_options.es_conn,
        index_name=config_options.ELASTICSEARCH_TWEET_INDEX,
        unique_field="twitter_id",
        source_category="author_details.username",
        weighted_search_fields=["content"],
        document_object_classes=(BaseTweet, FullTweet),
        essential_fields=[
            "twitter_id",
            "content",
            "author_details",
            "publish_date",
            "inserted_at",
        ],
    )


@dataclass
class SearchQuery:
    limit: int = 10_000
    sort_by: str | None = None
    sort_order: str | None = None
    search_term: str | None = None
    first_date: datetime | None = None
    last_date: datetime | None = None
    source_category: list[str] | None = None
    ids: list[str] | None = None
    highlight: bool = False
    highlight_symbol: str = "**"
    complete: bool = False  # For whether the query should only return the necessary information for creating an article object, or all data stored about the article
    cluster_id: int | None = None

    def generate_es_query(self, es_client) -> dict[str, Any]:
        query = {
            "size": self.limit,
            "sort": ["_doc"],
            "query": {"bool": {"filter": []}},
        }

        if self.highlight:
            query["highlight"] = {
                "pre_tags": [self.highlight_symbol],
                "post_tags": [self.highlight_symbol],
                "fields": {field_type: {} for field_type in es_client.search_fields},
            }

        if not self.complete:
            query["source"] = es_client.essential_fields

        if self.search_term:
            query["sort"].insert(0, "_score")

            query["query"]["bool"]["must"] = {
                "simple_query_string": {
                    "query": self.search_term,
                    "fields": es_client.weighted_search_fields,
                }
            }

        if self.sort_by and self.sort_order:
            query["sort"].insert(0, {self.sort_by: self.sort_order})

        if self.source_category:
            query["query"]["bool"]["filter"].append(
                {
                    "terms": {
                        es_client.source_category: [
                            source.lower() for source in self.source_category
                        ]
                    }
                }
            )

        if self.ids:
            query["query"]["bool"]["filter"].append({"terms": {"_id": self.ids}})

        if self.cluster_id:
            query["query"]["bool"]["filter"].append(
                {"term": {"ml.cluster": {"value": self.cluster_id}}}
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


class ElasticDB(Generic[DocumentBase, DocumentFull]):
    def __init__(
        self,
        *,
        es_conn,
        index_name,
        unique_field,
        source_category,
        weighted_search_fields,
        document_object_classes,
        essential_fields,
    ):
        self.index_name: str = index_name
        self.es: Elasticsearch = es_conn
        self.unique_field: str = unique_field
        self.source_category: str = source_category
        self.weighted_search_fields: list[str] = weighted_search_fields
        self.essential_fields: list[str] = essential_fields

        self.search_fields: list[str] = []
        for field_type in weighted_search_fields:
            self.search_fields.append(field_type.split("^")[0])

        self.document_object_classes: tuple[
            Type[DocumentBase], Type[DocumentFull]
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

    def _concat_strings(self, string_list: list[str]) -> str:
        final_string = " ... ".join(string_list)

        if not final_string[0].isupper():
            final_string = "..." + final_string

        if not final_string[-1] in [".", "!", "?"]:
            final_string += "..."

        return final_string

    @overload
    def _process_search_results(
        self, complete: Literal[False], search_results: ObjectApiResponse
    ) -> list[DocumentBase]:
        ...

    @overload
    def _process_search_results(
        self, complete: Literal[True], search_results: ObjectApiResponse
    ) -> list[DocumentFull]:
        ...

    @overload
    def _process_search_results(
        self, complete: bool, search_results: ObjectApiResponse
    ) -> list[DocumentBase] | list[DocumentFull]:
        ...

    def _process_search_results(
        self, complete: bool, search_results: ObjectApiResponse
    ) -> list[DocumentBase] | list[DocumentFull]:
        def _process_results(
            document_object_class: Type[AllDocuments],
        ) -> list[AllDocuments]:
            documents: list[AllDocuments] = []

            for result in search_results["hits"]["hits"]:

                if "highlight" in result:
                    for field_type in self.search_fields:
                        if field_type in result["highlight"]:
                            result["_source"][field_type] = self._concat_strings(
                                result["highlight"][field_type]
                            )

                try:
                    current_document = document_object_class(**result["_source"])
                    current_document.id = result["_id"]
                    documents.append(current_document)
                except ValidationError as e:
                    logger.error(
                        f'Encountered problem with article with ID "{result["_id"]}" and title "{result["_source"]["title"]}", skipping for now. Error: {e}'
                    )

            return documents

        if complete:
            return _process_results(self.document_object_classes[1])
        else:
            return _process_results(self.document_object_classes[0])

    @overload
    def query_large(
        self, query: dict[str, Any], complete: Literal[False]
    ) -> list[DocumentBase]:
        ...

    @overload
    def query_large(
        self, query: dict[str, Any], complete: Literal[True]
    ) -> list[DocumentFull]:
        ...

    @overload
    def query_large(
        self, query: dict[str, Any], complete: bool
    ) -> list[DocumentBase] | list[DocumentFull]:
        ...

    def query_large(self, query, complete):
        pit_id: str = self.es.open_point_in_time(
            index=self.index_name, keep_alive="1m"
        )["id"]

        documents = []
        search_after = None
        prior_limit = query["size"]

        while True:
            query["size"] = (
                10_000 if prior_limit >= 10_000 or prior_limit == 0 else prior_limit
            )

            search_results: ObjectApiResponse = self.es.search(
                **query,
                pit={"id": pit_id, "keep_alive": "1m"},
                search_after=search_after,
            )

            returned_documents = self._process_search_results(complete, search_results)

            documents.extend(returned_documents)

            if len(returned_documents) < 10_000:
                break

            search_after = search_results["hits"]["hits"][-1]["sort"]
            pit_id = search_results["pit_id"]

            if prior_limit > 0:
                prior_limit -= 10_000

        return documents

    @overload
    def query_documents(
        self, search_q: SearchQuery | None = ..., complete: Literal[False] = ...
    ) -> list[DocumentBase]:
        ...

    @overload
    def query_documents(
        self, search_q: SearchQuery | None = ..., complete: Literal[True] = ...
    ) -> list[DocumentFull]:
        ...

    @overload
    def query_documents(
        self, search_q: SearchQuery | None = ..., complete: bool = ...
    ) -> list[DocumentBase] | list[DocumentFull]:
        ...

    def query_documents(self, search_q=None, complete=False):
        if not search_q:
            search_q = SearchQuery()

        if search_q.limit <= 10_000 and search_q.limit != 0:
            search_results = self.es.search(
                **search_q.generate_es_query(self), index=self.index_name
            )

            return self._process_search_results(search_q.complete, search_results)
        else:

            return self.query_large(search_q.generate_es_query(self), search_q.complete)

    def query_all_documents(self) -> list[DocumentFull]:
        return self.query_documents(SearchQuery(limit=0, complete=True), True)

    def filter_document_list(self, document_attribute_list: list[str]) -> list[str]:
        filtered_document_list = []
        for attr in document_attribute_list:
            if not self.exists_in_db(attr):
                filtered_document_list.append(attr)

        return filtered_document_list

    # If there's more than 10.000 unique values, then this function will only get the first 10.000
    def get_unique_values(self, field_name: str | None = None) -> dict[str, int]:
        if not field_name:
            field_name = self.source_category

        search_q = {
            "size": 0,
            "aggs": {"unique_fields": {"terms": {"field": field_name, "size": 10_000}}},
        }

        return {
            unique_val["key"]: unique_val["doc_count"]
            for unique_val in self.es.search(**search_q, index=self.index_name)[
                "aggregations"
            ]["unique_fields"]["buckets"]
        }

    def save_documents(
        self, document_objects: list[DocumentBase] | list[DocumentFull]
    ) -> int:
        def convert_documents(
            documents: list[DocumentBase] | list[DocumentFull],
        ) -> Generator[dict[str, Any], None, None]:
            for document in documents:
                operation = {
                    "_index": self.index_name,
                    "_source": document.dict(exclude_none=True),
                }

                if "id" in operation["_source"]:
                    operation["_id"] = operation["_source"].pop("id")

                yield operation

        return bulk(self.es, convert_documents(document_objects))[0]

    def save_document(
        self, document_object: DocumentBase | DocumentFull
    ) -> str:
        document_dict: dict[str, Any] = document_object.dict(exclude_none=True)

        try:
            document_id = document_dict.pop("id")
            return self.es.index(index=self.index_name, document=document_dict, id=document_id)["_id"]
        except KeyError:
            return self.es.index(index=self.index_name, document=document_dict)["_id"]


    def get_last_document(
        self, source_category_value: list[str]
    ) -> OSINTerDocument | None:
        search_q = SearchQuery(
            limit=1,
            source_category=source_category_value,
            sort_by="inserted_at",
            sort_order="desc",
        )

        results = self.query_documents(search_q)

        try:
            return results[0]
        except IndexError:
            return None

    def increment_read_counter(self, document_id: str) -> None:
        increment_script = {"source": "ctx._source.read_times += 1", "lang": "painless"}
        self.es.update(index=self.index_name, id=document_id, script=increment_script)


ES_INDEX_CONFIGS = {
    "ELASTICSEARCH_TWEET_INDEX": {
        "dynamic": "strict",
        "properties": {
            "twitter_id": {"type": "keyword"},
            "content": {"type": "text"},
            "hashtags": {"type": "keyword"},
            "mentions": {"type": "keyword"},
            "inserted_at": {"type": "date"},
            "publish_date": {"type": "date"},
            "author_details": {
                "type": "object",
                "enabled": True,
                "properties": {
                    "author_id": {"type": "keyword"},
                    "name": {"type": "keyword"},
                    "username": {"type": "keyword"},
                },
            },
            "OG": {
                "type": "object",
                "enabled": True,
                "properties": {
                    "url": {"type": "keyword"},
                    "image_url": {"type": "keyword"},
                    "title": {"type": "text"},
                    "description": {"type": "text"},
                    "content": {"type": "text"},
                },
            },
            "read_times": {"type": "unsigned_long"},
        },
    },
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
                    "manual": {"type": "object", "dynamic": True},
                    "interresting": {"type": "object", "dynamic": True},
                    "automatic": {"type": "keyword"},
                },
            },
            "ml": {
                "type": "object",
                "properties": {
                    "similar": {"type": "keyword"},
                    "cluster": {"type": "short"},
                },
            },
        },
    },
    "ELASTICSEARCH_USER_INDEX": {
        "dynamic": "strict",
        "properties": {
            "username": {"type": "keyword"},
            "password_hash": {"type": "keyword"},
            "email_hash": {"type": "keyword"},
            "feeds": {"type": "flattened"},
            "collections": {
                "type": "object",
                "enabled": False,
                "dynamic": True,
                "properties": {
                    "Read Later": {"type": "keyword"},
                    "Already Read": {"type": "keyword"},
                },
            },
        },
    },
}
