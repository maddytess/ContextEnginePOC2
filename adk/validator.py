import re

from .models import AgentManifest, SkillManifestYaml, ValidationResult

_VALID_OUTPUT_TYPES = {"finding", "report", "plan", "triage", "closure_summary"}
_VALID_EXEC_LOCATIONS = {"client", "server", "hybrid"}
_WRITE_TOOL_CLASSES = {"action_write", "supervised_write", "automated_write"}
_AGENT_ID_RE = re.compile(r"^domain\.[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def validate_package(manifest: AgentManifest, skills: list[SkillManifestYaml]) -> ValidationResult:
    result = ValidationResult()
    _validate_agent(manifest, skills, result)
    for skill in skills:
        _validate_skill(skill, manifest, result)
    return result


def _validate_agent(manifest: AgentManifest, skills: list[SkillManifestYaml], result: ValidationResult) -> None:
    if not _AGENT_ID_RE.match(manifest.agent_id):
        result.errors.append(
            f"agent_id {manifest.agent_id!r} must match format domain.{{domain}}.{{name}} "
            f"(e.g. domain.security.exposure)"
        )

    if not manifest.capabilities:
        result.errors.append("agent.yaml: capabilities must have at least one entry")

    if not _SEMVER_RE.match(manifest.versioning.version):
        result.errors.append(f"agent.yaml: version {manifest.versioning.version!r} is not valid semver (X.Y.Z)")

    skill_map = {s.skill_id: s for s in skills}
    for sid in manifest.skills.exported_skill_ids:
        if sid not in skill_map:
            result.errors.append(f"agent.yaml: exported_skill_id {sid!r} has no corresponding skill.yaml in package")
    for sid in manifest.skills.hidden_skill_ids:
        if sid not in skill_map:
            result.errors.append(f"agent.yaml: hidden_skill_id {sid!r} has no corresponding skill.yaml in package")


def _validate_skill(skill: SkillManifestYaml, manifest: AgentManifest, result: ValidationResult) -> None:
    prefix = f"skill {skill.skill_id!r}:"

    for field_name, value in [
        ("purpose", skill.purpose),
        ("description", skill.description),
        ("display_name", skill.display_name),
    ]:
        if not value or not value.strip():
            result.errors.append(f"{prefix} {field_name} is required and must be non-empty")

    if not skill.capabilities:
        result.errors.append(f"{prefix} capabilities[] must have at least one entry")

    if not skill.context_descriptions:
        result.errors.append(f"{prefix} context_descriptions[] must have at least one entry")

    if skill.output_type not in _VALID_OUTPUT_TYPES:
        result.errors.append(
            f"{prefix} output_type {skill.output_type!r} must be one of {sorted(_VALID_OUTPUT_TYPES)}"
        )

    bad_locs = set(skill.tool_affinity.execution_locations) - _VALID_EXEC_LOCATIONS
    if bad_locs:
        result.errors.append(
            f"{prefix} tool_affinity.execution_locations contains invalid values: {sorted(bad_locs)}. "
            f"Must be subset of {sorted(_VALID_EXEC_LOCATIONS)}"
        )

    write_classes = set(skill.tool_affinity.allowed_tool_classes) & _WRITE_TOOL_CLASSES
    if write_classes:
        result.errors.append(
            f"{prefix} CE-013: skill references write tool class(es): {sorted(write_classes)}. "
            f"Skills are readonly only."
        )

    if skill.action_semantics.can_request_execution:
        result.errors.append(
            f"{prefix} CE-013: action_semantics.can_request_execution must be false for skills"
        )

    if not _SEMVER_RE.match(skill.version):
        result.errors.append(f"{prefix} version {skill.version!r} is not valid semver (X.Y.Z)")

    if skill.execution_plan is not None:
        _validate_execution_plan(skill, result)


def _validate_execution_plan(skill: SkillManifestYaml, result: ValidationResult) -> None:
    plan = skill.execution_plan
    prefix = f"skill {skill.skill_id!r} execution_plan:"

    step_ids = {s.step_id for s in plan.steps}

    has_root = any(not s.depends_on for s in plan.steps)
    if plan.steps and not has_root:
        result.errors.append(f"{prefix} no step has empty depends_on — nothing can start")

    for step in plan.steps:
        if step.context_type not in skill.supported_context_types:
            result.errors.append(
                f"{prefix} step {step.step_id!r}: context_type {step.context_type!r} "
                f"not in supported_context_types"
            )
        if step.tool_class not in skill.tool_affinity.allowed_tool_classes:
            result.warnings.append(
                f"{prefix} step {step.step_id!r}: tool_class {step.tool_class!r} "
                f"not in tool_affinity.allowed_tool_classes"
            )
        for dep in step.depends_on:
            if dep not in step_ids:
                result.errors.append(
                    f"{prefix} step {step.step_id!r}: depends_on references unknown step {dep!r}"
                )
