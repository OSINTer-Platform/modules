import os
import secrets
from pathlib import Path
import logging

from modules.elastic import (
    return_tweet_db_conn,
    return_article_db_conn,
    create_es_conn,
    ES_INDEX_CONFIGS,
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


def configure_logger(name: str = __name__) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    log_handlers = {
        "printHandler": {"logger": logging.StreamHandler(), "level": logging.DEBUG},
        "fileHandler": {
            "logger": logging.FileHandler(f"logs/{name}.info.log"),
            "level": logging.INFO,
        },
        "errorHandler": {
            "logger": logging.FileHandler(f"logs/{name}.error.log"),
            "level": logging.ERROR,
        },
    }

    logger_format = logging.Formatter(
        "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
    )

    for handler_name in log_handlers:
        log_handlers[handler_name]["logger"].setLevel(
            log_handlers[handler_name]["level"]
        )
        log_handlers[handler_name]["logger"].setFormatter(logger_format)
        logger.addHandler(log_handlers[handler_name]["logger"])

    return logger


class BaseConfig:
    def __init__(self):
        self.ELASTICSEARCH_ARTICLE_INDEX = (
            os.environ.get("ARTICLE_INDEX") or "osinter_articles"
        )
        self.ELASTICSEARCH_TWEET_INDEX = (
            os.environ.get("TWEET_INDEX") or "osinter_tweets"
        )
        self.ELASTICSEARCH_URL = (
            os.environ.get("ELASTICSEARCH_URL") or "http://localhost:9200"
        )
        self.ELASTICSEARCH_CERT_PATH = (
            os.environ.get("ELASTICSEARCH_CERT_PATH") or "./.elasticsearch.crt"
            if os.path.isfile("./.elasticsearch.crt")
            else None
        )

        self.es_conn = create_es_conn(
            self.ELASTICSEARCH_URL, self.ELASTICSEARCH_CERT_PATH
        )

        self.es_tweet_client = return_tweet_db_conn(self)
        self.es_article_client = return_article_db_conn(self)

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, item_name, item):
        setattr(self, item_name, item)


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

        for value_name in ["ENABLE_HTTPS", "EMAIL_SERVER_AVAILABLE", "ML_AVAILABLE"]:
            self[value_name] = bool(os.environ.get(value_name)) or False
