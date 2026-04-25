from typing import Optional

from asset_store import AssetStore, Collection, Document, EdgeType, Node, SurrealAssetStore
from adk.models import SkillManifestYaml
from context_engine.models import (
    ActionSemantics, ArtifactEffects, Evidence, ExecutionPlan, ExecutionStep,
    Safety, SkillRecord, ToolAffinity,
)

_store: AssetStore = SurrealAssetStore()


async def register_skill(
    skill: SkillManifestYaml,
    owner_agent_id: str,
    tenant_id: Optional[str],
) -> str:
    record = _to_skill_record(skill, owner_agent_id, tenant_id)
    doc = Document(id=record.skill_id, data=record.model_dump())
    await _store.save(Collection.Skill, doc)

    node = Node(
        id=skill.skill_id,
        node_type="Skill",
        properties={
            "domain": skill.domain,
            "owner_agent_id": owner_agent_id,
            "tenant_id": tenant_id,
        },
    )
    await _store.save_node(node)

    # Skill → References → ContextBuilder (graph edge for each declared context builder)
    for cb_id in skill.context_builder_ids:
        await _store.save_edge(skill.skill_id, cb_id, EdgeType.References)

    return skill.skill_id


def _to_skill_record(skill: SkillManifestYaml, owner_agent_id: str, tenant_id: Optional[str]) -> SkillRecord:
    plan = None
    if skill.execution_plan is not None:
        plan = ExecutionPlan(
            steps=[
                ExecutionStep(
                    step_id=s.step_id,
                    context_type=s.context_type,
                    tool_class=s.tool_class,
                    depends_on=s.depends_on,
                    required=s.required,
                    on_failure=s.on_failure,
                )
                for s in skill.execution_plan.steps
            ],
            on_partial_failure=skill.execution_plan.on_partial_failure,
        )
    else:
        plan = ExecutionPlan()

    return SkillRecord(
        skill_id=skill.skill_id,
        display_name=skill.display_name,
        owner_agent_id=owner_agent_id,
        capability_id=skill.capability_id,
        domain=skill.domain,
        tier=skill.tier,
        status=skill.status,
        tenant_id=tenant_id,
        purpose=skill.purpose,
        description=skill.description,
        capabilities=skill.capabilities,
        context_descriptions=skill.context_descriptions,
        output_type=skill.output_type,
        output_schema_ref=skill.output_schema_ref,
        context_builder_ids=skill.context_builder_ids,
        supported_context_types=skill.supported_context_types,
        tool_affinity=ToolAffinity(
            allowed_tool_classes=skill.tool_affinity.allowed_tool_classes,
            preferred_tool_tags=skill.tool_affinity.preferred_tool_tags,
            execution_locations=skill.tool_affinity.execution_locations,
        ),
        execution_plan=plan,
        artifact_effects=ArtifactEffects(
            can_create=skill.artifact_effects.can_create,
            can_update=skill.artifact_effects.can_update,
            can_enrich=skill.artifact_effects.can_enrich,
        ),
        action_semantics=ActionSemantics(
            can_request_execution=skill.action_semantics.can_request_execution,
            can_generate_plan_fragments=skill.action_semantics.can_generate_plan_fragments,
            can_generate_bundle_hints=skill.action_semantics.can_generate_bundle_hints,
            can_generate_playbook_candidates=skill.action_semantics.can_generate_playbook_candidates,
        ),
        safety=Safety(
            safety_class=skill.safety.safety_class,
            requires_human_review_for=skill.safety.requires_human_review_for,
        ),
        evidence=Evidence(
            emits_rationale=skill.evidence.emits_rationale,
            emits_confidence=skill.evidence.emits_confidence,
        ),
        version=skill.version,
    )
