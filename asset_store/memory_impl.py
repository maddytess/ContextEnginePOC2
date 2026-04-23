from typing import Optional

from .embeddings import embed_text

from .interface import (
    AssetStore, Collection, Direction, Document, EdgeType,
    Filters, Node, ScoredDoc,
)


def _cosine(a: list[float], b: list[float]) -> float:
    # Embeddings are already L2-normalised, so dot product == cosine similarity
    return sum(x * y for x, y in zip(a, b))


def _matches(doc: Document, filters: Filters) -> bool:
    for field, value in filters.fields.items():
        actual = doc.data.get(field)
        if value is None and actual is not None:
            return False
        if value is not None and actual != value:
            return False
    return True


class MemoryAssetStore(AssetStore):
    """In-memory implementation — no database connection required. Use in tests."""

    def __init__(self) -> None:
        self._docs: dict[tuple[Collection, str], Document] = {}
        self._vecs: dict[tuple[Collection, str], list[float]] = {}
        self._nodes: dict[str, Node] = {}
        self._edges: list[tuple[str, EdgeType, str]] = []

    # --- Semantic search ---

    async def find_by_text(
        self,
        collection: Collection,
        query_text: str,
        filters: Filters,
        limit: int,
        min_score: float,
    ) -> list[ScoredDoc]:
        query_vec = embed_text(query_text)
        scored = []
        for (col, id_), doc in self._docs.items():
            if col != collection or not _matches(doc, filters):
                continue
            vec = self._vecs.get((col, id_))
            if vec is None:
                continue
            score = _cosine(query_vec, vec)
            if score >= min_score:
                scored.append(ScoredDoc(document=doc, score=score))
        scored.sort(key=lambda s: s.score, reverse=True)
        return scored[:limit]

    # --- Document read ---

    async def find_by_id(self, collection: Collection, id: str) -> Optional[Document]:
        return self._docs.get((collection, id))

    async def find(
        self,
        collection: Collection,
        filters: Filters,
        limit: Optional[int] = None,
    ) -> list[Document]:
        results = [
            doc for (col, _), doc in self._docs.items()
            if col == collection and _matches(doc, filters)
        ]
        return results[:limit] if limit else results

    # --- Document write ---

    async def save(self, collection: Collection, document: Document) -> str:
        self._docs[(collection, document.id)] = document
        # Generate embedding so find_by_text works
        text = " ".join(str(v) for v in document.data.values() if isinstance(v, str))
        self._vecs[(collection, document.id)] = embed_text(text)
        return document.id

    async def delete(self, collection: Collection, id: str) -> None:
        self._docs.pop((collection, id), None)
        self._vecs.pop((collection, id), None)

    # --- Graph read ---

    async def get_neighbors(
        self,
        node_id: str,
        edge_types: list[EdgeType],
        direction: Direction,
    ) -> dict[EdgeType, list[Node]]:
        result: dict[EdgeType, list[Node]] = {et: [] for et in edge_types}
        for from_id, et, to_id in self._edges:
            if et not in edge_types:
                continue
            if direction in (Direction.Outbound, Direction.Both) and from_id == node_id:
                node = self._nodes.get(to_id)
                if node:
                    result[et].append(node)
            if direction in (Direction.Inbound, Direction.Both) and to_id == node_id:
                node = self._nodes.get(from_id)
                if node:
                    result[et].append(node)
        return result

    async def traverse_path(
        self,
        start_id: str,
        edge_sequence: list[EdgeType],
    ) -> list[Node]:
        current_ids = [start_id]
        visited: list[Node] = []
        for edge_type in edge_sequence:
            next_ids = []
            for from_id, et, to_id in self._edges:
                if et == edge_type and from_id in current_ids:
                    node = self._nodes.get(to_id)
                    if node:
                        visited.append(node)
                        next_ids.append(to_id)
            current_ids = next_ids
        return visited

    # --- Graph write ---

    async def save_node(self, node: Node) -> str:
        self._nodes[node.id] = node
        return node.id

    async def save_edge(self, from_id: str, to_id: str, edge_type: EdgeType) -> None:
        self._edges.append((from_id, edge_type, to_id))

    async def delete_node(self, id: str) -> None:
        self._nodes.pop(id, None)
        self._edges = [(f, et, t) for f, et, t in self._edges if f != id and t != id]

    async def delete_edge(self, from_id: str, to_id: str, edge_type: EdgeType) -> None:
        self._edges = [
            (f, et, t) for f, et, t in self._edges
            if not (f == from_id and t == to_id and et == edge_type)
        ]
