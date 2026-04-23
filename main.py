import asyncio
from context_engine.setup_schema import setup_schema
from context_engine.adk_register import register_skills
from context_engine.skill_resolver import classify_results, handle_resolve_skill
from context_engine.models import ResolveSkillRequest
from data.security_exposure_agent import SKILLS

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

    print("\n2. Registering Security Exposure Agent skills...")
    await register_skills(SKILLS)
    print(f"   {len(SKILLS)} skills registered.")

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
        print(f"  skill_id       : {s.skill_id}")
        print(f"  display_name   : {s.display_name}")
        print(f"  domain/tier    : {s.domain} / {s.tier}  source={s.source}")
        print(f"  purpose        : {s.purpose}")
        print(f"  output_type    : {s.output_type}")
        print(f"  capabilities   :")
        for c in s.capabilities:
            print(f"    - {c}")
        print(f"  tool_affinity  : classes={s.tool_affinity.allowed_tool_classes}  locations={s.tool_affinity.execution_locations}")
        print(f"  action_semantics: can_request_execution={s.action_semantics.can_request_execution}")
        print(f"  safety         : {s.safety.safety_class}")
        print(f"  evidence       : rationale={s.evidence.emits_rationale}  confidence={s.evidence.emits_confidence}")
        print(f"  version        : {s.version}")


if __name__ == "__main__":
    asyncio.run(main())
