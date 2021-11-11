# For generating random numbers for scrambling the OG tags
import random

# Used for substituting characthers from text
import re

# Used for sleeping
import time

# Used for scraping web papges in parrallel (multithreaded)
from concurrent.futures import ThreadPoolExecutor


from OSINTmodules.OSINTscraping import scrapeWebSoup

# Used for scraping the needed OG tags
from OSINTmodules.OSINTextract import extractMetaInformation



# Function for collecting OG tags from a list of lists with the URLs for different news sites, with the first element in each of the lists in the list being the name of the profile. Will run in parallel
def collectAllOGTags(articleURLLists):
    # The final collection for holding the scraped OG tags
    OGTagCollection = {}

    # A temporary list for storing the futures generated when launching tasks in parallel
    futureList = []

    # Launching a thread pool executor for parallisation
    with ThreadPoolExecutor(max_workers = 30) as executor:

        # Looping through the list of urls scraped from the front page of a couple of news sites
        for URLList in articleURLLists:

            # Getting the name of the current profile, which is stored in the start of each of the lists with URLs for the different news sites
            currentProfile = URLList.pop(0)

            # Appending a list to the futures list, containing two elements: The name of the profile for the scraped article, and the future itself
            futureList.append([currentProfile, executor.submit(collectOGTagsFromNewsSite, currentProfile, URLList)])

        # Looping through all the futures representing the parallel tasks that are running in the background, checking if they are done and then store the result and remove them from the list if they are
        while futureList != []:
            for future in futureList:
                if future[1].done():
                    OGTagCollection[future[0]] = future[1].result()[future[0]]
                    futureList.remove(future)
            time.sleep(0.1)

    return OGTagCollection


# Function used for ordering the OG tags into a dictionary based on source, that can then be used later. Will only gather articles from one news site at a time
def collectOGTagsFromNewsSite(profileName, URLList):

    # Creating the data structure that will store the OG tags
    OGTagCollection = {}
    OGTagCollection[profileName] = []

    # Looping through each URL for the articles, scraping the OG tags for those articles and then adding them to the final data structure
    for URL in URLList:
        pageSoup = scrapeWebSoup(URL)
        # In case the page that has been scraped returned anything but http response 200, the pagesoup returned will have the value none, which means we have to skip it
        if pageSoup != None:
            OGTags = extractMetaInformation(pageSoup)

            OGTagCollection[profileName].append({
                'profile'       : profileName,
                'url'           : URL,
                'title'         : re.sub(r'"', '', OGTags['og:title']),
                'description'   : re.sub(r'"', '', OGTags['og:description']),
                'image_url'     : OGTags['og:image'],
                'author'        : OGTags['author'],
                'publish_date'  : OGTags['publish_date']
            })

    return OGTagCollection
