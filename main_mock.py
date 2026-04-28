import asyncio
import sys

from context_engine.setup_schema import setup_schema
from context_engine.skill_resolver import classify_results, handle_resolve_skill
from context_engine.models import ResolveSkillRequest
from adk import load_package, validate_package, register_package

SAMPLE_QUERIES = [
    "what did my AWS EC2 cost last month?",
    "which EC2 instances have CPU utilization above 80%?",
    "who deleted my S3 bucket yesterday?",
    "scan my AWS account to refresh the inventory",
    "am I SOC 2 compliant?",
    "check my ISO 27001 compliance posture",
    "are we HIPAA compliant for PHI data?",
    "run a GDPR data protection audit",
    "show me IAM privilege escalation paths",
    "audit my IAM roles and access keys for security issues",
    "are all my S3 buckets and RDS databases encrypted?",
    "which of my resources are publicly accessible from the internet?",
    "run a PCI-DSS compliance check",
]


async def main():
    print("=== Context Engine POC — Mock Multi-Domain Catalog ===\n")

    print("1. Setting up SurrealDB schema...")
    await setup_schema()

    print("\n2. Loading and registering Mock Catalog via ADK...")
    pkg = load_package("mock-data")
    result = validate_package(pkg)
    if result.warnings:
        for w in result.warnings:
            print(f"   WARN: {w}")
    if not result.ok():
        for e in result.errors:
            print(f"   ERROR: {e}")
        print("ADK validation failed — aborting.")
        sys.exit(1)

    reg = await register_package(pkg)
    for tid in reg.tool_ids:
        print(f"   tool registered             : {tid}")
    for cb_id in reg.context_builder_ids:
        print(f"   context_builder registered  : {cb_id}")
    for sid in reg.skill_ids:
        print(f"   skill registered            : {sid}")
    print(f"   agent registered            : {reg.agent_id}")

    print("\n3. Phase 2C — /resolve/skill mode=search\n")
    top_hit = None
    for query in SAMPLE_QUERIES:
        request = ResolveSkillRequest(mode="search", query=query, request_id="req-mock", top_k=3)
        response = await handle_resolve_skill(request)
        decision = classify_results(response)
        print(f"Query   : {query!r}")
        print(f"Decision: {decision.upper()}")
        for m in response.matches:
            print(f"  → {m.skill_id:<50} confidence={m.confidence:.4f}  source={m.source}")
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
            request_id="req-mock-resolve",
        )
        resolved = await handle_resolve_skill(request)
        s = resolved.skill
        print(f"  skill_id            : {s.skill_id}")
        print(f"  display_name        : {s.display_name}")
        print(f"  owner_agent_id      : {s.owner_agent_id}")
        print(f"  domain / tier       : {s.domain} / {s.tier}  source={s.source}")
        print(f"  purpose             : {s.purpose}")
        print(f"  capabilities        :")
        for c in s.capabilities:
            print(f"    - {c}")
        print(f"  context_builder_ids : {s.context_builder_ids}")
        print(f"  output_type         : {s.output_type}")
        print(f"  version             : {s.version}")


if __name__ == "__main__":
    asyncio.run(main())
