import os
import secrets
from pathlib import Path
import logging

from OSINTmodules.OSINTelastic import returnTweetDBConn, returnArticleDBConn

def loadSecretKey():
    if os.path.isfile("./secret.key"):
        return Path("./secret.key").read_text()
    else:
        currentSecretKey = secrets.token_urlsafe(256)
        with os.fdopen(os.open(Path("./secret.key"), os.O_WRONLY | os.O_CREAT, 0o400), 'w') as file:
            file.write(currentSecretKey)
        return currentSecretKey

def loadElasticURL():
    if os.path.isfile("./.elasticsearch.url"):
        return Path("./.elasticsearch.url").read_text()
    else:
        return "http://localhost:9200"

def loadLogger():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    logHandlers = {
        "printHandler" : logging.StreamHandler(),
        "fileHandler" : logging.FileHandler('logs/info.log'),
        "errorHandler" : logging.FileHandler('logs/error.log')
    }

    logHandlers["printHandler"].setLevel(logging.DEBUG)
    logHandlers["fileHandler"].setLevel(logging.INFO)
    logHandlers["errorHandler"].setLevel(logging.ERROR)

    loggerFormat = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s')

    for handlerName in logHandlers:
        logHandlers[handlerName].setFormatter(loggerFormat)
        logger.addHandler(logHandlers[handlerName])

    return logger

class baseConfig():
    def __init__(self):
        self.ELASTICSEARCH_ARTICLE_INDEX = os.environ.get("ARTICLE_INDEX") or "osinter_articles"
        self.ELASTICSEARCH_TWEET_INDEX = os.environ.get("TWEET_INDEX") or "osinter_tweets"
        self.ELASTICSEARCH_USER_INDEX = os.environ.get("USER_INDEX") or "osinter_users"
        self.ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL') or loadElasticURL()
        self.ELASTICSEARCH_CERT_PATH = os.environ.get('ELASTICSEARCH_CERT_PATH') or "./.elasticsearch.crt" if os.path.isfile("./.elasticsearch.crt") else None

        self.logger = loadLogger()

        self.esTweetClient = returnTweetDBConn(self)
        self.esArticleClient = returnArticleDBConn(self)

class backendConfig(baseConfig):
    def __init__(self):
        baseConfig.__init__(self)
        self.TWITTER_CREDENTIAL_PATH = os.environ.get('TWITTER_CREDENTIAL_PATH') or "./.twitter_keys.yaml" if os.path.isfile("./.twitter_keys.yaml") else None


    def __getitem__(self, item):
        return getattr(self, item)

class frontendConfig(baseConfig):
    def __init__(self):
        baseConfig.__init__(self)
        SECRET_KEY = os.environ.get('SECRET_KEY') or loadSecretKey()
