from .asset_store import Collection, Direction, EdgeType, Filters, SurrealAssetStore
from .models import (
    ResolveSkillRequest,
    ResolveSkillResponse,
    SearchSkillResponse,
    SkillManifest,
    SkillMatch,
)

# Phase 2C semantics: 1 result → narrow, N results → broad, 0 → miss
NARROW_THRESHOLD = 0.60
BROAD_THRESHOLD = 0.20


class SkillNotFoundError(Exception):
    pass


async def handle_resolve_skill(
    request: ResolveSkillRequest,
) -> SearchSkillResponse | ResolveSkillResponse:
    """Single entry point for /resolve/skill. Dispatches on request.mode."""
    if request.mode == "search":
        return await _search(request)
    return await _resolve(request)


def classify_results(response: SearchSkillResponse) -> str:
    """Returns 'narrow', 'broad', or 'miss' per Phase 2C routing logic."""
    if not response.matches:
        return "miss"
    if len(response.matches) == 1 or response.matches[0].confidence >= NARROW_THRESHOLD:
        return "narrow"
    return "broad"


async def _search(request: ResolveSkillRequest) -> SearchSkillResponse:
    store = SurrealAssetStore()

    # CE business logic owns tenancy: fire tenant + global in parallel, tenant wins.
    # POC: global only — tenant parallel search to be added when tenant data exists.
    filters = Filters({"status": "active"})

    scored = await store.find_by_text(
        Collection.Skill,
        request.query,  # type: ignore[arg-type]  # validated non-None by ResolveSkillRequest
        filters,
        limit=request.top_k,
        min_score=BROAD_THRESHOLD,
    )

    matches = [
        SkillMatch(
            skill_id=s.document.data["skill_id"],
            owner_agent_id=s.document.data["owner_agent_id"],
            domain=s.document.data["domain"],
            confidence=round(s.score, 4),
            source="global" if s.document.data.get("tenant_id") is None else "tenant",
        )
        for s in scored
    ]
    return SearchSkillResponse(request_id=request.request_id, matches=matches)


async def _resolve(request: ResolveSkillRequest) -> ResolveSkillResponse:
    store = SurrealAssetStore()

    doc = await store.find_by_id(Collection.Skill, request.skill_id)  # type: ignore[arg-type]
    if doc is None:
        raise SkillNotFoundError(request.skill_id)

    # Scope enforcement: owner_agent_id must match
    if doc.data.get("owner_agent_id") != request.owner_agent_id:
        raise SkillNotFoundError(request.skill_id)

    # Graph call per asset_store.md §12 — empty in POC until RELATE data is seeded
    await store.get_neighbors(
        request.skill_id,  # type: ignore[arg-type]
        [EdgeType.References, EdgeType.ConstrainedBy, EdgeType.RendersVia, EdgeType.Produces],
        Direction.Outbound,
    )

    source = "global" if doc.data.get("tenant_id") is None else "tenant"
    manifest = SkillManifest(**{k: v for k, v in doc.data.items() if k != "embedding"}, source=source)
    return ResolveSkillResponse(request_id=request.request_id, skill=manifest)
