import asyncio
from .db import get_db
from .embeddings import embed_skill
from .models import SkillRecord


async def register_skills(skills: list[SkillRecord]) -> None:
    async with get_db() as db:
        for skill in skills:
            embedding = embed_skill(skill)
            record = {
                **skill.model_dump(),
                "embedding": embedding,
            }
            # Upsert using skill_id as the record key
            record_id = f"escher_skills_global:`{skill.skill_id}`"
            await db.upsert(record_id, record)
            print(f"  Registered: {skill.skill_id}")


if __name__ == "__main__":
    from data.security_exposure_agent import SKILLS
    asyncio.run(register_skills(SKILLS))
