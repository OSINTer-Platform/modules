from modules.objects import BaseArticle, FullArticle, BaseTweet, FullTweet
from elasticsearch import Elasticsearch
from elasticsearch.client import IndicesClient

from pydantic import ValidationError
from dataclasses import dataclass

from typing import Optional, List, Dict, Any

from datetime import datetime, timezone


def createESConn(addresses, certPath=None):
    if certPath:
        return Elasticsearch(addresses, ca_certs=certPath)
    else:
        return Elasticsearch(addresses, verify_certs=False)


def returnArticleDBConn(configOptions):
    return elasticDB(
        esConn=configOptions.es_conn,
        indexName=configOptions.ELASTICSEARCH_ARTICLE_INDEX,
        uniqueField="url",
        sourceCategory="profile",
        weightedSearchFields=["title^5", "description^3", "content"],
        document_object_classes={"full": FullArticle, "base": BaseArticle},
        essentialFields=[
            "title",
            "description",
            "url",
            "image_url",
            "profile",
            "source",
            "publish_date",
            "inserted_at",
        ],
        logger=configOptions.logger,
    )


def returnTweetDBConn(configOptions):
    return elasticDB(
        esConn=configOptions.es_conn,
        indexName=configOptions.ELASTICSEARCH_TWEET_INDEX,
        uniqueField="twitter_id",
        sourceCategory="author_details.username",
        weightedSearchFields=["content"],
        document_object_classes={"full": FullTweet, "base": BaseTweet},
        essentialFields=[
            "twitter_id",
            "content",
            "author_details",
            "publish_date",
            "inserted_at",
        ],
        logger=configOptions.logger,
    )


@dataclass
class searchQuery:
    limit: int = 10_000
    sortBy: Optional[str] = None
    sortOrder: Optional[str] = None
    searchTerm: Optional[str] = None
    firstDate: Optional[datetime] = None
    lastDate: Optional[datetime] = None
    sourceCategory: Optional[List[str]] = None
    IDs: Optional[List[str]] = None
    highlight: bool = False
    highlightSymbol: str = "**"
    complete: bool = False  # For whether the query should only return the necessary information for creating an article object, or all data stored about the article

    def generateESQuery(self, esClient):
        query = {
            "size": self.limit,
            "sort": ["_doc"],
            "query": {"bool": {"filter": []}},
        }

        if self.highlight:
            query["highlight"] = {
                "pre_tags": [self.highlightSymbol],
                "post_tags": [self.highlightSymbol],
                "fields": {fieldType: {} for fieldType in esClient.searchFields},
            }

        if not self.complete:
            query["source"] = esClient.essentialFields

        if self.searchTerm:
            query["sort"].insert(0, "_score")

            query["query"]["bool"]["must"] = {
                "simple_query_string": {
                    "query": self.searchTerm,
                    "fields": esClient.weightedSearchFields,
                }
            }

        if self.sortBy and self.sortOrder:
            query["sort"].insert(0, {self.sortBy: self.sortOrder})

        if self.sourceCategory:
            query["query"]["bool"]["filter"].append(
                {
                    "terms": {
                        esClient.sourceCategory: [
                            source.lower() for source in self.sourceCategory
                        ]
                    }
                }
            )

        if self.IDs:
            query["query"]["bool"]["filter"].append({"terms": {"_id": self.IDs}})

        if self.firstDate or self.lastDate:
            query["query"]["bool"]["filter"].append({"range": {"publish_date": {}}})

        if self.firstDate:
            query["query"]["bool"]["filter"][-1]["range"]["publish_date"][
                "gte"
            ] = self.firstDate.isoformat()

        if self.lastDate:
            query["query"]["bool"]["filter"][-1]["range"]["publish_date"][
                "lte"
            ] = self.lastDate.isoformat()

        return query


