# Used for checking if theres already a query paramter in the url
from urllib import parse

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
        HTML += '<article id="card-' + str(i) + '"><a href="' + URL + '"><h1>' + article['title'] + '</h1></a></article>\n'
        CSS += '#card-' + str(i) + '::before { background-image: url("' + article['image'] + '");}\n'
        JSList[0].append(URL)
        JSList[1].append(article['image'])
        JSList[2].append(article['title'])
        JSList[3].append(article['description'])

    for currentJSList in JSList:
        JS += 'const ' + currentJSList.pop(0) + ' = [ "' + currentJSList.pop(0) + '"' + "".join([(', "' + element + '"') for element in currentJSList]) + ' ]\n'

    return HTML, CSS, JS
