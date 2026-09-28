# ONE NATION → ONE COMMON MATERIAL CODE

**AI-Powered National Unified Material Master Platform** (SIH26099)

---

## 1. Objective / Problem Statement

Central Public Sector Enterprises (CPSEs) across Oil & Gas, Power, Steel, Mining and
Heavy Engineering procure and maintain materials that are frequently identical or
functionally equivalent, but are recorded under different codes, descriptions,
specifications and units of measure in each CPSE's own material master. This causes
duplicate purchasing, inconsistent inventory data, and lost opportunities for
collaborative procurement.

This platform automatically ingests each participating CPSE's material data through
secure, read-only database connectors, harmonizes it with an AI/NLP pipeline (SBERT →
pgvector → weighted scoring → technical-conflict detection → XGBoost ranking →
decision engine), and maintains a neutral **Common National Material Code** for every
harmonized material group — while permanently preserving traceability back to each
CPSE's own original material code.

**The CPSE always remains the owner of its original material master.** The platform
never overwrites a CPSE's own code or description; it only builds a centralized,
harmonized *national view* on top of automatically-synchronized copies of that data.

---

## 2. Architecture

```
CPSE source databases (Postgres / MySQL / Oracle / SQL Server)   Company's own CSV/Excel
        |  secure, read-only connector (app.connectors)          material master export
        v                                                                |
Automatic ingestion (full + incremental sync,          Governed self-service upload
        app.connectors.sync_engine)                    (app.api.endpoints.material_upload,
        |                                                strictly scoped to the uploader's
        |                                                own CPSE - see section 5)
        v                                                                |
        +---------------------------  both paths share  -----------------+
        |                              app.services.material_ingestion
        v
Central material database (cpse_materials) ── validation, cleaning, normalization,
        |                                       attribute extraction
        v
AI harmonization pipeline (app.ai.analyzer)
    normalize -> SBERT embedding -> pgvector candidate retrieval ->
    weighted scoring (description/spec/classification/grade/dimension/
    standard/UOM/manufacturer/function/criticality) -> technical conflict
    detection -> XGBoost blend (if trained) -> decision engine
        |
        v
Decision: IDENTICAL / DUPLICATE / NEAR_DUPLICATE / FUNCTIONALLY_EQUIVALENT /
          NOT_EQUIVALENT / TECHNICAL_CONFLICT / MANUAL_REVIEW
        |
        v
common_material_mappings (AI recommendation) ──> Governance / Approval workflow
        |                                              (Material Expert / Admin)
        v                                              |
common_materials (Common National Material Code) <─────┘
        |
        v
Procurement analytics (demand aggregation) + Audit trail (every step)
```

No step in this pipeline requires a human to manually type in a material record —
material data only ever enters the system through a source connector sync. Humans
**validate AI recommendations** (approve / reject / edit & approve / send to manual
review); they never hand-create the material master.

---

## 3. Technology Stack

**Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Radix UI primitives, React
Router, TanStack React Query, Recharts, Axios.

**Backend:** Python 3.12, FastAPI, SQLAlchemy 2.x, Pydantic v2, PostgreSQL + pgvector,
Alembic, JWT auth, Celery, Redis.

**AI/ML:** sentence-transformers (`all-MiniLM-L6-v2`) for text embeddings, pgvector
for ANN candidate retrieval, XGBoost for match ranking — each with a deterministic,
structurally-identical fallback so the pipeline runs even with no model weights
available, and never silently fabricates a score.

**Connectors:** SQLAlchemy-based read-only connectors — PostgreSQL and MySQL fully
implemented; Oracle and SQL Server are interface-complete and activate once their
optional vendor drivers (`oracledb`, `pyodbc`) are installed.

**File upload parsing:** stdlib `csv` for `.csv`, `openpyxl` for `.xlsx` — no `pandas`
dependency; `python-multipart` for FastAPI's multipart/form-data handling.

---

