# Escher Context Engine — Collection Schema & Formula Mapping

## 1. Formula → Collection → Phase Mapping

Every collection serves exactly one formula variable. Every collection is called exactly once at exactly the right phase. Runtime never fetches data early or late.

```
Formula Variable        Collection                   Phase         When
───────────────────────────────────────────────────────────────────────────
Skill(x)                Skill collection             2C Step 1     skill search (semantic)
Skill(x)                Skill collection             3             skill resolution (full)
capabilities            Intent collection            2C miss only  Code Agent grounding
capabilities            Intent collection            2W miss only  Code Agent grounding
ContextBuilder(x)       Context Builder collection   6             data fetch
Estate                  Local RAG (client)           6             data fetch
Tool_readonly           Tool collection              6             data fetch
Tool_write              Tool collection              5A State 7    playbook exec
Guardrail               Guardrail collection         7 + 5A        analysis + playbook
DomainLens              Domain Lens collection       7             analysis
ExpertGraph             Domain Expert Graph          7             analysis
Template                Template collection          9             render
Playbook(p)             Playbook collection          2C Step 1     write search (semantic)
Playbook(p)             Playbook collection          3 + 5A        operation path + exec
CloudKnowledge          Cloud Knowledge collection   2A            general knowledge
CloudKnowledge          Cloud Knowledge collection   2C/2W miss    Code Agent grounding
```

---

## 2. Collections

---

### 2.1 Intent Collection
**Formula variable:** capabilities + supported_context_types
**Phase:** 2C miss + 2W miss — Code Agent grounding only
**CE API:** /resolve/agent

**Purpose:** Lightweight. Serves Phase 2C/2W miss only. Provides capabilities and context boundary to Code Agent when no skill or playbook is found. Not the primary routing signal — Skill collection semantic search handles that.

**Collection:** `escher_intent_global`
**_id:** `agent_id`

```json
{
  "_id": "domain.security.exposure",
  "_embedding": [0.034, -0.121, 0.095, "...768 dims"],
  "_created_at": "2024-01-15T10:00:00Z",
  "_updated_at": "2024-01-15T10:00:00Z",

  "agent_id": "domain.security.exposure",
  "domain": "security",
  "tier_support": ["basic", "advanced"],
  "status": "active",
  "tenant_id": null,
  "can_trigger_playbook": true,

  "capabilities": [
    "detect public ingress and network exposure risks",
    "detect public storage access and open S3 buckets",
    "rank and prioritize exposure findings by severity",
    "suggest basic remediation paths for exposure risks"
  ],

  "supported_context_types": [
    "public_exposure_inventory",
    "resource_scope_summary",
    "environment_scope"
  ],

  "context_builder_ids": [
    "security.public_exposure_context"
  ]
}
```

**Embedding strategy:**
```
Single embedding over:
  capabilities[] joined as text
  + supported_context_types[] joined as text
One vector per agent document.
Searched against user prompt only on Phase 2C/2W miss.
Returns: capabilities + context_types + context_builder_ids
→ Code Agent uses these as domain boundary for generation
```

**Indexes:**
```
{ "agent_id": 1 }               unique
{ "domain": 1 }
{ "status": 1 }
{ "tenant_id": 1 }
{ "tier_support": 1 }
{ "can_trigger_playbook": 1 }
```

**Query pattern:**
```
Phase 2C/2W miss — Code Agent grounding only:
  semantic search on _embedding
  filter: status = active
  filter: tenant_id = null (always global)
  returns: matched agent + capabilities + context_types + context_builder_ids
  → handed to Code Agent as generation boundary
  → Code Agent also receives Cloud Knowledge from Step 3
```

**ADK places:** populated at agent registration from agent.yaml capabilities + context blocks

---

### 2.2 Skill Collection
**Formula variable:** Skill(x)
**Phase:** 2C Step 1 (semantic search) + Phase 3 (full manifest)
**CE API:** /resolve/skill

**Purpose:** Dual role. Phase 2C Step 1 — semantic search to decide narrow / broad / miss. Phase 3 — full manifest resolve scoped to matched agent.

**Collections:**
- `escher_skills_global`
- `escher_skills_{tenant_id}`

**_id:** `skill_id`

