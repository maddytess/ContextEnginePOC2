# Escher Runtime Framework

## 1. Overview

The Runtime Framework is the execution engine owned by Escher core. It is stateless, formula-driven, and orchestrates every interaction between the client, the Context Engine, the Integration Service, and the LLM.

Domain teams and external developers do not interact with this directly — the ADK handles authoring and registration, the Context Engine handles server-side knowledge storage and retrieval, the Context Manager (Tauri plugin) manages client-side state and estate, and the Runtime Framework handles execution.

```
agent.yaml           → authored by domain team, single source of truth
ADK                  → splits agent.yaml, validates, places into Context Engine
Context Engine       → abstracts RAG + Graph, exposes intent-based API
Local Context        → client side estate + history + artifacts (Tauri plugin)
Integration Service  → manages all external system connections
Runtime Framework    → execution engine, orchestrates everything, stateless
```

---

## 2. Why This Approach

When teams first think about building an agentic platform, the natural instinct is one agent per domain, one agent per skill — each autonomous, each reasoning independently. For Escher that would mean 100+ agents. At scale this breaks down:

**Maintenance explosion** — 100 agents = 100 deployment units, 100 prompt contexts, 100 update surfaces.

**Fragmented reasoning** — A question like "my EC2 is slow and has a security risk?" gets split across agents that each see only a slice. No single agent reasons holistically.

**Hallucination risk** — Each isolated agent fills gaps with invented answers.

**This is why Escher does not follow the conventional agent model.** Instead of 100 autonomous agents, Escher has three formulas and registered assets. The formulas execute for every request. Agents in Escher are stateless executors of deterministic formulas whose inputs are fully governed and traceable.

---

## 3. Core Design Rules

### 3.1 Readonly vs Operation — Fundamental Split

```
Skills     → readonly only
             analyze, detect, assess, summarize
             never mutate resources
             use readonly tools only

Tools      → used by both
             readonly tools → skills
             write tools    → playbooks only, never skills

Playbooks  → write only
             always mutates resources
             always requires user confirmation
             always produces evidence
             always plan-first
```

Enforced at two levels:
- ADK validates at registration — skill referencing write tool = registration failure
- Runtime Framework enforces at execution — skill cannot trigger write tool

### 3.2 Three Flows

```
Flow 1 — Skill         → skill found, client executes, tags connect phases
Flow 2 — Knowledge     → no skill, server reasons, gateway drives
Flow 3 — Playbook      → operation intent, state machine, plan-first always
```

Each flow is independent. Tags are the connective tissue between agents within a flow. No agent depends on another agent's internal state.

### 3.3 Tags

Tags are how agents know what to fetch from the Context Engine. Two sets:

```
Internal tags  → server only, never sent to client
                 full CE resolution info
                 stored in tag store keyed by request_id
                 TTL: request lifecycle

External tags  → client facing, minimal, opaque
                 {request_id, session_id, tenant_id,
                  plan_id, step_id, status, output_type}
```

For full tag schema see: **Escher Tags Specification**

### 3.4 Narrow vs Broad

```
Narrow → execute immediately (Flow 1 single agent):
  1 agent matched
  OR N agents, outputs converge on same type
  AND readonly

Broad → plan first (Flow 1 multi-agent):
  N agents with independent intents
  OR account-wide scope
  AND readonly
  → plan presented to user → confirm → execute parallel → synthesize
```

### 3.5 Code Agent as Fallback

```
Triggers when:
  READ path  → no skill matched at Phase 2C
  WRITE path → no playbook matched at Phase 2C

Grounding (fetched at Phase 2C miss — not re-fetched at Phase 5C):
  CE /resolve/agent    → capabilities + context boundary
  CE /answer/knowledge → Cloud Knowledge concept understanding

No new CE calls at Phase 5C.
Code Agent uses grounding passed from Phase 2C.

Output:
  READ miss  → generates skill candidate (readonly only)
               saves via ADK → Skill collection (is_candidate: true)
               user confirms → Phase 3

  WRITE miss → generates playbook candidate
               saves via ADK → Playbook collection (is_candidate: true)
               user confirms → Phase 5A
```

