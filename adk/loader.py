import json
from pathlib import Path

import yaml

from .models import (
    AgentManifest, ContextBuilderManifestYaml, Package, SkillManifestYaml, ToolManifestYaml,
)


def load_package(package_dir: str) -> Package:
    root = Path(package_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"Package directory not found: {package_dir}")

    agent_path = root / "agent.yaml"
    if not agent_path.exists():
        raise FileNotFoundError(f"agent.yaml not found in {package_dir}")

    with open(agent_path) as f:
        agent_data = yaml.safe_load(f)
    manifest = AgentManifest.model_validate(agent_data)

    return Package(
        manifest=manifest,
        skills=_load_skills(root, manifest),
        tools=_load_tools(root),
        context_builders=_load_context_builders(root),
    )


def _load_skills(root: Path, manifest: AgentManifest) -> list[SkillManifestYaml]:
    skill_ids = list(manifest.skills.exported_skill_ids) + list(manifest.skills.hidden_skill_ids)
    skills: list[SkillManifestYaml] = []
    skills_dir = root / "skills"

    for skill_id in skill_ids:
        skill_name = skill_id.split(".")[-1]
        skill_path = _find_skill_manifest(skills_dir, skill_id, skill_name)
        if skill_path is None:
            raise FileNotFoundError(
                f"skill manifest not found for skill_id={skill_id!r}. "
                f"Looked for skill.json and skill.yaml under {skills_dir / skill_name} and {skills_dir / skill_id}"
            )
        skills.append(SkillManifestYaml.model_validate(_load_file(skill_path)))

    return skills


def _load_tools(root: Path) -> list[ToolManifestYaml]:
    tools_dir = root / "tools"
    if not tools_dir.is_dir():
        return []
    paths = sorted(tools_dir.glob("*.json")) or sorted(tools_dir.glob("*.yaml"))
    return [ToolManifestYaml.model_validate(_load_file(p)) for p in paths]


def _load_context_builders(root: Path) -> list[ContextBuilderManifestYaml]:
    cb_dir = root / "context_builders"
    if not cb_dir.is_dir():
        return []
    cbs: list[ContextBuilderManifestYaml] = []
    for path in sorted(cb_dir.glob("*.yaml")):
        cbs.append(ContextBuilderManifestYaml.model_validate(_load_file(path)))
    return cbs


def _find_skill_manifest(skills_dir: Path, skill_id: str, skill_name: str) -> Path | None:
    for base in [skills_dir / skill_name, skills_dir / skill_id]:
        for ext in (".json", ".yaml"):
            p = base / f"skill{ext}"
            if p.exists():
                return p
    return None


def _load_file(path: Path) -> dict:
    with open(path) as f:
        if path.suffix == ".json":
            return json.load(f)
        return yaml.safe_load(f)
