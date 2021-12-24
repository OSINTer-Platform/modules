from elasticsearch import Elasticsearch

class elasticDB():
    def __init__(self, indexName):
        self.indexName = indexName
        self.es = Elasticsearch()

    # Function for taking in a list of lists of articles with the first entry of each list being the name of the profile, and then removing all the articles that already has been saved in the database
    def filterArticleURLList(es, indexName, articleURLCollection):
        # The final list that will be returned in the same format as the articleURLCollection list, but with the already stored articles removed
        filteredArticleURLDict = {}

        for profileName in articleURLCollection:
            filteredArticleURLDict[profileName] = []
            for URL in filteredArticleURLDict:
                # Checking if the article is already stored in the es db using the URL as that is probably not going to change and is uniqe
                if int(es.search(index=indexName, body={'query': { "term" : {"url.keyword": {"value" : URL}}}})["hits"]["total"]["value"]) == 0:
                    newURLList.append(URL)

        return filteredArticleURLDict

    # Function for getting each unique profile in the DB
    def requestProfileListFromDB(self):
        searchQ = {"size" : 0, "aggs" : {"profileNames" : {"terms" : { "field" : "profile",  "size" : 500 }}}}

        return [uniqueVal["key"] for uniqueVal in self.es.search(searchQ, self.indexName)["aggregations"]["profileNames"]["buckets"]]