**Phase 2C Step 1 — semantic search:**
```
Embedded fields: purpose + description + display_name + capability_id
Returns (projection only):
  skill_id, owner_agent_id, domain, confidence
  one skill  → narrow → Phase 3
  many skills → broad → Phase 3
  no match   → miss → Intent collection + Cloud Knowledge → Phase 5C
```

**Full document JSON (Phase 3 returns all fields):**

```json
{
  "_id": "security.detect_public_ingress",
  "_embedding": [0.034, -0.121, 0.095, "...768 dims"],
  "_created_at": "2024-01-15T10:00:00Z",
  "_updated_at": "2024-01-15T10:00:00Z",
  "_version": "0.1.0",

  "skill_id":        "security.detect_public_ingress",
  "display_name":    "Detect Public Ingress",
  "owner_agent_id":  "domain.security.exposure",
  "capability_id":   "detect_public_exposure",
  "domain":          "security",
  "tier":            "basic",
  "status":          "active",
  "tenant_id":       null,

  "purpose":     "Detect public ingress patterns and generate exposure findings.",
  "description": "Finds publicly accessible EC2 instances, open security groups, internet-facing load balancers, and public S3 buckets. Use this for questions like: which EC2 instances are unsecured, what security groups have open ingress, show me public-facing resources, find exposed infrastructure in my AWS account.",

  "context_builder_ids": [
    "security.public_exposure_context"
  ],

  "supported_context_types": [
    "public_exposure_inventory",
    "resource_scope_summary",
    "environment_scope"
  ],

  "tool_affinity": {
    "allowed_tool_classes":  ["inventory_read"],
    "preferred_tool_tags":   ["security", "ingress", "aws"],
    "execution_locations":   ["client"]
  },

  "output_type":       "finding",
  "output_schema_ref": "schemas/public_exposure_finding.yaml",

  "artifact_effects": {
    "can_create": ["finding"],
    "can_update": [],
    "can_enrich": ["triage"]
  },

  "action_semantics": {
    "can_request_execution":            false,
    "can_generate_plan_fragments":      true,
    "can_generate_bundle_hints":        false,
    "can_generate_playbook_candidates": true
  },

  "safety": {
    "safety_class":              "advisory",
    "requires_human_review_for": []
  },

  "evidence": {
    "emits_rationale":  true,
    "emits_confidence": true
  }
}
```

**What each Phase 3 field drives:**
```
context_builder_ids      → Phase 6 CE /resolve/context
supported_context_types  → Phase 6 Local Context estate scoping
tool_affinity            → Phase 6 readonly tool selection
output_type              → written to Tag Store → Phase 9 /resolve/template
output_schema_ref        → skill executable output contract
artifact_effects         → Phase 9 artifact persistence
action_semantics         → Analysis Agent output constraints
safety.safety_class      → Analysis Agent reasoning constraints
evidence                 → Analysis Agent output requirements
```

**Written to Tag Store at Phase 3:**
```
skill_id, owner_agent_id, domain, tier,
output_type, context_builder_ids
```

**Indexes:**
```
{ "skill_id": 1 }                              unique
{ "owner_agent_id": 1 }                        Phase 3 scoped lookup
{ "domain": 1 }
{ "tier": 1 }
{ "status": 1 }
{ "tenant_id": 1 }
{ "owner_agent_id": 1, "status": 1, "tenant_id": 1 }
```

---

### 2.3 Context Builder Collection
**Formula variable:** ContextBuilder(x)
**Phase:** 6 — data fetch
**CE API:** /resolve/context

**Purpose:** Defines exactly what data to collect and how. Called after skill is resolved. Returns collection units and tool preferences.

**Collection:** `escher_context_builders_global`
**_id:** `context_builder_id`

