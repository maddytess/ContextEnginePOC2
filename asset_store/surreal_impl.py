from typing import Any, Optional

from .db import get_db
from .embeddings import embed_text

from .interface import (
    AssetStore, Collection, Direction, Document, EdgeType,
    Filters, Node, ScoredDoc,
)

# SurrealDB table per collection — the only place in the CE that knows table names
_TABLE: dict[Collection, str] = {
    Collection.Skill: "escher_skills_global",
    Collection.Agent: "escher_agent_registry_global",
    Collection.Tool: "escher_tools_global",
    Collection.ContextBuilder: "escher_context_builders_global",
}

# Fields joined for embedding at write time, per asset_store.md §9.3
_EMBED_FIELDS: dict[Collection, list[str]] = {
    Collection.Skill: ["purpose", "description", "display_name", "capability_id", "capabilities", "context_descriptions"],
    Collection.Agent: ["capabilities"],
    Collection.Tool: ["purpose", "tool_class"],
    Collection.ContextBuilder: ["purpose", "data_type"],
    Collection.Playbook: ["trigger_conditions", "name"],
    Collection.DomainLens: ["title", "content"],
    Collection.CloudKnowledge: ["title", "content"],
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
        query_old = f"""
            SELECT *, vector::similarity::cosine(embedding, $vec) AS score
            FROM {table}
            {where}
            ORDER BY score DESC
            LIMIT {limit}
        """
        query = f"""
            SELECT *, vector::similarity::cosine(embedding, $vec) AS score
            FROM {table}
            {where}
                AND embedding <|{limit},40|> $vec   -- HNSW KNN: K neighbours, EF=40
            ORDER BY score DESC LIMIT {limit}
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
            parts = []
            for f in fields:
                val = data.get(f, "")
                if isinstance(val, list):
                    parts.append(" ".join(str(v) for v in val))
                else:
                    parts.append(str(val))
            text = " ".join(parts)
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

    # --- Graph read ---

    async def get_neighbors(
        self,
        node_id: str,
        edge_types: list[EdgeType],
        direction: Direction,
    ) -> dict[EdgeType, list[Node]]:
        result: dict[EdgeType, list[Node]] = {}

        async with get_db() as db:
            for edge_type in edge_types:
                table = edge_type.value
                neighbor_ids: list[str] = []

                if direction in (Direction.Outbound, Direction.Both):
                    rows = await db.query(
                        f"SELECT to_id FROM {table} WHERE from_id = '{node_id}'"
                    ) or []
                    neighbor_ids.extend(r["to_id"] for r in rows if "to_id" in r)

                if direction in (Direction.Inbound, Direction.Both):
                    rows = await db.query(
                        f"SELECT from_id FROM {table} WHERE to_id = '{node_id}'"
                    ) or []
                    neighbor_ids.extend(r["from_id"] for r in rows if "from_id" in r)

                nodes: list[Node] = []
                for nid in neighbor_ids:
                    node_rows = await db.query(f"SELECT * FROM escher_nodes:`{nid}`") or []
                    if node_rows:
                        row = node_rows[0]
                        props = {k: v for k, v in row.items() if k not in ("id", "node_type")}
                        nodes.append(Node(id=nid, node_type=row.get("node_type", ""), properties=props))

                result[edge_type] = nodes

        return result

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
        data = {"id": node.id, "node_type": node.node_type, **node.properties}
        async with get_db() as db:
            result = await db.upsert(f"escher_nodes:`{node.id}`", data)
        if isinstance(result, str) and result.startswith("Could"):
            raise RuntimeError(f"SurrealDB node upsert failed for {node.id}: {result}")
        return node.id

    async def save_edge(self, from_id: str, to_id: str, edge_type: EdgeType) -> None:
        # RELATE creates a directed graph edge in SurrealDB
        query = (
            f"RELATE escher_nodes:`{from_id}`->{edge_type.value}->escher_nodes:`{to_id}`"
            f" CONTENT {{ from_id: '{from_id}', to_id: '{to_id}' }}"
        )
        async with get_db() as db:
            result = await db.query(query)
        if isinstance(result, str) and result.startswith("Could"):
            raise RuntimeError(f"SurrealDB RELATE failed {from_id}->{to_id}: {result}")

    async def delete_node(self, id: str) -> None:
        async with get_db() as db:
            await db.query(f"DELETE escher_nodes:`{id}`")

    async def delete_edge(self, from_id: str, to_id: str, edge_type: EdgeType) -> None:
        query = (
            f"DELETE escher_nodes:`{from_id}`->{edge_type.value} "
            f"WHERE out = escher_nodes:`{to_id}`"
        )
        async with get_db() as db:
            await db.query(query)
