from OSINTmodules.OSINTobjects import Article
from elasticsearch import Elasticsearch
from elasticsearch.client import IndicesClient

class elasticDB():
    def __init__(self, addresses, indexName):
        self.indexName = indexName
        self.es = Elasticsearch(addresses)

    def queryArticles(self, searchQ):
        articleList = []

        searchResults = self.es.search(searchQ, self.indexName)

        for queryResult in searchResults["hits"]["hits"]:

            if "highlight" in queryResult:
                for fieldType in ["title", "description"]:
                    if fieldType in queryResult["highlight"]:
                        queryResult["_source"][fieldType] = " ... ".join(queryResult["highlight"][fieldType])

            currentArticle = Article(**queryResult["_source"])
            currentArticle.id = queryResult["_id"]
            articleList.append(currentArticle)

        return {"articles" : articleList, "result_number" : searchResults["hits"]["total"]["value"]}


    # Function for taking in a list of lists of articles with the first entry of each list being the name of the profile, and then removing all the articles that already has been saved in the database
    def filterArticleURLList(self, articleURLCollection):
        # The final list that will be returned in the same format as the articleURLCollection list, but with the already stored articles removed
        filteredArticleURLDict = {}

        for profileName in articleURLCollection:
            filteredArticleURLDict[profileName] = []
            for URL in articleURLCollection[profileName]:
                # Checking if the article is already stored in the es db using the URL as that is probably not going to change and is uniqe
                if int(self.es.search(index=self.indexName, body={'query': { "term" : {"url": {"value" : URL}}}})["hits"]["total"]["value"]) == 0:
                    filteredArticleURLDict[profileName].append(URL)

        return filteredArticleURLDict

    # Function for getting each unique profile in the DB
    def requestProfileListFromDB(self):
        searchQ = {"size" : 0, "aggs" : {"profileNames" : {"terms" : { "field" : "profile",  "size" : 500 }}}}

        return [uniqueVal["key"] for uniqueVal in self.es.search(searchQ, self.indexName)["aggregations"]["profileNames"]["buckets"]]

    def requestArticlesFromDB(self, profileList=None, limit=100, idList=None):
        if not profileList:
            profileList = self.requestProfileListFromDB()

        if idList:
            searchQ = {
                      "size"  : int(limit),
                      "sort"  : {
                          "inserted_at" : "desc"
                      },
                      "query" : {
                          "bool" : {
                              "must" : [
                                  { "terms" : {"profile" : profileList} },
                                  { "terms" : {"_id" : idList} }
                              ]
                          }
                      }
                    }
        else:
            searchQ = {
                      "size"  : int(limit),
                      "sort"  : {"inserted_at" : "desc"},
                      "query" : { "terms" : {"profile" : profileList} }
                    }

        return self.queryArticles(searchQ)


    def saveArticle(self, articleObject):
        self.es.index(self.indexName, articleObject.as_dict())

    def searchArticles(self, text, limit=100, profileList=None):
        if not profileList:
            profileList = self.requestProfileListFromDB()

        searchQ = {
                  "size" : int(limit),
                  "query": {
                    "bool" : {
                      "must" : {
                        "multi_match": {
                          "query"  : text,
                          "type"   : "most_fields",
                          "fields" : ["title^5", "description^3", "contents"]
                        }
                      },
                      "filter" : {
                          "terms" : {
                              "profile" : profileList
                          }
                      }
                    }
                  },
                  "highlight" : {
                    "pre_tags" : ["***"],
                    "post_tags" : ["***"],
                    "fields" : {
                      "title" : {},
                      "description": {}
                    }
                  }
                }

        return self.queryArticles(searchQ)

def configureElasticsearch(address, indexName):
    es = Elasticsearch(address)

    es.indices.delete(index=indexName, ignore=[400, 404])

    indexConfig= {
                  "settings": {
                    "index.number_of_shards": 1
                  },
                  "mappings": {
                    "dynamic" : "strict",
                    "properties": {
                      "title": {"type" : "text"},
                      "description": {"type" : "text"},
                      "contents": {"type" : "text"},

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
                               }

                    }
                  }
                }

    esIndexClient = IndicesClient(es)

    esIndexClient.create(indexName, body=indexConfig)
