import logging
import os
from typing import Any, TypedDict

from .elastic import (
    create_es_conn,
    return_article_db_conn,
    return_cluster_db_conn,
    return_cve_db_conn,
)


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
        self.OPENAI_KEY = os.environ.get("OPENAI_KEY", None)
        self.OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        self.OPENAI_TOKEN_LIMIT = int(os.environ.get("OPENAI_TOKEN_LIMIT", 16000))

        self.NVD_KEY = os.environ.get("NVD_KEY", None)

        self.ELASTICSEARCH_ARTICLE_INDEX = (
            os.environ.get("ARTICLE_INDEX") or "osinter_articles"
        )
        self.ELASTICSEARCH_CLUSTER_INDEX = (
            os.environ.get("CLUSTER_INDEX") or "osinter_clusters"
        )
        self.ELASTICSEARCH_CVE_INDEX = os.environ.get("CVE_INDEX") or "osinter_cves"
        self.ELASTICSEARCH_URL = (
            os.environ.get("ELASTICSEARCH_URL") or "http://localhost:9200"
        )
        self.ELASTICSEARCH_CERT_PATH = (
            os.environ.get("ELASTICSEARCH_CERT_PATH") or "./.elasticsearch.crt"
            if os.path.isfile("./.elasticsearch.crt")
            else None
        )
        self.ELASTICSEARCH_VERIFY_TLS = bool(
            os.environ.get("ELASTICSEARCH_TLS", bool(self.ELASTICSEARCH_CERT_PATH))
        )

        self.ELASTICSEARCH_ELSER_PIPELINE = os.environ.get("ELSER_PIPELINE", None)
        self.ELASTICSEARCH_ELSER_ID = os.environ.get("ELSER_ID", None)
        self.ELSER_AVAILABLE = bool(self.ELASTICSEARCH_ELSER_ID) and bool(
            self.ELASTICSEARCH_ELSER_PIPELINE
        )

        self.COUCHDB_URL, self.COUCHDB_NAME = self.get_couchdb_details()

        self.es_conn = create_es_conn(
            self.ELASTICSEARCH_URL,
            self.ELASTICSEARCH_VERIFY_TLS,
            self.ELASTICSEARCH_CERT_PATH,
        )

        self.es_article_client = return_article_db_conn(
            self.es_conn,
            self.ELASTICSEARCH_ARTICLE_INDEX,
            self.ELASTICSEARCH_ELSER_PIPELINE,
            self.ELASTICSEARCH_ELSER_ID,
        )

        self.es_cluster_client = return_cluster_db_conn(
            self.es_conn, self.ELASTICSEARCH_CLUSTER_INDEX, None, None
        )

        self.es_cve_client = return_cve_db_conn(
            self.es_conn, self.ELASTICSEARCH_CVE_INDEX, None, None
        )

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def __setitem__(self, item_name: str, item: Any) -> None:
        setattr(self, item_name, item)

    @staticmethod
    def get_couchdb_details() -> tuple[str, str]:
        """
        Returns tuble[COUCHDB_URL, COUCHDB_NAME]
        """
        COUCHDB_URL = (
            os.environ.get("COUCHDB_URL") or "http://admin:admin@localhost:5984/"
        )

        COUCHDB_NAME = os.environ.get("USER_DB_NAME") or "osinter_users"

        return COUCHDB_URL, COUCHDB_NAME
