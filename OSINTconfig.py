import os
import secrets
from pathlib import Path
import logging

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

    printHandler = logging.StreamHandler()
    fileHandler = logging.FileHandler('log')

    loggerFormat = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
    printHandler.setFormatter(loggerFormat)
    fileHandler.setFormatter(loggerFormat)

    logger.addHandler(printHandler)
    logger.addHandler(fileHandler)

    return logger

class backendConfig():
    ELASTICSEARCH_ARTICLE_INDEX = os.environ.get("ARTICLE_INDEX") or "osinter_articles"
    ELASTICSEARCH_USER_INDEX = os.environ.get("USER_INDEX") or "osinter_users"
    ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL') or loadElasticURL()
    ELASTICSEARCH_CERT_PATH = os.environ.get('ELASTICSEARCH_CERT_PATH') or "./.elasticsearch.crt" if os.path.isfile("./.elasticsearch.crt") else None

    logger = loadLogger()

class frontendConfig(backendConfig):
    SECRET_KEY = os.environ.get('SECRET_KEY') or loadSecretKey()
