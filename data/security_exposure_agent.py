from context_engine.models import SkillRecord

# Security Exposure Agent — 3 skills from agents.yaml.md Full Example
# Embedding text per adk.md §6.1: purpose + description + display_name + capability_id

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
        output_type="finding",
        context_builder_ids=["security.public_exposure_context"],
        supported_context_types=[
            "public_exposure_inventory",
            "resource_scope_summary",
            "environment_scope",
        ],
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
        output_type="finding",
        context_builder_ids=["security.public_exposure_context"],
        supported_context_types=[
            "public_exposure_inventory",
            "resource_scope_summary",
            "environment_scope",
        ],
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
        output_type="report",
        context_builder_ids=["security.public_exposure_context"],
        supported_context_types=[
            "public_exposure_inventory",
            "resource_scope_summary",
        ],
    ),
]
