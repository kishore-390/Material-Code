# ONE NATION → ONE COMMON MATERIAL CODE

**AI-Powered CPSE Material Harmonization Platform**

A real, working full-stack prototype that harmonizes material codes used by
different Central Public Sector Enterprises (CPSEs). When two CPSEs describe
the same physical item differently (e.g. `IOCL-PIP-1023` "Carbon Steel
Seamless Pipe" vs `ONGC-4481` "Seamless Carbon Steel Pipe"), the platform's AI
pipeline detects the equivalence, scores it explainably, and — depending on
confidence — either auto-generates a Common Material Code, routes it to a
Material Expert for approval, or declines to harmonize it.

---

## 1. Objective

Different CPSEs maintain independent material masters with inconsistent
codes, descriptions, specifications and units for identical or near-identical
items. This causes duplicate purchasing, inconsistent inventory data, and
lost procurement leverage. This platform:

1. Ingests material data (manual entry, CSV/Excel bulk upload, images) from
   any CPSE.
2. Normalizes descriptions, specifications, categories and units of measure.
3. Generates text + image embeddings and runs a **pgvector** similarity
   search to retrieve plausible duplicate candidates — never a full
   table scan.
4. Computes an **explainable, weighted similarity score** across six
   components (description, specification, category, UOM, image, attributes).
5. Applies a **deterministic decision engine** (≥95% auto-harmonize,
   85–95% human review, 60–85% low confidence, <60% no common code).
6. Keeps AI **recommendation**, human **approval**, and Common Material
   **Master updates** as three strictly separated steps, all captured in an
   immutable audit log.

---

## 2. Architecture

```
React + TS Frontend (Vite)
        |  REST (Axios / React Query)
        v
FastAPI Backend  ────────────┬───────────────┐
        |                    |               |
        v                    v               v
PostgreSQL + pgvector      Redis        Celery Workers
        |                                    |
        v                                    v
Material Database                    AI Processing Pipeline
        |                              (text + image embeddings,
        v                               pgvector search, scoring)
   Decision Engine
   >=95%        85-94.99%        <85%
   Auto      Human Review     Low Confidence / Reject
   Harmonize     Required
        |
        v
Common Material Code Generator (DB sequence, transaction-safe)
        |
        v
Common Material Master + Audit Log + Notifications
```

See `backend/app/ai/analyzer.py` for the pipeline orchestrator and
`backend/app/services/decision_engine.py` / `scoring.py` for the rules.

---

## 3. Technology Stack

**Frontend:** React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui-style
components (Radix primitives + class-variance-authority), React Router,
TanStack React Query, Recharts, Axios, lucide-react.

**Backend:** Python 3.12, FastAPI, SQLAlchemy 2.x, Pydantic v2, PostgreSQL,
pgvector, Alembic, JWT auth (python-jose), Passlib/bcrypt, Celery, Redis.

**AI/ML:** sentence-transformers (`all-MiniLM-L6-v2`) for text embeddings,
CLIP (`openai/clip-vit-base-patch32`) for image embeddings, scikit-learn,
Pillow — all with a deterministic, structurally-identical **mock fallback**
(feature-hashing bag-of-words / pixel histogram) so the whole pipeline runs
even with no internet access to download model weights. Swapping in the real
models requires zero API changes.

**Infrastructure:** Docker, Docker Compose.

---

## 4. Project Structure

```
material/
├── backend/
│   ├── app/
│   │   ├── main.py                FastAPI app, CORS, static /uploads mount
│   │   ├── core/                  settings, security (JWT/bcrypt)
│   │   ├── db/                    session, declarative base, extension init
│   │   ├── models/                SQLAlchemy models (15 tables)
│   │   ├── schemas/                Pydantic request/response models
│   │   ├── api/endpoints/          auth, materials, ai, harmonization,
│   │   │                           approvals, common_codes, cpse, dashboard,
│   │   │                           audit, notifications, settings
│   │   ├── services/               normalization, scoring, decision_engine,
│   │   │                           code_generator, harmonization_service,
│   │   │                           bulk_import, file_storage, audit/notify
│   │   ├── ai/                     text/image embeddings, similarity, analyzer
│   │   ├── workers/                Celery app + tasks
│   │   └── seed.py                 realistic seed data + demo scenarios
│   ├── alembic/                    migrations (0001_initial creates all tables)
│   ├── tests/                      pytest: scoring, decision engine, auth, API
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/                  one file per route (see section 9)
│   │   ├── components/, components/ui/   shared UI + shadcn-style primitives
│   │   ├── charts/                 Recharts wrappers
│   │   ├── services/                Axios API clients
│   │   ├── auth/                    AuthContext, RequireAuth guard
│   │   └── types/                   shared TypeScript types
│   └── Dockerfile
├── uploads/                        bind-mounted file storage (materials/documents/images)
├── docker-compose.yml
└── .env.example
```

---

## 5. Running with Docker

```bash
cp .env.example .env        # edit secrets/passwords for anything beyond local demo use
docker compose build
docker compose up -d
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.seed
```

- Frontend: http://localhost:5174
- Backend API root: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- PostgreSQL (for pgAdmin/psql from your host machine): `localhost:5544`
- pgAdmin (optional, containerized): `docker compose --profile tools up -d pgadmin` → http://localhost:5050

> Ports 5173, 5432 and 5433 are commonly already in use by other local
> projects, so this stack maps its frontend to **5174** and Postgres to
> **5544** on the host. These are only host-side port numbers — containers
> always talk to each other over the internal Docker network
> (`postgres:5432`), so this never needs to match `DATABASE_URL`.

### Viewing the database in a desktop pgAdmin / DBeaver / psql

If you already have pgAdmin installed natively (not the containerized one
above), register a **new server** connection — don't reuse an existing one,
it's almost certainly pointing at a different local Postgres instance:

| Field | Value |
|---|---|
| Host | `localhost` |
| Port | `5544` |
| Maintenance database | `material_harmonization` |
| Username | `material_admin` |
| Password | value of `POSTGRES_PASSWORD` in your `.env` |

Other useful commands:

```bash
docker compose logs -f backend worker
docker compose down                 # stop everything
docker compose down -v              # also wipe the Postgres volume
```

> The backend container runs `alembic upgrade head` automatically on
> startup, and creates the `vector` / `uuid-ossp` Postgres extensions on
> first boot — no manual DB setup required beyond the seed command above.

---

## 6. Environment Variables

See `.env.example` for the full list. Key ones:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | SQLAlchemy connection string (Postgres) |
| `REDIS_URL` / `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | Celery/Redis wiring |
| `JWT_SECRET_KEY` | **Change this** before any non-local use |
| `TEXT_EMBEDDING_MODEL` / `IMAGE_EMBEDDING_MODEL` | HuggingFace model ids |
| `AI_USE_MOCK_FALLBACK` | If real models fail to load, fall back to the deterministic mock embedder instead of raising |
| `THRESHOLD_AUTO` / `THRESHOLD_REVIEW` / `THRESHOLD_LOW` | Decision thresholds (also editable at runtime from Admin → Settings) |
| `WEIGHT_DESCRIPTION` … `WEIGHT_ATTRIBUTES` | Scoring weights (must sum to 1.0) |

Frontend credentials/URLs are never hardcoded in source — `VITE_API_URL` is
injected at container start and read via `import.meta.env`.

---

## 7. Sample Login Credentials (from `app/seed.py`)

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `Admin@123` |
| Material Expert | `raj.kumar` | `Expert@123` |
| Material Expert | `priya.sharma` | `Expert@123` |
| CPSE User (IOCL) | `iocl.user` | `Cpse@123` |
| CPSE User (ONGC) | `ongc.user` | `Cpse@123` |
| CPSE User (BPCL) | `bpcl.user` | `Cpse@123` |
| CPSE User (HPCL) | `hpcl.user` | `Cpse@123` |
| CPSE User (SAIL) | `sail.user` | `Cpse@123` |
| Viewer | `viewer` | `Viewer@123` |

---

## 8. How Material Upload Works

`/materials/upload` supports:

- **Single upload** — a form (material code, description, specification,
  category, UOM, CPSE, manufacturer, brand, material type, free-form
  attributes, image) posted as `multipart/form-data` to `POST /api/materials`.
- **Bulk upload** — CSV/Excel with columns `material_code, description,
  specification, category, uom, cpse, manufacturer, brand, material_type,
  image`. The flow is: upload → `POST /api/materials/bulk/validate` (returns
  a per-row validation report: missing description, invalid/missing UOM,
  duplicate material code, unknown CPSE) → review in the browser → confirm →
  `POST /api/materials/bulk/import`, which imports only the valid rows and
  queues each one for AI analysis via Celery.

Every created material is automatically queued for AI analysis
(`app.workers.tasks.ai_analysis`) so uploads never block on embedding
generation, even for large batches.

---

## 9. How AI Matching Works

1. **Normalize** (`app/services/normalization.py`): uppercase, punctuation,
   unit vocabulary (`M`/`Metre`/`Meter` → `METER`), technical abbreviations
   (`CS` → `CARBON STEEL`), and dimension formats (`4"`, `4 inch`, `DN100`
   all collapse to a single `4IN` token) — while the *original* values are
   always preserved alongside the normalized ones.
