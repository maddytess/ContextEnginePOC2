from .asset_store import Collection, Filters, SurrealAssetStore
from .models import SkillSearchResult

# Phase 2C semantics: 1 result → narrow, N results → broad, 0 → miss
NARROW_THRESHOLD = 0.60
BROAD_THRESHOLD = 0.20


async def search_skills(
    prompt: str,
    tenant_id: str | None = None,
    top_k: int = 5,
) -> list[SkillSearchResult]:
    store = SurrealAssetStore()

    # CE business logic owns tenancy: fire tenant + global in parallel, tenant wins.
    # POC: global only (tenant_id=None means no tenant filter applied yet).
    filters = Filters({"status": "active"})

    scored = await store.find_by_text(
        Collection.Skill,
        prompt,
        filters,
        limit=top_k,
        min_score=BROAD_THRESHOLD,
    )

    return [
        SkillSearchResult(
            skill_id=s.document.data["skill_id"],
            owner_agent_id=s.document.data["owner_agent_id"],
            domain=s.document.data["domain"],
            confidence=round(s.score, 4),
        )
        for s in scored
    ]


def classify_results(results: list[SkillSearchResult]) -> str:
    """Returns 'narrow', 'broad', or 'miss' per Phase 2C routing logic."""
    if not results:
        return "miss"
    if len(results) == 1 or results[0].confidence >= NARROW_THRESHOLD:
        return "narrow"
    return "broad"


if __name__ == "__main__":
    import asyncio

    async def demo():
        queries = [
            "show me my unsecured EC2 instances",
            "which S3 buckets are publicly accessible?",
            "what should I fix first?",
        ]
        for q in queries:
            results = await search_skills(q)
            decision = classify_results(results)
            print(f"\nQuery: {q!r}")
            print(f"Decision: {decision}")
            for r in results:
                print(f"  {r.skill_id}  confidence={r.confidence}")

    asyncio.run(demo())