```json
{
  "_id": "security.public_exposure_context",
  "_embedding": [0.028, -0.107, 0.083, "...768 dims"],
  "_created_at": "2024-01-15T10:00:00Z",
  "_updated_at": "2024-01-15T10:00:00Z",
  "_version": "0.1.0",

  "context_builder_id": "security.public_exposure_context",
  "name": "public_exposure_context",
  "display_name": "Public Exposure Context",
  "domain": "security",
  "data_type": "public_exposure_inventory",
  "provider": "aws",
  "status": "active",
  "tenant_id": null,

  "purpose": "Gather normalized context needed to detect public exposure risks.",

  "collection_units": [
    {
      "unit_id": "fetch_network_ingress_surface",
      "purpose": "gather public ingress candidates",
      "required": true,
      "context_type": "public_exposure_inventory",
      "preferred_tool_classes": ["inventory_read"],
      "preferred_tool_tags": ["security", "ingress", "aws"],
      "execution_locations": ["client"],
      "freshness_window": "30m",
      "cache_policy": "refresh_if_stale",
      "normalization_schema_ref": "schemas/public_exposure_inventory.yaml"
    },
    {
      "unit_id": "fetch_public_storage_surface",
      "purpose": "gather public S3 bucket exposure",
      "required": false,
      "context_type": "resource_scope_summary",
      "preferred_tool_classes": ["inventory_read"],
      "preferred_tool_tags": ["security", "storage", "aws"],
      "execution_locations": ["client"],
      "freshness_window": "30m",
      "cache_policy": "refresh_if_stale",
      "normalization_schema_ref": "schemas/storage_exposure_inventory.yaml"
    }
  ],

  "output_schema_ref": "schemas/public_exposure_context.yaml",

  "orchestration": {
    "merge_strategy": "union",
    "dedupe_keys": ["environment"],
    "max_parallel_units": 3
  },

  "fallbacks": {
    "on_missing_required_context": "request_more",
    "fallback_probe_policy": "allowed_with_review"
  }
}
```

**Indexes:**
```
{ "context_builder_id": 1 }     unique
{ "domain": 1 }
{ "data_type": 1 }
{ "provider": 1 }
{ "status": 1 }
{ "tenant_id": 1 }
{ "data_type": 1, "provider": 1 }
```

---

### 2.4 Tool Collection
**Formula variable:** Tool_readonly + Tool_write
**Phase:** 6 (readonly) + 5A State 7 (write)
**CE API:** /resolve/context (readonly) + /resolve/tools (write)

**Purpose:** Concrete execution mechanisms. Readonly tools fetched at Phase 6 for skills. Write tools fetched at Phase 5A State 7 for playbooks.

**Collection:** `escher_tools_global`
**_id:** `tool_id`

**Readonly tool:**
```json
{
  "_id": "aws.describe_public_ingress_surface",
  "_embedding": [0.038, -0.094, 0.071, "...768 dims"],
  "_created_at": "2024-01-15T10:00:00Z",
  "_updated_at": "2024-01-15T10:00:00Z",
  "_version": "0.1.0",

  "tool_id": "aws.describe_public_ingress_surface",
  "name": "Describe Public Ingress Surface",
  "tool_class": "inventory_read",
  "tool_type": "readonly",
  "domain": ["security"],
  "provider": "aws",
  "execution_location": "client",
  "safety_class": "read_only",
  "tenant_id": null,

  "purpose": "Fetch security group ingress rules and internet-facing resources.",

  "auth": "customer_cloud_credentials",
  "output_schema_ref": "schemas/public_exposure_inventory.yaml",
  "cacheable": true,

  "resource_types": [
    "security_group",
    "load_balancer",
    "internet_gateway"
  ],

  "api_calls": [
    "ec2:DescribeSecurityGroups",
    "ec2:DescribeInternetGateways",
    "elasticloadbalancing:DescribeLoadBalancers"
  ]
}
```

**Write tool:**
```json
{
  "_id": "aws.lock_security_group",
  "_embedding": [0.051, -0.083, 0.092, "...768 dims"],
  "_created_at": "2024-01-15T10:00:00Z",
  "_updated_at": "2024-01-15T10:00:00Z",
  "_version": "0.1.0",

  "tool_id": "aws.lock_security_group",
  "name": "Lock Security Group Ingress",
  "tool_class": "action_write",
  "tool_type": "write",
  "domain": ["security"],
  "provider": "aws",
  "execution_location": "server",
  "safety_class": "supervised_write",
  "tenant_id": null,

  "purpose": "Remove overly permissive ingress rules from a security group.",

  "auth": "customer_cloud_credentials",
  "output_schema_ref": "schemas/security_group_mutation_result.yaml",
  "cacheable": false,
  "requires_human_review": true,
  "rollback_api": "ec2:AuthorizeSecurityGroupIngress",

  "resource_types": ["security_group"],

  "api_calls": [
    "ec2:RevokeSecurityGroupIngress",
    "ec2:DescribeSecurityGroups"
  ]
}
```

