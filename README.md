# v4-architecture-docs

Architecture specification for the Escher v4 platform. This repository contains the design documents that define how the platform is built — not implementation code.

---

## Documents

| File | What it covers |
|---|---|
| [framework.md](framework.md) | Runtime Framework — the stateless execution engine. Three execution flows, three agent formulas, Gateway phase routing, broad flow, evidence and artifact model. Start here for the overall picture. |
| [agents.yaml.md](agents.yaml.md) | `agent.yaml` canonical spec — the single source of truth authored by domain teams. All sections, validation rules, ADK placement map, and a full worked example (Security Exposure Agent). |
| [context_engine.md](context_engine.md) | Context Engine — intent-based API, all nine CE endpoints with request/response schemas, collection tenancy model, Tag Store, collection schemas, graph layer, CRUD validation rules, and error codes. |
| [context_manager.md](context_manager.md) | Context Manager (Tauri plugin) — client-side estate store (local RAG), serial DB schema, entry mode detection, request assembly per flow, plan tracking, synthesis trigger, skill execution, estate sync, and the full Tauri command/event interface. |
| [adk.md](adk.md) | Agent Development Kit — authoring, validation, and registration toolchain. Asset placement map, readonly vs write enforcement, capabilities and skill embedding strategy, playbook candidate save-back, package structure, and per-asset CRUD rules. |
| [schema_json.md](schema_json.md) | Full JSON document schemas for every Context Engine collection, with indexes, embedding strategies, query patterns, and a formula-to-collection-to-phase mapping table. |

---

## Platform at a Glance

```
Domain team authors agent.yaml
  ↓
ADK validates, embeds, splits, and registers into Context Engine
  ↓
Client (Tauri) — Context Manager attaches estate, detects entry mode, sends to Gateway
  ↓
Gateway classifies intent → routes to correct flow
  ↓
  Flow 1 (Skill)     → client executes skill locally → Analysis Agent → UI Agent → client
  Flow 2 (Knowledge) → Analysis Agent (server) → UI Agent → client
  Flow 3 (Playbook)  → 8-state machine → user confirms plan → execute → client
  ↓
Context Manager persists artifacts + evidence to local serial DB
```

**What never leaves the client machine:** estate data, conversation history, credentials, artifacts, evidence.

**What the server holds between calls:** nothing. All state arrives pre-assembled per request.

---

## Key Concepts

**Three formulas, not 100 agents.** Every request resolves to one of three formulas — `Agent_skill`, `Agent_knowledge`, `Agent_playbook`. The formula is fixed; only the registered asset values substituted into it change.

**Readonly vs write — hard split.** Skills are readonly only (analyze, detect, assess). Playbooks are write only (mutate resources, require user confirmation). Enforced at ADK registration and again at runtime.

**agent.yaml is the only authoring surface.** Domain teams write one file. ADK splits it and places each section into the correct Context Engine collection. The Runtime Framework never reads `agent.yaml` directly.

**Tags are the connective tissue.** Internal tags (server-only, TTL-cleared per request) carry `skill_id`, `playbook_id`, `context_builder_ids`, `param_set`, and routing metadata between agents without any agent holding persistent state. External tags (`request_id`, `session_id`, `status`, `output_type`) are the only tag surface visible to the client.

**Tenant isolation is architectural.** Separate collections per tenant, not query filters. Tenant results always take precedence over global. The only exception: guardrails are always `global ∪ tenant` — tenant guardrails add to global, never replace.