2. **Embed** (`app/ai/text_embeddings.py`, `image_embeddings.py`): a text
   embedding from the normalized description/specification/category, and an
   image embedding if a photo was provided. Stored in `pgvector` columns.
3. **Retrieve candidates** (`app/ai/similarity.py`): pgvector cosine-distance
   ANN search, pre-filtered by normalized category, capped to a handful of
   candidates — the platform never does an O(n²) full-table compare.
4. **Score** (`app/services/scoring.py`): six explainable component scores
   (description 30%, specification 25%, category 15%, UOM 10%, image 15%,
   attributes 5%), each independently inspectable, blended into one final
   confidence score.
5. **Decide** (`app/services/decision_engine.py`):
   - `≥ 95%` → `AUTO_HARMONIZATION` — a Common Material Code is generated
     immediately (transaction-safe DB sequence), linked to both materials,
     and the action is written to the audit log.
   - `85% – 94.99%` → `HUMAN_REVIEW_REQUIRED` — an Approval Request is
     created and the Material Expert role is notified. No master update
     happens until a human acts.
   - `60% – 84.99%` → `LOW_CONFIDENCE` — nothing is auto-created; the
     uploader can manually request expert review.
   - `< 60%` → `NO_COMMON_CODE` — the material is left as-is.

The `/materials/:id/analysis` page renders every component score with a
progress bar and a plain-language reason, never just a single percentage.

