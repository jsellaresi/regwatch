from pydantic import BaseModel, Field
from typing import Literal


class Gap(BaseModel):
    regulation_ref: str = Field(description="Formato exacto: 'GDPR Art. 17(1)'")
    gap_description: str
    risk_level: Literal["HIGH", "MEDIUM", "LOW"]
    remediation: str
    confidence: float = Field(ge=0.0, le=1.0)


class GapReport(BaseModel):
    gaps: list[Gap] = Field(default_factory=list)


class JudgeScores(BaseModel):
    legal_accuracy: int = Field(ge=0, le=10)
    citation_quality: int = Field(ge=0, le=10)
    actionability: int = Field(ge=0, le=10)
    overall_score: float = Field(ge=0.0, le=10.0)
    critical_issues: list[str] = Field(default_factory=list)
    approved: bool
