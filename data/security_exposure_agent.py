from context_engine.models import (
    ActionSemantics, ArtifactEffects, Evidence, ExecutionPlan, ExecutionStep,
    Safety, SkillRecord, ToolAffinity,
)

_TOOL_AFFINITY = ToolAffinity(
    allowed_tool_classes=["cloud_read"],
    preferred_tool_tags=["aws", "security"],
    execution_locations=["client"],
)

_ACTION_SEMANTICS = ActionSemantics(
    can_request_execution=False,
    can_generate_plan_fragments=True,
    can_generate_bundle_hints=True,
    can_generate_playbook_candidates=False,
)

_SAFETY = Safety(safety_class="advisory", requires_human_review_for=[])

_EVIDENCE = Evidence(emits_rationale=True, emits_confidence=True)

# Shared execution plan for all three exposure skills — same context builder drives each
_EXPOSURE_PLAN = ExecutionPlan(
    steps=[
        ExecutionStep(
            step_id="fetch_exposure_inventory",
            context_type="public_exposure_inventory",
            tool_class="inventory_read",
            depends_on=[],
            required=True,
            on_failure="stop",
        ),
        ExecutionStep(
            step_id="fetch_resource_scope",
            context_type="resource_scope_summary",
            tool_class="inventory_read",
            depends_on=["fetch_exposure_inventory"],
            required=False,
            on_failure="skip",
        ),
        ExecutionStep(
            step_id="fetch_environment_scope",
            context_type="environment_scope",
            tool_class="inventory_read",
            depends_on=[],
            required=False,
            on_failure="skip",
        ),
    ],
    on_partial_failure="continue",
)

SKILLS = [
    SkillRecord(
        skill_id="security.detect_public_ingress",
        display_name="Detect Public Ingress",
        owner_agent_id="domain.security.exposure",
        capability_id="detect_public_exposure",
        domain="security",
        tier="basic",
        status="active",
        tenant_id=None,
        purpose="Detect public ingress patterns and generate exposure findings.",
        description=(
            "Finds publicly accessible EC2 instances, open security groups, "
            "internet-facing load balancers, and public S3 buckets. Use this for "
            "questions like: which EC2 instances are unsecured, what security groups "
            "have open ingress, show me public-facing resources, find exposed "
            "infrastructure in my AWS account."
        ),
        capabilities=[
            "List EC2 instances with public IP addresses",
            "Find security groups with unrestricted ingress rules (0.0.0.0/0 or ::/0)",
            "Identify internet-facing load balancers",
            "Detect public S3 buckets via ACL and policy analysis",
        ],
        context_descriptions=[
            "Public exposure inventory across EC2, security groups, load balancers, and S3",
            "Resource scope and environment metadata for the account being analysed",
        ],
        output_type="finding",
        output_schema_ref="schemas/security/public_ingress_finding.json",
        context_builder_ids=["security.public_exposure_context"],
        supported_context_types=[
            "public_exposure_inventory",
            "resource_scope_summary",
            "environment_scope",
        ],
        tool_affinity=_TOOL_AFFINITY,
        execution_plan=_EXPOSURE_PLAN,
        artifact_effects=ArtifactEffects(
            can_create=["ExposureFinding"],
            can_update=[],
            can_enrich=["ResourceInventory"],
        ),
        action_semantics=_ACTION_SEMANTICS,
        safety=_SAFETY,
        evidence=_EVIDENCE,
        version="1.0.0",
    ),
    SkillRecord(
        skill_id="security.detect_public_storage_access",
        display_name="Detect Public Storage Access",
        owner_agent_id="domain.security.exposure",
        capability_id="detect_public_exposure",
        domain="security",
        tier="basic",
        status="active",
        tenant_id=None,
        purpose="Detect publicly accessible S3 buckets and storage resources.",
        description=(
            "Identifies S3 buckets with public access enabled, bucket policies "
            "allowing public reads, and ACLs that expose data to the internet. "
            "Use for: find public S3 buckets, show me storage with open access, "
            "which buckets have no access control, list publicly readable storage "
            "in my AWS account."
        ),
        capabilities=[
            "List S3 buckets with Block Public Access disabled",
            "Detect bucket policies that grant public read or write",
            "Find buckets with ACLs that expose objects to AllUsers or AuthenticatedUsers",
        ],
        context_descriptions=[
            "S3 bucket inventory with public access settings and policy analysis",
            "Resource scope and environment metadata for the account being analysed",
        ],
        output_type="finding",
        output_schema_ref="schemas/security/public_storage_finding.json",
        context_builder_ids=["security.public_exposure_context"],
        supported_context_types=[
            "public_exposure_inventory",
            "resource_scope_summary",
            "environment_scope",
        ],
        tool_affinity=_TOOL_AFFINITY,
        execution_plan=_EXPOSURE_PLAN,
        artifact_effects=ArtifactEffects(
            can_create=["ExposureFinding"],
            can_update=[],
            can_enrich=["StorageInventory"],
        ),
        action_semantics=_ACTION_SEMANTICS,
        safety=_SAFETY,
        evidence=_EVIDENCE,
        version="1.0.0",
    ),
    SkillRecord(
        skill_id="security.rank_basic_exposure_findings",
        display_name="Rank Basic Exposure Findings",
        owner_agent_id="domain.security.exposure",
        capability_id="detect_public_exposure",
        domain="security",
        tier="basic",
        status="active",
        tenant_id=None,
        purpose="Rank and prioritize security exposure findings by severity and risk.",
        description=(
            "Analyzes a set of exposure findings and ranks them by severity, risk "
            "score, and business impact. Use for: which exposure is most critical, "
            "rank my security findings, prioritize what to fix first, show me the "
            "highest risk exposures in my account, what should I remediate first."
        ),
        capabilities=[
            "Score exposure findings by severity (critical, high, medium, low)",
            "Rank findings by combined risk score and estimated business impact",
            "Produce a prioritized remediation order with rationale per finding",
        ],
        context_descriptions=[
            "Set of exposure findings produced by prior detect skills",
            "Resource scope and environment metadata for weighting business impact",
        ],
        output_type="report",
        output_schema_ref="schemas/security/exposure_rank_report.json",
        context_builder_ids=["security.public_exposure_context"],
        supported_context_types=[
            "public_exposure_inventory",
            "resource_scope_summary",
        ],
        tool_affinity=_TOOL_AFFINITY,
        execution_plan=ExecutionPlan(
            steps=[
                ExecutionStep(
                    step_id="fetch_exposure_inventory",
                    context_type="public_exposure_inventory",
                    tool_class="inventory_read",
                    depends_on=[],
                    required=True,
                    on_failure="stop",
                ),
                ExecutionStep(
                    step_id="fetch_resource_scope",
                    context_type="resource_scope_summary",
                    tool_class="inventory_read",
                    depends_on=["fetch_exposure_inventory"],
                    required=False,
                    on_failure="skip",
                ),
            ],
            on_partial_failure="continue",
        ),
        artifact_effects=ArtifactEffects(
            can_create=["ExposureRankReport"],
            can_update=["ExposureFinding"],
            can_enrich=[],
        ),
        action_semantics=_ACTION_SEMANTICS,
        safety=_SAFETY,
        evidence=_EVIDENCE,
        version="1.0.0",
    ),
]
