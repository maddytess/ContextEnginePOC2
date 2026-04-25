from typing import Optional

from .models import Package, RegistrationResult
from context_engine.crud.skill import register_skill
from context_engine.crud.agent import register_agent
from context_engine.crud.tool import register_tool
from context_engine.crud.context_builder import register_context_builder


async def register_package(pkg: Package, tenant_id: Optional[str] = None) -> RegistrationResult:
    tool_ids: list[str] = []
    for tool in pkg.tools:
        tool_ids.append(await register_tool(tool))

    cb_ids: list[str] = []
    for cb in pkg.context_builders:
        cb_ids.append(await register_context_builder(cb))

    skill_ids: list[str] = []
    for skill in pkg.skills:
        skill_ids.append(await register_skill(skill, pkg.manifest.agent_id, tenant_id))

    agent_id = await register_agent(pkg.manifest, skill_ids, tenant_id)

    return RegistrationResult(
        agent_id=agent_id,
        skill_ids=skill_ids,
        tool_ids=tool_ids,
        context_builder_ids=cb_ids,
    )