class elasticDB:
    def __init__(
        self,
        *,
        esConn,
        indexName,
        uniqueField,
        sourceCategory,
        weightedSearchFields,
        document_object_classes,
        essentialFields,
        logger,
    ):
        self.indexName = indexName
        self.es = esConn
        self.uniqueField = uniqueField
        self.sourceCategory = sourceCategory
        self.weightedSearchFields = weightedSearchFields
        self.essentialFields = essentialFields

        self.searchFields = []
        for fieldType in weightedSearchFields:
            self.searchFields.append(fieldType.split("^")[0])

        self.document_object_classes = document_object_classes
        self.logger = logger

    # Checking if the document is already stored in the es db using the URL as that is probably not going to change and is uniqe
    def existsInDB(self, token):
        return (
            int(
                self.es.search(
                    index=self.indexName,
                    body={"query": {"term": {self.uniqueField: {"value": token}}}},
                )["hits"]["total"]["value"]
            )
            != 0
        )

    def concatStrings(self, stringList):
        finalString = " ... ".join(stringList)

        if not finalString[0].isupper():
            finalString = "..." + finalString

        if not finalString[-1] in [".", "!", "?"]:
            finalString += "..."

        return finalString

    def _process_search_results(self, complete: bool, search_results: Dict[Any, Any]):
        document_list = []

        if complete:
            document_object_class = self.document_object_classes["full"]
        else:
            document_object_class = self.document_object_classes["base"]

        for query_result in search_results["hits"]["hits"]:

            if "highlight" in query_result:
                for field_type in self.searchFields:
                    if field_type in query_result["highlight"]:
                        query_result["_source"][field_type] = self.concatStrings(
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

    def queryDocuments(self, searchQ: Optional[searchQuery] = None):

        if not searchQ:
            searchQ = searchQuery()

        search_results = self.es.search(
            **searchQ.generateESQuery(self), index=self.indexName
        )

        return self._process_search_results(searchQ.complete, search_results)

    # Function for taking in a list of lists of documents with the first entry of each list being the name of the profile, and then removing all the documents that already has been saved in the database
    def filterDocumentList(self, documentAttributeList):
        filteredDocumentList = []
        for attr in documentAttributeList:
            if not self.existsInDB(attr):
                filteredDocumentList.append(attr)

        return filteredDocumentList

    # Function for getting each unique profile in the DB
    def requestSourceCategoryListFromDB(self):
        searchQ = {
            "size": 0,
            "aggs": {
                "sourceCategory": {"terms": {"field": self.sourceCategory, "size": 500}}
            },
        }

        return [
            uniqueVal["key"]
            for uniqueVal in self.es.search(**searchQ, index=self.indexName)[
                "aggregations"
            ]["sourceCategory"]["buckets"]
        ]

    def saveDocument(self, documentObject):
        documentDict = {
            key: value
            for key, value in documentObject.dict().items()
            if value is not None
        }

        if "id" in documentDict:
            documentID = documentDict.pop("id")
        else:
            documentID = ""

        if documentID:
            return self.es.index(
                index=self.indexName, document=documentDict, id=documentID
            )["_id"]
        else:
            return self.es.index(index=self.indexName, document=documentDict)["_id"]

    def getLastDocument(self, sourceCategoryValue=None):
        searchQ = {"size": 1, "sort": {"publish_date": "desc"}}

        if sourceCategoryValue and isinstance(sourceCategoryValue, list):
            searchQ["query"] = {"terms": {self.sourceCategory: sourceCategoryValue}}
        elif sourceCategoryValue:
            searchQ["query"] = {"term": {self.sourceCategory: sourceCategoryValue}}
        else:
            searchQ["query"] = {"term": {"": ""}}

        results = self.queryDocuments(searchQ)

        if results["result_number"]:
            return results["documents"][0]
        else:
            return None

    def incrementReadCounter(self, documentID):
        incrementScript = {"source": "ctx._source.read_times += 1", "lang": "painless"}
        self.es.update(index=self.indexName, id=documentID, script=incrementScript)


def configureElasticsearch(configOptions):
    es = configOptions.es_conn

    indexConfigs = {
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

    esIndexClient = IndicesClient(es)

    for indexName in indexConfigs:
        esIndexClient.create(
            index=configOptions[indexName],
            mappings=indexConfigs[indexName],
            ignore=[400],
        )
