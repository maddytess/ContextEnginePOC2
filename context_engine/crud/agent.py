from typing import Optional

from asset_store import AssetStore, Collection, Document, EdgeType, Node, SurrealAssetStore
from adk.models import AgentManifest

_store: AssetStore = SurrealAssetStore()


async def register_agent(
    manifest: AgentManifest,
    skill_ids: list[str],
    tenant_id: Optional[str],
) -> str:
    domain = manifest.classification.domain

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
        "domain": domain,
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

    # Domain node (idempotent upsert — shared across all agents in this domain)
    domain_node = Node(id=domain, node_type="Domain", properties={"domain": domain})
    await _store.save_node(domain_node)

    # Agent node
    agent_node = Node(
        id=manifest.agent_id,
        node_type="Agent",
        properties={"domain": domain, "tenant_id": tenant_id},
    )
    await _store.save_node(agent_node)

    # Domain → owns → Agent
    await _store.save_edge(domain, manifest.agent_id, EdgeType.Owns)

    # Agent → exports → Skill (exported_skill_ids only — hidden skills are not part of exported surface)
    exported = set(manifest.skills.exported_skill_ids)
    for skill_id in skill_ids:
        if skill_id in exported:
            await _store.save_edge(manifest.agent_id, skill_id, EdgeType.Exports)

    return manifest.agent_id
