import logging
import os
import secrets
from typing import Any, TypedDict

from .elastic import create_es_conn, return_article_db_conn


def load_secret_key() -> str:
    if os.path.isfile("secret.key"):
        with open("secret.key", "r") as key_file:
            return key_file.read()
    else:
        current_secret_key: str = secrets.token_urlsafe(256)
        with os.fdopen(
            os.open("secret.key", os.O_WRONLY | os.O_CREAT, 0o400), "w"
        ) as key_file:
            key_file.write(current_secret_key)
        return current_secret_key


class LogHandler(TypedDict):
    logger: logging.Handler
    level: int


def configure_logger(name: str = __name__) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    log_handlers: dict[str, LogHandler] = {
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
    def __init__(self) -> None:
        self.ELASTICSEARCH_ARTICLE_INDEX = (
            os.environ.get("ARTICLE_INDEX") or "osinter_articles"
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

        self.es_article_client = return_article_db_conn(
            self.es_conn, self.ELASTICSEARCH_ARTICLE_INDEX
        )

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def __setitem__(self, item_name: str, item: Any) -> None:
        setattr(self, item_name, item)


class FrontendConfig(BaseConfig):
    def __init__(self) -> None:
        super().__init__()
        self.SECRET_KEY = os.environ.get("SECRET_KEY") or load_secret_key()

        self.ACCESS_TOKEN_EXPIRE_HOURS = int(
            os.environ.get("ACCESS_TOKEN_EXPIRE_HOURS") or 24
        )

        self.REMEMBER_ACCESS_TOKEN_EXPIRE_HOURS = int(
            os.environ.get("REMEMBER_ACCESS_TOKEN_EXPIRE_HOURS") or 24 * 30
        )

        self.JWT_ALGORITHMS = (os.environ.get("JWT_ALGORITHMS") or "HS256").split(" ")

        self.ENABLE_HTTPS = bool(os.environ.get("ENABLE_HTTPS")) or False
        self.ML_AVAILABLE = bool(os.environ.get("ML_AVAILABLE")) or False
        self.EMAIL_SERVER_AVAILABLE = (
            bool(os.environ.get("EMAIL_SERVER_AVAILABLE")) or False
        )

        self.COUCHDB_URL = (
            os.environ.get("COUCHDB_URL") or "http://admin:admin@localhost:5984/"
        )
        self.COUCHDB_NAME = os.environ.get("USER_DB_NAME") or "osinter_users"
