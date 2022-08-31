from modules.objects import BaseArticle, FullArticle, BaseTweet, FullTweet
from elasticsearch import Elasticsearch
from elasticsearch.client import IndicesClient

from pydantic import ValidationError
from dataclasses import dataclass

from typing import Optional, List, Dict, Any, Union

from datetime import datetime, timezone


def create_es_conn(addresses, cert_path=None):
    if cert_path:
        return Elasticsearch(addresses, ca_certs=cert_path)
    else:
        return Elasticsearch(addresses, verify_certs=False)


def return_article_db_conn(config_options):
    return ElasticDB(
        es_conn=config_options.es_conn,
        index_name=config_options.ELASTICSEARCH_ARTICLE_INDEX,
        unique_field="url",
        source_category="profile",
        weighted_search_fields=["title^5", "description^3", "content"],
        document_object_classes={"full": FullArticle, "base": BaseArticle},
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
        logger=config_options.logger,
    )


def return_tweet_db_conn(config_options):
    return ElasticDB(
        es_conn=config_options.es_conn,
        index_name=config_options.ELASTICSEARCH_TWEET_INDEX,
        unique_field="twitter_id",
        source_category="author_details.username",
        weighted_search_fields=["content"],
        document_object_classes={"full": FullTweet, "base": BaseTweet},
        essential_fields=[
            "twitter_id",
            "content",
            "author_details",
            "publish_date",
            "inserted_at",
        ],
        logger=config_options.logger,
    )


@dataclass
class SearchQuery:
    limit: int = 10_000
    sort_by: Optional[str] = None
    sort_order: Optional[str] = None
    search_term: Optional[str] = None
    first_date: Optional[datetime] = None
    last_date: Optional[datetime] = None
    source_category: Optional[List[str]] = None
    ids: Optional[List[str]] = None
    highlight: bool = False
    highlight_symbol: str = "**"
    complete: bool = False  # For whether the query should only return the necessary information for creating an article object, or all data stored about the article

    def generate_es_query(self, es_client):
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


