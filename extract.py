# For parsing html
from bs4 import BeautifulSoup

# For parsing application/ld+json
import json

import re

from dateutil.parser import parse
from datetime import timezone, datetime


# Used for matching the relevant information from LD+JSON
json_patterns = {
    "publish_date": re.compile(r'("datePublished": ")(.*?)(?=")'),
    "author": re.compile(r'("@type": "Person",.*?"name": ")(.*?)(?=")'),
}

# Function for using the class of a container along with the element type and class of desired html tag (stored in the contentDetails variable) to extract that specific tag. Data is found under the "scraping" class in the profiles.
def locate_content(css_selector, soup, recursive=True):
    try:
        return soup.select(css_selector, recursive=recursive)
    except:
        return BeautifulSoup("Unknown", "html.parser")


# Function used for removing certain tags with or without class from a soup. Takes in a list of element tag and class in the format: "tag,class;tag,class;..."
def clean_soup(soup, remove_selectors):
    for css_selector in remove_selectors.split(";"):
        for tag in soup.select(css_selector):
            tag.decompose()

    return soup


def extract_article_content(selectors, soup, delimiter="\n"):

    # Clean the textlist for unwanted html elements
    if selectors["remove"] != "":
        cleaned_soup = clean_soup(soup, selectors["remove"])
        text_list = locate_content(selectors["container"], cleaned_soup, recursive=True)
    else:
        text_list = locate_content(selectors["container"], soup, recursive=True)

    if text_list == "Unknown":
        raise Exception(
            "Wasn't able to fetch the text for the following soup:" + str(soup)
        )

    assembled_text = ""
    assembled_clear_text = ""
    text_tag_types = ["p", "span"] + [f"h{i}" for i in range(1, 7)]

    for text_soup in text_list:

        for text_tag in text_soup.find_all(text_tag_types):
            if text_tag.string:
                text_tag.string.replace_with(text_tag.string.strip())

        assembled_clear_text = assembled_clear_text + text_soup.get_text() + delimiter
        assembled_text = assembled_text + str(text_soup) + delimiter

    return assembled_text, assembled_clear_text


# Function for scraping meta information (like title, author and publish date) from articles. This both utilizes the OG tags and LD+JSON data, and while the proccess for extracting the OG tags is fairly simply as those is (nearly) always following the same standard, the LD+JSON data is a little more complicated. Here the data isn't parsed as JSON, but rather as a string where the relevant pieces of information is extracted using regex. It's probably ugly and definitly not the officially "right" way of doing this, but different placement of the information in the JSON object on different websites using different attributes made parsing the information from a python JSON object near impossible. As such, be warned that this function is not for the faint of heart
def extract_meta_information(page_soup, scraping_targets, site_url):
    OG_tags = {}

    for meta_tag in scraping_targets:
        OG_tags[meta_tag] = None

        if not scraping_targets[meta_tag]:
            continue

        try:
            tag_selector, tag_field = scraping_targets[meta_tag].split(";")
        except ValueError:
            tag_selector = scraping_targets[meta_tag]

            if "meta" in tag_selector:
                tag_field = "content"
            elif "datetime" in tag_selector:
                tag_field = "datetime"
            else:
                tag_field = None

        try:
            tag = page_soup.select(tag_selector)[0]
        except IndexError:
            continue

        if tag_field:
            OG_tags[meta_tag] = tag.get(tag_field)
        else:
            OG_tags[meta_tag] = tag.text

    if OG_tags["author"] == None or OG_tags["publish_date"] == None:

        # Use ld+json to extract extra information not found in the meta OG tags like author and publish date
        json_script_tags = page_soup.find_all("script", {"type": "application/ld+json"})

        for script_tag in json_script_tags:
            # Converting to and from JSON to standardize the format to avoid things like line breaks and excesive spaces at the end and start of line. Will also make sure there spaces in the right places between the keys and values so it isn't like "key" :"value" and "key  : "value" but rather "key": "value" and "key": "value".
            try:
                script_tag_string = json.dumps(json.loads("".join(script_tag.contents)))
            except json.decoder.JSONDecodeError:
                pass

            for pattern in json_patterns:
                if OG_tags[pattern] == None:
                    detail_match = json_patterns[pattern].search(script_tag_string)
                    if detail_match != None:
                        # Selecting the second group, since the first one is used to located the relevant information. The reason for not using lookaheads is because python doesn't allow non-fixed lengths of those, which is needed when trying to select pieces of text that doesn't always conform to a standard.
                        OG_tags[pattern] = detail_match.group(2)

    if OG_tags["image_url"] == None:
        OG_tags["image_url"] = f"{site_url}/favicon.ico"

    if OG_tags["publish_date"]:
        OG_tags["publish_date"] = parse(OG_tags["publish_date"]).astimezone(
            timezone.utc
        )
    else:
        OG_tags["publish_date"] = datetime.now(timezone.utc)

    return OG_tags