**Indexes:**
```
{ "tool_id": 1 }                unique
{ "tool_class": 1 }
{ "tool_type": 1 }
{ "provider": 1 }
{ "execution_location": 1 }
{ "safety_class": 1 }
{ "domain": 1 }
{ "tenant_id": 1 }
{ "tool_type": 1, "tool_class": 1, "provider": 1 }
```

---

### 2.5 Guardrail Collection
**Formula variable:** Guardrail
**Phase:** 7 — analysis + 5A State 7 — playbook execution
**CE API:** /resolve/guardrails

**Purpose:** Safety and policy rules. Always fetched at analysis time and before each write step. Global + tenant always combined.

**Collections:**
- `escher_guardrails_global`
- `escher_guardrails_{tenant_id}`

**_id:** `guardrail_id`

```json
{
  "_id": "security.never_fabricate_findings",
  "_created_at": "2024-01-15T10:00:00Z",
  "_updated_at": "2024-01-15T10:00:00Z",
  "_version": "0.1.0",

  "guardrail_id": "security.never_fabricate_findings",
  "name": "Never fabricate security findings",
  "scope": "domain",
  "skill_id": null,
  "owner_agent_id": null,
  "domain": "security",
  "tenant_id": null,

  "rules": [
    {
      "rule_id": "no_invented_findings",
      "description": "Never report a security finding without direct evidence from estate data.",
      "enforcement": "hard",
      "action": "block"
    },
    {
      "rule_id": "cite_evidence_source",
      "description": "Every finding must reference the specific resource and tool output.",
      "enforcement": "hard",
      "action": "block"
    },
    {
      "rule_id": "confidence_required",
      "description": "Every finding must include a confidence score.",
      "enforcement": "soft",
      "action": "warn"
    }
  ]
}
```

**Note:** No `_embedding` — guardrails are pure filter retrieval. No semantic search needed.

**Indexes:**
```
{ "guardrail_id": 1 }           unique
{ "scope": 1 }
{ "skill_id": 1 }
{ "owner_agent_id": 1 }
{ "domain": 1 }
{ "tenant_id": 1 }
{ "scope": 1, "domain": 1, "tenant_id": 1 }
```

---

### 2.6 Domain Lens Collection
**Formula variable:** DomainLens
**Phase:** 7 — analysis (advanced tier only)
**CE API:** /resolve/domain_knowledge

**Purpose:** Domain philosophy and reasoning documents. LLM reasons over content at analysis time.

**Collections:**
- `escher_domain_lens_global`
- `escher_domain_lens_{tenant_id}`

**_id:** `lens_id`

```json
{
  "_id": "security.cspm_framework_reference",
  "_embedding": [0.041, -0.099, 0.076, "...768 dims"],
  "_created_at": "2024-01-15T10:00:00Z",
  "_updated_at": "2024-01-15T10:00:00Z",
  "_version": "0.1.0",

  "lens_id": "security.cspm_framework_reference",
  "domain": "security",
  "title": "CSPM Framework Reference",
  "content_type": "framework",
  "tenant_id": null,

  "content": "Cloud Security Posture Management focuses on continuous monitoring of cloud infrastructure configurations against security best practices. Key principles include: least privilege access, encryption at rest and in transit, network segmentation, audit logging, and automated remediation of policy violations..."
}
```

**Indexes:**
```
{ "lens_id": 1 }                unique
{ "domain": 1 }
{ "content_type": 1 }
{ "tenant_id": 1 }
{ "domain": 1, "tenant_id": 1 }
```

---

### 2.7 Template Collection
**Formula variable:** Template
**Phase:** 9 — render
**CE API:** /resolve/template

**Purpose:** UI rendering templates. Called last. Tag hierarchy: skill → agent → domain.

**Collections:**
- `escher_templates_global`
- `escher_templates_{tenant_id}`

**_id:** `template_id`

