from datetime import datetime, timezone

from searchtweets import load_credentials, collect_results, gen_request_parameters


def gatherTweetData(credentials, author, lastTweetID=None):

    queryParams = {
        "tweet_fields": "created_at,text,entities",
        "user_fields": "username",
        "expansions": "author_id",
        "results_per_call": 100,
        "granularity": None,
    }

    searchQuery = f"-is:reply -is:retweet "

    if isinstance(author, list):
        searchQuery += f"(from:{' OR from:'.join(author)})"
    elif isinstance(author, str):
        searchQuery += f"from:{author}"

    if lastTweetID:
        query = gen_request_parameters(searchQuery, since_id=lastTweetID, **queryParams)
    else:
        query = gen_request_parameters(searchQuery, **queryParams)

    return collect_results(query, max_tweets=100, result_stream_args=credentials)


def processTweetData(tweetData):
    tweets = tweetData[0]["data"]
    authors = {
        authorBlock.pop("id"): authorBlock
        for authorBlock in tweetData[0]["includes"]["users"]
    }

    for tweet in tweets:
        authorID = tweet.pop("author_id")
        tweet["author_details"] = {"author_id": authorID}
        tweet["author_details"].update(authors[authorID])

        tweet["publish_date"] = datetime.strptime(
            tweet.pop("created_at"), "%Y-%m-%dT%H:%M:%S.%fZ"
        ).replace(tzinfo=timezone.utc)

        if "entities" in tweet:
            entitySpecs = {
                "hashtags": {
                    "identifier": "tag",
                    "link": "https://twitter.com/hashtag/",
                    "prepend": "#",
                },
                "mentions": {
                    "identifier": "username",
                    "link": "https://twitter.com/",
                    "prepend": "@",
                },
            }

            for entityName in entitySpecs:
                if entityName in tweet["entities"]:
                    tweet[entityName] = []
                    for entity in tweet["entities"].pop(entityName):

                        ID = entity[entitySpecs[entityName]["identifier"]]

                        tweet["text"] = tweet["text"].replace(
                            f"{entitySpecs[entityName]['prepend']}{ID}",
                            f"[{entitySpecs[entityName]['prepend']}{ID}]({entitySpecs[entityName]['link']}{ID})",
                        )
                        tweet[entityName].append(ID)

            if "urls" in tweet["entities"]:
                for URLDetails in tweet["entities"].pop("urls"):
                    if "title" in URLDetails:
                        tweet["OG"] = {}

                        for detail in ["title", "description", "unwound_url"]:
                            if detail in URLDetails:
                                tweet["OG"][detail.split("_")[-1]] = URLDetails[detail]

                        if "images" in URLDetails:
                            tweet["OG"]["image_url"] = URLDetails["images"][0]["url"]
                    else:
                        tweet["text"] = tweet["text"].replace(
                            URLDetails["url"],
                            f"[{URLDetails['display_url']}]({URLDetails['expanded_url']})",
                        )

            tweet.pop("entities")

        tweet["content"] = tweet.pop("text")
        tweet["twitter_id"] = tweet.pop("id")

    return tweets
