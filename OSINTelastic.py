from OSINTmodules.OSINTobjects import Article, Tweet
from elasticsearch import Elasticsearch
from elasticsearch.client import IndicesClient

from datetime import datetime, timezone

def createESConn(addresses, certPath=None):
    if certPath:
        return Elasticsearch(addresses, ca_certs=certPath)
    else:
        return Elasticsearch(addresses, verify_certs=False)

def returnArticleDBConn(configOptions):
    DBConn = createESConn(configOptions.ELASTICSEARCH_URL, configOptions.ELASTICSEARCH_CERT_PATH)

    return elasticDB(DBConn, configOptions.ELASTICSEARCH_ARTICLE_INDEX, "url", "profile", ["title^5", "description^3", "content"], Article)

def returnTweetDBConn(configOptions):
    DBConn = createESConn(configOptions.ELASTICSEARCH_URL, configOptions.ELASTICSEARCH_CERT_PATH)

    return elasticDB(DBConn, configOptions.ELASTICSEARCH_TWEET_INDEX, "twitter_id", "author", ["content"], Tweet)

class elasticDB():
    def __init__(self, esConn, indexName, uniqueField, sourceCategory, weightedSearchFields, documentObjectClass):
        self.indexName = indexName
        self.es = esConn
        self.uniqueField = uniqueField
        self.sourceCategory = sourceCategory
        self.weightedSearchFields = weightedSearchFields

        self.searchFields = []
        for fieldType in weightedSearchFields:
            self.searchFields.append(fieldType.split("^")[0])

        self.documentObjectClass = documentObjectClass

    # Checking if the document is already stored in the es db using the URL as that is probably not going to change and is uniqe
    def existsInDB(self, token):
        return int(self.es.search(index=self.indexName, body={'query': { "term" : {self.uniqueField: {"value" : token}}}})["hits"]["total"]["value"]) != 0

    def concatStrings(self, stringList):
        finalString = " ... ".join(stringList)

        if not finalString[0].isupper():
            finalString = "..." + finalString

        if not finalString[-1] in [".", "!", "?"]:
            finalString += "..."

        return finalString

    def queryDocuments(self, searchQ):
        documentList = []

        searchResults = self.es.search(**searchQ, index=self.indexName)

        for queryResult in searchResults["hits"]["hits"]:

            if "highlight" in queryResult:
                for fieldType in self.searchFields:
                    if fieldType in queryResult["highlight"]:
                        queryResult["_source"][fieldType] = self.concatStrings(queryResult["highlight"][fieldType])

            for timeValue in ["publish_date", "inserted_at"]:
                queryResult["_source"][timeValue] = datetime.strptime(queryResult["_source"][timeValue], "%Y-%m-%dT%H:%M:%S%z")

            currentDocument = self.documentObjectClass(**queryResult["_source"])
            currentDocument.id = queryResult["_id"]
            documentList.append(currentDocument)

        return {"documents" : documentList, "result_number" : searchResults["hits"]["total"]["value"]}


    # Function for taking in a list of lists of documents with the first entry of each list being the name of the profile, and then removing all the documents that already has been saved in the database
    def filterDocumentList(self, documentAttributeList):
        filteredDocumentList = []
        for attr in documentAttributeList:
            if not self.existsInDB(attr):
                filteredDocumentList.append(attr)

        return filteredDocumentList

    # Function for getting each unique profile in the DB
    def requestSourceCategoryListFromDB(self):
        searchQ = {"size" : 0, "aggs" : {"sourceCategory" : {"terms" : { "field" : self.sourceCategory,  "size" : 500 }}}}

        return [uniqueVal["key"] for uniqueVal in self.es.search(**searchQ, index=self.indexName)["aggregations"]["sourceCategory"]["buckets"]]

    def saveDocument(self, documentObjectClass):
        documentDict = documentObjectClass.as_dict()

        if "id" in documentDict:
            documentID = documentDict.pop("id")
        else:
            documentID = ""

        if documentID:
            return self.es.index(index=self.indexName, document=documentDict, id=documentID)["_id"]
        else:
            return self.es.index(index=self.indexName, document=documentDict)["_id"]


    def searchDocuments(self, paramaters):
        searchQ = {
                  "size" : 50,
                  "query": {
                    "bool" : {
                      "filter" : []
                    }
                  },
                  "highlight" : {
                    "pre_tags" : ["***"],
                    "post_tags" : ["***"],
                    "fields" : { fieldType:{} for fieldType in self.searchFields }
                    }
                  }

        if "limit" in paramaters:
            searchQ["size"] = int(paramaters["limit"])

        if "sortBy" in paramaters and "sortOrder" in paramaters:
            searchQ["sort"] = { paramaters["sortBy"] : paramaters["sortOrder"] }
        elif not "searchTerm" in paramaters:
            searchQ["sort"] = {"publish_date" : "desc"}

        if "searchTerm" in paramaters:
            searchQ["query"]["bool"]["must"] = {"simple_query_string" : {"query" : paramaters["searchTerm"], "fields" : self.weightedSearchFields} }

        if "sourceCategory" in paramaters:
            searchQ["query"]["bool"]["filter"].append({ "terms" : { self.sourceCategory : paramaters["sourceCategory"] } })

        if "IDs" in paramaters:
            searchQ["query"]["bool"]["filter"].append({ "terms" : { "_id" : paramaters["IDs"] } })

        if "firstDate" in paramaters or "lastDate" in paramaters:
            searchQ["query"]["bool"]["filter"].append({"range" : {"publish_date" : {}}})

        if "firstDate" in paramaters:
            searchQ["query"]["bool"]["filter"][-1]["range"]["publish_date"]["gte"] = paramaters["firstDate"].isoformat()

        if "lastDate" in paramaters:
            searchQ["query"]["bool"]["filter"][-1]["range"]["publish_date"]["lte"] = paramaters["lastDate"].isoformat()

        return self.queryDocuments(searchQ)

    def getLastDocument(self, sourceCategory=None):
        searchQ = {
                  "size" : 1,
                  "sort" : {
                      "publish_date" : "desc"
                  }
              }

        if sourceCategory and isinstance(sourceCategory, list):
            searchQ["query"] = { "terms" : { self.sourceCategory : sourceCategory } }
        elif sourceCategory:
            searchQ["query"] = { "term" : { self.sourceCategory : sourceCategory } }

        results = self.queryDocuments(searchQ)

        if results["result_number"]:
            return results["documents"][0]
        else:
            return None

    def incrementReadCounter(self, documentID):
        incrementScript = {
                            "source" : "ctx._source.read_times += 1",
                            "lang" : "painless"
                }
        self.es.update(index=self.indexName, id=documentID, script=incrementScript)

