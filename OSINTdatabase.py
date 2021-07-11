def initiateArticleTable(connection):
    tableContentList = [
                            "id BIGSERIAL NOT NULL PRIMARY KEY",
                            "title VARCHAR(150) NOT NULL",
                            "description VARCHAR(350)",
                            "url VARCHAR(300) NOT NULL",
                            "image_url VARCHAR(300)",
                            "profile VARCHAR(30) NOT NULL",
                            "scraped BOOL NOT NULL"
                        ]
    createTable(connection, "articles", tableContentList)

# Function for creating new tables
def createTable(connection, tableName, tableContentList):
    # Making sure the tablename is in all lowercase
    tableName = tableName.lower()
    # Opening new cursor that will automatically close when function is done
    with connection.cursor() as cur:
        # Checking if a table with the specified wanted name already exists
        cur.execute("SELECT to_regclass('public.{}');".format(tableName))
        if cur.fetchall()[0][0] == None:
            # Creating the text used to specify the contents of the table
            tableContents = ", ".join([x for x in tableContentList])
            # Creating the table with the specified content
            cur.execute("CREATE TABLE {} ({});".format(tableName, tableContents))
            # Writing the changes to the database
            connection.commit()
        else:
            print("Table \"%s\" already exists, skipping it for now" % tableName)

# Function for writting OG tags to database
def writeOGTagsToDB(connection, OGTags, tableName):
    # Making sure the tablename is in all lowercase
    tableName = tableName.lower()
    # List to hold all the urls along with the profile names off the articles that haven't been scraped and saved in the database before so the whole article can be scraped
    newUrls = list()
    with connection.cursor() as cur:
        for newsSite in OGTags:
            # Looping through each collection of tags an creating a list inside the original list to hold articles from each news site
            newUrls.append([newsSite])
            for tags in OGTags[newsSite]:
                # Checking if the article is already stored in the database using the URL as that is probably not going to change and is uniqe
                cur.execute("SELECT exists (SELECT 1 FROM {} WHERE url = %s);".format(tableName), (tags['url'],))
                if cur.fetchall()[0][0] == False:
                    # Adding the url to list of new articles since it was not found in the database
                    newUrls[-1].append(tags['url'])
                    insertQuery = "INSERT INTO {} (title, description, url, image_url, profile, scraped) VALUES (%s, %s, %s, %s, %s, false);".format(tableName)
                    insertParameters = (tags['title'][:150], tags['description'][:350], tags['url'], tags['image'], newsSite)
                    cur.execute(insertQuery, insertParameters)
    connection.commit()
    # Return the list of urls not already in the database so they can be scraped
    return newUrls

def requestOGTagsFromDB(connection, tableName, profileList, limit):

    # Making sure the limit given is actually an intenger
    if type(limit) != int:
        raise Exception("An internal number given when trying to access the database appears to not be a number but instead: \"{}\"".format(limit))

    # The dictionary to hold the OG tags
    OGTagCollection = {}

    with connection.cursor() as cur:
        for profile in profileList:

            # As the profiles is each stored as a tuble when recieved from the database, one has to remember to take the first (and) only element of the tuble to work with
            OGTagCollection[profile] = []

            # Take the 10 newest articles from a specfic source that has been scraped
            cur.execute("SELECT * FROM {} WHERE profile=%s AND scraped=true ORDER BY id DESC LIMIT {};".format(tableName, limit), (profile,))
            queryResults = cur.fetchall()

            # Adding them to the final OG tag collection
            for result in queryResults:
                OGTagCollection[profile].append({
                         'profile'      : result[5],
                         'url'          : result[3],
                         'title'        : result[1],
                         'description'  : result[2],
                         'image'        : result[4]
                    })
    return OGTagCollection

def findUnscrapedArticles(connection, tableName, profileList):
    articleCollection = []

    with connection.cursor() as cur:
        # Go through each of the profiles one by one, so that the urls will be grouped by profile making scraping easier
        for profile in profileList:
            # Create a new list inside the "master" list with the first entry being the profile
            articleCollection.append([profile])
            # Finding all articles for that specific profile that hasn't yet been marked as scraped
            cur.execute("SELECT * FROM {} WHERE profile=%s AND scraped=false".format(tableName), (profile,))
            queryResults = cur.fetchall()

            # Adding the results one by one to the latest added list in the "master" list which is the one for the current profile
            for result in queryResults:
                # Only adding the url as that is the only needed part
                articleCollection[-1].append(result[3])

    return articleCollection

# Function for taking in a list of lists of articles with the first entry of each list being the name of the profile, and then removing all the articles that already has been saved in the database
def filterArticleURLList(connection, tableName, articleURLCollection):
    # The final list that will be returned in the same format as the articleURLCollection list, but with the already stored articles removed
    filteredArticleURLList = []

    with connection.cursor() as cur:
        for URLList in articleURLCollection:
            # The first element is always just the profile, so that should simply be copied to the filtered list
            filteredArticleURLList.append([URLList.pop(0)])
            for URL in URLList:
                # Checking if the article is already stored in the database using the URL as that is probably not going to change and is uniqe
                cur.execute("SELECT exists (SELECT 1 FROM {} WHERE url = %s);".format(tableName), (URL,))
                if cur.fetchall()[0][0] == False:
                    filteredArticleURLList[-1].append(URL)

    return filteredArticleURLList


def requestProfileListFromDB(connection, tableName):
    with connection.cursor() as cur:
        # Get the different profiles stored in the database
        cur.execute("SELECT DISTINCT profile FROM {};".format(tableName))
        profiles = [item for element in cur.fetchall() for item in element]
        return profiles


def markAsScraped(connection, URL):
    with connection.cursor() as cur:
        cur.execute("UPDATE articles SET scraped = true WHERE url = %s;", (URL,))
        connection.commit()
