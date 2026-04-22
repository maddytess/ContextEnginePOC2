from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class Collection(str, Enum):
    Skill = "Skill"
    Agent = "Agent"
    Playbook = "Playbook"
    ContextBuilder = "ContextBuilder"
    Tool = "Tool"
    Guardrail = "Guardrail"
    DomainLens = "DomainLens"
    Template = "Template"
    CloudKnowledge = "CloudKnowledge"


class EdgeType(str, Enum):
    # ADK Platform Graph
    References = "References"
    ConstrainedBy = "ConstrainedBy"
    RendersVia = "RendersVia"
    Produces = "Produces"
    Recommends = "Recommends"
    CollectsVia = "CollectsVia"
    Invokes = "Invokes"
    Requires = "Requires"
    # Domain Expert Graph
    EvidencedBy = "EvidencedBy"
    CollectedVia = "CollectedVia"
    RemediatedBy = "RemediatedBy"
    # Cloud Knowledge Graph
    OptionallyUses = "OptionallyUses"
    DifferFrom = "DifferFrom"


class Direction(str, Enum):
    Outbound = "Outbound"
    Inbound = "Inbound"
    Both = "Both"


@dataclass
class Document:
    id: str
    data: dict[str, Any]


@dataclass
class ScoredDoc:
    document: Document
    score: float


@dataclass
class Node:
    id: str
    node_type: str
    properties: dict[str, Any]


@dataclass
class Filters:
    fields: dict[str, Any] = field(default_factory=dict)


class AssetStore(ABC):

    # --- Semantic search ---

    @abstractmethod
    async def find_by_text(
        self,
        collection: Collection,
        query_text: str,
        filters: Filters,
        limit: int,
        min_score: float,
    ) -> list[ScoredDoc]: ...

    # --- Document read ---

    @abstractmethod
    async def find_by_id(
        self,
        collection: Collection,
        id: str,
    ) -> Optional[Document]: ...

    @abstractmethod
    async def find(
        self,
        collection: Collection,
        filters: Filters,
        limit: Optional[int] = None,
    ) -> list[Document]: ...

    # --- Document write (CRUD layer / ADK path only) ---

    @abstractmethod
    async def save(self, collection: Collection, document: Document) -> str: ...

    @abstractmethod
    async def delete(self, collection: Collection, id: str) -> None: ...

    # --- Graph read ---

    @abstractmethod
    async def get_neighbors(
        self,
        node_id: str,
        edge_types: list[EdgeType],
        direction: Direction,
    ) -> dict[EdgeType, list[Node]]: ...

    @abstractmethod
    async def traverse_path(
        self,
        start_id: str,
        edge_sequence: list[EdgeType],
    ) -> list[Node]: ...

    # --- Graph write (CRUD layer / ADK path only) ---

    @abstractmethod
    async def save_node(self, node: Node) -> str: ...

    @abstractmethod
    async def save_edge(self, from_id: str, to_id: str, edge_type: EdgeType) -> None: ...

    @abstractmethod
    async def delete_node(self, id: str) -> None: ...

    @abstractmethod
    async def delete_edge(self, from_id: str, to_id: str, edge_type: EdgeType) -> None: ...