---

## 10. How Human Approval Works

The **Approval Center** (`/approvals`) lists every pending `HUMAN_REVIEW_REQUIRED`
or manually-submitted request. Opening one (`/approvals/:id`) shows a
field-by-field, side-by-side comparison (description, specification,
category, UOM, manufacturer, brand, image) each flagged `Same` / `Similar` /
`Different`. A Material Expert or Admin can:

- **Approve** — generates/reuses a Common Material Code and updates the
  Common Material Master.
- **Merge** — same effect as approve, recorded distinctly for reporting.
- **Reject** / **Not Same Material** — no master update; the requester is
  notified with the reason.
- **Request More Information** — leaves the request open and notifies the
  original uploader.

Every action is written to `approval_actions` (`approved_by`, `remarks`,
timestamp) and mirrored into the global `audit_logs` table.

---

## 11. How Common Codes Are Generated

`app/services/code_generator.py` builds
`<MATERIAL-TYPE-SHORT>-<CATEGORY-SHORT>-<SEQUENCE>` (e.g. `CS-PIPE-00124`,
`BALL-VALVE-00087`). The sequence comes from a real PostgreSQL sequence
(`common_material_code_seq`, created by the initial migration) — `nextval()`
is atomic at the database level, so concurrent Celery workers can never
collide or double-issue a code. Codes are **never** a concatenation of the
source material codes.

---

## 12. Governance Rule

AI never silently writes to the Common Material Master. The three steps are
strictly separated in the schema and the code path:

- **AI recommendation** → `ai_analysis` + `material_matches` rows (read-only
  facts about what the AI found).
- **Human approval** (when required) → `approval_requests` +
  `approval_actions`.
