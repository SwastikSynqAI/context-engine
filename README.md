# Context Engine - Enterprise AI Data Intelligence Layer

An open-source, self-hosted AI infrastructure layer for enterprise operations. Combines a **Context API** (entity graph, RAG, RLHF, policy engine) with a fully automated **AI Hiring Pipeline** — built with FastAPI, Next.js 14, PostgreSQL, and Claude (Anthropic).

> Built and open-sourced by [SwastikSynqAI](https://github.com/SwastikSynqAI). Battle-tested in production.

---

## What This Is

A two-part system:

### 1. Context API (`/src`)
A data intelligence backend that ingests, stores, and reasons over enterprise data:
- **Entity Graph** — companies, contacts, deals, properties with relationship mapping
- **RAG Context Engine** — retrieves relevant context for any query using pgvector embeddings
- **RLHF Feedback Loop** — captures human corrections to improve AI responses over time
- **Decision Capture** — records every human decision with reasoning for future model training
- **Policy Engine** — configurable rules that govern AI behaviour (auto-reject, flag, escalate)
- **Evaluation Framework** — Claude-as-judge scoring for response quality
- **Intent Classifier** — routes queries to the right reasoning path
- **ICP Learner** — learns ideal customer profile from decision history
- **Multi-source Ingestion** — Gmail, Google Sheets, HubSpot, documents

### 2. AI Hiring Pipeline (`/src/engines/hr` + `/frontend/app/hire`)
A complete end-to-end recruitment engine:
- **AI Resume Scoring** — Claude evaluates resumes against role-specific rubrics (with keyword fallback)
- **Automated Pre-screening** — structured email conversation, AI-scored
- **Proctored Online Tests** — aptitude, English, domain modules, auto-graded
- **HR Kanban Dashboard** — 10-stage pipeline with full candidate profiles
- **Offer Letter Generation** — Claude-drafted, one-click, auto-emailed
- **Analytics** — funnel, weekly intake, scores by role
- **Full Email Automation** — every touchpoint automated (test invite, reminders, HOD notification, rejection)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+ / FastAPI (fully async) |
| Database | PostgreSQL 15 + pgvector extension |
| ORM | SQLAlchemy 2.0 (async) + Alembic migrations |
| AI | Anthropic Claude (Haiku for scoring, Sonnet for generation) |
| Frontend | Next.js 14 App Router + TypeScript |
| Styling | Tailwind CSS |
| Workers | APScheduler (background jobs) |
| Auth | JWT + bcrypt |
| Email | SMTP (any provider) |
| Container | Docker + Docker Compose |
| Calendar | Google Calendar API (optional) |

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- An [Anthropic API key](https://console.anthropic.com/)
- SMTP credentials (Gmail, Resend, Postmark, etc.)

### 1. Clone and configure

```bash
git clone https://github.com/SwastikSynqAI/context-engine.git
cd context-engine

# Copy example env and fill in your values
cp .env.example .env
nano .env  # or your editor of choice
```

### 2. Set required variables in `.env`

```env
ANTHROPIC_API_KEY=sk-ant-...         # Required — get from console.anthropic.com
POSTGRES_PASSWORD=your-secure-pass   # Set a strong password
JWT_SECRET_KEY=your-random-secret    # Generate: openssl rand -hex 32
ADMIN_EMAIL=admin@yourcompany.com
SMTP_HOST=smtp.gmail.com
SMTP_USERNAME=you@yourcompany.com
SMTP_PASSWORD=your-app-password
```

### 3. Start

```bash
docker-compose up -d
```

Services:
- **API** → http://localhost:8000
- **Frontend** → http://localhost:3002
- **API Docs** → http://localhost:8000/docs
- **pgAdmin** → http://localhost:5050

### 4. Run migrations

```bash
docker exec context_engine_api alembic upgrade head
```

### 5. Create admin user

```bash
# Generate a bcrypt hash for your password
python3 -c "import bcrypt; print(bcrypt.hashpw(b'YourPassword', bcrypt.gensalt()).decode())"

# Set in .env:
# ADMIN_PASSWORD_HASH=<the hash above>
# ADMIN_EMAIL=admin@yourcompany.com
```

### 6. Seed demo data (optional)

```bash
docker exec context_engine_api python /app/scripts/seed_demo.py
```

---

## Project Structure

```
context-engine/
├── src/                          # FastAPI backend
│   ├── main.py                   # App entry point + lifespan
│   ├── config.py                 # All settings (Pydantic Settings)
│   ├── database.py               # Async SQLAlchemy session factory
│   ├── api/routes/               # REST endpoints
│   │   ├── auth.py               # JWT login
│   │   ├── entities.py           # Entity CRUD
│   │   ├── context.py            # Query / RAG endpoint
│   │   ├── decisions.py          # Decision capture
│   │   ├── rules.py              # Policy rules
│   │   ├── hr.py                 # Public careers form + test submission
│   │   ├── hr_dashboard.py       # HR admin pipeline API
│   │   ├── evals.py              # Evaluation runs
│   │   └── oversight.py          # Quality monitoring
│   ├── engines/hr/               # Hiring pipeline engine
│   │   ├── inbound/              # Form receiver, resume extractor, deduplication
│   │   ├── scoring/              # Resume scorer (Claude + keyword fallback)
│   │   ├── screening/            # Pre-screen dispatcher, question bank, scorer
│   │   ├── ranking/              # Shortlister
│   │   ├── rubric.py             # Role-specific scoring rubrics
│   │   └── models.py             # HR Pydantic models
│   ├── reasoning/                # Core AI reasoning layer
│   │   ├── context_engine.py     # RAG + RLHF context retrieval
│   │   ├── rules_engine.py       # Configurable policy rules
│   │   ├── policy_engine.py      # Policy enforcement
│   │   ├── intent_classifier.py  # Query routing
│   │   ├── icp_learner.py        # Ideal customer profile learning
│   │   ├── decision_capture.py   # Human decision recording
│   │   └── evaluator.py          # Claude-as-judge evals
│   ├── ingestion/                # Data source connectors
│   │   ├── gmail.py              # Gmail ingestion
│   │   ├── sheets.py             # Google Sheets
│   │   ├── hubspot.py            # HubSpot CRM
│   │   └── documents.py          # Document parsing
│   ├── graph/                    # Entity graph layer
│   │   ├── entity_store.py       # Entity CRUD + vector search
│   │   ├── embedder.py           # pgvector embedding generation
│   │   └── relationship_mapper.py
│   ├── services/
│   │   ├── offer_generator.py    # Offer letter generation (Claude + template fallback)
│   │   ├── test_engine.py        # Test generation + scoring
│   │   ├── gcal_service.py       # Google Calendar integration
│   │   └── imap_service.py       # IMAP email checking
│   └── workers/                  # APScheduler background jobs
│       ├── scheduler.py          # Job registration
│       ├── resume_worker.py      # Scores unscored resumes every 5 min
│       ├── reply_checker.py      # Checks candidate email replies
│       ├── stage_advancement.py  # Auto-advances screened candidates
│       └── reminder_worker.py    # Sends reminders every 6 hours
├── frontend/                     # Next.js 14 frontend
│   ├── app/
│   │   ├── hire/                 # HR dashboard (pipeline, analytics, settings, candidate detail)
│   │   ├── apply/                # Public careers application form
│   │   ├── test/[token]/         # Candidate test interface
│   │   ├── query/                # Context query interface
│   │   ├── teach/                # RLHF teaching interface
│   │   └── oversight/            # Quality monitoring UI
│   └── lib/
│       ├── api.ts                # Context API client
│       └── hire-api.ts           # Hiring API client
├── alembic/                      # Database migrations
│   └── versions/
│       ├── 001_initial_schema.py
│       ├── 002_rules_and_conflicts.py
│       ├── 003_oversight.py
│       └── 004_hr_engine.py
├── tests/                        # Full test suite (pytest)
├── scripts/
│   ├── seed_demo.py              # Populate with demo candidates
│   └── seed_intelligence.py      # Populate context data
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## Configuration Reference

All configuration is via environment variables. See `.env.example` for the full list.

### Core (Required)

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `DATABASE_URL` | PostgreSQL connection string |
| `JWT_SECRET_KEY` | Random secret for JWT signing (min 32 chars) |
| `ADMIN_EMAIL` | Login email for HR dashboard |
| `ADMIN_PASSWORD_HASH` | bcrypt hash of admin password |

### Email (Required for automation)

| Variable | Description |
|----------|-------------|
| `SMTP_HOST` | SMTP server hostname |
| `SMTP_PORT` | SMTP port (default: 587) |
| `SMTP_USERNAME` | SMTP login username |
| `SMTP_PASSWORD` | SMTP login password |
| `HIRING_EMAIL` | From-address for all hiring emails |

### HR Pipeline (Optional — has defaults)

| Variable | Description | Default |
|----------|-------------|---------|
| `HR_RESUME_SCORE_THRESHOLD` | Min resume score to trigger pre-screening | 60 |
| `HR_SCREEN_SCORE_THRESHOLD` | Min screen score to advance | 60 |
| `HR_TEST_PASS_THRESHOLD` | Min test score to pass | 60 |
| `ADMIN_NOTIFY_EMAIL` | Email to notify on shortlists | same as `ADMIN_EMAIL` |

### Optional Integrations

| Variable | Description |
|----------|-------------|
| `GOOGLE_CREDENTIALS_JSON` | Google OAuth2 credentials (for Calendar/Gmail) |
| `HUBSPOT_API_KEY` | HubSpot CRM ingestion |

---

## Hiring Pipeline — Stage Flow

```
Application Submitted
        ↓
Resume Scored by Claude (every 5 min, worker)
        ↓  if score ≥ threshold
Pre-screen Email Conversation Started (automated)
        ↓  candidate replies over days
Screen Score Computed
        ↓  HR advances
Proctored Test Sent (auto-email with unique link)
        ↓  candidate completes
Test Auto-Graded (Aptitude 35% + English 30% + Domain 35%)
        ↓  HR reviews
HR Decision → Pass or Reject
        ↓
Shortlisted → Offer Letter Generated → Sent
        ↓
Hired
```

---

## Customising the HR Rubric

Rubrics live in `src/engines/hr/rubric.py`. Each role has a `RoleRubric` with:
- Scoring dimensions and weights
- Role-specific keywords
- Scoring prompt template

To add a new role:
```python
# In rubric.py
RUBRICS["your_role"] = RoleRubric(
    role="your_role",
    display_name="Your Role Title",
    dimensions=[...],
    keywords=[...],
)
```

---

## Enabling / Disabling Background Workers

Workers are controlled in `src/main.py` via the APScheduler lifespan. To pause all automation (e.g. during setup or tuning):

```python
# In src/main.py — comment out the scheduler block:
@asynccontextmanager
async def lifespan(app: FastAPI):
    # from src.workers.scheduler import create_scheduler
    # scheduler = create_scheduler()
    # scheduler.start()
    yield
    # scheduler.shutdown(wait=False)
```

Re-enable by uncommenting.

---

## Running Tests

```bash
# From project root
docker exec context_engine_api pytest tests/ -v

# HR-specific tests only
docker exec context_engine_api pytest tests/hr/ -v
```

---

## API Documentation

Full interactive API docs at **http://localhost:8000/docs** (Swagger UI).

Key endpoints:

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/login` | Get JWT token |
| `GET` | `/entities` | List all entities |
| `POST` | `/entities` | Create entity |
| `POST` | `/context/query` | RAG context query |
| `POST` | `/hr/apply` | Submit job application |
| `GET` | `/hire/pipeline` | Kanban pipeline data |
| `GET` | `/hire/analytics` | Analytics summary |
| `POST` | `/hire/{id}/advance` | Advance candidate stage |
| `POST` | `/hire/{id}/offer` | Generate offer letter |
| `GET` | `/health` | System health check |

---

## Architecture Decisions

**Why FastAPI + async?** The pipeline involves many I/O-bound operations (LLM calls, email, database). Async throughout allows handling many concurrent candidates without thread-pool overhead.

**Why pgvector instead of a vector DB?** One less infrastructure dependency. PostgreSQL with pgvector handles embedding search well at startup scale, and you already have Postgres for everything else.

**Why Claude for scoring?** Structured JSON output with reasoning traces, green/red flags, and per-dimension scores. The rubric-based prompt approach makes scoring auditable and adjustable without retraining.

**Why keyword fallback?** The pipeline must never stall due to an API outage. Every Claude-dependent step has a deterministic fallback so HR can continue working regardless.

---

## Contributing

PRs welcome. Please:
1. Keep the fallback pattern for any new AI-dependent feature
2. Add tests for new pipeline stages
3. Update `.env.example` for any new config

---

## License

MIT — use freely, build on it, just don't remove the license header.

---

## Acknowledgements

Built with [FastAPI](https://fastapi.tiangolo.com/), [Next.js](https://nextjs.org/), [Anthropic Claude](https://www.anthropic.com/), [pgvector](https://github.com/pgvector/pgvector), and [APScheduler](https://apscheduler.readthedocs.io/).
