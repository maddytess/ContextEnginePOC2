from pydantic import BaseModel
from typing import Optional


class SkillRecord(BaseModel):
    skill_id: str
    display_name: str
    owner_agent_id: str
    capability_id: str
    domain: str
    tier: str
    status: str
    tenant_id: Optional[str]
    purpose: str
    description: str
    output_type: str
    context_builder_ids: list[str]
    supported_context_types: list[str]


class SkillSearchResult(BaseModel):
    skill_id: str
    owner_agent_id: str
    domain: str
    confidence: float
