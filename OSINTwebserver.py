# Used for checking if theres already a query paramter in the url
from urllib import parse

from OSINTmodules import OSINTdatabase

# Function for generating the needed source code for the front page displaying the articles
def generatePageDetails(OGTags):
    HTML = ""
    CSS = ""
    JS = ""
    # The JS variable contains the list for the following variables: articleURLs imageURLs, titles and descriptions. The string hardcoded into these right here is the name of the javascript arrays that each of these list in the JSList will create
    JSList = [["articleURLs"],["imageURLs"],["titles"],["descriptions"]]
    for i,article in enumerate(OGTags):
        # If there's already a paramater in the url it will add the OSINTerProfile parameter with &, otherwise it will simply use ?
        # OSINTerProfile is used when scraping the website, to know what profile is associated with the article the user choose
        URL = article['url'] + ('&' if parse.urlparse(article['url']).query else '?') + "OSINTerProfile=" + article['profile']
        HTML += '<article id="card-' + str(i) + '"><a href="' + URL + '" target="_blank"><h1>' + article['title'] + '</h1></a></article>\n'
        CSS += '#card-' + str(i) + '::before { background-image: url("' + article['image'] + '");}\n'
        JSList[0].append(URL)
        JSList[1].append(article['image'])
        JSList[2].append(article['title'])
        JSList[3].append(article['description'])

    for currentJSList in JSList:
        JS += 'const ' + currentJSList.pop(0) + ' = [ "' + currentJSList.pop(0) + '"' + "".join([(', "' + element + '"') for element in currentJSList]) + ' ]\n'

    return HTML, CSS, JS


def generateSourcesList(sourceDetailsList):
    HTML = ""

    for source in sourceDetailsList:
        HTML += '<label for="{}-checkbox">\n'.format(source)
        HTML += '<article class="leaderboard__profile">\n'
        HTML += '<img src="{}" alt="{}" class="leaderboard__picture">\n'.format(sourceDetailsList[source]['image'], sourceDetailsList[source]['name'])
        HTML += '<span class="leaderboard__name">{}</span>\n'.format(sourceDetailsList[source]['name'])
        HTML += '<input id="{}-checkbox" type="checkbox" class="checkbox" name="profiles" value="{}">\n'.format(source, source)
        HTML += '</article>\n'
        HTML += '</label>\n\n'

    return HTML


def verifyProfiles(profiles, connection, tableName):
    # Getting the profiles that are actually stored
    storedProfiles = OSINTdatabase.requestProfileListFromDB(connection, tableName)
    # Looping through the profiles we want to confirm are matching those stored
    for profile in profiles:
        if profile not in storedProfiles:
            return profile

    return True
