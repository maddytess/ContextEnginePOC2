import asyncio
from asset_store.db import get_db

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
DEFINE FIELD IF NOT EXISTS output_type             ON escher_skills_global TYPE string;
DEFINE FIELD IF NOT EXISTS output_schema_ref       ON escher_skills_global TYPE option<string>;
DEFINE FIELD IF NOT EXISTS context_builder_ids     ON escher_skills_global TYPE array<string>;
DEFINE FIELD IF NOT EXISTS supported_context_types ON escher_skills_global TYPE array<string>;
DEFINE FIELD IF NOT EXISTS capabilities            ON escher_skills_global TYPE array<string>;
DEFINE FIELD IF NOT EXISTS context_descriptions    ON escher_skills_global TYPE array<string>;
DEFINE FIELD IF NOT EXISTS tool_affinity                              ON escher_skills_global TYPE object;
DEFINE FIELD IF NOT EXISTS tool_affinity.allowed_tool_classes         ON escher_skills_global TYPE array<string>;
DEFINE FIELD IF NOT EXISTS tool_affinity.preferred_tool_tags          ON escher_skills_global TYPE array<string>;
DEFINE FIELD IF NOT EXISTS tool_affinity.execution_locations          ON escher_skills_global TYPE array<string>;

DEFINE FIELD IF NOT EXISTS execution_plan                              ON escher_skills_global TYPE object;
DEFINE FIELD IF NOT EXISTS execution_plan.on_partial_failure           ON escher_skills_global TYPE string;
DEFINE FIELD IF NOT EXISTS execution_plan.steps                        ON escher_skills_global TYPE array;
DEFINE FIELD IF NOT EXISTS execution_plan.steps[*]                     ON escher_skills_global TYPE object;
DEFINE FIELD IF NOT EXISTS execution_plan.steps[*].step_id             ON escher_skills_global TYPE string;
DEFINE FIELD IF NOT EXISTS execution_plan.steps[*].context_type        ON escher_skills_global TYPE string;
DEFINE FIELD IF NOT EXISTS execution_plan.steps[*].tool_class          ON escher_skills_global TYPE string;
DEFINE FIELD IF NOT EXISTS execution_plan.steps[*].depends_on          ON escher_skills_global TYPE array<string>;
DEFINE FIELD IF NOT EXISTS execution_plan.steps[*].required            ON escher_skills_global TYPE bool;
DEFINE FIELD IF NOT EXISTS execution_plan.steps[*].on_failure          ON escher_skills_global TYPE string;

DEFINE FIELD IF NOT EXISTS artifact_effects            ON escher_skills_global TYPE object;
DEFINE FIELD IF NOT EXISTS artifact_effects.can_create ON escher_skills_global TYPE array<string>;
DEFINE FIELD IF NOT EXISTS artifact_effects.can_update ON escher_skills_global TYPE array<string>;
DEFINE FIELD IF NOT EXISTS artifact_effects.can_enrich ON escher_skills_global TYPE array<string>;

DEFINE FIELD IF NOT EXISTS action_semantics                                    ON escher_skills_global TYPE object;
DEFINE FIELD IF NOT EXISTS action_semantics.can_request_execution              ON escher_skills_global TYPE bool;
DEFINE FIELD IF NOT EXISTS action_semantics.can_generate_plan_fragments        ON escher_skills_global TYPE bool;
DEFINE FIELD IF NOT EXISTS action_semantics.can_generate_bundle_hints          ON escher_skills_global TYPE bool;
DEFINE FIELD IF NOT EXISTS action_semantics.can_generate_playbook_candidates   ON escher_skills_global TYPE bool;

DEFINE FIELD IF NOT EXISTS safety                             ON escher_skills_global TYPE object;
DEFINE FIELD IF NOT EXISTS safety.safety_class                ON escher_skills_global TYPE string;
DEFINE FIELD IF NOT EXISTS safety.requires_human_review_for   ON escher_skills_global TYPE array<string>;

DEFINE FIELD IF NOT EXISTS evidence                  ON escher_skills_global TYPE object;
DEFINE FIELD IF NOT EXISTS evidence.emits_rationale  ON escher_skills_global TYPE bool;
DEFINE FIELD IF NOT EXISTS evidence.emits_confidence ON escher_skills_global TYPE bool;
DEFINE FIELD IF NOT EXISTS version                 ON escher_skills_global TYPE option<string>;
DEFINE FIELD IF NOT EXISTS embedding               ON escher_skills_global TYPE array<float>;

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
