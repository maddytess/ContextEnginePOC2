import asyncio
from context_engine.setup_schema import setup_schema
from context_engine.adk_register import register_skills
from context_engine.skill_search import search_skills, classify_results
from data.security_exposure_agent import SKILLS

SAMPLE_QUERIES = [
    "show me my unsecured EC2 instances",
    "which S3 buckets are publicly accessible?",
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

    print("\n3. Running Phase 2C semantic skill search...\n")
    for query in SAMPLE_QUERIES:
        results = await search_skills(query, top_k=3)
        decision = classify_results(results)
        print(f"Query   : {query!r}")
        print(f"Decision: {decision.upper()}")
        if results:
            for r in results:
                print(f"  → {r.skill_id:<45} confidence={r.confidence:.4f}")
        else:
            print("  → no match (MISS → Code Agent)")
        print()


if __name__ == "__main__":
    asyncio.run(main())