### 3.6 Integration Service

```
Standalone service — Framework never calls Slack, Jira, Linear directly

Touch points:
  Gateway Phase 2B → direct integration intent
  Flow 3 State 7   → playbook step notification
  Phase 9          → artifact events:
                       finding → jira
                       plan approved → slack
                       playbook complete → pagerduty
```

### 3.7 LLM + RAG — Not RAG Alone

```
Context Engine → retrieves registered, grounded knowledge
LLM            → reasons over retrieved knowledge
                 fills gaps intelligently
                 generates code when needed

Low CE confidence ≠ failure
LLM reasons intelligently over partial results
```

---

## 4. Agent Formulas

Three formulas — one per flow. Every execution is a substitution of registered asset values into the correct formula at runtime. The LLM is the reasoning engine inside the formula. The formula is the agent.

For tag schema used in each formula see: **Escher Tags Specification**
For agent.yaml section that sources each variable see: **Section 4.4 Formula → agent.yaml Mapping**

---

### 4.1 Formula 1 — Agent_skill (Flow 1)

**When:** Skill found, execution_location client or hybrid

```
Agent_skill(x, d, t, tags) =

  Skill(x, t→global)
    source:    CE /resolve/skill
    from:      agent.yaml → skills.exported_skill_ids
    tags used: skill_id, owner_agent_id, tenant_id

  ∪ ContextBuilder(x, global)
    source:    CE /resolve/context
    from:      agent.yaml → context.declared_context_builders
    tags used: context_builder_ids, tenant_id

  ∪ Estate(context_types, local)
    source:    client local RAG
    from:      agent.yaml → context.supported_context_types
    tags used: session_id
    rule:      scoped to supported_context_types — never full estate
               attached by client before sending to Gateway

  ∪ Tool_readonly(CB(x), global)
    source:    CE /resolve/context
    from:      agent.yaml → tool_access.readonly_tools
    tags used: context_builder_ids, tenant_id
    rule:      readonly tools only — write tools never in skill flow

  ∪ Guardrail(tags, global∪tenant)
    source:    CE /resolve/guardrails
    from:      agent.yaml → policy → Guardrail collection
    tags used: skill_id, owner_agent_id, domain, tenant_id
    rule:      global ∪ tenant always — never just one

  ∪ DomainLens(tags, t→global)           [advanced tier only]
    source:    CE /resolve/domain_knowledge
    from:      agent.yaml → domain_knowledge.lens
    tags used: domain, tier, tenant_id

  ∪ ExpertGraph(tags, t→global)          [advanced tier only]
    source:    CE /resolve/domain_knowledge
    from:      agent.yaml → domain_knowledge.expert_graph
    tags used: domain, tier, tenant_id

  ∪ Template(tags, t→global)
    source:    CE /resolve/template
    from:      Template collection via ADK
    tags used: skill_id, domain, output_type, tenant_id

  ∪ Artifact(x, t)
    source:    client serial DB
    from:      agent.yaml → artifacts.can_create
    tags used: session_id, tenant_id

  ∪ Evidence(runtime, t)
    source:    assembled at runtime, persisted by client
    tags used: session_id, tenant_id

Where:
  x     = skill_id resolved by CE /resolve/skill
  d     = domain from skill manifest
  t     = tenant_id from session tags
  tags  = internal tags — server side only
```

---

### 4.2 Formula 2 — Agent_knowledge (Flow 2)

**When:** No skill matched, general knowledge, server-side reasoning

