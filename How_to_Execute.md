# How to Execute — Context Engine POC

## What This POC Does

Implements the first slice of the Escher Context Engine: the **Phase 2C skill search path**.

Given a natural language user prompt, the system:
1. Embeds the prompt using a local sentence-transformers model
2. Performs cosine similarity search against skill embeddings stored in SurrealDB
3. Returns a ranked list of matching skills with a routing decision: **NARROW** (one clear match), **BROAD** (multiple candidates), or **MISS** (no match → Code Agent)

The 3 skills registered are from the Security Exposure Agent (`agents.yaml.md` Full Example):
- `security.detect_public_ingress`
- `security.detect_public_storage_access`
- `security.rank_basic_exposure_findings`

Skill embeddings follow `adk.md §6.1`: `purpose + description + display_name + capability_id` joined as text, encoded to a 768-dim dense vector.

---

## Project Structure

```
ContextEnginePOC2/
├── docker-compose.yml              # SurrealDB container
├── requirements.txt                # Python dependencies
├── .env                            # DB connection config
├── main.py                         # Entry point: register + search demo
│
├── context_engine/
│   ├── db.py                       # Async SurrealDB connection (reads .env)
│   ├── embeddings.py               # sentence-transformers wrapper (768-dim)
│   ├── models.py                   # Pydantic: SkillRecord, SkillSearchResult
│   ├── setup_schema.py             # Creates table + HNSW index in SurrealDB
│   ├── adk_register.py             # Embeds skills and upserts into SurrealDB
│   └── skill_search.py             # Phase 2C semantic search + routing logic
│
└── data/
    └── security_exposure_agent.py  # Seed data: 3 SkillRecord definitions
```

---

## Prerequisites

- Python 3.13 with a `.venv` at `./venv` (already created)
- Docker Desktop running

---

## Step 1 — Start SurrealDB

```bash
docker compose up -d
```

This starts SurrealDB in **in-memory mode** (data resets on container restart).

**Verify it's running:**
```bash
docker compose ps
```

Expected output:
```
NAME                            STATUS          PORTS
contextenginepoc2-surrealdb-1   Up              0.0.0.0:8000->8000/tcp
```

**Container details:**
| Setting | Value |
|---|---|
| Image | `surrealdb/surrealdb:latest` |
| Port | `8000` (HTTP + WebSocket) |
| Username | `root` |
| Password | `root` |
| Storage | `memory` (in-process, resets on restart) |
| Namespace | `escher` |
| Database | `main` |

**Stop SurrealDB:**
```bash
docker compose down
```

---

## Step 2 — Install Dependencies

```bash
.venv/bin/pip install -r requirements.txt
```

Key packages:
| Package | Purpose |
|---|---|
| `surrealdb` | Async Python SDK for SurrealDB |
| `sentence-transformers` | Local embedding model (`all-mpnet-base-v2`, 768-dim) |
| `torch` | Required by sentence-transformers |
| `pydantic` | Data models for SkillRecord, SkillSearchResult |
| `python-dotenv` | Reads `.env` for DB connection config |

The embedding model (`all-mpnet-base-v2`) is downloaded automatically on first run (~420 MB, cached in `~/.cache/huggingface/`).

---

## Step 3 — Run the Demo

```bash
.venv/bin/python main.py
```

`main.py` does three things in sequence:
1. **Setup schema** — creates `escher_skills_global` table and HNSW vector index in SurrealDB
2. **Register skills** — embeds all 3 skills and upserts them into SurrealDB
3. **Run searches** — runs 5 sample queries and prints routing decisions

**Expected output:**
```
=== Context Engine POC ===

1. Setting up SurrealDB schema...
Schema ready: escher_skills_global table + HNSW index defined.

2. Registering Security Exposure Agent skills...
  Registered: security.detect_public_ingress
  Registered: security.detect_public_storage_access
  Registered: security.rank_basic_exposure_findings
   3 skills registered.

3. Running Phase 2C semantic skill search...

Query   : 'show me my unsecured EC2 instances'
Decision: BROAD
  → security.detect_public_ingress                confidence=0.5434
  → security.detect_public_storage_access         confidence=0.4777

Query   : 'which S3 buckets are publicly accessible?'
Decision: NARROW
  → security.detect_public_storage_access         confidence=0.6997
  → security.detect_public_ingress                confidence=0.4787

Query   : 'what should I fix first?'
Decision: NARROW
  → security.rank_basic_exposure_findings         confidence=0.2163

Query   : 'find open security groups with unrestricted ingress'
Decision: BROAD
  → security.detect_public_ingress                confidence=0.5720
  → security.detect_public_storage_access         confidence=0.3820
  → security.rank_basic_exposure_findings         confidence=0.2018

Query   : 'show me all internet-facing resources'
Decision: BROAD
  → security.detect_public_ingress                confidence=0.3863
  → security.detect_public_storage_access         confidence=0.2886
```

