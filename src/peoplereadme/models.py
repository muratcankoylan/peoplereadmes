"""Pydantic models for persona packages and pipeline artifacts.

These models are the canonical machine-readable schemas described in the PRD:
persona manifest (persona.json), traces, persona.lock, fidelity reports, and
feed events. JSON Schema for the persona object also lives in
schemas/persona.schema.json at the repo root.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class PersonaClass(StrEnum):
    SELF = "self"
    OTHER = "other"


class Consent(BaseModel):
    granted_by: str
    date: str
    scope: str


class IdentityBoundary(BaseModel):
    allowed: list[str]
    disallowed: list[str]


class Project(BaseModel):
    model_config = {"extra": "allow"}

    name: str
    category: str
    data_source: str
    method_summary: str
    risk_notes: list[str]
    primary_url: str | None = None
    interface_shape: str | None = None
    status: str | None = None


class Heuristic(BaseModel):
    model_config = {"extra": "allow"}

    id: str
    name: str
    description: str


class Safety(BaseModel):
    required_defaults: list[str]
    refusal_categories: list[str]


class PersonaManifest(BaseModel):
    """The persona.json object, validated by schemas/persona.schema.json."""

    id: str
    name: str
    scope: str
    persona_class: PersonaClass = Field(alias="class")
    consent: Consent | None = None
    allowed_exports: list[str] = Field(default_factory=list)
    identity_boundary: IdentityBoundary
    projects: list[Project]
    heuristics: list[Heuristic]
    safety: Safety

    model_config = {"populate_by_name": True}

    def model_dump_persona(self) -> dict:
        return self.model_dump(by_alias=True, exclude_none=True)


class TraceContext(BaseModel):
    type: Literal["thread", "diff", "news_item", "prior_state", "prompt_free"]
    content: str
    reconstruction_quality: float = Field(ge=0.0, le=1.0)


class TraceBehavior(BaseModel):
    content: str
    artifact_url: str | None = None


class TraceSource(BaseModel):
    url: str
    tier: str
    hash: str


class Trace(BaseModel):
    id: str
    persona_id: str
    kind: Literal[
        "post", "reply", "thread", "commit", "pr_review", "launch", "article", "decision"
    ]
    context: TraceContext
    behavior: TraceBehavior
    source: TraceSource
    timestamp: str
    split: Literal["train", "dev", "test", "live"]


class Compilability(BaseModel):
    score: int = Field(ge=0, le=100)
    band: Literal["not_compilable", "partial", "full"]


class CompiledEntry(BaseModel):
    model: str
    optimizer: str
    modules: list[str]
    cost_usd: float


class EvidenceSummary(BaseModel):
    items: int
    merkle_root: str
    latest: str


class TraceCounts(BaseModel):
    train: int
    dev: int
    test: int
    live: int


class ChangelogEntry(BaseModel):
    version: str
    trigger: str
    changes: list[str]


class PersonaLock(BaseModel):
    persona: str
    version: str
    persona_class: PersonaClass = Field(alias="class")
    rubric_version: int
    evidence: EvidenceSummary | None = None
    traces: TraceCounts | None = None
    compilability: Compilability | None = None
    compiled: list[CompiledEntry] = Field(default_factory=list)
    fidelity: dict | None = None
    changelog: list[ChangelogEntry] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class Indistinguishability(BaseModel):
    judge_accuracy: float
    score: float
    ci95: tuple[float, float]


class JudgeInfo(BaseModel):
    model: str
    human_agreement_kappa: float
    n_calibration_pairs: int


class FidelityReport(BaseModel):
    persona: str
    model: str
    rubric_version: int
    n_test: int
    indistinguishability: Indistinguishability
    dimensions: dict[str, float]
    judge: JudgeInfo
    baseline_delta: dict[str, str]
    timestamp: str


class FeedEvent(BaseModel):
    type: Literal[
        "evidence_absorbed", "live_eval", "drift_alert", "recompiled", "report_published"
    ]
    persona_id: str
    timestamp: str
    payload: dict = Field(default_factory=dict)