```
Agent_knowledge(d, t, tags) =

  Capabilities(d, global)
    source:    CE /resolve/agent
    from:      agent.yaml → capabilities block (embedded as vectors)
    tags used: tenant_id, flow

  ∪ CloudKnowledge(d, global)
    source:    CE /answer/knowledge
    from:      CE Cloud Knowledge collection + Cloud Knowledge Graph
    tags used: domain, tenant_id
    rule:      RAG + graph combined internally by CE

  ∪ Estate(prompt_context, local)
    source:    client local RAG
    rule:      client attaches estate to initial prompt
               scoped to entities mentioned in prompt
               no context_builder — prompt-driven scoping

  ∪ Guardrail(tags, global∪tenant)
    source:    CE /resolve/guardrails
    from:      agent.yaml → policy → Guardrail collection
    tags used: domain, tenant_id
    rule:      global ∪ tenant always
               skill_id null — domain level guardrails only

  ∪ DomainLens(tags, t→global)           [advanced tier only]
    source:    CE /resolve/domain_knowledge
    from:      agent.yaml → domain_knowledge.lens
    tags used: domain, tier, tenant_id

  ∪ ExpertGraph(tags, t→global)          [advanced tier only]
    source:    CE /resolve/domain_knowledge
    from:      agent.yaml → domain_knowledge.expert_graph
    tags used: domain, tier, tenant_id

  ∪ Template(tags, t→global)
    source:    CE /resolve/template
    from:      Template collection via ADK
    tags used: domain, output_type, tenant_id
    note:      skill_id null — domain level template only

  ∪ Artifact(d, t)
    source:    client serial DB
    tags used: session_id, tenant_id

  ∪ Evidence(runtime, t)
    source:    assembled at runtime, persisted by client
    tags used: session_id, tenant_id

Where:
  x     = skill_id resolved by CE /resolve/skill
  d     = domain from skill manifest
  t     = tenant_id from session tags
  tags  = internal tags — server side only

Absent vs Agent_knowledge:
  owner_agent_id in tags → null
  skill_id in tags       → null
  context_builder_ids    → null
```

---

### 4.3 Formula 3 — Agent_playbook (Flow 3)

**When:** Operation/write intent, playbook flow

```
Agent_playbook(p, d, t, tags) =

  Playbook(p, t→global)
    source:    CE /resolve/playbook
    from:      agent.yaml → playbooks.owned_playbook_ids
               OR generated by CodeGen + saved via ADK
    tags used: playbook_id, domain, tenant_id
    rule:      CE searched first by trigger_conditions
               found → use registered playbook
               not found → CodeGen generates dynamically
               user decides to save or discard after execution

  ∪ Approach(CloudKnowledge, global)     [if no playbook found]
    source:    CE /answer/knowledge + CE /resolve/agent
    from:      CE Cloud Knowledge + Intent collection (capabilities)
    tags used: domain, tenant_id, language
    rule:      3-5 approaches generated by ApproachSelectionService
               user selects one → approach_id recorded in tags
               only called when Playbook(p) returns empty

  ∪ ContextBuilder(p, global)            [read-then-write steps only]
    source:    CE /resolve/context
    from:      agent.yaml → playbooks.context.declared_context_builders
    tags used: context_builder_ids, tenant_id
    rule:      optional — only for steps needing readonly context
               before write execution

  ∪ Estate(context_types, local)         [read-then-write steps only]
    source:    client local RAG
    from:      agent.yaml → playbooks.context.supported_context_types
    tags used: session_id
    rule:      only when ContextBuilder(p) is present

  ∪ Tool_write(p, global)
    source:    CE /resolve/tools
    from:      agent.yaml → tool_access.write_tools
    tags used: domain, tenant_id, language
    rule:      write tools only in playbook flow
               requires_human_review enforced before execution

  ∪ Params(user_input)
    source:    user — collected interactively via UI Agent
    from:      playbook.mandatory_parameters[]
    tags used: param_set in internal tags after collection
    rule:      loop until all mandatory params collected
               injected into scripts as ${user.X}
               never sent to client after injection

  ∪ Guardrail(tags, global∪tenant)
    source:    CE /resolve/guardrails
    from:      agent.yaml → policy → Guardrail collection
    tags used: playbook_id, domain, tenant_id
    rule:      global ∪ tenant always

  ∪ Template(tags, t→global)
    source:    CE /resolve/template
    from:      Template collection via ADK
    tags used: domain, output_type: closure_summary, tenant_id

  ∪ Evidence(execution, t)
    source:    captured per step during execution
    tags used: plan_id, step_id, session_id, tenant_id

  ∪ Artifact(p, t)
    source:    client serial DB
    tags used: session_id, tenant_id

Where:
  p     = playbook_id from CE or CodeGen
  d     = domain from playbook manifest
  t     = tenant_id from session tags
  tags  = internal tags — server side only
          each step has own request_id → own tag store entry

Absent vs Agent_skill:
  Skill(x)              → skills are readonly
                           playbooks handle write
  skill_id in tags      → null
  owner_agent_id in tags → null
```

