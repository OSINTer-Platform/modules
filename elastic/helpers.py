from elasticsearch import Elasticsearch

from ..objects import (
    BaseArticle,
    FullArticle,
    PartialArticle,
    BaseCluster,
    FullCluster,
    PartialCluster,
    BaseCVE,
    FullCVE,
    PartialCVE,
)
from .client import ElasticDB
from .queries import ArticleSearchQuery, CVESearchQuery, ClusterSearchQuery


def create_es_conn(
    addresses: str | list[str], verify_certs: bool, cert_path: None | str = None
) -> Elasticsearch:
    if cert_path:
        return Elasticsearch(
            addresses, ca_certs=cert_path, verify_certs=verify_certs, timeout=30
        )
    else:
        return Elasticsearch(addresses, verify_certs=verify_certs, timeout=30)


def return_article_db_conn(
    es_conn: Elasticsearch,
    index_name: str,
    ingest_pipeline: str | None,
    elser_model_id: str | None,
) -> ElasticDB[BaseArticle, PartialArticle, FullArticle, ArticleSearchQuery]:
    return ElasticDB[BaseArticle, PartialArticle, FullArticle, ArticleSearchQuery](
        es_conn=es_conn,
        index_name=index_name,
        ingest_pipeline=ingest_pipeline,
        unique_field="url",
        elser_model_id=elser_model_id,
        document_object_classes={
            "base": BaseArticle,
            "full": FullArticle,
            "partial": PartialArticle,
            "search_query": ArticleSearchQuery,
        },
    )


def return_cluster_db_conn(
    es_conn: Elasticsearch,
    index_name: str,
    ingest_pipeline: str | None,
    elser_model_id: str | None,
) -> ElasticDB[BaseCluster, PartialCluster, FullCluster, ClusterSearchQuery]:
    return ElasticDB[BaseCluster, PartialCluster, FullCluster, ClusterSearchQuery](
        es_conn=es_conn,
        index_name=index_name,
        ingest_pipeline=ingest_pipeline,
        unique_field="nr",
        elser_model_id=elser_model_id,
        document_object_classes={
            "base": BaseCluster,
            "full": FullCluster,
            "partial": PartialCluster,
            "search_query": ClusterSearchQuery,
        },
    )


def return_cve_db_conn(
    es_conn: Elasticsearch,
    index_name: str,
    ingest_pipeline: str | None,
    elser_model_id: str | None,
) -> ElasticDB[BaseCVE, PartialCVE, FullCVE, CVESearchQuery]:
    return ElasticDB[BaseCVE, PartialCVE, FullCVE, CVESearchQuery](
        es_conn=es_conn,
        index_name=index_name,
        ingest_pipeline=ingest_pipeline,
        unique_field="cve",
        elser_model_id=elser_model_id,
        document_object_classes={
            "base": BaseCVE,
            "full": FullCVE,
            "partial": PartialCVE,
            "search_query": CVESearchQuery,
        },
    )
