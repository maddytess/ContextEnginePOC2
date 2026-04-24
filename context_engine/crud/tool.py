from asset_store import AssetStore, Collection, Document, Node, SurrealAssetStore
from adk.models import ToolManifestYaml

_store: AssetStore = SurrealAssetStore()


async def register_tool(tool: ToolManifestYaml) -> str:
    data = tool.model_dump()
    doc = Document(id=tool.tool_id, data=data)
    await _store.save(Collection.Tool, doc)

    node = Node(
        id=tool.tool_id,
        node_type="Tool",
        properties={
            "tool_type": tool.tool_type,
            "tool_class": tool.tool_class,
            "provider": tool.provider,
        },
    )
    await _store.save_node(node)

    return tool.tool_id