---

### 4.4 Formula → agent.yaml Mapping

| Formula Variable | agent.yaml Section | CE API |
|---|---|---|
| Skill(x) | skills.exported_skill_ids | /resolve/skill |
| ContextBuilder(x) | context.declared_context_builders | /resolve/context |
| Estate (skill) | context.supported_context_types | client local RAG |
| Estate (playbook) | playbooks.context.supported_context_types | client local RAG |
| Tool_readonly | tool_access.readonly_tools | /resolve/context |
| Tool_write | tool_access.write_tools | /resolve/tools |
| Playbook(p) | playbooks.owned_playbook_ids | /resolve/playbook |
| Capabilities | capabilities block | /resolve/agent |
| CloudKnowledge | — platform owned | /answer/knowledge |
| Guardrail | policy block | /resolve/guardrails |
| DomainLens | domain_knowledge.lens | /resolve/domain_knowledge |
| ExpertGraph | domain_knowledge.expert_graph | /resolve/domain_knowledge |
| Template | — platform owned | /resolve/template |
| Artifact | artifacts block | client serial DB |
| Evidence | — runtime assembled | client serial DB |
| Params | playbooks.parameter_schema | user input |
| Approach | playbooks.approach_hints | ApproachSelectionService |

---

### 4.5 Formula Properties

**Completeness**
```
∀ formula:
  Every variable must resolve before execution
  Missing variable → validation error → stop

Agent_skill:
  Skill(x) ≠ ∅
  ContextBuilder(x) ≠ ∅
  Guardrail(tags) ≠ ∅ (minimum global)
  Template(tags) ≠ ∅ (minimum domain level)

Agent_knowledge:
  CloudKnowledge ≠ ∅ OR LLM fallback declared
  Guardrail(tags) ≠ ∅
  Template(tags) ≠ ∅

Agent_playbook:
  Playbook(p) ≠ ∅ (registered or generated)
  Guardrail(tags) ≠ ∅
  Template(tags) ≠ ∅
  Params complete if mandatory_parameters declared
```

**Substitutability**
```
Agent_skill(security.detect_public_ingress, security, t, tags)
Agent_skill(compliance.detect_soc2_gaps, compliance, t, tags)
Agent_skill(reliability.analyze_latency_spike, reliability, t, tags)
  → same formula, different values, same execution path
```

**Guardrail monotonicity**
```
∀ formula:
  Guardrail(tags, global∪tenant) =
    Guardrail(global) ∪ Guardrail(tenant)
  Always both. Never just one.
  Tenant adds to global. Never replaces.
```

**Tenant isolation**
```
∀ t₁ ≠ t₂:
  Agent_*(*, d, t₁, tags₁) ∩
  Agent_*(*, d, t₂, tags₂) =
    {global assets only}

Estate is always client local — physically isolated.
Evidence and Artifacts always tenant scoped.
Server holds no tenant state between calls.
```

**Local-first trust**
```
Estate data          → never leaves client machine
Conversation history → never leaves client machine
Credentials          → never leave client machine
Internal tags        → never sent to client
Server sees only     → prompt + estate_context + request metadata
```

---

## 5. Gateway — Unified Entry Point

The Gateway is the single entry point for all requests. It handles entry mode detection, intent classification, skill/playbook resolution, and routing to the correct flow.

```
Client sends:
  prompt + estate_context + session_id + tenant_id
  optional: target flag (t:h, t:p, t:br, cg)

Gateway does:
  1. Entry mode detection
  2. Intent classification (if Mode 1)
  3. Skill or playbook resolution (if cloud_intent)
  4. Tag assembly → writes to tag store
  5. Route to correct flow
```

### 5.1 Entry Mode Detection

