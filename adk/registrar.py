from typing import Optional

from .models import AgentManifest, RegistrationResult, SkillManifestYaml
from context_engine.crud.skill import register_skill
from context_engine.crud.agent import register_agent


async def register_package(
    manifest: AgentManifest,
    skills: list[SkillManifestYaml],
    tenant_id: Optional[str] = None,
) -> RegistrationResult:
    skill_ids: list[str] = []
    for skill in skills:
        sid = await register_skill(skill, manifest.agent_id, tenant_id)
        skill_ids.append(sid)

    agent_id = await register_agent(manifest, skill_ids, tenant_id)

    return RegistrationResult(agent_id=agent_id, skill_ids=skill_ids)
