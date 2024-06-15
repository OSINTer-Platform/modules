from typing import Any, Literal, TypedDict

ES_INDEX_CONFIGS: dict[str, dict[str, dict[str, Any]]] = {
    "ELASTICSEARCH_ARTICLE_INDEX": {
        "properties": {
            "title": {"type": "text"},
            "description": {"type": "text"},
            "content": {"type": "text"},
            "formatted_content": {"type": "text"},
            "url": {"type": "keyword"},
            "profile": {"type": "keyword"},
            "source": {"type": "keyword"},
            "image_url": {"type": "keyword"},
            "author": {"type": "keyword"},
            "inserted_at": {"type": "date"},
            "publish_date": {"type": "date"},
            "read_times": {"type": "unsigned_long"},
            "tags": {
                "type": "object",
                "properties": {
                    "interesting": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "keyword"},
                            "values": {"type": "keyword"},
                        },
                    },
                    "automatic": {"type": "keyword"},
                },
            },
            "similar": {"type": "keyword"},
            "ml": {
                "type": "object",
                "properties": {
                    "cluster": {"type": "keyword"},
                    "coordinates": {"type": "float"},
                    "labels": {"type": "keyword"},
                    "incident": {"type": "integer"},
                },
            },
        },
    },
    "ELASTICSEARCH_CLUSTER_INDEX": {
        "properties": {
            "nr": {"type": "integer"},
            "document_count": {"type": "integer"},
            "title": {"type": "text"},
            "description": {"type": "text"},
            "summary": {"type": "text"},
            "keywords": {"type": "keyword"},
            "documents": {"type": "keyword"},
            "dating": {"type": "date"},
        },
    },
    "ELASTICSEARCH_CVE_INDEX": {
        "properties": {
            "cve": {"type": "keyword"},
            "document_count": {"type": "integer"},
            "title": {"type": "text"},
            "description": {"type": "text"},
            "publish_date": {"type": "date"},
            "modified_date": {"type": "date"},
            "weaknesses": {"type": "keyword"},
            "status": {"type": "keyword"},
            "cvss2": {
                "type": "object",
                "properties": {
                    "source": {"type": "keyword"},
                    "base_severity": {"type": "keyword"},
                    "exploitability_score": {"type": "half_float"},
                    "impact_score": {"type": "half_float"},
                    "ac_insuf_info": {"type": "boolean"},
                    "obtain_all_privilege": {"type": "boolean"},
                    "obtain_user_privilege": {"type": "boolean"},
                    "obtain_other_privilege": {"type": "boolean"},
                    "user_interaction_required": {"type": "boolean"},
                    "cvss_data": {
                        "type": "object",
                        "properties": {
                            "version": {"type": "keyword"},
                            "vector_string": {"type": "keyword"},
                            "access_vector": {"type": "keyword"},
                            "access_complexity": {"type": "keyword"},
                            "authentication": {"type": "keyword"},
                            "confidentiality_impact": {"type": "keyword"},
                            "integrity_impact": {"type": "keyword"},
                            "availability_impact": {"type": "keyword"},
                            "base_score": {"type": "half_float"},
                        },
                    },
                },
            },
            "cvss3": {
                "type": "object",
                "properties": {
                    "source": {"type": "keyword"},
                    "exploitability_score": {"type": "half_float"},
                    "impact_score": {"type": "half_float"},
                    "cvss_data": {
                        "type": "object",
                        "properties": {
                            "version": {"type": "keyword"},
                            "vector_string": {"type": "keyword"},
                            "attack_vector": {"type": "keyword"},
                            "attack_complexity": {"type": "keyword"},
                            "privileges_required": {"type": "keyword"},
                            "user_interaction": {"type": "keyword"},
                            "scope": {"type": "keyword"},
                            "confidentiality_impact": {"type": "keyword"},
                            "integrity_impact": {"type": "keyword"},
                            "availability_impact": {"type": "keyword"},
                            "base_score": {"type": "half_float"},
                            "base_severity": {"type": "keyword"},
                        },
                    },
                },
            },
            "references": {
                "type": "object",
                "properties": {
                    "url": {"type": "keyword"},
                    "source": {"type": "keyword"},
                    "tags": {"type": "keyword"},
                },
            },
            "keywords": {"type": "keyword"},
            "documents": {"type": "keyword"},
            "dating": {"type": "date"},
        },
    },
}


class SearchTemplate(TypedDict):
    script: dict[Literal["source"], str]
    dictionary: dict[
        Literal["properties"], dict[str, bool | dict[str, dict[str, str] | str]]
    ]