```
MODE 1 — Full flow (default)
  No target flag, no prior session context
  → full classification → Phase 1

MODE 2 — Direct agent call
  Client sends target flag:
    t:h  → Analysis Agent directly
    t:p  → Playbook Agent directly
    t:br → Analysis Agent directly
    cg   → Code Agent directly
  Skips classification entirely

MODE 3 — Follow-up
  Client detects follow-up → sends directly to Analysis Agent
  Context Manager handles Mode 3 detection
  Gateway not involved
```

### 5.2 Intent Classification (Mode 1 — LLM Haiku)

```
greeting          → respond directly                    [TERMINAL]
unclear           → ask clarification                   [TERMINAL]

knowledge_intent  → Phase 2A
  pure conceptual, no estate, no resource action
  answer is same for everyone — no tenant data involved
  "when should I use ECS vs EC2?"
  "what is a security group?"
  "cloud functions vs lambda?"

integration_intent→ Phase 2B → Integration Service      [TERMINAL]
  "create a jira ticket"
  "notify slack"
  "open a github PR"

cloud_read        → Phase 2C
  involves customer estate, no mutation
  "show me unsecured EC2 instances in my account"
  "find public S3 buckets"
  "what security groups have open ingress?"

cloud_write       → Phase 3W
  involves customer resource mutation
  "remediate the exposed security group"
  "lock down public access on this bucket"
  "restart the degraded service"

Key distinction:
  knowledge_intent → no estate, same answer for everyone → Phase 2A
  cloud_read       → requires tenant estate, no mutation → Phase 2C
  cloud_write      → requires resource mutation          → Phase 3W
```

### 5.3 Phase 2A — General Knowledge

```
CE /answer/knowledge
  → Cloud Knowledge RAG + Cloud Knowledge Graph
  → returns enriched cloud concepts + relationships

LLM reasons over returned context
→ answer directly                                       [TERMINAL]

Fallback:
  nothing in CE → LLM answers from training
  caveat surfaced to user
```

### 5.4 Phase 2B — Integration Intent

```
Integration Service
  → resolve connector + execute action
  → create ticket / send message / open PR              [TERMINAL]
```

### 5.5 Phase 2C — Cloud Read (skill search only)

```
Entry: cloud_read from Phase 1

CE Skill collection search (semantic)
  embedding: purpose + description + display_name + capability_id
  filter:    status = active, tenant_id = tenant OR null
  │
  ├─ one skill matched   → narrow → Phase 3
  ├─ many skills matched → broad  → Phase 3
  └─ no skill matched    → MISS
        CE /resolve/agent
          → capabilities + context_types + context_builder_ids
          → domain boundary for Code Agent
        CE /answer/knowledge
          → Cloud Knowledge → concept understanding
        → Phase 5C

Phase 2C has one job: skill search + narrow vs broad decision.
No write logic here. No playbook search here.
```

### 5.6 Phase 3W — Cloud Write (playbook search only)

```
Entry: cloud_write from Phase 1

CE Playbook collection search (semantic, by trigger)
  embedding: trigger_conditions + display_name
  filter:    status = active, tenant_id = tenant OR null
  │
  ├─ playbook found  → Phase 3
  └─ no match        → MISS
        CE /resolve/agent
          → capabilities + context_types + context_builder_ids
          → domain boundary for Code Agent
        CE /answer/knowledge
          → Cloud Knowledge → concept understanding
        → Phase 5C

Phase 3W has one job: playbook search.
No read logic here. No skill search here.
```

### 5.6 Phase 3 — Skill / Playbook Resolution

```
READ path (from Phase 2C skill match):
  CE /resolve/skill
    → scoped to matched agent (owner_agent_id)
    → returns full skill manifest:
        skill_id, display_name, owner_agent_id
        domain, tier, purpose, description
        context_builder_ids, supported_context_types
        tool_affinity (readonly only)
        output_type, output_schema_ref
        artifact_effects, action_semantics
        safety, evidence
    → writes to Tag Store:
        skill_id, owner_agent_id, domain, tier,
        output_type, context_builder_ids
  → Phase 4

WRITE path (from Phase 2C playbook match):
  CE /resolve/playbook
    → direct lookup by playbook_id
    → returns full playbook manifest:
        steps, approaches, params, rollback
        context_builder_ids, supported_context_types
        safety_class, evidence_requirements
    → writes to Tag Store:
        playbook_id, domain, approach options
  → Phase 5A (skip Phase 4)
```

