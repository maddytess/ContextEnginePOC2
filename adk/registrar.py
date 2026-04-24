from typing import Optional

from .models import AgentManifest, RegistrationResult, SkillManifestYaml, ToolManifestYaml
from context_engine.crud.skill import register_skill
from context_engine.crud.agent import register_agent
from context_engine.crud.tool import register_tool


async def register_package(
    manifest: AgentManifest,
    skills: list[SkillManifestYaml],
    tools: list[ToolManifestYaml],
    tenant_id: Optional[str] = None,
) -> RegistrationResult:
    # Tools registered first — skills may reference tool classes they provide
    tool_ids: list[str] = []
    for tool in tools:
        tid = await register_tool(tool)
        tool_ids.append(tid)

    skill_ids: list[str] = []
    for skill in skills:
        sid = await register_skill(skill, manifest.agent_id, tenant_id)
        skill_ids.append(sid)

    agent_id = await register_agent(manifest, skill_ids, tenant_id)

    return RegistrationResult(agent_id=agent_id, skill_ids=skill_ids, tool_ids=tool_ids)
