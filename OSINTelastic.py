from OSINTmodules.OSINTobjects import BaseArticle, FullArticle, BaseTweet, FullTweet
from elasticsearch import Elasticsearch
from elasticsearch.client import IndicesClient

from pydantic import ValidationError
from dataclasses import dataclass

from typing import Optional, List

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
        documentObjectClasses={"full": FullArticle, "base": BaseArticle},
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
        documentObjectClasses={"full": FullTweet, "base": BaseTweet},
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
    complete: bool = False  # For whether the query should only return the necessary information for creating an article object, or all data stored about the article

    def generateESQuery(self, esClient):
        query = {"size": self.limit, "query": {"bool": {"filter": []}}}

        if self.highlight:
            query["highlight"] = {
                "pre_tags": ["***"],
                "post_tags": ["***"],
                "fields": {fieldType: {} for fieldType in esClient.searchFields},
            }

        if not self.complete:
            query["source"] = esClient.essentialFields

        if self.sortBy and self.sortOrder:
            query["sort"] = {self.sortBy: self.sortOrder}
        elif not self.searchTerm:
            query["sort"] = {"publish_date": "desc"}

        if self.searchTerm:
            query["query"]["bool"]["must"] = {
                "simple_query_string": {
                    "query": self.searchTerm,
                    "fields": esClient.weightedSearchFields,
                }
            }

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
        documentObjectClasses,
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

        self.documentObjectClasses = documentObjectClasses
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

    def queryDocuments(self, searchQ: Optional[searchQuery] = None):
        documentList = []
        if searchQ and searchQ.complete:
            documentObjectClass = self.documentObjectClasses["full"]
        else:
            documentObjectClass = self.documentObjectClasses["base"]

        if searchQ:
            searchResults = self.es.search(
                **searchQ.generateESQuery(self), index=self.indexName
            )
        else:
            searchResults = self.es.search(
                **searchQuery().generateESQuery(self), index=self.indexName
            )

        for queryResult in searchResults["hits"]["hits"]:

            if "highlight" in queryResult:
                for fieldType in self.searchFields:
                    if fieldType in queryResult["highlight"]:
                        queryResult["_source"][fieldType] = self.concatStrings(
                            queryResult["highlight"][fieldType]
                        )

            try:
                currentDocument = documentObjectClass(**queryResult["_source"])
                currentDocument.id = queryResult["_id"]
                documentList.append(currentDocument)
            except ValidationError as e:
                self.logger.error(
                    f'Encountered problem with article with ID "{queryResult["_id"]}" and title "{queryResult["_source"]["title"]}", skipping for now. Error: {e}'
                )

        return {
            "documents": documentList,
            "result_number": searchResults["hits"]["total"]["value"],
        }

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
                "read_article_ids": {"type": "keyword"},
                "feeds": {"type": "flattened"},
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