**Rule:** Phase 3 never decides read vs write. Split decided at Phase 2C. Phase 3 only resolves.

### 5.7 Tag Assembly

After Phase 3, Gateway writes final tags to Tag Store:

```
Narrow / Flow 1:
  Single request_id → single tag store entry
  External tags sent to client

Broad:
  One request_id per step + synthesis step
  Each written to tag store separately
  Plan object sent to client (external tags only)

Flow 3:
  One request_id per playbook step
  Each written to tag store separately
  Plan object sent to client (external tags only)
```

---

## 6. Three Flows

For full flow details see: **Escher — Three Execution Flows**

### Flow 1 — Skill (Client Executes)

**Formula:** `Agent_skill(x, d, t, tags)`

```
Gateway resolves skill → sends manifest + external tags to client
Client re-scopes estate → executes skill locally
Client → Analysis Agent (t:h) with skill_output + request_id
Analysis Agent looks up internal tags → CE /resolve/guardrails
                                      → CE /resolve/domain_knowledge [advanced]
Analysis Agent → UI Agent with request_id
UI Agent looks up internal tags → CE /resolve/template
UI Agent → Client: rendered response + external tags
Client persists artifacts + evidence to serial DB
```

### Flow 2 — Knowledge (Server Side)

**Formula:** `Agent_knowledge(d, t, tags)`

```
Gateway → Analysis Agent with prompt + knowledge_context + request_id
Analysis Agent looks up internal tags → CE /resolve/guardrails
                                      → CE /resolve/domain_knowledge [advanced]
Analysis Agent → UI Agent with request_id
UI Agent looks up internal tags → CE /resolve/template
UI Agent → Client: rendered response + external tags
Client persists artifacts to serial DB
```

### Flow 3 — Playbook (Operation)

**Formula:** `Agent_playbook(p, d, t, tags)`

```
State 1 — Classification
  LLM classifies: CODE_REQUEST | OPERATION_REQUEST | EXPLAIN_REQUEST
  CE /resolve/playbook → found: State 4 | not found: State 2

State 2 — Approach Selection
  CE /resolve/agent + /answer/knowledge
  3-5 approaches → user selects

State 3 — Playbook Generation
  CodeGenClient (LLM, execution_timeout from agent.yaml)
  Generates: steps, scripts, parameters, rollback_steps
  Saved via ADK → Playbook collection (is_candidate: true)

State 4 — Context Fetch
  If playbook has context block:
    CE /resolve/context → readonly context before write execution
    Client estate scoped by playbook.context.supported_context_types

State 5 — Parameter Collection
  Extract mandatory_parameters from playbook
  UI Agent collects interactively → loop until complete
  param_set stored in internal tags → injected as ${user.X}

State 6 — Plan + Confirmation
  Plan assembled with tagged steps (request_id per step)
  User confirms → execution begins | cancels → [TERMINAL]

State 7 — Execution
  Execute steps → CE /resolve/guardrails before each write step
  Evidence captured per step
  Integration Service notified if configured

State 8 — Result
  Analysis Agent → CE /resolve/guardrails → closure summary
  UI Agent → CE /resolve/template → rendered response
  Client persists artifacts + evidence to serial DB
  User prompted: save playbook candidate? yes → ADK promotes
```

---

## 7. Broad Flow — Multi-Agent Plan

Broad flow is an extension of Flow 1. Multiple skills execute in parallel as independent tagged steps.

```
Gateway Phase 2C detects broad:
  N agents with independent intents
  OR account-wide scope

Plan assembled:
  step per agent — each with own request_id → own tag store entry
  synthesis step — depends_on all skill steps

User confirms plan

Parallel execution:
  Each step → client executes skill locally
  Each step → Analysis Agent with step request_id
  Each step result → written to serial DB (plan_id + step_id)

Synthesis trigger (Context Manager):
  All depends_on steps complete → trigger synthesis
  Analysis Agent reads all step results from serial DB by plan_id
  Produces unified summary

UI Agent renders combined result
Client persists final artifact
```

