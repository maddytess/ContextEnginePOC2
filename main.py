import asyncio
import sys

from context_engine.setup_schema import setup_schema
from context_engine.skill_resolver import classify_results, handle_resolve_skill
from context_engine.models import ResolveSkillRequest
from adk import load_package, validate_package, register_package

SAMPLE_QUERIES = [
    "show me my unsecured EC2 instances",
    "which S3 buckets are publicly accessible?",
    "what should I fix first?",
    "find open security groups with unrestricted ingress",
    "show me all internet-facing resources",
]


async def main():
    print("=== Context Engine POC ===\n")

    print("1. Setting up SurrealDB schema...")
    await setup_schema()

    print("\n2. Loading and registering Security Exposure Agent via ADK...")
    manifest, skills = load_package("data/security_exposure_agent")
    result = validate_package(manifest, skills)
    if result.warnings:
        for w in result.warnings:
            print(f"   WARN: {w}")
    if not result.ok():
        for e in result.errors:
            print(f"   ERROR: {e}")
        print("ADK validation failed — aborting.")
        sys.exit(1)

    reg = await register_package(manifest, skills)
    print(f"   agent registered : {reg.agent_id}")
    for sid in reg.skill_ids:
        print(f"   skill registered : {sid}")

    print("\n3. Phase 2C — /resolve/skill mode=search\n")
    top_hit = None
    for query in SAMPLE_QUERIES:
        request = ResolveSkillRequest(mode="search", query=query, request_id="req-demo", top_k=3)
        response = await handle_resolve_skill(request)
        decision = classify_results(response)
        print(f"Query   : {query!r}")
        print(f"Decision: {decision.upper()}")
        for m in response.matches:
            print(f"  → {m.skill_id:<45} confidence={m.confidence:.4f}  source={m.source}")
            if top_hit is None:
                top_hit = m
        if not response.matches:
            print("  → no match (MISS → Code Agent)")
        print()

    print("4. Phase 3 — /resolve/skill mode=resolve\n")
    if top_hit:
        print(f"Resolving: {top_hit.skill_id!r}  owner={top_hit.owner_agent_id!r}\n")
        request = ResolveSkillRequest(
            mode="resolve",
            skill_id=top_hit.skill_id,
            owner_agent_id=top_hit.owner_agent_id,
            request_id="req-demo-resolve",
        )
        resolved = await handle_resolve_skill(request)
        s = resolved.skill
        print(f"  skill_id            : {s.skill_id}")
        print(f"  display_name        : {s.display_name}")
        print(f"  owner_agent_id      : {s.owner_agent_id}")
        print(f"  capability_id       : {s.capability_id}")
        print(f"  domain / tier       : {s.domain} / {s.tier}  source={s.source}")
        print(f"  purpose             : {s.purpose}")
        print(f"  description         : {s.description}")
        print(f"  capabilities        :")
        for c in s.capabilities:
            print(f"    - {c}")
        print(f"  context_descriptions:")
        for d in s.context_descriptions:
            print(f"    - {d}")
        print(f"  context_builder_ids : {s.context_builder_ids}")
        print(f"  supported_context_types: {s.supported_context_types}")
        print(f"  tool_affinity       : classes={s.tool_affinity.allowed_tool_classes}  tags={s.tool_affinity.preferred_tool_tags}  locations={s.tool_affinity.execution_locations}")
        print(f"  execution_plan      : on_partial_failure={s.execution_plan.on_partial_failure}")
        for step in s.execution_plan.steps:
            print(f"    step {step.step_id}: context={step.context_type}  tool={step.tool_class}  required={step.required}  on_failure={step.on_failure}  depends_on={step.depends_on}")
        print(f"  output_type         : {s.output_type}")
        print(f"  output_schema_ref   : {s.output_schema_ref}")
        print(f"  artifact_effects    : create={s.artifact_effects.can_create}  update={s.artifact_effects.can_update}  enrich={s.artifact_effects.can_enrich}")
        print(f"  action_semantics    : exec={s.action_semantics.can_request_execution}  plan_frags={s.action_semantics.can_generate_plan_fragments}  bundle={s.action_semantics.can_generate_bundle_hints}  playbook={s.action_semantics.can_generate_playbook_candidates}")
        print(f"  safety              : class={s.safety.safety_class}  review_for={s.safety.requires_human_review_for}")
        print(f"  evidence            : rationale={s.evidence.emits_rationale}  confidence={s.evidence.emits_confidence}")
        print(f"  version             : {s.version}")


if __name__ == "__main__":
    asyncio.run(main())
