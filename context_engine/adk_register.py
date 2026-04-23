from asset_store import Collection, Document, SurrealAssetStore
from .models import SkillRecord


async def register_skills(skills: list[SkillRecord]) -> None:
    store = SurrealAssetStore()
    for skill in skills:
        doc = Document(id=skill.skill_id, data=skill.model_dump())
        await store.save(Collection.Skill, doc)
        print(f"  Registered: {skill.skill_id}")
