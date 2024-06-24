from typing import Any
from elasticsearch import Elasticsearch
from transformers import BertTokenizer

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
from .client import ElasticDB, PrePipeline
from .queries import ArticleSearchQuery, CVESearchQuery, ClusterSearchQuery

bert_tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")


# Needs to be global to allow pickling for multiprocessing
def chunk_for_elser(doc: dict[str, Any]) -> dict[str, Any]:
    def chunk(
        text: str, chunk_size: int = 500, overlap_ratio: float = 0.5
    ) -> list[str]:
        step_size = round(chunk_size * (1 - overlap_ratio))

        # Setting max length to silence warnings about model only being able to handle 512 tokens
        tokens = bert_tokenizer.encode(text, max_length=0, truncation=True)
        tokens = tokens[1:-1]  # remove special beginning and end tokens

        result = []
        for i in range(0, len(tokens), step_size):
            end = i + chunk_size
            chunk = tokens[i:end]
            result.append(bert_tokenizer.decode(chunk))
            if end >= len(tokens):
                break

        return result

    if "content" in doc:
        if not "embeddings" in doc:
            doc["embeddings"] = {}

        doc["embeddings"]["content_chunks"] = [
            {"text": chnk} for chnk in chunk(doc["content"])
        ]

    return doc


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
        pre_pipelines=[
            PrePipeline(
                name="Chunk for elser",
                call=chunk_for_elser,
                requires_elser=True,
                requires_pipeline=True,
            )
        ],
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
