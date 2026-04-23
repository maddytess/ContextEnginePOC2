from typing import Literal, Optional
from pydantic import BaseModel, model_validator


# --- Agent manifest models (parsed from agent.yaml) ---

class AgentOwner(BaseModel):
    team: str
    contact: str


class AgentClassification(BaseModel):
    domain: str
    product_scope: str = "horizontal"
    tier_support: list[str] = ["basic"]


class AgentSkills(BaseModel):
    exported_skill_ids: list[str] = []
    hidden_skill_ids: list[str] = []


class PlaybookParameter(BaseModel):
    name: str
    type: str
    description: str = ""
    example: str = ""


class PlaybookOptionalParameter(BaseModel):
    name: str
    type: str
    default: object = None


class PlaybookParameterSchema(BaseModel):
    mandatory: list[PlaybookParameter] = []
    optional: list[PlaybookOptionalParameter] = []


class PlaybookContext(BaseModel):
    context_descriptions: list[str] = []
    supported_context_types: list[str] = []
    declared_context_builders: list[str] = []


class AgentPlaybooks(BaseModel):
    can_trigger: bool = False
    can_generate_candidate: bool = False
    owned_playbook_ids: list[str] = []
    context: Optional[PlaybookContext] = None
    target_language: str = "python"
    parameter_schema: Optional[PlaybookParameterSchema] = None
    approach_hints: list[str] = []
    rollback_support: bool = False
    execution_timeout: int = 600


class AgentContext(BaseModel):
    context_descriptions: list[str] = []
    supported_context_types: list[str] = []
    declared_context_builders: list[str] = []


class ReadonlyToolAccess(BaseModel):
    allowed_tool_classes: list[str] = []
    preferred_tool_tags: list[str] = []
    execution_locations: list[str] = []


class WriteToolAccess(BaseModel):
    allowed_tool_classes: list[str] = []
    preferred_tool_tags: list[str] = []
    requires_human_review: bool = True


class AgentToolAccess(BaseModel):
    readonly_tools: ReadonlyToolAccess = ReadonlyToolAccess()
    write_tools: Optional[WriteToolAccess] = None


class AgentDomainKnowledge(BaseModel):
    lens: list[str] = []
    expert_graph: list[str] = []


class AgentArtifacts(BaseModel):
    can_read: list[str] = []
    can_create: list[str] = []
    can_update: list[str] = []
    can_enrich: list[str] = []


class AgentPolicy(BaseModel):
    safety_class: str = "advisory"
    requires_human_review_for: list[str] = []
    prohibited_actions: list[str] = []


class AgentComposition(BaseModel):
    usable_in_profiles: list[str] = []
    compatible_agents: list[str] = []
    conflicts_with_agents: list[str] = []


class AgentQuality(BaseModel):
    maturity: str = "beta"


class AgentVersioning(BaseModel):
    version: str
    changelog_url: Optional[str] = None


class AgentManifest(BaseModel):
    schema_version: int = 1
    agent_id: str
    name: str
    display_name: str
    agent_type: str = "domain"
    status: str = "active"
    owner: AgentOwner
    purpose: str
    description: str
    classification: AgentClassification
    capabilities: list[str]
    skills: AgentSkills = AgentSkills()
    playbooks: Optional[AgentPlaybooks] = None
    context: AgentContext = AgentContext()
    tool_access: AgentToolAccess = AgentToolAccess()
    domain_knowledge: Optional[AgentDomainKnowledge] = None
    artifacts: AgentArtifacts = AgentArtifacts()
    policy: AgentPolicy = AgentPolicy()
    composition: AgentComposition = AgentComposition()
    quality: AgentQuality = AgentQuality()
    versioning: AgentVersioning = AgentVersioning(version="0.1.0")


# --- Skill manifest models (parsed from skill.yaml) ---

class SkillExecutionStep(BaseModel):
    step_id: str
    context_type: str
    tool_class: str
    depends_on: list[str] = []
    required: bool = True
    on_failure: str = "stop"


class SkillExecutionPlan(BaseModel):
    steps: list[SkillExecutionStep] = []
    on_partial_failure: str = "continue"


class SkillToolAffinity(BaseModel):
    allowed_tool_classes: list[str] = []
    preferred_tool_tags: list[str] = []
    execution_locations: list[str] = []


class SkillArtifactEffects(BaseModel):
    can_create: list[str] = []
    can_update: list[str] = []
    can_enrich: list[str] = []


class SkillActionSemantics(BaseModel):
    can_request_execution: bool = False
    can_generate_plan_fragments: bool = False
    can_generate_bundle_hints: bool = False
    can_generate_playbook_candidates: bool = False


class SkillSafety(BaseModel):
    safety_class: str = "advisory"
    requires_human_review_for: list[str] = []


class SkillEvidence(BaseModel):
    emits_rationale: bool = True
    emits_confidence: bool = True


class SkillManifestYaml(BaseModel):
    skill_id: str
    display_name: str
    owner_agent_id: str
    capability_id: str
    domain: str
    tier: str = "basic"
    status: str = "active"
    tenant_id: Optional[str] = None
    purpose: str
    description: str
    capabilities: list[str] = []
    context_descriptions: list[str] = []
    output_type: Literal["finding", "report", "plan", "triage", "closure_summary"]
    output_schema_ref: Optional[str] = None
    context_builder_ids: list[str] = []
    supported_context_types: list[str] = []
    tool_affinity: SkillToolAffinity = SkillToolAffinity()
    execution_plan: Optional[SkillExecutionPlan] = None
    artifact_effects: SkillArtifactEffects = SkillArtifactEffects()
    action_semantics: SkillActionSemantics = SkillActionSemantics()
    safety: SkillSafety = SkillSafety()
    evidence: SkillEvidence = SkillEvidence()
    version: str = "1.0.0"


# --- Registration result ---

class RegistrationResult(BaseModel):
    agent_id: str
    skill_ids: list[str]


# --- Validation result ---

class ValidationResult(BaseModel):
    errors: list[str] = []
    warnings: list[str] = []

    def ok(self) -> bool:
        return len(self.errors) == 0