ES_SEARCH_APPLICATIONS: dict[
    Literal["ARTICLES"], dict[Literal["template"], SearchTemplate]
] = {
    "ARTICLES": {
        "template": {
            "script": {
                "source": """{
    "query": {
        "bool": {
            "should": [
                {{#semantic_search}}
                    {
                        "text_expansion": {
                        "elastic_ml.title_tokens": {
                            "model_text": "{{semantic_search}}",
                            "model_id": "{{elser_model}}{{^elser_model}}.elser_model_2{{/elser_model}}",
                            "boost": 15
                        }
                        }
                    },
                    {
                        "text_expansion": {
                        "elastic_ml.description_tokens": {
                            "model_text": "{{semantic_search}}",
                            "model_id": "{{elser_model}}{{^elser_model}}.elser_model_2{{/elser_model}}",
                            "boost": 9
                        }
                        }
                    },
                    {
                        "text_expansion": {
                        "elastic_ml.content_tokens": {
                            "model_text": "{{semantic_search}}",
                            "model_id": "{{elser_model}}{{^elser_model}}.elser_model_2{{/elser_model}}",
                            "boost": 15
                        }
                        }
                    }
                {{/semantic_search}}
            ],
            "must": [
                {{#search_term}}
                    {
                        "simple_query_string": {
                            "query": "{{search_term}}",
                            "fields": [
                                "title^5",
                                "description^3",
                                "content^1"
                            ]
                        }
                    }
                {{/search_term}}
            ],
            "filter": [
                {{#filters}}
                    {{#toJson}}.{{/toJson}},
                {{/filters}}
                {{#ids.0}}
                    {
                        "terms": {
                            "_id": {{#toJson}}ids{{/toJson}}
                        }
                    },
                {{/ids.0}}

                {{#sources.0}}
                    {
                        "terms": {
                            "profile": {{#toJson}}sources{{/toJson}}
                        }
                    },
                {{/sources.0}}

                {{#cluster_id}}
                    {
                        "term": {
                            "ml.cluster": "{{cluster_id}}"
                        }
                    },
                {{/cluster_id}}

                {
                    "range": {
                        "publish_date": {
                            {{#first_date}}
                                "gte": "{{first_date}}"
                            {{/first_date}}

                            {{#first_date}}
                                {{#last_date}}
                                    ,
                                {{/last_date}}
                            {{/first_date}}

                            {{#last_date}}
                                "lte": "{{last_date}}"
                            {{/last_date}}
                        }
                    }
                }
            ]
        }
    },
    {{#highlight}}
        "highlight": {
            "pre_tags": ["{{highlight_symbol}}{{^highlight_symbol}}**{{/highlight_symbol}}"],
            "post_tags": ["{{highlight_symbol}}{{^highlight_symbol}}**{{/highlight_symbol}}"],
            "fields": {
                "title": {},
                "description": {},
                "content": {}
            }
        },
    {{/highlight}}

    "_source": {
        {{#include_fields.0}}
            "includes": {{#toJson}}include_fields{{/toJson}},
        {{/include_fields.0}}

        {{#exclude_fields.0}}
            "excludes": [{{#exclude_fields}}"{{.}}", {{/exclude_fields}} "elastic_ml"]
        {{/exclude_fields.0}}

        {{^exclude_fields}}
            "excludes": ["elastic_ml"]
        {{/exclude_fields}}
    },

    {{#sort.0}}
        "sort": {{#toJson}}sort{{/toJson}},
    {{/sort.0}}
    {{^sort.0}}
        "sort": [
            {{#sort_by}}
                {"{{sort_by}}": "{{sort_order}}{{^sort_order}}desc{{/sort_order}}"},
            {{/sort_by}}

            {{#semantic_search}}
                {"_score": "desc"},
            {{/semantic_search}}
            {{^semantic_search}}
                {{#search_term}}
                    {"_score": "desc"},
                {{/search_term}}
            {{/semantic_search}}

            {{#sort_tiebreaker}}
                "url",
            {{/sort_tiebreaker}}
            "_doc"
        ],
    {{/sort.0}}

    {{#search_after.0}}
        "search_after": {{#toJson}}search_after{{/toJson}},
    {{/search_after.0}}

    {{#aggregations}}
        "aggregations": {{#toJson}}aggregations{{/toJson}},
    {{/aggregations}}

    "from": "{{from}}{{^from}}0{{/from}}",
    "size": "{{limit}}{{^limit}}10{{/limit}}",
    "track_total_hits": "{{track_total}}{{^track_total}}false{{/track_total}}"
}"""
            },
            "dictionary": {
                "properties": {
                    "highlight_symbol": {"type": "string"},
                    "elser_model": {"type": "string"},
                    "semantic_search": {"type": "string"},
                    "search_term": {"type": "string"},
                    "cluster_id": {"type": "string"},
                    "first_date": {"type": "string"},
                    "last_date": {"type": "string"},
                    "sort_by": {"type": "string"},
                    "sort_order": {"type": "string"},
                    "ids": {"type": "array", "items": {"type": "string"}},
                    "sources": {"type": "array", "items": {"type": "string"}},
                    "include_fields": {"type": "array", "items": {"type": "string"}},
                    "exclude_fields": {"type": "array", "items": {"type": "string"}},
                    "filters": {"type": "array", "items": {"type": "object"}},
                    "sort": {"type": "array", "items": {"type": "object"}},
                    "search_after": {"type": "array"},
                    "from": {"type": "integer"},
                    "limit": {"type": "integer"},
                    "highlight": {"type": "boolean"},
                    "track_total": {"type": "boolean"},
                    "sort_tiebreaker": {"type": "boolean"},
                    "additionalProperties": False,
                }
            },
        }
    }
}
