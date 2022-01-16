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
                if "description" in queryResult["highlight"]:
                    descriptionText = " ... ".join(queryResult["highlight"]["description"])
                    if not descriptionText[0].isupper():
                        descriptionText = "..." + descriptionText

                    if not descriptionText[-1] == ".":
                        descriptionText += "..."

                    queryResult["_source"]["description"] = descriptionText

                if "title" in queryResult["highlight"]:
                    queryResult["_source"]["title"] = " ... ".join(queryResult["highlight"]["title"])

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

    def saveArticle(self, articleObject):
        self.es.index(self.indexName, articleObject.as_dict())

    def searchArticles(self, paramaters):
        searchQ = {
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
                      "description": {}
                    }
                  }
                }

        if "limit" in paramaters:
            searchQ["size"] = int(paramaters["limit"])

        if "sorting" in paramaters:
            searchQ["sort"] = paramaters["sorting"]
        else:
            searchQ["sort"] = {"publish_date" : "desc"}

        if "searchTerm" in paramaters:
            searchQ["query"]["bool"]["must"] = {"simple_query_string" : {"query" : paramaters["searchTerm"], "fields" : ["title^5", "description^3", "contents"]} }

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

def configureElasticsearch(address, indexName):
    es = Elasticsearch(address)

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

    esIndexClient.create(indexName, body=indexConfig, ignore=[400, 404])