def configureElasticsearch(configOptions):
    es = createESConn(configOptions.ELASTICSEARCH_URL, configOptions.ELASTICSEARCH_CERT_PATH)

    indexConfigs = {
        "ELASTICSEARCH_TWEET_INDEX" : {
                      "dynamic" : "strict",
                      "properties": {
                        "title": {"type" : "text"},
                        "description": {"type" : "text"},
                        "content": {"type" : "text"},
                        "formatted_content" : {"type" : "text"},

                        "url": {"type" : "keyword"},
                        "profile": {"type" : "keyword"},
                        "source": {"type" : "keyword"},
                        "image_url": {"type" : "keyword"},
                        "author": {"type" : "keyword"},

                        "inserted_at" : {"type" : "date"},
                        "publish_date" : {"type" : "date"},

                        "tags" : {
                                    "type" : "object",
                                    "enabled" : False,
                                    "properties" : {
                                        "manual" : {"type" : "object", "dynamic" : True},
                                        "interresting" : {"type" : "object", "dynamic" : True},
                                        "automatic" : {"type" : "keyword"}
                                    }
                                 },
                        "read_times" : {"type" :  "unsigned_long"}
                      }
                    },

        "ELASTICSEARCH_ARTICLE_INDEX" : {
                      "dynamic" : "strict",
                      "properties": {
                        "title": {"type" : "text"},
                        "description": {"type" : "text"},
                        "content": {"type" : "text"},
                        "formatted_content" : {"type" : "text"},

                        "url": {"type" : "keyword"},
                        "profile": {"type" : "keyword"},
                        "source": {"type" : "keyword"},
                        "image_url": {"type" : "keyword"},
                        "author": {"type" : "keyword"},

                        "inserted_at" : {"type" : "date"},
                        "publish_date" : {"type" : "date"},

                        "tags" : {
                                    "type" : "object",
                                    "enabled" : False,
                                    "properties" : {
                                        "manual" : {"type" : "object", "dynamic" : True},
                                        "interresting" : {"type" : "object", "dynamic" : True},
                                        "automatic" : {"type" : "keyword"}
                                    }
                                 },
                        "read_times" : {"type" :  "unsigned_long"}
                },

        "ELASTICSEARCH_USER_INDEX" : {
                      "dynamic" : "strict",
                      "properties" : {
                          "username" : {"type" : "keyword"},
                          "password_hash" : {"type" : "keyword"},
                          "read_article_ids" : {"type" : "keyword"},
                          "saved_article_ids" : {"type" : "keyword"}
                      }
                }
        }

    esIndexClient = IndicesClient(es)

    for indexName in indexConfigs:
        esIndexClient.create(index=configOptions[indexName], mappings=indexConfigs[indexName], ignore=[400])
