from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class IndianCollege(BaseModel):
    id: str
    name: str
    short_name: str
    category: str
    state: str
    city: str
    domain: str
    admissions_portal: str
    entrance_exams: list[str] = Field(default_factory=list)
    counseling_body: str
    country: str = "India"


# Backward-compatibility alias
class University(BaseModel):
    name: str
    country: str = "India"
    domain: str
    id: str | None = None
    short_name: str | None = None
    category: str | None = None
    state: str | None = None
    city: str | None = None
    admissions_portal: str | None = None
    entrance_exams: list[str] = Field(default_factory=list)
    counseling_body: str | None = None


class Requirement(BaseModel):
    id: str
    title: str
    description: str
    required: bool = True
    document_type: str
    check: str = "present"
    value: float | None = None
    source_url: str
    source_category: Literal["official", "government", "community"] = "official"
    source_name: str = "Official College Portal"


class RequirementChecklist(BaseModel):
    requirement_set_id: str
    university_name: str
    university_domain: str
    application_type: str
    college_category: str = "Engineering"
    counseling_body: str | None = None
    requirements: list[Requirement]
    disclaimer: str
    sources_found: list[dict[str, str]] = Field(default_factory=list)


class ExtractedDocument(BaseModel):
    filename: str
    document_type: str
    extracted_text: str
    fields: dict[str, str] = Field(default_factory=dict)


class ValidationResult(BaseModel):
    rule_id: str
    title: str
    status: str
    message: str
    evidence: str | None = None
    source_url: str | None = None
    source_category: str | None = None
    source_name: str | None = None


class VerificationResponse(BaseModel):
    verification_id: str
    applicant_name: str
    university_name: str
    application_type: str
    readiness_score: int
    results: list[ValidationResult]
    suggestions: list[str]
    documents: list[ExtractedDocument]
    audit_trail: list[str]
    report_url: str
    created_at: datetime