class ElasticDB:
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
        logger,
    ):
        self.index_name = index_name
        self.es = es_conn
        self.unique_field = unique_field
        self.source_category = source_category
        self.weighted_search_fields = weighted_search_fields
        self.essential_fields = essential_fields

        self.search_fields = []
        for field_type in weighted_search_fields:
            self.search_fields.append(field_type.split("^")[0])

        self.document_object_classes = document_object_classes
        self.logger = logger

    # Checking if the document is already stored in the es db using the URL as that is probably not going to change and is uniqe
    def exists_in_db(self, token):
        return (
            int(
                self.es.search(
                    index=self.index_name,
                    body={"query": {"term": {self.unique_field: {"value": token}}}},
                )["hits"]["total"]["value"]
            )
            != 0
        )

    def _concat_strings(self, string_list):
        final_string = " ... ".join(string_list)

        if not final_string[0].isupper():
            final_string = "..." + final_string

        if not final_string[-1] in [".", "!", "?"]:
            final_string += "..."

        return final_string

    def _process_search_results(self, complete: bool, search_results: Dict[Any, Any]):
        document_list = []

        if complete:
            document_object_class = self.document_object_classes["full"]
        else:
            document_object_class = self.document_object_classes["base"]

        for query_result in search_results["hits"]["hits"]:

            if "highlight" in query_result:
                for field_type in self.search_fields:
                    if field_type in query_result["highlight"]:
                        query_result["_source"][field_type] = self._concat_strings(
                            query_result["highlight"][field_type]
                        )

            try:
                current_document = document_object_class(**query_result["_source"])
                current_document.id = query_result["_id"]
                document_list.append(current_document)
            except ValidationError as e:
                self.logger.error(
                    f'Encountered problem with article with ID "{query_result["_id"]}" and title "{query_result["_source"]["title"]}", skipping for now. Error: {e}'
                )

        return {
            "documents": document_list,
            "result_number": search_results["hits"]["total"]["value"],
        }

    def query_large(self, query: Dict[any, any], complete: bool):
        pit_id = self.es.open_point_in_time(index=self.index_name, keep_alive="1m")[
            "id"
        ]

        documents = []
        search_after = None
        prior_limit = query["size"]

        while True:
            query["size"] = (
                10_000 if prior_limit >= 10_000 or prior_limit == 0 else prior_limit
            )

            search_results = self.es.search(
                **query,
                pit={"id": pit_id, "keep_alive": "1m"},
                search_after=search_after,
            )

            returned_documents = self._process_search_results(
                complete, search_results
            )["documents"]

            documents.extend(returned_documents)

            if len(returned_documents) < 10_000:
                break

            search_after = search_results["hits"]["hits"][-1]["sort"]
            pit_id = search_results["pit_id"]

            if prior_limit > 0:
                prior_limit -= 10_000

        return documents


    def query_documents(self, search_q: Optional[SearchQuery] = None):

        if not search_q:
            search_q = SearchQuery()

        if search_q.limit <= 10_000 and search_q.limit != 0:
            search_results = self.es.search(
                **search_q.generate_es_query(self), index=self.index_name
            )

            return self._process_search_results(search_q.complete, search_results)
        else:

            documents = self.query_large(search_q.generate_es_query(self), search_q.complete)

            return {"documents": documents, "result_number": len(documents)}

    # Function for taking in a list of lists of documents with the first entry of each list being the name of the profile, and then removing all the documents that already has been saved in the database
    def filter_document_list(self, document_attribute_list):
        filtered_document_list = []
        for attr in document_attribute_list:
            if not self.exists_in_db(attr):
                filtered_document_list.append(attr)

        return filtered_document_list

    # If there's more than 10.000 unique values, then this function will only get the first 10.000
    def get_unique_values(self, field_name: Optional[str] = None) -> List[Union[str, int]]:
        if not field_name:
            field_name = self.source_category

        search_q = {
            "size": 0,
            "aggs": {
                "unique_fields": {
                    "terms": {"field": field_name, "size": 10_000}
                }
            },
        }

        return [
            unique_val["key"]
            for unique_val in self.es.search(**search_q, index=self.index_name)[
                "aggregations"
            ]["unique_fields"]["buckets"]
        ]

    def save_document(self, document_object):
        document_dict = {
            key: value
            for key, value in document_object.dict().items()
            if value is not None
        }

        if "id" in document_dict:
            document_id = document_dict.pop("id")
        else:
            document_id = ""

        if document_id:
            return self.es.index(
                index=self.index_name, document=document_dict, id=document_id
            )["_id"]
        else:
            return self.es.index(index=self.index_name, document=document_dict)["_id"]

    def get_last_document(self, source_category_value=None):
        search_q = {"size": 1, "sort": {"publish_date": "desc"}}

        if source_category_value and isinstance(source_category_value, list):
            search_q["query"] = {"terms": {self.source_category: source_category_value}}
        elif source_category_value:
            search_q["query"] = {"term": {self.source_category: source_category_value}}
        else:
            search_q["query"] = {"term": {"": ""}}

        results = self.query_documents(search_q)

        if results["result_number"]:
            return results["documents"][0]
        else:
            return None

    def increment_read_counter(self, document_id):
        increment_script = {"source": "ctx._source.read_times += 1", "lang": "painless"}
        self.es.update(index=self.index_name, id=document_id, script=increment_script)


def configure_elasticsearch(config_options):
    es = config_options.es_conn

    index_configs = {
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
                "tags": {
                    "type": "object",
                    "enabled": False,
                    "properties": {
                        "manual": {"type": "object", "dynamic": True},
                        "interresting": {"type": "object", "dynamic": True},
                        "automatic": {"type": "keyword"},
                    },
                },
                "read_times": {"type": "unsigned_long"},
                "similar": {"type": "keyword"},
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

    es_index_client = IndicesClient(es)

    for index_name in index_configs:
        es_index_client.create(
            index=config_options[index_name],
            mappings=index_configs[index_name],
            ignore=[400],
        )
