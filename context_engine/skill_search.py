import asyncio
from .db import get_db
from .embeddings import embed_text
from .models import SkillSearchResult

# Phase 2C semantics: 1 result → narrow, N results → broad, 0 → miss
NARROW_THRESHOLD = 0.60
BROAD_THRESHOLD = 0.20


async def search_skills(
    prompt: str,
    tenant_id: str | None = None,
    top_k: int = 5,
) -> list[SkillSearchResult]:
    query_embedding = embed_text(prompt)

    # POC: full table scan — correct at 3-record scale, no index needed.
    # Production equivalent using the HNSW index (swap in when collection grows):
    #
    #   SELECT skill_id, owner_agent_id, domain,
    #          vector::similarity::cosine(embedding, $vec) AS confidence
    #   FROM escher_skills_global
    #   WHERE status = 'active'
    #         AND embedding <|{top_k},40|> $vec   -- HNSW KNN: K neighbours, EF=40 (beam width)
    #   ORDER BY confidence DESC
    #   LIMIT {top_k}
    #
    # The <|K,EF|> operator uses the HNSW index defined on the embedding field;
    # it never scans the full table. EF=40 is a typical recall/speed tradeoff —
    # raise it (e.g. 80) for higher recall at the cost of more graph traversal.
    query = f"""
        SELECT skill_id, owner_agent_id, domain,
               vector::similarity::cosine(embedding, $vec) AS confidence
        FROM escher_skills_global
        WHERE status = 'active'
        ORDER BY confidence DESC
        LIMIT {top_k}
    """

    async with get_db() as db:
        results = await db.query(query, {"vec": query_embedding})

    raw = results if results else []
    return [
        SkillSearchResult(
            skill_id=r["skill_id"],
            owner_agent_id=r["owner_agent_id"],
            domain=r["domain"],
            confidence=round(float(r["confidence"]), 4),
        )
        for r in raw
        if float(r["confidence"]) >= BROAD_THRESHOLD
    ]


def classify_results(results: list[SkillSearchResult]) -> str:
    """Returns 'narrow', 'broad', or 'miss' per Phase 2C routing logic."""
    if not results:
        return "miss"
    if len(results) == 1 or results[0].confidence >= NARROW_THRESHOLD:
        return "narrow"
    return "broad"


if __name__ == "__main__":
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
