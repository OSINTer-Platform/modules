# Used for sleeping
import time

# Used for determining the path to the geckodriver
from pathlib import Path

# For manipulating lists in a way that's less memory intensive
import itertools

# Used to gather the urls from the articles, by reading a RSS feed
import feedparser

# Used for scraping static pages
import requests

# Used for dynamically scraping pages that aren't static
from selenium import webdriver

# Used for running the browser headlessly
from selenium.webdriver.firefox.options import Options

# For parsing html
from bs4 import BeautifulSoup

from modules.misc import cat_url

# Used for selecting a random elemen from browserHeaders list
import random

import logging

logger = logging.getLogger("osinter")

# Used for simulating an actual browser when scraping for OGTags, stolen from here
browser_headers_list = [
    # Firefox 77 Mac
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:77.0) Gecko/20100101 Firefox/77.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.google.com/",
        "Connection": "keep-alive",
    },
    # Firefox 77 Windows
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:77.0) Gecko/20100101 Firefox/77.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.google.com/",
    },
    # Chrome 83 Mac
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Referer": "https://www.google.com/",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
    },
    # Chrome 83 Windows
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Referer": "https://www.google.com/",
        "Accept-Language": "en-US,en;q=0.9",
    },
]

# Simple function for scraping static page and converting it to a soup
def scrape_web_soup(url):
    current_headers = random.choice(browser_headers_list)
    page_source = requests.get(url, headers=current_headers)
    if page_source.status_code != 200:

        print(f"Error: Status code {page_source.status_code}, skipping URL {url}")
        return None
    return BeautifulSoup(page_source.content, "html.parser")


# Scraping targets is element and class of element in which the target url is stored, and the profile_name is prepended on the list, to be able to find the profile again when it's needed for scraping
def scrape_article_urls(root_url, front_page_url, scraping_targets, profile_name):

    print(scraping_targets["container_list"])
    # Getting a soup for the website
    front_page_soup = (
        scrape_web_soup(front_page_url).select(scraping_targets["container_list"])[0]
        if scraping_targets["container_list"] != []
        else scrape_web_soup(front_page_url)
    )

    article_urls = [
        cat_url(
            root_url,
            link.get("href")
            if scraping_targets["link_containers"] == ""
            else link.select(scraping_targets["links"])[0].get("href"),
        )
        for link in itertools.islice(
            front_page_soup.select(
                scraping_targets["link_containers"]
                if scraping_targets["link_containers"] != ""
                else scraping_targets["links"]
            ),
            10,
        )
    ]

    return article_urls


# Function for scraping a list of recent articles using the url to a RSS feed
def get_article_urls_from_rss(rss_url, profile_name):
    # Parse the whole RSS feed
    rss_feed = feedparser.parse(rss_url)

    # List for holding the urls from the RSS feed
    article_urls = []

    # Extracting the urls only, as these are the only relevant information. Also only take the first 10, if more is given to only get the newest articles
    for entry in itertools.islice(rss_feed.entries, 10):
        article_urls.append(entry.id)

    return article_urls


def scrape_page_dynamic(page_url, scraping_types, load_time=3, headless=True):

    # Setting the options for running the browser driver headlessly so it doesn't pop up when running the script
    driver_options = Options()
    driver_options.headless = headless

    # Setup the webdriver with options
    with webdriver.Firefox(
        options=driver_options,
        executable_path=Path("./tools/geckodriver").resolve(),
        log_path=Path("./logs/geckodriver.log").resolve(),
    ) as driver:

        # Actually scraping the page
        driver.get(page_url)

        # Sleeping a pre-specified time to let the driver actually render the page properly
        time.sleep(load_time)

        for scraping_type in scraping_types:
            current_type = scraping_type.split(":")
            if current_type[0] == "JS":
                driver.execute_script(
                    Path(f"./profiles/js_injections/{current_type[1]}.js").read_text()
                )
                while driver.execute_script("return document.osinterReady") == False:
                    time.sleep(1)

        # Getting the source code for the page
        page_source = driver.page_source

        return page_source