```json
{
  "_id": "security.exposure_finding_template",
  "_created_at": "2024-01-15T10:00:00Z",
  "_updated_at": "2024-01-15T10:00:00Z",
  "_version": "0.1.0",

  "template_id": "security.exposure_finding_template",
  "name": "Security Exposure Finding",
  "skill_id": "security.detect_public_ingress",
  "agent_id": "domain.security.exposure",
  "domain": "security",
  "output_type": "finding",
  "tenant_id": null,

  "output_schema_ref": "schemas/finding_candidate.yaml",

  "template_body": {
    "sections": [
      {
        "id": "summary",
        "label": "Exposure Summary",
        "type": "text",
        "source": "analysis.summary"
      },
      {
        "id": "findings",
        "label": "Findings",
        "type": "list",
        "source": "skill_output.findings",
        "item_template": {
          "title": "{{resource_id}}",
          "severity": "{{severity}}",
          "description": "{{description}}",
          "evidence": "{{evidence_refs}}"
        }
      },
      {
        "id": "confidence",
        "label": "Confidence",
        "type": "score",
        "source": "analysis.confidence"
      },
      {
        "id": "actions",
        "label": "Recommended Actions",
        "type": "action_list",
        "source": "analysis.recommendations"
      }
    ]
  }
}
```

**Note:** No `_embedding` — templates are pure filter retrieval by skill_id → agent_id → domain hierarchy.

**Indexes:**
```
{ "template_id": 1 }            unique
{ "skill_id": 1 }
{ "agent_id": 1 }
{ "domain": 1 }
{ "output_type": 1 }
{ "tenant_id": 1 }
{ "skill_id": 1, "output_type": 1, "tenant_id": 1 }
```

---

### 2.8 Playbook Collection
**Formula variable:** Playbook(p)
**Phase:** 2C Step 1 write (semantic search) + Phase 3 + 5A (full manifest)
**CE API:** /resolve/playbook

**Purpose:** Registered and generated playbooks. Searched by trigger at Phase 2C write path. Full manifest fetched at Phase 3 and 5A.

**Collections:**
- `escher_playbooks_global`
- `escher_playbooks_{tenant_id}`

**_id:** `playbook_id`

```json
{
  "_id": "security.remediate_public_exposure",
  "_embedding": [0.044, -0.102, 0.081, "...768 dims"],
  "_created_at": "2024-01-15T10:00:00Z",
  "_updated_at": "2024-01-15T10:00:00Z",
  "_version": "0.1.0",

  "playbook_id": "security.remediate_public_exposure",
  "name": "Remediate Public Exposure",
  "domain": "security",
  "tier": "basic",
  "is_candidate": false,
  "generated_by": "registered",
  "tenant_id": null,

  "trigger_conditions": [
    "public_exposure_finding",
    "open_security_group_detected",
    "internet_facing_resource_unprotected"
  ],

  "context": {
    "supported_context_types": [
      "public_exposure_inventory",
      "security_group_config"
    ],
    "declared_context_builders": [
      "security.public_exposure_context"
    ]
  },

  "steps": [
    {
      "step_id": "step_1",
      "name": "Fetch current exposure surface",
      "type": "readonly",
      "tool_id": "aws.describe_public_ingress_surface",
      "required": true,
      "on_failure": "stop"
    },
    {
      "step_id": "step_2",
      "name": "Lock overly permissive security groups",
      "type": "write",
      "tool_id": "aws.lock_security_group",
      "required": true,
      "on_failure": "rollback"
    }
  ],

  "scripts": [
    {
      "step_id": "step_1",
      "language": "python",
      "body": "import boto3\nsession = boto3.Session(profile_name='${user.profile}', region_name='${user.region}')\nec2 = session.client('ec2')\nreturn ec2.describe_security_groups()",
      "params_used": ["profile", "region"]
    },
    {
      "step_id": "step_2",
      "language": "python",
      "body": "import boto3\nsession = boto3.Session(profile_name='${user.profile}', region_name='${user.region}')\nec2 = session.client('ec2')\nec2.revoke_security_group_ingress(GroupId='${sg_id}', IpPermissions=rules)",
      "params_used": ["profile", "region"]
    }
  ],

  "target_language": "python",

  "mandatory_parameters": [
    {
      "name": "region",
      "type": "string",
      "description": "AWS region to remediate",
      "example": "us-east-1"
    },
    {
      "name": "profile",
      "type": "string",
      "description": "AWS CLI profile",
      "example": "tessell_prod_infra"
    }
  ],

  "optional_parameters": [
    {
      "name": "dry_run",
      "type": "boolean",
      "description": "Run without making changes",
      "default": false
    }
  ],

  "rollback_steps": [
    {
      "step_id": "rollback_2",
      "script_id": "step_2_rollback",
      "reverses": "step_2"
    }
  ],

  "approach_hints": [
    "prefer least-privilege remediation",
    "avoid broad policy changes"
  ],

  "execution_timeout": 600,
  "rollback_support": true,

  "safety": {
    "safety_class": "supervised",
    "requires_human_review_for": ["step_2"]
  },

  "evidence_requirements": [
    "security_group_state_before",
    "security_group_state_after",
    "api_calls_made"
  ]
}
```

