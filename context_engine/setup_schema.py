import asyncio
from .db import get_db

DDL = """
DEFINE TABLE IF NOT EXISTS escher_skills_global SCHEMAFULL;

DEFINE FIELD IF NOT EXISTS skill_id            ON escher_skills_global TYPE string;
DEFINE FIELD IF NOT EXISTS display_name        ON escher_skills_global TYPE string;
DEFINE FIELD IF NOT EXISTS owner_agent_id      ON escher_skills_global TYPE string;
DEFINE FIELD IF NOT EXISTS capability_id       ON escher_skills_global TYPE string;
DEFINE FIELD IF NOT EXISTS domain              ON escher_skills_global TYPE string;
DEFINE FIELD IF NOT EXISTS tier                ON escher_skills_global TYPE string;
DEFINE FIELD IF NOT EXISTS status              ON escher_skills_global TYPE string;
DEFINE FIELD IF NOT EXISTS tenant_id           ON escher_skills_global TYPE option<string>;
DEFINE FIELD IF NOT EXISTS purpose             ON escher_skills_global TYPE string;
DEFINE FIELD IF NOT EXISTS description         ON escher_skills_global TYPE string;
DEFINE FIELD IF NOT EXISTS output_type         ON escher_skills_global TYPE string;
DEFINE FIELD IF NOT EXISTS context_builder_ids ON escher_skills_global TYPE array<string>;
DEFINE FIELD IF NOT EXISTS supported_context_types ON escher_skills_global TYPE array<string>;
DEFINE FIELD IF NOT EXISTS embedding           ON escher_skills_global TYPE array<float>;

DEFINE INDEX IF NOT EXISTS skill_id_idx ON escher_skills_global FIELDS skill_id UNIQUE;
DEFINE INDEX IF NOT EXISTS skill_embedding_idx ON escher_skills_global
    FIELDS embedding HNSW DIMENSION 768 DIST COSINE TYPE F32;
"""


async def setup_schema():
    async with get_db() as db:
        await db.query(DDL)
        print("Schema ready: escher_skills_global table + HNSW index defined.")


if __name__ == "__main__":
    asyncio.run(setup_schema())
