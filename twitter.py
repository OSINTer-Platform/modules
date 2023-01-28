from datetime import datetime, timezone

from searchtweets import collect_results, gen_request_parameters


def gather_tweet_data(credentials, author, last_tweet_id=None):

    query_params = {
        "tweet_fields": "created_at,text,entities",
        "user_fields": "username",
        "expansions": "author_id",
        "results_per_call": 100,
        "granularity": None,
    }

    search_query = f"-is:reply -is:retweet "

    if isinstance(author, list):
        search_query += f"(from:{' OR from:'.join(author)})"
    elif isinstance(author, str):
        search_query += f"from:{author}"

    if last_tweet_id:
        query = gen_request_parameters(
            search_query, since_id=last_tweet_id, **query_params
        )
    else:
        query = gen_request_parameters(search_query, **query_params)

    return collect_results(query, max_tweets=100, result_stream_args=credentials)


def process_tweet_data(tweet_data):
    tweets = tweet_data[0]["data"]
    authors = {
        author_block.pop("id"): author_block
        for author_block in tweet_data[0]["includes"]["users"]
    }

    for tweet in tweets:
        author_id = tweet.pop("author_id")
        tweet["author_details"] = {"author_id": author_id}
        tweet["author_details"].update(authors[author_id])

        tweet["publish_date"] = datetime.strptime(
            tweet.pop("created_at"), "%Y-%m-%dT%H:%M:%S.%fZ"
        ).replace(tzinfo=timezone.utc)

        if "entities" in tweet:
            entity_specs = {
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

            for entity_name in entity_specs:
                if entity_name in tweet["entities"]:
                    tweet[entity_name] = []
                    for entity in tweet["entities"].pop(entity_name):

                        ID = entity[entity_specs[entity_name]["identifier"]]

                        tweet["text"] = tweet["text"].replace(
                            f"{entity_specs[entity_name]['prepend']}{ID}",
                            f"[{entity_specs[entity_name]['prepend']}{ID}]({entity_specs[entity_name]['link']}{ID})",
                        )
                        tweet[entity_name].append(ID)

            if "urls" in tweet["entities"]:
                for url_details in tweet["entities"].pop("urls"):
                    if "title" in url_details:
                        tweet["OG"] = {}

                        for detail in ["title", "description", "unwound_url"]:
                            if detail in url_details:
                                tweet["OG"][detail.split("_")[-1]] = url_details[detail]

                        if "images" in url_details:
                            tweet["OG"]["image_url"] = url_details["images"][0]["url"]
                    else:
                        tweet["text"] = tweet["text"].replace(
                            url_details["url"],
                            f"[{url_details['display_url']}]({url_details['expanded_url']})",
                        )

            tweet.pop("entities")

        tweet["content"] = tweet.pop("text")
        tweet["twitter_id"] = tweet.pop("id")

    return tweets