---

## Run Individual Modules

**Schema setup only:**
```bash
.venv/bin/python -m context_engine.setup_schema
```

**Skill registration only:**
```bash
.venv/bin/python -m context_engine.adk_register
```

**Skill search only (3 hardcoded demo queries):**
```bash
.venv/bin/python -m context_engine.skill_search
```

---

## Inspect SurrealDB Directly

**Via curl (REST API):**
```bash
curl -X POST http://localhost:8000/sql \
  -H "Accept: application/json" \
  -H "NS: escher" \
  -H "DB: main" \
  -u root:root \
  --data "SELECT skill_id, array::len(embedding) AS emb_len FROM escher_skills_global"
```

**Via Surrealist (GUI):**
Download [Surrealist](https://surrealdb.com/surrealist) and connect with:
- URL: `ws://localhost:8000`
- Namespace: `escher`
- Database: `main`
- Username: `root` / Password: `root`

Useful queries:
```sql
-- List all registered skills
SELECT skill_id, domain, tier, status FROM escher_skills_global;

-- Check embedding dimensions
SELECT skill_id, array::len(embedding) AS dims FROM escher_skills_global;

-- Show full record
SELECT * FROM escher_skills_global WHERE skill_id = 'security.detect_public_ingress';

-- Show defined indexes
INFO FOR TABLE escher_skills_global;
```

---

## How Semantic Search Works

### Embedding Strategy (adk.md §6.1)

At registration time, each skill is encoded as a single 768-dim dense vector:
```
embedding_text = purpose + description + display_name + capability_id
vector = all-mpnet-base-v2.encode(embedding_text, normalize=True)
```

At search time, the user prompt is encoded the same way:
```
query_vector = all-mpnet-base-v2.encode(prompt, normalize=True)
```

### SurrealDB Query

```sql
SELECT skill_id, owner_agent_id, domain,
       vector::similarity::cosine(embedding, $vec) AS confidence
FROM escher_skills_global
WHERE status = 'active'
ORDER BY confidence DESC
LIMIT 5
```

The `escher_skills_global` table has an HNSW index defined (768-dim, cosine distance). At POC scale (3 records) a full cosine scan is used — the HNSW index engages automatically at production scale when queried with the `<|K,EF|>` KNN operator.

### Routing Thresholds

| Threshold | Value | Meaning |
|---|---|---|
| `NARROW_THRESHOLD` | `0.60` | Top result ≥ 0.60 → single clear match |
| `BROAD_THRESHOLD` | `0.20` | Any result ≥ 0.20 → included in candidates |
| Below `BROAD_THRESHOLD` | — | All results filtered → MISS → Code Agent |

**Routing decision (Phase 2C):**
- **NARROW** — 1 result returned, or top result ≥ 0.60
- **BROAD** — multiple results above threshold
- **MISS** — no results above threshold → Code Agent grounding path

---

## Switching to Persistent Storage

The current setup uses `memory` mode (data lost on container restart). To persist data:

1. Edit `docker-compose.yml`:
```yaml
services:
  surrealdb:
    image: surrealdb/surrealdb:latest
    ports:
      - "8000:8000"
    volumes:
      - ./data/surreal:/data
    command: start --log trace --user root --pass root file:/data/escher.db
```

2. Restart the container:
```bash
docker compose down && docker compose up -d
```

---

## Environment Config (`.env`)

```
SURREAL_URL=ws://localhost:8000/rpc
SURREAL_USER=root
SURREAL_PASS=root
SURREAL_NS=escher
SURREAL_DB=main
```

All connection settings are read from `.env` via `context_engine/db.py`. Override any value by editing `.env` before running.
