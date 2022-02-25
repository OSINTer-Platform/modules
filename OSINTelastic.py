from OSINTmodules.OSINTobjects import Article
from elasticsearch import Elasticsearch
from elasticsearch.client import IndicesClient

from datetime import datetime, timezone

class elasticDB():
    def __init__(self, addresses, certPath, indexName):
        self.indexName = indexName

        if certPath:
            self.es = Elasticsearch(addresses, ca_certs=certPath)
        else:
            self.es = Elasticsearch(addresses, verify_certs=False)

    # Checking if the article is already stored in the es db using the URL as that is probably not going to change and is uniqe
    def existsInDB(self, url):
        return int(self.es.search(index=self.indexName, body={'query': { "term" : {"url": {"value" : url}}}})["hits"]["total"]["value"]) != 0

    def concatStrings(self, stringList):
        finalString = " ... ".join(stringList)

        if not finalString[0].isupper():
            finalString = "..." + finalString

        if not finalString[-1] in [".", "!", "?"]:
            finalString += "..."

        return finalString

    def queryArticles(self, searchQ):
        articleList = []

        searchResults = self.es.search(**searchQ, index=self.indexName)

        for queryResult in searchResults["hits"]["hits"]:

            if "highlight" in queryResult:
                if "content" in queryResult["highlight"]:
                    queryResult["_source"]["summary"] = self.concatStrings(queryResult["highlight"]["content"])

                if "description" in queryResult["highlight"]:
                    queryResult["_source"]["description"] = self.concatStrings(queryResult["highlight"]["description"])

                if "title" in queryResult["highlight"]:
                    queryResult["_source"]["title"] = " ... ".join(queryResult["highlight"]["title"])

            for timeValue in ["publish_date", "inserted_at"]:
                queryResult["_source"][timeValue] = datetime.strptime(queryResult["_source"][timeValue], "%Y-%m-%dT%H:%M:%S%z")

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
                if not self.existsInDB(URL):
                    filteredArticleURLDict[profileName].append(URL)

        return filteredArticleURLDict

    # Function for getting each unique profile in the DB
    def requestProfileListFromDB(self):
        searchQ = {"size" : 0, "aggs" : {"profileNames" : {"terms" : { "field" : "profile",  "size" : 500 }}}}

        return [uniqueVal["key"] for uniqueVal in self.es.search(**searchQ, index=self.indexName)["aggregations"]["profileNames"]["buckets"]]

    def saveArticle(self, articleObject):
        articleDict = articleObject.as_dict()

        for timeValue in ["publish_date", "inserted_at"]:
            articleDict[timeValue] = articleDict[timeValue].strftime("%Y-%m-%dT%H:%M:%S%z")

        if "id" in articleDict:
            articleID = articleDict.pop("id")
        else:
            articleID = ""

        if articleID:
            return self.es.index(index=self.indexName, document=articleDict, id=articleID)["_id"]
        else:
            return self.es.index(index=self.indexName, document=articleDict)["_id"]


    def searchArticles(self, paramaters):
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
                    "fields" : {
                      "title" : {},
                      "description": {},
                      "content" : {}
                    }
                  }
                }

        if "limit" in paramaters:
            searchQ["size"] = int(paramaters["limit"])

        if "sortBy" in paramaters and "sortOrder" in paramaters:
            searchQ["sort"] = { paramaters["sortBy"] : paramaters["sortOrder"] }
        elif not "searchTerm" in paramaters:
            searchQ["sort"] = {"publish_date" : "desc"}

        if "searchTerm" in paramaters:
            searchQ["query"]["bool"]["must"] = {"simple_query_string" : {"query" : paramaters["searchTerm"], "fields" : ["title^5", "description^3", "content"]} }

        if "profiles" in paramaters:
            searchQ["query"]["bool"]["filter"].append({ "terms" : { "profile" : paramaters["profiles"] } })

        if "IDs" in paramaters:
            searchQ["query"]["bool"]["filter"].append({ "terms" : { "_id" : paramaters["IDs"] } })

        if "firstDate" in paramaters or "lastDate" in paramaters:
            searchQ["query"]["bool"]["filter"].append({"range" : {"publish_date" : {}}})

        if "firstDate" in paramaters:
            searchQ["query"]["bool"]["filter"][-1]["range"]["publish_date"]["gte"] = paramaters["firstDate"].isoformat()

        if "lastDate" in paramaters:
            searchQ["query"]["bool"]["filter"][-1]["range"]["publish_date"]["lte"] = paramaters["lastDate"].isoformat()

        return self.queryArticles(searchQ)

    def incrementReadCounter(self, articleID):
        incrementScript = {
                    "script" : {
                            "source" : "ctx._source.read_times += 1",
                            "lang" : "painless"
                        }
                }
        self.es.update(index=self.indexName, id=articleID, script=incrementScript)

def configureElasticsearch(address, certPath, indexName):
    if certPath:
        es = Elasticsearch(address, ca_certs=certPath)
    else:
        es = Elasticsearch(address, verify_certs=False)

    indexConfig= {
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
                }

    esIndexClient = IndicesClient(es)

    esIndexClient.create(index=indexName, mappings=indexConfig)
