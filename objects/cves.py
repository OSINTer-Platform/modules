from datetime import datetime
from typing import Literal
from typing_extensions import Annotated

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
)
from pydantic.alias_generators import to_camel

from .generic import AbstractDocument, AbstractPartialDocument


class FromCammel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class CVEHighlights(BaseModel):
    title: list[str] | None = None
    description: list[str] | None = None


class AbstractCVE(AbstractDocument):
    highlights: CVEHighlights | None = None


class CVEReference(BaseModel):
    url: str
    source: str
    tags: list[str] = []


class CVSS3Data(FromCammel):
    version: Literal["3.0", "3.1"]
    vector_string: str
    attack_vector: Literal["NETWORK", "ADJACENT_NETWORK", "LOCAL", "PHYSICAL"]
    attack_complexity: Literal["LOW", "HIGH"]
    privileges_required: Literal["NONE", "LOW", "HIGH"]
    user_interaction: Literal["NONE", "REQUIRED"]
    scope: Literal["UNCHANGED", "CHANGED"]
    confidentiality_impact: Literal["NONE", "LOW", "HIGH"]
    integrity_impact: Literal["NONE", "LOW", "HIGH"]
    availability_impact: Literal["NONE", "LOW", "HIGH"]
    base_score: float
    base_severity: Literal["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]


class CVSS3(FromCammel):
    source: str
    exploitability_score: float
    impact_score: float
    cvss_data: CVSS3Data


class CVSS2Data(FromCammel):
    version: Literal["2.0"]
    vector_string: str
    access_vector: Literal["NETWORK", "ADJACENT_NETWORK", "LOCAL"]
    access_complexity: Literal["LOW", "MEDIUM", "HIGH"]
    authentication: Literal["MULTIPLE", "SINGLE", "NONE"]
    confidentiality_impact: Literal["NONE", "PARTIAL", "COMPLETE"]
    integrity_impact: Literal["NONE", "PARTIAL", "COMPLETE"]
    availability_impact: Literal["NONE", "PARTIAL", "COMPLETE"]
    base_score: float


class CVSS2(FromCammel):
    source: str
    base_severity: Literal["LOW", "MEDIUM", "HIGH"]
    exploitability_score: float
    impact_score: float
    ac_insuf_info: bool
    obtain_all_privilege: bool
    obtain_user_privilege: bool
    obtain_other_privilege: bool
    user_interaction_required: bool | None = None
    cvss_data: CVSS2Data


class BaseCVE(AbstractCVE):
    cve: str
    document_count: int = 0

    title: str
    description: str
    keywords: list[str]

    publish_date: Annotated[datetime, AwareDatetime]
    modified_date: Annotated[datetime, AwareDatetime]

    weaknesses: list[str]

    status: Literal[
        "Awaiting Analysis",
        "Received",
        "Analyzed",
        "Rejected",
        "Modified",
        "Undergoing Analysis",
        "Deferred"
    ]

    cvss3: CVSS3 | None = None
    cvss2: CVSS2 | None = None


class FullCVE(BaseCVE):
    documents: set[str]
    dating: set[Annotated[datetime, AwareDatetime]]
    references: list[CVEReference]


class PartialCVE(AbstractCVE, AbstractPartialDocument):
    cve: int | None = None
    document_count: int | None = None

    title: str | None = None
    description: str | None = None
    keywords: list[str] | None = None

    publish_date: Annotated[datetime, AwareDatetime] | None = None
    modified_date: Annotated[datetime, AwareDatetime] | None = None

    weaknesses: list[str] | None = None

    status: (
        Literal[
            "Awaiting Analysis",
            "Received",
            "Analyzed",
            "Rejected",
            "Modified",
            "Undergoing Analysis",
        ]
        | None
    ) = None

    cvss3: CVSS3 | None = None
    cvss2: CVSS2 | None = None

    documents: set[str] | None = None
    dating: set[Annotated[datetime, AwareDatetime]] | None = None
    references: list[CVEReference]