---

## 8. Context Engine Touch Points

For full CE API spec see: **Escher Context Engine — Section 4**

| Phase | CE API | Collection(s) | Tenant Scope |
|---|---|---|---|
| 2A | /answer/knowledge | Cloud Knowledge + Graph | global |
| 2C read step 1 | Skill collection search | Skill collection | tenant → global |
| 2C miss step 2 | /resolve/agent | Intent collection | global |
| 2C miss step 3 | /answer/knowledge | Cloud Knowledge + Graph | global |
| 2C write step 1 | Playbook collection search | Playbook collection | tenant → global |
| 3 read | /resolve/skill | Skill collection + ADK Graph | tenant → global |
| 3 write | /resolve/playbook | Playbook collection + ADK Graph | tenant → global |
| 4 | none | — | — |
| 5A state 2 | /resolve/agent | Intent collection | global |
| 5A state 2 | /answer/knowledge | Cloud Knowledge + Graph | global |
| 5A state 4 | /resolve/context | Context Builder + Tool | global |
| 5A state 7 | /resolve/guardrails | Guardrail collection | always both |
| 5B | /resolve/skill + /resolve/context | Skill + Context Builder + Tool | tenant → global |
| 5C | none — grounding from Phase 2C | — | — |
| 6 | /resolve/context | Context Builder + Tool | global |
| Analysis | /resolve/guardrails | Guardrail collection | always both |
| Analysis | /resolve/domain_knowledge | Domain Lens + Expert Graph | tenant → global |
| 9 | /resolve/template | Template collection | tenant → global |

---

## 9. Agents in the Framework

All agents are stateless. State arrives via request_id → tag store lookup. No agent holds memory between calls.

| Agent | Phase | Responsibility |
|---|---|---|
| Gateway | 1, 2C, 3 | Entry point — classification, skill/playbook resolution, tag assembly, routing |
| Analysis Agent | Analysis, 8 | Reasoning over skill output or knowledge context. Reads internal tags via request_id. |
| UI Agent | 9 | Template resolution and rendering. Reads internal tags via request_id. |
| Code Agent | 5C | No skill matched (read) or no playbook matched (write) at Phase 2C. Grounded by Phase 2C miss context. Generates skill or playbook candidate. |
| CodeGenClient | 5A State 3 | Generates playbook from scratch — long running |
| ApproachSelectionService | 5A State 2 | Generates 3-5 approaches using /resolve/agent + /answer/knowledge |

---

## 10. Basic vs Advanced Tier

```
Basic tier:
  CE /resolve/domain_knowledge skipped
  LLM reasons on estate context + normalized data + guardrails only

Advanced tier:
  CE /resolve/domain_knowledge included
  Domain Lens → domain philosophy
  Expert Graph → control → evidence → remediation chain
  Deeper grounded reasoning
```

Tier declared in agent.yaml `classification.tier_support`.
Tier in internal tags controls CE behavior at runtime.

---

## 11. Evidence

Assembled at runtime per flow. Always tenant scoped. Persisted by client to serial DB. Never held server side.

```
Flow 1 — skill execution evidence:
  tools called (readonly), estate data referenced,
  guardrails applied, confidence, reasoning trace

Flow 2 — knowledge evidence:
  cloud knowledge sources, guardrails applied,
  confidence, reasoning trace

Flow 3 — playbook execution evidence (per step):
  tools called (write), resources affected,
  script executed, output, timestamp, rollback status,
  guardrails applied, confidence
```

---

## 12. Artifacts

Always tenant scoped. Returned to client. Persisted to serial DB. Never written server side.

```
Artifact families:
  estate_view, report, finding, plan,
  bundle, run, evidence, playbook

Skill manifests declare permissions:
  artifact_effects:
    can_create: [finding, report]
    can_update: []
    can_enrich: [evidence]

Agent-level artifacts.can_create is the outer boundary.
Skill-level artifact_effects must be a strict subset.
Framework enforces permissions at runtime.
```

---