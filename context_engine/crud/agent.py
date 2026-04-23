from typing import Optional

from asset_store import AssetStore, Collection, Document, EdgeType, Node, SurrealAssetStore
from adk.models import AgentManifest

_store: AssetStore = SurrealAssetStore()


async def register_agent(
    manifest: AgentManifest,
    skill_ids: list[str],
    tenant_id: Optional[str],
) -> str:
    agent_data = {
        "agent_id": manifest.agent_id,
        "name": manifest.name,
        "display_name": manifest.display_name,
        "agent_type": manifest.agent_type,
        "status": manifest.status,
        "owner_team": manifest.owner.team,
        "owner_contact": manifest.owner.contact,
        "purpose": manifest.purpose,
        "description": manifest.description,
        "domain": manifest.classification.domain,
        "product_scope": manifest.classification.product_scope,
        "tier_support": manifest.classification.tier_support,
        "capabilities": manifest.capabilities,
        "exported_skill_ids": manifest.skills.exported_skill_ids,
        "hidden_skill_ids": manifest.skills.hidden_skill_ids,
        "version": manifest.versioning.version,
        "maturity": manifest.quality.maturity,
        "tenant_id": tenant_id,
    }

    doc = Document(id=manifest.agent_id, data=agent_data)
    await _store.save(Collection.Agent, doc)

    node = Node(
        id=manifest.agent_id,
        node_type="Agent",
        properties={
            "domain": manifest.classification.domain,
            "tenant_id": tenant_id,
        },
    )
    await _store.save_node(node)

    for skill_id in skill_ids:
        await _store.save_edge(manifest.agent_id, skill_id, EdgeType.References)

    return manifest.agent_id
