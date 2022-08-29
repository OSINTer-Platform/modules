import os
import secrets
from pathlib import Path
import logging

from modules.elastic import (
    return_tweet_db_conn,
    return_article_db_conn,
    create_es_conn,
)


def load_secret_key():
    if os.path.isfile("./secret.key"):
        return Path("./secret.key").read_text()
    else:
        current_secret_key = secrets.token_urlsafe(256)
        with os.fdopen(
            os.open(Path("./secret.key"), os.O_WRONLY | os.O_CREAT, 0o400), "w"
        ) as file:
            file.write(current_secret_key)
        return current_secret_key


def load_elastic_url():
    if os.path.isfile("./.elasticsearch.url"):
        return Path("./.elasticsearch.url").read_text()
    else:
        return "http://localhost:9200"


def load_logger():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    log_handlers = {
        "printHandler": logging.StreamHandler(),
        "fileHandler": logging.FileHandler("logs/info.log"),
        "errorHandler": logging.FileHandler("logs/error.log"),
    }

    log_handlers["printHandler"].setLevel(logging.DEBUG)
    log_handlers["fileHandler"].setLevel(logging.INFO)
    log_handlers["errorHandler"].setLevel(logging.ERROR)

    logger_format = logging.Formatter(
        "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
    )

    for handler_name in log_handlers:
        log_handlers[handler_name].setFormatter(logger_format)
        logger.addHandler(log_handlers[handler_name])

    return logger


class BaseConfig:
    def __init__(self):
        self.ELASTICSEARCH_ARTICLE_INDEX = (
            os.environ.get("ARTICLE_INDEX") or "osinter_articles"
        )
        self.ELASTICSEARCH_TWEET_INDEX = (
            os.environ.get("TWEET_INDEX") or "osinter_tweets"
        )
        self.ELASTICSEARCH_USER_INDEX = os.environ.get("USER_INDEX") or "osinter_users"
        self.ELASTICSEARCH_URL = (
            os.environ.get("ELASTICSEARCH_URL") or load_elastic_url()
        )
        self.ELASTICSEARCH_CERT_PATH = (
            os.environ.get("ELASTICSEARCH_CERT_PATH") or "./.elasticsearch.crt"
            if os.path.isfile("./.elasticsearch.crt")
            else None
        )

        self.logger = load_logger()

        self.es_conn = create_es_conn(
            self.ELASTICSEARCH_URL, self.ELASTICSEARCH_CERT_PATH
        )

        self.es_tweet_client = return_tweet_db_conn(self)
        self.es_article_client = return_article_db_conn(self)

    def __getitem__(self, item):
        return getattr(self, item)


class BackendConfig(BaseConfig):
    def __init__(self):
        BaseConfig.__init__(self)
        self.TWITTER_CREDENTIAL_PATH = (
            os.environ.get("TWITTER_CREDENTIAL_PATH") or "./.twitter_keys.yaml"
            if os.path.isfile("./.twitter_keys.yaml")
            else None
        )


class FrontendConfig(BaseConfig):
    def __init__(self):
        BaseConfig.__init__(self)
        self.SECRET_KEY = os.environ.get("SECRET_KEY") or load_secret_key()

        self.ACCESS_TOKEN_EXPIRE_HOURS = int(
            os.environ.get("ACCESS_TOKEN_EXPIRE_HOURS") or 24
        )

        self.REMEMBER_ACCESS_TOKEN_EXPIRE_HOURS = int(
            os.environ.get("REMEMBER_ACCESS_TOKEN_EXPIRE_HOURS") or 24 * 30
        )

        self.JWT_ALGORITHMS = (os.environ.get("JWT_ALGORITHMS") or "HS256").split(" ")

        self.HTTPS = os.environ.get("ENABLE_HTTPS") or False
        self.EMAIL_SERVER_AVAILABLE = os.environ.get("EMAIL_SERVER_AVAILABLE") or False