- **Master update** → only `app/services/harmonization_service.py`
  (`approve_harmonization`) ever writes `common_material_codes` /
  `materials.common_code_id`, and every call is paired with an
  `audit_logs` entry in the same transaction — including the automatic
  ≥95% path, which is still fully logged as an `AI ENGINE` actor.

---

## 13. Testing

```bash
docker compose exec backend pytest -v
```

Covers: weighted scoring math (`test_scoring.py`), the four decision
boundaries — 96%→AUTO, 90%→HUMAN_REVIEW, 75%→LOW_CONFIDENCE,
55%→NO_COMMON_CODE — (`test_decision_engine.py`), JWT auth/register/login
(`test_auth.py`), and the materials API including RBAC (CPSE-scoped uploads,
viewer cannot create, duplicate code rejection) in `test_materials_api.py`.
Integration tests spin up an isolated `material_harmonization_test` database
on the same Postgres instance.

---

## 14. Demo Script (matches the three scripted scenarios)

The seed script (`python -m app.seed`) creates 12 duplicate material groups
across 10 CPSEs (pipes, valves, bearings, lubricants, flanges, motors, pumps,
cables, transformers, fasteners, gaskets, industrial chemicals), ~100
standalone materials, and a couple of explicitly engineered edge cases, then
runs every material through the **real** AI pipeline (embeddings from the
live `sentence-transformers/all-MiniLM-L6-v2` model when available, no
hardcoded scores). A representative run against the seed data produced:

1. **High confidence (≥95%)** — `IOCL-PIP-1023` (Carbon Steel Seamless Pipe,
   ASTM A106 Grade B, 4") matched `ONGC-4481` (Seamless Carbon Steel Pipe,
   ASTM A106 Gr.B, 4") at **96.2%** and was auto-harmonized into a new
   Common Material Code with no human step — check the Common Material
   Master. The other two CPSEs in the same physical group,
   `BPCL-CS-0912` and `HPCL-P-7821`, scored 92–94% against each other (see
   next point) rather than jumping straight to auto-harmonization — a
   realistic outcome, since each material is scored against its own single
   best candidate, not the whole group at once.
2. **Human review (85–95%)** — `HPCL-P-7821` vs `IOCL-PIP-1023` (**94.0%**),
   `BPCL-CS-0912` vs `HPCL-P-7821` (**92.3%**), and `ONGC-VLV-9091` vs
   `ONGC-6612` (**90.0%**, Cast Steel Gate Valve, same size but different
   pressure class) all landed in the human-review band. Open the Approval
   Center, review the side-by-side comparison, and click Approve — approving
   `HPCL-P-7821` reuses the Common Material Code already created in step 1
   (since its top candidate is already harmonized), and approving
   `BPCL-CS-0912` next folds it into the same code too. This is the intended
   governance behavior: the ≥95% pair auto-harmonizes instantly, and the
   rest of the group joins only once a Material Expert confirms it.
3. **Low confidence / no match (<85%)** — `HPCL-CBL-5502` (PVC Insulated
   Electrical Cable) scored 78.5% against the nearest cable in the catalogue
   — too low to harmonize automatically, with an option to request expert
   review. Among the randomly-sized standalone materials, a few pairs with
   no real counterpart in the catalogue (e.g. a lone 65" flange) score in
   the 40–55% range and land on `NO_COMMON_CODE`, showing "No sufficiently
   similar material found."

Because scoring runs against live embeddings rather than fixed numbers, your
exact percentages may differ slightly by a point or two between runs or AI
backends (real model vs. mock fallback) — the point of the demo is the four
*decision bands*, which are deterministic given the score, not the specific
decimal.

---

## 15. API Documentation

Full interactive documentation is served by FastAPI itself:

- Swagger UI → http://localhost:8000/docs
- ReDoc → http://localhost:8000/redoc

Endpoint groups: `/api/auth`, `/api/materials` (+ `/search`, `/{id}/similar`,
`/bulk/validate`, `/bulk/import`), `/api/ai`, `/api/harmonization`,
`/api/approvals`, `/api/common-codes`, `/api/cpse`, `/api/dashboard`,
`/api/audit-logs`, `/api/notifications`, `/api/settings`.
