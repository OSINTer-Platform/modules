from feedgen.feed import FeedGenerator

import os
import sqlite3
from OSINTmodules.OSINTprofiles import getProfiles


def verifyProfiles(profiles, esClient):
    # Getting the profiles that are stored in the database
    DBStoredProfiles = esClient.requestSourceCategoryListFromDB()

    # Getting the names of the locally avaiable profiles stored in the json files
    localProfiles = getProfiles(justNames=True)

    # Looping through the profiles we want to confirm are matching those stored
    for profile in profiles:
        if profile not in DBStoredProfiles or profile not in localProfiles:
            return False

    return True


def initiateUserDB(DBName, userTable):
    if not os.path.exists(DBName):
        conn = sqlite3.connect(DBName)
        cur = conn.cursor()

        cur.execute(
            f""" CREATE TABLE {userTable}
                    (   username text NOT NULL PRIMARY KEY,
                        saved_article_ids text DEFAULT '',
                        read_article_ids text DEFAULT '',
                        password_hash text NOT NULL,
                        id text NOT NULL    )
                    """
        )

        conn.commit()
        conn.close()


def generateRSSFeed(articleList):
    fg = FeedGenerator()
    fg.title("OSINTer feed")
    fg.description("An RSS feed from the OSINTer project")
    fg.link(href="https://github.com/bertmad3400/OSINTer")
    fg.logo("https://raw.githubusercontent.com/bertmad3400/OSINTer/master/logo.png")
    fg.language("en")

    for article in articleList:
        fe = fg.add_entry()
        fe.title(article.title)
        fe.link(href=article.url)
        fe.description(article.description)
        fe.id(article.id)
        fe.source(title=article.source)
        fe.author(name=article.author)
        fe.pubDate(article.publish_date)

    return fg