**Embedding strategy:**
```
Embed: trigger_conditions[] joined as text + name + domain
Phase 2C write Step 1: semantic search → returns playbook_id + confidence only
Phase 3 / 5A: direct lookup by playbook_id → returns full document
```

**Indexes:**
```
{ "playbook_id": 1 }            unique
{ "domain": 1 }
{ "tier": 1 }
{ "is_candidate": 1 }
{ "generated_by": 1 }
{ "tenant_id": 1 }
{ "domain": 1, "tenant_id": 1, "is_candidate": 1 }
```

---

### 2.9 Cloud Knowledge Collection
**Formula variable:** CloudKnowledge
**Phase:** 2A (general knowledge) + 2C miss step 3 (Code Agent grounding) + 2W miss step 3 (Code Agent grounding)
**CE API:** /answer/knowledge

**Purpose:** Cloud service concepts and relationships. LLM reasons over content. Graph traversal enriches results.

**Collection:** `escher_cloud_knowledge_global`
**_id:** `knowledge_id`

```json
{
  "_id": "aws.ecs.overview",
  "_embedding": [0.029, -0.118, 0.074, "...768 dims"],
  "_created_at": "2024-01-15T10:00:00Z",
  "_updated_at": "2024-01-15T10:00:00Z",
  "_version": "0.1.0",

  "knowledge_id": "aws.ecs.overview",
  "provider": "aws",
  "service": "ecs",
  "resource_type": null,
  "tenant_id": null,

  "title": "Amazon ECS — Elastic Container Service",

  "content": "Amazon ECS is a fully managed container orchestration service. ECS supports Fargate (serverless) and EC2 launch types. Requires VPC, IAM roles, and optionally an ALB for traffic routing. Tasks are defined via Task Definitions specifying container images, CPU, memory, and IAM permissions.",

  "relationships": [
    {
      "target_service": "vpc",
      "relationship_type": "requires",
      "required": true
    },
    {
      "target_service": "iam",
      "target_resource_type": "role",
      "relationship_type": "requires",
      "required": true
    },
    {
      "target_service": "ecr",
      "relationship_type": "pulls_from",
      "required": false
    },
    {
      "target_service": "alb",
      "relationship_type": "optionally_uses",
      "required": false
    }
  ]
}
```

**Indexes:**
```
{ "knowledge_id": 1 }           unique
{ "provider": 1 }
{ "service": 1 }
{ "resource_type": 1 }
{ "tenant_id": 1 }
{ "provider": 1, "service": 1 }
```

---

### 2.10 Tag Store
**Formula variable:** tags (internal)
**Phase:** all phases
**CE API:** internal — not exposed to Framework directly

**Purpose:** Stores internal tags per request. TTL auto-delete. Never sent to client.

**Collection:** `escher_tag_store`
**_id:** `request_id`

```json
{
  "_id": "req_abc123",
  "expires_at": "2024-01-15T11:00:00Z",

  "request_id": "req_abc123",
  "tenant_id": "acme_corp",
  "session_id": "sess_xyz789",
  "user_id": "user_456",
  "tier": "advanced",

  "flow": "skill",
  "plan_id": null,
  "step_id": null,
  "step_ids": null,
  "depends_on": null,

  "owner_agent_id": "domain.security.exposure",
  "skill_id": "security.detect_public_ingress",
  "playbook_id": null,
  "domain": "security",
  "context_builder_ids": ["security.public_exposure_context"],
  "output_type": "finding",

  "execution_location": "client",
  "language": null,
  "approach_id": null,
  "param_set": null
}
```

**Indexes:**
```
{ "request_id": 1 }             unique
{ "expires_at": 1 }             TTL index — auto-delete
{ "tenant_id": 1 }
{ "session_id": 1 }
{ "plan_id": 1 }
```

