# Used for handling relative paths
from pathlib import Path

# For filling out template files like html overview template and markdown template
from string import Template

# For converting html to markdown
from markdownify import markdownify

# Used for creating the name of the markdown file in a safe maner
from OSINTmodules.OSINTmisc import fileSafeString

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
def createMDFile(sourceName, articleMetaTags, articleContent, articleTags, MDFilePath="./", intObjects = {}, manualTags=[]):

    # Define the title
    title = articleMetaTags['title']

    # Define the subtitle too, if it exist
    if articleMetaTags['description'] != "Unknown":
        subtitle = articleMetaTags['description']
    else:
        subtitle = ""

    # Convert the link for the article to markdown format
    MDSourceURL = "[article](" + articleMetaTags['url'] + ")"

    # Define the details section by creating markdown list with "+"
    MDDetails = ""
    detailLabels = ["Source: ", "Link: ", "Date: ", "Author: "]
    for i,detail in enumerate([sourceName, articleMetaTags['url'], articleMetaTags['publishDate'], articleMetaTags['author']]):
        MDDetails += "+ " + detailLabels[i] + detail + '\n'

    MDImage = "![Article Image](" + articleMetaTags['image'] + ")"

    # Convert the scraped article to markdown
    MDContent = markdownify(articleContent)

    MDIntObjects = ""
    for objectName in intObjects:
        MDIntObjects += f"#### {objectName}\n[[{']] [['.join(intObjects[objectName])}]]\n"

    MDManualTags = " ".join([ f"[[{tag}]]" for tag in manualTags])

    # And lastly, some tags
    MDTags = "[[" + "]] [[".join(articleTags) + "]] [[" + sourceName + "]]"

    # Creating a structure for the template
    contentList = {
        'title': title,
        'subtitle': subtitle,
        'information': MDDetails,
        'articleImage' : MDImage,
        'articleContent': MDContent,
        'manualTags' : MDManualTags,
        'tags': MDTags,
        'intObjects' : MDIntObjects
    }

    # Converting the title of the article to a string that can be used as filename and then opening the file in append mode (will create file if it doesn't exist)
    MDFileName = MDFilePath + fileSafeString(articleMetaTags['title']) + ".md"

    writeTemplateToFile(contentList, "./tools/markdownTemplate.md", MDFileName)

    # Returning the file name, so it's possible to locate the file
    return fileSafeString(articleMetaTags['title'])
