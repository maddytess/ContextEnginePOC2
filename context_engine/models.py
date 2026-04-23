from typing import Literal, Optional, Union
from pydantic import BaseModel, model_validator


# --- Nested manifest models ---

class ToolAffinity(BaseModel):
    allowed_tool_classes: list[str] = []
    preferred_tool_tags: list[str] = []
    execution_locations: list[str] = []


class ArtifactEffects(BaseModel):
    can_create: list[str] = []
    can_update: list[str] = []
    can_enrich: list[str] = []


class ActionSemantics(BaseModel):
    can_request_execution: bool = False  # always False — skills are readonly
    can_generate_plan_fragments: bool = False
    can_generate_bundle_hints: bool = False
    can_generate_playbook_candidates: bool = False


class Safety(BaseModel):
    safety_class: str = "advisory"
    requires_human_review_for: list[str] = []


class Evidence(BaseModel):
    emits_rationale: bool = True
    emits_confidence: bool = True


# --- Registration model (written by ADK, stored in Skill collection) ---

class SkillRecord(BaseModel):
    skill_id: str
    display_name: str
    owner_agent_id: str
    capability_id: str
    domain: str
    tier: str
    status: str
    tenant_id: Optional[str] = None
    purpose: str
    description: str
    capabilities: list[str] = []
    context_descriptions: list[str] = []
    output_type: str
    output_schema_ref: Optional[str] = None
    context_builder_ids: list[str]
    supported_context_types: list[str]
    tool_affinity: ToolAffinity = ToolAffinity()
    artifact_effects: ArtifactEffects = ArtifactEffects()
    action_semantics: ActionSemantics = ActionSemantics()
    safety: Safety = Safety()
    evidence: Evidence = Evidence()
    version: Optional[str] = None


# --- Search mode (Phase 2C) response ---

class SkillMatch(BaseModel):
    skill_id: str
    owner_agent_id: str
    domain: str
    confidence: float
    source: Literal["tenant", "global"]


class SearchSkillResponse(BaseModel):
    request_id: str
    matches: list[SkillMatch]


# --- Resolve mode (Phase 3) response ---

class SkillManifest(BaseModel):
    skill_id: str
    display_name: str
    owner_agent_id: str
    domain: str
    tier: str
    purpose: str
    description: str
    capabilities: list[str] = []
    context_descriptions: list[str] = []
    context_builder_ids: list[str]
    supported_context_types: list[str]
    tool_affinity: ToolAffinity = ToolAffinity()
    output_type: str
    output_schema_ref: Optional[str] = None
    artifact_effects: ArtifactEffects = ArtifactEffects()
    action_semantics: ActionSemantics = ActionSemantics()
    safety: Safety = Safety()
    evidence: Evidence = Evidence()
    version: Optional[str] = None
    source: Literal["tenant", "global"]


class ResolveSkillResponse(BaseModel):
    request_id: str
    skill: SkillManifest


# --- /resolve/skill request (both modes share one model) ---

class ResolveSkillRequest(BaseModel):
    tenant_id: Optional[str] = None
    request_id: str = ""
    mode: Literal["search", "resolve"]
    # search mode fields
    query: Optional[str] = None
    top_k: int = 5
    # resolve mode fields
    skill_id: Optional[str] = None
    owner_agent_id: Optional[str] = None

    @model_validator(mode="after")
    def _check_mode_fields(self) -> "ResolveSkillRequest":
        if self.mode == "search" and not self.query:
            raise ValueError("query is required for mode=search")
        if self.mode == "resolve" and not (self.skill_id and self.owner_agent_id):
            raise ValueError("skill_id and owner_agent_id are required for mode=resolve")
        return self


# --- Kept for internal backwards compat (classify_results, older callers) ---

class SkillSearchResult(BaseModel):
    skill_id: str
    owner_agent_id: str
    domain: str
    confidence: float
