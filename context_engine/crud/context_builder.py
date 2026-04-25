from asset_store import AssetStore, Collection, Document, EdgeType, Filters, Node, SurrealAssetStore
from adk.models import ContextBuilderManifestYaml

_store: AssetStore = SurrealAssetStore()


async def register_context_builder(cb: ContextBuilderManifestYaml) -> str:
    doc = Document(id=cb.context_builder_id, data=cb.model_dump())
    await _store.save(Collection.ContextBuilder, doc)

    node = Node(
        id=cb.context_builder_id,
        node_type="ContextBuilder",
        properties={"domain": cb.domain, "data_type": cb.data_type},
    )
    await _store.save_node(node)

    # ContextBuilder → CollectsVia → Tool for each tool class declared across collection units
    seen_tool_classes: set[str] = {
        tc
        for unit in cb.collection_units
        for tc in unit.preferred_tool_classes
    }
    for tc in seen_tool_classes:
        tool_docs = await _store.find(Collection.Tool, Filters(fields={"tool_class": tc}))
        for tool_doc in tool_docs:
            tool_id = tool_doc.data.get("tool_id", tool_doc.id)
            await _store.save_edge(cb.context_builder_id, tool_id, EdgeType.CollectsVia)

    return cb.context_builder_id
