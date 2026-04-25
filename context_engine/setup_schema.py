import asyncio
from asset_store.db import get_db

DDL = """
-- ── Skill collection ──────────────────────────────────────────────────────────
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

-- ── Agent Registry ─────────────────────────────────────────────────────────────
DEFINE TABLE IF NOT EXISTS escher_agent_registry_global SCHEMAFULL;

DEFINE FIELD IF NOT EXISTS agent_id         ON escher_agent_registry_global TYPE string;
DEFINE FIELD IF NOT EXISTS name             ON escher_agent_registry_global TYPE string;
DEFINE FIELD IF NOT EXISTS display_name     ON escher_agent_registry_global TYPE string;
DEFINE FIELD IF NOT EXISTS agent_type       ON escher_agent_registry_global TYPE string;
DEFINE FIELD IF NOT EXISTS status           ON escher_agent_registry_global TYPE string;
DEFINE FIELD IF NOT EXISTS owner_team       ON escher_agent_registry_global TYPE string;
DEFINE FIELD IF NOT EXISTS owner_contact    ON escher_agent_registry_global TYPE string;
DEFINE FIELD IF NOT EXISTS purpose          ON escher_agent_registry_global TYPE string;
DEFINE FIELD IF NOT EXISTS description      ON escher_agent_registry_global TYPE string;
DEFINE FIELD IF NOT EXISTS domain           ON escher_agent_registry_global TYPE string;
DEFINE FIELD IF NOT EXISTS product_scope    ON escher_agent_registry_global TYPE string;
DEFINE FIELD IF NOT EXISTS tier_support     ON escher_agent_registry_global TYPE array<string>;
DEFINE FIELD IF NOT EXISTS capabilities     ON escher_agent_registry_global TYPE array<string>;
DEFINE FIELD IF NOT EXISTS exported_skill_ids ON escher_agent_registry_global TYPE array<string>;
DEFINE FIELD IF NOT EXISTS hidden_skill_ids   ON escher_agent_registry_global TYPE array<string>;
DEFINE FIELD IF NOT EXISTS version          ON escher_agent_registry_global TYPE option<string>;
DEFINE FIELD IF NOT EXISTS maturity         ON escher_agent_registry_global TYPE option<string>;
DEFINE FIELD IF NOT EXISTS tenant_id        ON escher_agent_registry_global TYPE option<string>;
DEFINE FIELD IF NOT EXISTS embedding        ON escher_agent_registry_global TYPE array<float>;

DEFINE INDEX IF NOT EXISTS agent_id_idx ON escher_agent_registry_global FIELDS agent_id UNIQUE;
DEFINE INDEX IF NOT EXISTS agent_embedding_idx ON escher_agent_registry_global
    FIELDS embedding HNSW DIMENSION 768 DIST COSINE TYPE F32;

-- ── Tool collection ───────────────────────────────────────────────────────────
DEFINE TABLE IF NOT EXISTS escher_tools_global SCHEMAFULL;

DEFINE FIELD IF NOT EXISTS tool_id            ON escher_tools_global TYPE string;
DEFINE FIELD IF NOT EXISTS name               ON escher_tools_global TYPE string;
DEFINE FIELD IF NOT EXISTS purpose            ON escher_tools_global TYPE string;
DEFINE FIELD IF NOT EXISTS tool_class         ON escher_tools_global TYPE string;
DEFINE FIELD IF NOT EXISTS tool_type          ON escher_tools_global TYPE string;
DEFINE FIELD IF NOT EXISTS domain             ON escher_tools_global TYPE array<string>;
DEFINE FIELD IF NOT EXISTS provider           ON escher_tools_global TYPE string;
DEFINE FIELD IF NOT EXISTS resource_types     ON escher_tools_global TYPE array<string>;
DEFINE FIELD IF NOT EXISTS api_calls          ON escher_tools_global TYPE array<string>;
DEFINE FIELD IF NOT EXISTS execution_location ON escher_tools_global TYPE string;
DEFINE FIELD IF NOT EXISTS execution_timeout  ON escher_tools_global TYPE int;
DEFINE FIELD IF NOT EXISTS input_schema                        ON escher_tools_global TYPE object;
DEFINE FIELD IF NOT EXISTS input_schema.parameters             ON escher_tools_global TYPE array;
DEFINE FIELD IF NOT EXISTS input_schema.parameters[*]          ON escher_tools_global TYPE object;
DEFINE FIELD IF NOT EXISTS input_schema.parameters[*].name     ON escher_tools_global TYPE string;
DEFINE FIELD IF NOT EXISTS input_schema.parameters[*].type     ON escher_tools_global TYPE string;
DEFINE FIELD IF NOT EXISTS input_schema.parameters[*].required ON escher_tools_global TYPE bool;
DEFINE FIELD IF NOT EXISTS input_schema.parameters[*].description ON escher_tools_global TYPE string;
DEFINE FIELD IF NOT EXISTS output_schema_ref  ON escher_tools_global TYPE string;
DEFINE FIELD IF NOT EXISTS safety_class       ON escher_tools_global TYPE string;
DEFINE FIELD IF NOT EXISTS auth               ON escher_tools_global TYPE option<string>;
DEFINE FIELD IF NOT EXISTS cacheable          ON escher_tools_global TYPE option<bool>;
DEFINE FIELD IF NOT EXISTS idempotent             ON escher_tools_global TYPE option<bool>;
DEFINE FIELD IF NOT EXISTS requires_human_review  ON escher_tools_global TYPE option<bool>;
DEFINE FIELD IF NOT EXISTS rollback_supported     ON escher_tools_global TYPE option<bool>;
DEFINE FIELD IF NOT EXISTS rollback_api           ON escher_tools_global TYPE option<array<string>>;
DEFINE FIELD IF NOT EXISTS version            ON escher_tools_global TYPE string;
DEFINE FIELD IF NOT EXISTS tenant_id          ON escher_tools_global TYPE option<string>;
DEFINE FIELD IF NOT EXISTS embedding          ON escher_tools_global TYPE array<float>;

DEFINE INDEX IF NOT EXISTS tool_id_idx ON escher_tools_global FIELDS tool_id UNIQUE;
DEFINE INDEX IF NOT EXISTS tool_embedding_idx ON escher_tools_global
    FIELDS embedding HNSW DIMENSION 768 DIST COSINE TYPE F32;

-- ── Context Builder collection ────────────────────────────────────────────────
DEFINE TABLE IF NOT EXISTS escher_context_builders_global SCHEMAFULL;

DEFINE FIELD IF NOT EXISTS context_builder_id ON escher_context_builders_global TYPE string;
DEFINE FIELD IF NOT EXISTS name               ON escher_context_builders_global TYPE string;
DEFINE FIELD IF NOT EXISTS display_name       ON escher_context_builders_global TYPE string;
DEFINE FIELD IF NOT EXISTS domain             ON escher_context_builders_global TYPE string;
DEFINE FIELD IF NOT EXISTS data_type          ON escher_context_builders_global TYPE string;
DEFINE FIELD IF NOT EXISTS provider           ON escher_context_builders_global TYPE string;
DEFINE FIELD IF NOT EXISTS status             ON escher_context_builders_global TYPE string;
DEFINE FIELD IF NOT EXISTS tenant_id          ON escher_context_builders_global TYPE option<string>;
DEFINE FIELD IF NOT EXISTS purpose            ON escher_context_builders_global TYPE string;
DEFINE FIELD IF NOT EXISTS output_schema_ref  ON escher_context_builders_global TYPE string;
DEFINE FIELD IF NOT EXISTS version            ON escher_context_builders_global TYPE string;

DEFINE FIELD IF NOT EXISTS collection_units                                        ON escher_context_builders_global TYPE array;
DEFINE FIELD IF NOT EXISTS collection_units[*]                                     ON escher_context_builders_global TYPE object;
DEFINE FIELD IF NOT EXISTS collection_units[*].unit_id                             ON escher_context_builders_global TYPE string;
DEFINE FIELD IF NOT EXISTS collection_units[*].purpose                             ON escher_context_builders_global TYPE string;
DEFINE FIELD IF NOT EXISTS collection_units[*].required                            ON escher_context_builders_global TYPE bool;
DEFINE FIELD IF NOT EXISTS collection_units[*].context_type                        ON escher_context_builders_global TYPE string;
DEFINE FIELD IF NOT EXISTS collection_units[*].preferred_tool_classes              ON escher_context_builders_global TYPE array<string>;
DEFINE FIELD IF NOT EXISTS collection_units[*].preferred_tool_tags                 ON escher_context_builders_global TYPE array<string>;
DEFINE FIELD IF NOT EXISTS collection_units[*].execution_locations                 ON escher_context_builders_global TYPE array<string>;
DEFINE FIELD IF NOT EXISTS collection_units[*].freshness_window                    ON escher_context_builders_global TYPE string;
DEFINE FIELD IF NOT EXISTS collection_units[*].cache_policy                        ON escher_context_builders_global TYPE string;
DEFINE FIELD IF NOT EXISTS collection_units[*].normalization_schema_ref            ON escher_context_builders_global TYPE string;

DEFINE FIELD IF NOT EXISTS orchestration                         ON escher_context_builders_global TYPE option<object>;
DEFINE FIELD IF NOT EXISTS orchestration.merge_strategy          ON escher_context_builders_global TYPE option<string>;
DEFINE FIELD IF NOT EXISTS orchestration.dedupe_keys             ON escher_context_builders_global TYPE option<array<string>>;
DEFINE FIELD IF NOT EXISTS orchestration.max_parallel_units      ON escher_context_builders_global TYPE option<int>;

DEFINE FIELD IF NOT EXISTS fallbacks                                          ON escher_context_builders_global TYPE option<object>;
DEFINE FIELD IF NOT EXISTS fallbacks.on_missing_required_context              ON escher_context_builders_global TYPE option<string>;
DEFINE FIELD IF NOT EXISTS fallbacks.fallback_probe_policy                    ON escher_context_builders_global TYPE option<string>;

DEFINE FIELD IF NOT EXISTS embedding ON escher_context_builders_global TYPE array<float>;

DEFINE INDEX IF NOT EXISTS cb_id_idx ON escher_context_builders_global FIELDS context_builder_id UNIQUE;
DEFINE INDEX IF NOT EXISTS cb_embedding_idx ON escher_context_builders_global
    FIELDS embedding HNSW DIMENSION 768 DIST COSINE TYPE F32;

-- ── Graph nodes (SCHEMALESS — typed by node_type field) ───────────────────────
DEFINE TABLE IF NOT EXISTS escher_nodes SCHEMALESS;
"""


async def setup_schema():
    async with get_db() as db:
        await db.query(DDL)
        print("Schema ready: escher_skills_global, escher_agent_registry_global, escher_tools_global, escher_nodes defined.")


if __name__ == "__main__":
    asyncio.run(setup_schema())