---

### 2.11 Agent Registry

**Formula variable:** Agent manifest + capabilities
**Phase:** 2C miss + 3W miss — Code Agent grounding only
**CE API:** `/resolve/agent`

**Purpose:** Stores full agent manifests and capability embeddings. Searched only at Phase 2C miss (read) and Phase 3W miss (write) to provide Code Agent with domain boundary — what this agent can do and what data it works with. Not searched on every prompt.

**Collection:** `escher_agent_registry_global`
**_id:** `agent_id`

```json
{
  "_id": "domain.security.exposure",
  "_embedding": [0.034, -0.121, 0.095, "...768 dims"],
  "_created_at": "2024-01-15T10:00:00Z",
  "_updated_at": "2024-01-15T10:00:00Z",

  "agent_id":     "domain.security.exposure",
  "name":         "exposure",
  "display_name": "Security Exposure Agent",
  "agent_type":   "domain",
  "domain":       "security",
  "tier_support": ["basic", "advanced"],
  "status":       "active",
  "tenant_id":    null,

  "capabilities": [
    "detect public ingress and network exposure risks",
    "detect public storage access and open S3 buckets",
    "rank and prioritize exposure findings by severity",
    "suggest basic remediation paths for exposure risks"
  ],
  "capabilities_embedding": [0.034, -0.121, "...768 dims"],

  "supported_context_types": [
    "public_exposure_inventory",
    "resource_scope_summary",
    "environment_scope"
  ],
  "context_builder_ids": [
    "security.public_exposure_context"
  ],

  "skill_refs": [
    "security.detect_public_ingress",
    "security.detect_public_storage_access",
    "security.rank_basic_exposure_findings"
  ],

  "composition": {
    "usable_in_profiles":    ["hero_admin", "cspm_deep"],
    "compatible_agents":     ["domain.security.remediation_planning"],
    "conflicts_with_agents": []
  },

  "version":   "0.1.0",
  "tenant_id": null
}
```

**Embedding strategy:**
```
capabilities[] joined as text → single dense vector
Searched at Phase 2C miss / 3W miss only
Returns: agent_id + capabilities + context_types + context_builder_ids
→ Code Agent uses as domain boundary for generation
→ NOT searched on every prompt — Skill collection handles that
```

**What each field drives:**
```
capabilities           → Code Agent boundary — what this domain can do
supported_context_types→ Code Agent boundary — what estate data exists
context_builder_ids    → Code Agent boundary — what can be fetched
skill_refs             → ADK Graph — agent → skill edges
composition            → ADK Graph — compatible/conflicts edges
tier_support           → CE scoping — advanced tier adds domain_knowledge
```

**Indexes:**
```
{ "agent_id": 1 }               unique
{ "domain": 1 }
{ "status": 1 }
{ "tier_support": 1 }
{ "tenant_id": 1 }
```

**Query pattern:**
```
Phase 2C miss / 3W miss — Code Agent grounding:
  semantic search on _embedding (capabilities)
  filter: status = active
  filter: tenant_id = null (always global)
  returns: agent_id + capabilities + context_types + context_builder_ids
  → passed to Code Agent alongside Cloud Knowledge
  → Code Agent generates skill (read miss) or playbook (write miss)
    within this domain boundary
```

**ADK places:** populated at agent registration from agent.yaml
  - capabilities embedded as dense vectors at registration time
  - re-embedded automatically on capabilities update

---

## 3. Collection Summary

| Collection | Formula Variable | Phase | Embedding | Tenant Scope |
|---|---|---|---|---|
| Skill | Skill(x) | 2C Step 1 (search) + Phase 3 (full) | purpose + description + display_name + capability_id | tenant → global |
| Intent | capabilities + context_types | 2C/2W miss only | capabilities + context joined | global |
| Playbook | Playbook(p) | 2C write Step 1 (search) + Phase 3 + 5A (full) | trigger_conditions + name | tenant → global |
| Context Builder | ContextBuilder(x) | 6 | purpose + data_type | global |
| Tool | Tool_readonly + Tool_write | 6 + 5A State 7 | purpose + tool_class | global |
| Guardrail | Guardrail | 7 + 5A State 7 | none — filter only | always both |
| Domain Lens | DomainLens | 7 | title + content | tenant → global |
| Template | Template | 9 | none — filter only | tenant → global |
| Cloud Knowledge | CloudKnowledge | 2A + 2C/2W miss | title + content | global |
| Tag Store | tags | all | none | per request |