## 4. Project Structure

```
material/
├── backend/
│   ├── app/
│   │   ├── main.py                FastAPI app, CORS
│   │   ├── core/                  settings, JWT/bcrypt security
│   │   ├── db/                    session, declarative base, extension init
│   │   ├── models/                SQLAlchemy models (spec section 5 schema)
│   │   ├── schemas/                Pydantic request/response models
│   │   ├── connectors/             SourceConnector interface + Postgres/MySQL/
│   │   │                           Oracle/SQL Server implementations + sync engine
│   │   ├── api/endpoints/          auth, cpse-materials, material_upload (company
│   │   │                           self-service upload), demo_import (DEMO ONLY admin
│   │   │                           CSV import), common-materials, harmonization,
│   │   │                           approvals, synchronization, procurement, analytics,
│   │   │                           dashboard, audit, notifications, settings
│   │   ├── services/               normalization, scoring, decision_engine,
│   │   │                           code_generator, harmonization_service (governance),
│   │   │                           duplicate_service, duplicate_code_service,
│   │   │                           procurement_service, attribute_extraction,
│   │   │                           material_ingestion (shared upsert core used by
│   │   │                           connectors AND both upload paths),
│   │   │                           csv_import_service (shared CSV/Excel parse+validate)
│   │   ├── ai/                     text embeddings, similarity, conflict detector,
│   │   │                           XGBoost ranker, analyzer (pipeline orchestrator)
│   │   ├── workers/                Celery app + sync/AI-analysis tasks
│   │   ├── seed.py                 roles + one ADMIN login - zero business data
│   │   └── demo_seed.py            OPT-IN demo CPSEs + demo source tables + real sync
│   ├── alembic/                    migrations (0001_initial creates the full schema)
│   ├── tests/                      pytest suite (see section 19)
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/                  one file per route (see section 21)
│   │   ├── components/, components/ui/   shared UI + design-system primitives
│   │   ├── services/                Axios API clients
│   │   └── types/                   shared TypeScript types
│   └── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## 5. Data Ingestion & the Database Connector Architecture

**Production material data is connector-first, not upload-first.** The primary,
recommended way a CPSE's material master enters this platform is a `source_connections`
row (spec section 5.6) — a secure, read-only database connector configuration:

- `database_type`: `POSTGRESQL` | `MYSQL` | `ORACLE` | `SQLSERVER`
- `host` / `port` / `database_name` / `table_name`
- `username_reference` / `secret_reference`: the **names** of environment variables
  holding the read-only credentials — never the credentials themselves. They are
  never stored in the database and never returned by any API response.
- `column_mapping`: how that CPSE's own source columns map onto the canonical
  material record (`app.connectors.base.CanonicalMaterialRecord`) — since every
  CPSE's schema is unknown in advance, this is what makes the connector
  architecture extensible without a code change per CPSE.
- `cursor_column`: the source column used for incremental sync.

`app.connectors.sync_engine` does FETCH → VALIDATE → NORMALIZE → ATTRIBUTE EXTRACTION
→ idempotent UPSERT (keyed on `cpse_id` + `original_material_code`) → triggers the
existing AI pipeline only for created/changed records. The incremental cursor only
advances after a batch succeeds with zero failures; a human-**APPROVED** mapping is
never silently reassigned by a later sync (see `app.ai.analyzer._handle_decision`).

Adding a new CPSE that uses an already-supported database type requires **no code
change** — only a new `source_connections` row plus the credential environment
variables it names.

### CSV / Excel upload — two governed exceptions, not a second ingestion architecture

Two upload paths exist **on top of**, not instead of, the connector architecture above.
Both parse a file into the exact same `CanonicalMaterialRecord` shape a connector
produces and feed it through the identical `app.services.material_ingestion` →
AI pipeline → settlement path — there is no separate upload-specific matching logic.

| | `POST /api/materials/upload/*` | `POST /api/demo-import/*` |
|---|---|---|
| Audience | A CPSE's own **Company Admin / Company User** (or a central admin uploading on a CPSE's behalf) | **Admin only**, for live demonstrations |
| Data marked | `is_demo_data = False` — real production data | `is_demo_data = True` — always, permanently |
| CPSE scope | Strictly the uploader's own CPSE (`app.api.deps.scoped_cpse_id`) — a company user can never target another company | Any already-onboarded CPSE |
| Can create a new CPSE? | No | No |
| Can overwrite existing data? | Yes — a company re-uploading its own real data is a normal update, same as a connector re-sync | Never overwrites real (non-demo) data; refuses with a clear error |
| File formats | `.csv`, `.xlsx` | `.csv` |
| Frontend page | **Material Master → Upload Materials** | **CPSE Network → Demo Data Import** ("DEMO ONLY" labeled) |

This exists because a CPSE onboarding this platform for the first time will not
always have a live, reachable database connector ready on day one — a governed
self-service upload of their own real material master is a legitimate production
path, provided it can never leak into or overwrite another company's data, and never
lets an upload masquerade as automated connector data. See
`app/services/csv_import_service.py` for the shared validation/import core.

---

## 6. Automatic Synchronization

Celery Beat ticks every `SOURCE_SYNC_BEAT_TICK_SECONDS` and checks each enabled
`source_connections` row's own `sync_interval_seconds`; whichever are due get an
incremental sync enqueued (`app.workers.tasks.check_due_source_syncs`). Full and
incremental syncs share the same `_run_sync` implementation and are also triggerable
on demand via `POST /api/synchronization/{id}/sync` (incremental) or
`/full-sync`.

---

## 7. Data Normalization

`app/services/normalization.py` uppercases, collapses whitespace, expands technical
abbreviations (`SS` → `STAINLESS STEEL`), and canonicalizes dimension notation (`4"`,
`4 inch`, `DN100` → one token) — while the *original* CPSE values are always preserved
alongside the normalized ones used for comparison.

`app/services/attribute_extraction.py` backfills `material_grade` / `dimensions` /
`standard` from free text (reusing the same regex vocabulary as the conflict
detector, see `app/ai/attribute_patterns.py`) only when a CPSE's source table didn't
supply them as separate columns — it never overwrites a value the source explicitly
provided.

---

## 8. AI Pipeline

1. **SBERT** (`app/ai/text_embeddings.py`) — real sentence-transformers model with a
   deterministic hashing-based fallback of identical dimensionality.
2. **pgvector** (`app/ai/similarity.py`) — the primary candidate-retrieval layer:
   cosine-distance ANN search pre-filtered by normalized classification. There is no
   FAISS anywhere in this codebase.
3. **Weighted scoring** (`app/services/scoring.py`) — eleven independently
   inspectable 0–100 component scores (description, specification, classification,
   UOM, attributes, grade, dimension, standard, manufacturer, function, criticality).
   Packaging/pack size is *never* a scoring component, and a packaging-only UOM
   difference (e.g. `PC` vs `BOX`) is never treated as a conflict.
4. **Technical conflict detection** (`app/ai/conflict_detector.py`) — a genuine
   grade/dimension/thread/voltage/pressure mismatch always overrides similarity,
   however high.
5. **XGBoost** (`app/ai/ml_ranker.py`) — blends its prediction into the final score
   only when a trained model exists AND the rule-based classification score clears a
   safety floor; otherwise the pure rule-based score decides. No trained model ships
   in this repo by default — see `app/ml/train_xgb_ranker.py`.
6. **Decision engine** (`app/services/decision_engine.py`) — turns the score +
   conflict signal into one of `IDENTICAL / DUPLICATE / NEAR_DUPLICATE /
   FUNCTIONALLY_EQUIVALENT / NOT_EQUIVALENT / TECHNICAL_CONFLICT / MANUAL_REVIEW`.

`app/ai/analyzer.py` orchestrates all of the above and is the **only** place that
creates or updates a `common_material_mappings` row — AI never writes `APPROVED`
directly; a mapping always starts as `AI_RECOMMENDED` / `PENDING_VALIDATION` /
`MANUAL_REVIEW` / `TECHNICAL_CONFLICT` (spec section 9/10/14).

---

## 9. Common National Material Code & CPSE Mapping

`app/services/code_generator.py` issues neutral `CM-XXXXXX` codes from a Postgres
sequence (`nextval()` is atomic, so concurrent workers never collide). A
`common_material_mappings` row links one `cpse_materials` row to one
`common_materials` row with a `mapping_type` (IDENTICAL/DUPLICATE/NEAR_DUPLICATE/
FUNCTIONALLY_EQUIVALENT/MANUAL_MAPPING/LEGACY_MAPPING) and a `decision_status`
governing whether it is official yet. Re-analyzing the same pair updates the
existing mapping rather than creating a duplicate (idempotency, spec section 29).

---

## 10. Legacy Code Rationalization

`GET /api/legacy-codes` groups `cpse_materials` by identical `original_material_code`
across two or more CPSEs — a deliberately separate concept from AI-detected material
*equivalence*. Each pair is classified as `AI_TECHNICAL_EQUIVALENCE` (already linked
to the same common material), `TECHNICAL_CONFLICT` (a real mismatch despite sharing a
code), or `SAME_SOURCE_CODE` (no relationship established yet).

---

## 11. Approval / Governance Workflow

`app/services/harmonization_service.py` is the **only** place that moves a mapping to
an official state — `approve_mapping`, `reject_mapping`, `edit_and_approve_mapping`,
`send_to_manual_review`, `request_more_info` — each paired with an audit log entry
and an `approval_actions` row in the same transaction. Frontend: **Approvals** →
Pending Validation / Approved / Rejected.

---

## 12. Procurement Analytics

`procurement_history` rows (flagged `is_demo_data` when seeded by `app.demo_seed`)
feed `app/services/procurement_service.py`, which aggregates demand per Common
Material Code across CPSEs into a **potential collaborative procurement opportunity**
— always phrased as an estimate, never a realized savings claim.

---

## 13. Audit & Governance

Every AI decision and human action is written to `audit_logs` with `before_state` /
`after_state` / `reason` / `ai_model_version` / `confidence` in addition to a
free-form `details` blob — see `app/services/audit_service.py`.

---

## 14. Security

- Database credentials never touch the frontend or an API response — connectors
  resolve them only from environment variables named by `username_reference` /
  `secret_reference` (`app/connectors/registry.py`).
- Every connector is read-only by construction — the `SourceConnector` interface has
  no write method at all, and the Postgres/MySQL connectors additionally set a
  session-level read-only pragma as defense in depth.
- Table/column identifiers from `column_mapping`/`table_name` are validated against
  a strict allowlist regex before being interpolated into SQL (`app.connectors.base.
  validate_identifier`) — closing the SQL-injection surface outright.
- Roles: `ADMIN`, `MATERIAL_EXPERT`, `REVIEWER`, `VIEWER` (spec section 31).
- JWT auth (`python-jose`), bcrypt password hashing.
- **Company-level data isolation** (`app.api.deps.scoped_cpse_id` / `assert_cpse_access`):
  a user registered against a specific CPSE (`users.cpse_id` set — a "Company
  Admin"/"Company User" in the sense of section 1) can only ever list/view/search/
  upload materials for their own company; any `cpse_id` they pass in a request is
  verified against their own, never trusted outright. This applies to
  `/api/cpse-materials`, `/api/cpse`, `/api/materials/upload/*`, and blocks
  cross-company `/api/cpse-materials/{id}/similar` and the aggregate
  `/api/dashboard/*` endpoints outright. A central user (no `cpse_id` — the "Central/
  Admin/Human Approval user") is unrestricted, since cross-company comparison is the
  entire point of the harmonization/approval workflow.

---

## 15. Running with Docker

```bash
cp .env.example .env        # edit secrets/passwords for anything beyond local demo use
docker compose build
docker compose up -d
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.seed
```

- Frontend: http://localhost:5174
- Backend API root / Swagger UI: http://localhost:8000 / http://localhost:8000/docs
- PostgreSQL (host access): `localhost:5544`

After `python -m app.seed`, the central database is empty (zero CPSEs, materials,
common materials, mappings) except the four roles and one `admin` login — exactly as
spec section 43 requires. Log in as `admin` / `Admin@123` and change the password.

### Demo users

| Username | Password | Role | Company | Notes |
|---|---|---|---|---|
| `admin` | `Admin@123` | ADMIN | *(central, no CPSE)* | Created by `python -m app.seed`; full cross-company/central access. |

There is no other pre-seeded login — `app.seed` intentionally creates only this one
account (spec section 43's "zero business data" requirement). To demonstrate the
company/central role split described in this project's brief, register additional
users via `POST /api/auth/register` (or the Login page's registration flow, if
enabled) after running `app.demo_seed` (which creates the `IOCL`, `ONGC`, `BPCL`
CPSEs):

```bash
curl -X POST http://localhost:8000/api/auth/register -H "Content-Type: application/json" -d '{
  "username": "iocl_manager", "email": "iocl_manager@iocl.example",
  "full_name": "IOCL Material Manager", "password": "Company@123",
  "role_name": "MATERIAL_EXPERT", "cpse_code": "IOCL"
}'
```

A user registered **with** a `cpse_code` is a *Company Admin/User* — scoped to that
one CPSE everywhere in the API (see section 14). A user registered **without** one is
a *Central/Admin/Approval* user — unrestricted, for cross-company harmonization,
approval, and dashboard analytics.

### Demo data (opt-in, clearly separate from production data)

```bash
docker compose exec backend python -m app.demo_seed
```

Creates a handful of demo CPSEs, a plainly-named `demo_source_<cpse_code>` table per
CPSE (standing in for "the CPSE's own external database" — in production this would
be a genuinely separate database), registers real `source_connections` rows
(`is_demo=true`) pointing at them, and runs a **real** full sync through the actual
`PostgresConnector` + AI pipeline. Nothing here bypasses the real ingestion/AI code
path — it only supplies the source data.

---

## 16. Environment Variables

See `.env.example`. Each CPSE's read-only database credentials are set as a pair of
environment variables named by that CPSE's own `source_connections.username_reference`
/ `secret_reference` — never hardcoded, never a single global pair.

---

## 17. Database Migration

```bash
docker compose exec backend alembic upgrade head
```

`alembic/versions/0001_initial.py` creates the entire schema from a clean database.

---

## 18. Running Backend / Frontend / Workers Individually

```bash
# Backend
cd backend && uvicorn app.main:app --reload

# Celery worker (AI analysis + syncs)
cd backend && celery -A app.workers.celery_app worker --loglevel=info

# Celery beat (scheduled incremental syncs)
cd backend && celery -A app.workers.celery_app beat --loglevel=info

# Frontend
cd frontend && npm install && npm run dev
```

---

## 19. Testing

```bash
docker compose exec backend pytest -v
```

Covers: weighted scoring math and decision-engine category boundaries
(`test_scoring.py`, `test_decision_engine.py`), the six required harmonization
fixtures from the spec (`test_harmonization_cases.py`), connector behavior including
SQL-injection-safe identifier validation, paging, and incremental cursoring against a
throwaway SQLite database (`test_connectors.py`), mapping governance/idempotency and
the approved-mapping-protection invariant (`test_mapping_governance.py`), JWT
auth/RBAC (`test_auth.py`), CPSE/material/legacy-code/duplicate-detection read APIs,
automatic batch settlement/convergence (`test_sync_settlement.py`), the DEMO ONLY
admin CSV import (`test_csv_import.py`), the company self-service CSV/Excel upload
(`test_material_upload.py`), per-company data isolation/RBAC
(`test_company_data_isolation.py`), and the XGBoost fallback + safety-gate blend
logic (`test_xgboost_ranker.py`). 122 tests, all passing.

---

## 20. API Endpoint Reference

| Area | Endpoints |
|---|---|
| Auth | `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me` |
| CPSE roster | `GET/POST /api/cpse`, `GET/PUT/PATCH /api/cpse/{id}` *(company-scoped)* |
| Materials | `GET /api/cpse-materials`, `GET /api/cpse-materials/search`, `GET /api/cpse-materials/{id}`, `GET /api/cpse-materials/{id}/similar` *(company-scoped; similarity is central-only)* |
| Company upload | `POST /api/materials/upload/validate`, `POST /api/materials/upload/confirm`, `GET /api/materials/upload/history`, `GET /api/materials/upload/template` |
| Demo import (admin only) | `POST /api/demo-import/validate`, `POST /api/demo-import/confirm`, `GET /api/demo-import/history`, `GET /api/demo-import/sample-csv` |
| Synchronization | `GET/POST /api/synchronization`, `.../{id}/test-connection`, `.../{id}/sync`, `.../{id}/full-sync`, `.../{id}/sync-history` |
| Harmonization | `GET /api/harmonization/*` (duplicates/near-duplicates/functional-equivalence/technical-conflicts), `POST /api/harmonization/scan` |
| Common materials | `GET /api/common-materials`, `GET /api/common-materials/{code}` |
| Duplicate codes | `GET /api/duplicate-codes`, `GET /api/duplicate-codes/{code}` |
| Approvals | `GET /api/approvals`, `POST /api/approvals/{id}/approve`, `/reject`, `/edit-and-approve`, `/manual-review` |
| Analytics | `GET /api/analytics/*`, `GET /api/procurement/*` |
| Dashboard | `GET /api/dashboard/statistics`, `GET /api/dashboard/trends` *(central users only)* |
| Audit | `GET /api/audit-logs` |
| Notifications / Settings | `GET /api/notifications`, `GET/PUT /api/settings` |

Full interactive schema: `http://localhost:8000/docs` (Swagger UI) once the backend
is running.

---

## 21. Frontend Pages / Routes

`/dashboard` · `/materials`, `/materials/cpse`, `/materials/{id}`, `/materials/{id}/analysis`
· `/material-upload` (company self-service upload) · `/common-material-master`,
`/common-material-master/{code}` · `/legacy-codes`, `/legacy-codes/{code}` ·
`/harmonization/recommendations`, `/duplicates`, `/near-duplicates`,
`/functional-equivalence`, `/technical-conflicts`, `/harmonization/pairs/{mappingId}`
(side-by-side comparison + AI explanation + Approve/Reject) · `/cpse`, `/cpse/{id}` ·
`/synchronization` (Data Synchronization) · `/demo-import` (Demo Data Import - DEMO
ONLY, clearly labeled) · `/approvals/pending`, `/approved`, `/rejected`, `/approvals/{id}`
· `/analytics`, `/analytics/procurement`, `/analytics/classification`, `/analytics/trends`
· `/audit-log` · `/governance/rules` · `/notifications` · `/settings` · `/login`.

---

## 22. Terminology

CPSE Material · Common Material · Common National Material Code · Common Material
Master · Material Harmonization · Duplicate Material · Near-Duplicate Material ·
Functionally Equivalent Material · Technical Conflict · Legacy Material Code ·
Material Mapping · Procurement Aggregation · Material Master Governance.

The official product name is **AI-Powered National Unified Material Master** — not an
"ERP Harmonizer", "Upload Manager", or "Source DB Manager".
#   M a t e r i a l - C o d e  
 