from typing import TypedDict


class TermAggBucket(TypedDict):
    key: str
    doc_count: int


class TermAgg(TypedDict):
    doc_count_error_upper_bound: int
    sum_other_doc_count: int
    buckets: list[TermAggBucket]


class SignificantTermAggBucket(TypedDict):
    key: str
    doc_count: int
    bg_count: int
    score: int


class SignificantTermAgg(TypedDict):
    doc_count: int
    bg_count: int
    buckets: list[SignificantTermAggBucket]