---

## Appendix A — Design Decisions

### A.1 Why Skill collection is searched first at Phase 2C

Phase 2C needs to decide: is there a skill for this prompt? The Skill collection already has purpose + description + capability_id embeddings — exactly what is needed for this decision. Searching Skill collection directly at Phase 2C avoids an extra collection and keeps the skill as the primary routing artifact for read intent. The Intent collection is not needed until a miss occurs.

```
Skill collection   → primary routing — Phase 2C Step 1
                     semantic search on user prompt
                     one match  → narrow
                     many match → broad
                     no match   → Phase 5C (Code Agent)

Intent collection  → Code Agent grounding — Phase 2C/2W miss only
                     provides capabilities + context boundary
                     Code Agent uses to generate within domain
```

### A.2 Why Intent collection is Code Agent grounding only

When skill search fails, Code Agent needs to know: what can this domain do, and what estate data can it access? The Intent collection holds exactly this — agent capabilities and context types. It is a lightweight projection of agent.yaml, purpose-built for this grounding use case. It is not needed when a skill is found because the Skill collection already carries the domain context.

```
Agent Registry    → full manifest, used by ADK for validation
                    not searched at runtime
Intent collection → lightweight projection, used at Phase 2C/2W miss
                    populated from same agent.yaml
                    single embedding, fast search
                    returns: capabilities + context_types + context_builder_ids
                    → Code Agent uses as domain boundary
```

### A.3 Why Guardrails and Templates have no embedding

Guardrails are retrieved by exact scope hierarchy: skill → agent → domain → global. There is no semantic ambiguity. A guardrail either applies to this skill or it does not. Semantic search would add noise and risk returning wrong guardrails.

Templates are retrieved by output_type + skill_id → agent_id → domain hierarchy. Same reason — exact match, no ambiguity. If a template exists for this skill and output_type, use it. If not, fall back to domain level.

### A.4 Why param_set is in internal tags not a separate store

Params are collected from the user and injected into scripts as `${user.X}`. They are request-scoped — only valid for this execution. Storing them in the tag store (which has TTL auto-delete) is correct. They should not persist beyond the request. They should never be sent to the client after injection.

---

## Appendix B — Formula Reference

```
Agent_skill(x, d, t, tags):
  Skill(x)           → Skill collection          Phase 2C Step 1 (search)
                                                  Phase 3 (full manifest)
  ContextBuilder(x)  → Context Builder collection Phase 6
  Estate             → Local RAG (client)         Phase 6
  Tool_readonly      → Tool collection            Phase 6
  Guardrail          → Guardrail collection       Phase 7
  DomainLens         → Domain Lens collection     Phase 7 [advanced]
  ExpertGraph        → Domain Expert Graph        Phase 7 [advanced]
  Template           → Template collection        Phase 9
  Artifact           → client serial DB           Phase 9
  Evidence           → client serial DB           Phase 9

Agent_knowledge(d, t, tags):
  CloudKnowledge     → Cloud Knowledge collection Phase 2A
  Estate             → Local RAG (client)         initial prompt
  Guardrail          → Guardrail collection       Phase 7
  DomainLens         → Domain Lens collection     Phase 7 [advanced]
  ExpertGraph        → Domain Expert Graph        Phase 7 [advanced]
  Template           → Template collection        Phase 9

Agent_playbook(p, d, t, tags):
  Playbook(p)        → Playbook collection        Phase 2C write Step 1 (search)
                                                  Phase 3 + 5A (full manifest)
  Approach           → Intent collection          Phase 2W miss — capabilities
                     + Cloud Knowledge collection Phase 2W miss — concept grounding
  ContextBuilder(p)  → Context Builder collection Phase 5A State 4 [read-then-write]
  Estate             → Local RAG (client)         Phase 5A State 4 [read-then-write]
  Tool_write         → Tool collection            Phase 5A State 7
  Params             → user input                 Phase 5A State 5
  Guardrail          → Guardrail collection       Phase 5A State 7 + Phase 7
  Template           → Template collection        Phase 9
  Evidence           → client serial DB           Phase 5A State 7
  Artifact           → client serial DB           Phase 9
```