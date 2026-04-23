import os
from pathlib import Path

import yaml

from .models import AgentManifest, SkillManifestYaml


def load_package(package_dir: str) -> tuple[AgentManifest, list[SkillManifestYaml]]:
    root = Path(package_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"Package directory not found: {package_dir}")

    agent_path = root / "agent.yaml"
    if not agent_path.exists():
        raise FileNotFoundError(f"agent.yaml not found in {package_dir}")

    with open(agent_path) as f:
        agent_data = yaml.safe_load(f)
    manifest = AgentManifest.model_validate(agent_data)

    skill_ids = list(manifest.skills.exported_skill_ids) + list(manifest.skills.hidden_skill_ids)
    skills: list[SkillManifestYaml] = []

    skills_dir = root / "skills"
    for skill_id in skill_ids:
        skill_name = skill_id.split(".")[-1]
        skill_path = _find_skill_yaml(skills_dir, skill_id, skill_name)
        if skill_path is None:
            raise FileNotFoundError(
                f"skill.yaml not found for skill_id={skill_id!r}. "
                f"Looked in: {skills_dir / skill_name}/skill.yaml and {skills_dir / skill_id}/skill.yaml"
            )
        with open(skill_path) as f:
            skill_data = yaml.safe_load(f)
        skill = SkillManifestYaml.model_validate(skill_data)
        skills.append(skill)

    return manifest, skills


def _find_skill_yaml(skills_dir: Path, skill_id: str, skill_name: str) -> Path | None:
    candidates = [
        skills_dir / skill_name / "skill.yaml",
        skills_dir / skill_id / "skill.yaml",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None
