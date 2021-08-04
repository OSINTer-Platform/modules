# Used for handling relative paths
from pathlib import Path

# For filling out template files like html overview template and markdown template
from string import Template

# For converting html to markdown
from markdownify import markdownify

# Used for creating the name of the markdown file in a safe maner
from OSINTmodules.OSINTmisc import fileSafeString

from OSINTmodules.OSINTwebserver import generatePageDetails

# Function for writing details from a template to a file
def writeTemplateToFile(contentList, templateFile, newFilePath):
    # Open the template for the given file
    with open(Path(templateFile), "r") as source:
        # Read the template file
        sourceTemplate = Template(source.read())
        # Load the template but fill in the values from contentList
        filledTemplate = sourceTemplate.substitute(contentList)
        # Write the filled template to a new file that can then be used
        with open(Path(newFilePath), "w") as newF:
            newF.write(filledTemplate)

# Function for taking in some details about an articles and creating a markdown file with those
def createMDFile(sourceName, sourceURL, articleDetails, articleContent, articleTags, MDFilePath="./"):

    # Define the title
    title = articleDetails[0]

    # Define the subtitle too, if it exist
    if articleDetails[1] != "Unknown":
        subtitle = articleDetails[1]
    else:
        subtitle = ""

    # Convert the link for the article to markdown format
    MDSourceURL = "[article](" + sourceURL + ")"

    # Define the details section by creating markdown list with "+"
    MDDetails = ""
    detailLabels = ["Source: ", "Link: ", "Date: ", "Author: "]
    for i,detail in enumerate([sourceName, MDSourceURL, articleDetails[2], articleDetails[3]]):
        MDDetails += "+ " + detailLabels[i] + detail + '\n'

    # Convert the scraped article to markdown
    MDContent = markdownify(articleContent)

    # And lastly, some tags
    MDTags = "[[" + "]] [[".join(articleTags) + "]] [[" + sourceName + "]]"

    # Creating a structure for the template
    contentList = {
        'title': title,
        'subtitle': subtitle,
        'information': MDDetails,
        'articleContent': MDContent,
        'tags': MDTags
    }

    # Converting the title of the article to a string that can be used as filename and then opening the file in append mode (will create file if it doesn't exist)
    MDFileName = MDFilePath + fileSafeString(articleDetails[0]) + ".md"

    writeTemplateToFile(contentList, "./tools/markdownTemplate.md", MDFileName)

    # Returning the file name, so it's possible to locate the file
    return fileSafeString(articleDetails[0])

# Function used for constructing the CSS and HTML needed for the front end used for presenting the users with the different articles
def constructArticleOverview(OGTags, overviewPath="./"):

    HTML, CSS, JS = generatePageDetails(OGTags)

    # Make template for HTML file
    writeTemplateToFile({'CSS': CSS, 'HTML': HTML}, "./webFront/index.html", overviewPath + "overview.html")

    # Make the template for the JS file
    writeTemplateToFile({'variables': JS}, "./webFront/switchOverview.js", overviewPath + "script.js")
