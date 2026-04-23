from typing import Any, Optional

from context_engine.db import get_db
from context_engine.embeddings import embed_text

from .interface import (
    AssetStore, Collection, Direction, Document, EdgeType,
    Filters, Node, ScoredDoc,
)

# SurrealDB table per collection — the only place in the CE that knows table names
_TABLE: dict[Collection, str] = {
    Collection.Skill: "escher_skills_global",
}

# Fields joined for embedding at write time, per asset_store.md §9.3
_EMBED_FIELDS: dict[Collection, list[str]] = {
    Collection.Skill: ["purpose", "description", "display_name", "capability_id"],
    Collection.Playbook: ["trigger_conditions", "name"],
    Collection.DomainLens: ["title", "content"],
    Collection.CloudKnowledge: ["title", "content"],
    Collection.Tool: ["purpose", "tool_class"],
}


def _table(collection: Collection) -> str:
    if collection not in _TABLE:
        raise NotImplementedError(f"Collection {collection} not yet mapped to a SurrealDB table")
    return _TABLE[collection]


def _build_where(filters: Filters) -> str:
    if not filters.fields:
        return ""
    clauses = []
    for field, value in filters.fields.items():
        if value is None:
            clauses.append(f"{field} IS NULL")
        elif isinstance(value, str):
            clauses.append(f"{field} = '{value}'")
        else:
            clauses.append(f"{field} = {value}")
    return "WHERE " + " AND ".join(clauses)


class SurrealAssetStore(AssetStore):

    # --- Semantic search ---

    async def find_by_text(
        self,
        collection: Collection,
        query_text: str,
        filters: Filters,
        limit: int,
        min_score: float,
    ) -> list[ScoredDoc]:
        table = _table(collection)
        vec = embed_text(query_text)  # embedding is an AssetStore concern — CE never sees a vector
        where = _build_where(filters)

        # POC: full scan with cosine similarity. Production equivalent using the HNSW index:
        #
        #   SELECT *, vector::similarity::cosine(embedding, $vec) AS score
        #   FROM {table}
        #   {where}
        #     AND embedding <|{limit},40|> $vec   -- HNSW KNN: K neighbours, EF=40
        #   ORDER BY score DESC LIMIT {limit}
        #
        # The <|K,EF|> operator uses the HNSW index; it never scans the full table.
        # EF=40 is a typical recall/speed tradeoff — raise it for higher recall.
        query = f"""
            SELECT *, vector::similarity::cosine(embedding, $vec) AS score
            FROM {table}
            {where}
            ORDER BY score DESC
            LIMIT {limit}
        """

        async with get_db() as db:
            rows = await db.query(query, {"vec": vec}) or []

        results = []
        for row in rows:
            score = float(row.get("score", 0.0))
            if score < min_score:
                continue
            data = {k: v for k, v in row.items() if k != "score"}
            results.append(ScoredDoc(document=Document(id=row["skill_id"], data=data), score=score))
        return results

    # --- Document read ---

    async def find_by_id(self, collection: Collection, id: str) -> Optional[Document]:
        table = _table(collection)
        async with get_db() as db:
            rows = await db.query(f"SELECT * FROM {table}:`{id}`") or []
        if not rows:
            return None
        return Document(id=id, data=rows[0])

    async def find(
        self,
        collection: Collection,
        filters: Filters,
        limit: Optional[int] = None,
    ) -> list[Document]:
        table = _table(collection)
        where = _build_where(filters)
        limit_clause = f"LIMIT {limit}" if limit else ""
        async with get_db() as db:
            rows = await db.query(f"SELECT * FROM {table} {where} {limit_clause}") or []
        return [Document(id=r.get("skill_id", r.get("id", "")), data=r) for r in rows]

    # --- Document write ---

    async def save(self, collection: Collection, document: Document) -> str:
        table = _table(collection)
        data = dict(document.data)

        # AssetStore generates and stores the embedding — caller passes plain data, never a vector
        if collection in _EMBED_FIELDS:
            fields = _EMBED_FIELDS[collection]
            text = " ".join(str(data.get(f, "")) for f in fields)
            data["embedding"] = embed_text(text)

        async with get_db() as db:
            result = await db.upsert(f"{table}:`{document.id}`", data)
        # SurrealDB SDK returns error strings instead of raising — catch them explicitly
        if isinstance(result, str) and result.startswith("Could"):
            raise RuntimeError(f"SurrealDB upsert failed for {document.id}: {result}")
        return document.id

    async def delete(self, collection: Collection, id: str) -> None:
        table = _table(collection)
        async with get_db() as db:
            await db.query(f"DELETE {table}:`{id}`")

    # --- Graph read (not yet wired to SurrealDB graph layer — POC scope) ---

    async def get_neighbors(
        self,
        node_id: str,
        edge_types: list[EdgeType],
        direction: Direction,
    ) -> dict[EdgeType, list[Node]]:
        # SurrealDB graph traversal via RELATE relationships.
        # Direction mapping: Outbound → ->, Inbound → <-, Both → <->
        # Example for outbound References edges:
        #   SELECT ->References->* AS neighbors FROM escher_skills_global:`{node_id}`
        # Returns empty until RELATE data is seeded — no NotImplementedError so
        # resolve mode can call this cleanly without a hard failure.
        return {et: [] for et in edge_types}

    async def traverse_path(
        self,
        start_id: str,
        edge_sequence: list[EdgeType],
    ) -> list[Node]:
        # Chained hop-by-hop traversal, e.g.:
        #   control -Requires-> requirement -EvidencedBy-> evidence_type -CollectedVia-> tool
        # Not yet seeded with graph data in POC.
        return []

    # --- Graph write ---

    async def save_node(self, node: Node) -> str:
        raise NotImplementedError("Graph write not yet implemented in POC")

    async def save_edge(self, from_id: str, to_id: str, edge_type: EdgeType) -> None:
        raise NotImplementedError("Graph write not yet implemented in POC")

    async def delete_node(self, id: str) -> None:
        raise NotImplementedError("Graph write not yet implemented in POC")

    async def delete_edge(self, from_id: str, to_id: str, edge_type: EdgeType) -> None:
        raise NotImplementedError("Graph write not yet implemented in POC")
