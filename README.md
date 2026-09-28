# 🤖 AI Code Review & Rewrite Agent (Hindsight-Powered)

> **An AI-powered developer tool that reviews, detects, and improves source code using Google Gemini AI and learns across reviews using Hindsight persistent agent memory.**

AI Code Review & Rewrite Agent helps developers identify **bugs, security vulnerabilities, performance issues, and code-quality problems**, while also generating optimized code automatically. Featuring persistent memory powered by **Hindsight**, the agent retains durable architectural conventions, coding rules, and past findings, allowing previous review insights to genuinely inform subsequent code evaluations.

---

## ✨ Features

* 🧠 **Hindsight Persistent Memory** — Retains project-level coding conventions and architectural patterns across reviews
* 🔄 **Feedback → Retain → Reflect → Review Pipeline** — Learns from developer feedback (accept, reject, resolve) and synthesizes high-level conventions
* 👤 **Developer & Team Memory Isolation** — Tracks developer-specific habits while scoping shared team conventions without cross-project contamination
* 🪞 **Hindsight Reflection Engine** — Leverages Hindsight's `reflect()` API to synthesize durable conventions from recurring patterns
* 🚫 **Negative Feedback Suppression** — Prevents repeatedly proposing recommendations previously rejected by the team for project-specific reasons
* ⚖️ **Calibrated Confidence Wording** — Distinguishes between isolated observations, repeated patterns, and established conventions
* 🛡️ **Secret & Token Sanitization** — Automatically redacts API keys, passwords, and tokens before retention
* 🔍 **AI Code Review** — Analyze code and receive intelligent feedback powered by Gemini 2.5 Flash
* 🐛 **Bug & Vulnerability Detection** — Identify logical errors, security flaws, and performance bottlenecks
* ⚡ **Performance Optimization** — Find inefficient algorithms and suggest optimized implementations
* ✍️ **AI Code Rewrite** — Generate cleaner, secure, and idiomatic code with diff breakdown
* 🌐 **Multi-Language Support** — Review Python, JavaScript, TypeScript, Rust, and Go
* 📊 **Developer Dashboard** — Interactive code review interface with memory visibility and feedback actions (Accept, Reject, Mark Fixed)
* 🛡️ **Graceful Degradation** — Always functions as a standard review agent even if memory services or reflection are offline

---

## 🛠️ Tech Stack

* **Frontend:** HTML5 • TailwindCSS • Modern Vanilla JavaScript • Glassmorphism UI
* **Backend:** Python 3.12 • FastAPI • Pydantic v2 • Uvicorn
* **Agent Memory:** [Hindsight](https://github.com/vectorize-io/hindsight) (`hindsight-client` with `arecall`, `aretain`, `areflect`)
* **AI Engine:** Google Gemini API (`gemini-2.5-flash`)
* **Testing:** Pytest • Pytest-Asyncio • HTTPX

---

## 🧠 Hindsight Memory Architecture

```text
               +-------------------------------------------------+
               |                  Developer                      |
               +-----------------------+-------------------------+
                                       |
                                       | Submits Code
                                       v
               +-------------------------------------------------+
               |              FastAPI Backend                    |
               +-----------------------+-------------------------+
                                       |
           1. Recall Relevant Memories | (Scoped by Project ID)
                                       v
               +-------------------------------------------------+
               |              Hindsight Server                   |
               |       (Persistent Memory Bank Layer)            |
               +-----------------------+-------------------------+
                                       |
           2. Returns Durable Context  | (Conventions, Patterns)
                                       v
               +-------------------------------------------------+
               |           Memory Context Builder                |
               |      - Injection-safe sanitization              |
               |      - Bounded prompt assembly                  |
               +-----------------------+-------------------------+
                                       |
           3. Code + Memory Context    |
                                       v
               +-------------------------------------------------+
               |               Google Gemini AI                  |
               |  - Identifies new issues                        |
               |  - Evaluates consistency with past conventions  |
               +-----------------------+-------------------------+
                                       |
           4. Review Findings          |
                                       v
               +-------------------------------------------------+
               |          Knowledge Extractor & Sanitizer        |
               |      - Extracts durable rules & findings        |
               |      - Redacts API keys & secrets               |
               +-----------------------+-------------------------+
                                       |
           5. Retain New Knowledge     |
                                       v
               +-------------------------------------------------+
               |             Hindsight Retain                    |
               |       (Updates persistent project bank)         |
               +-----------------------+-------------------------+
                                       |
                                       v
               +-------------------------------------------------+
               |   Client Response (Review + Memory Status)      |
               +-------------------------------------------------+
```

### Memory Pipeline: FEEDBACK → RETAIN → REFLECT → LEARN PATTERNS → PERSONALIZED REVIEW

1. **RECALL**: Queries Hindsight for project memories (`project:{project_id}`) and, if provided, developer-specific memories (`developer:{developer_id}`).
2. **REFLECT**: When sufficient memories exist (configured threshold, default 2), calls Hindsight's `reflect()` API to synthesize higher-level conventions and team patterns from past reviews and feedback.
3. **USE MEMORY & CONSTRAINTS**: The `MemoryContextBuilder` injects:
   - Established Team Conventions & Reflected Syntheses
   - Negative constraints: `[Team Decisions: REJECTED Suggestions (DO NOT REPEAT)]` to prevent re-proposing rejected patterns
   - Developer-specific habits and preferred styles
   - Calibrated confidence wording (distinguishing single observations from established patterns)
4. **REVIEW**: Gemini evaluates code with full awareness of team conventions and past feedback decisions.
5. **USER FEEDBACK**: Developers accept, reject, or mark suggestions as fixed in the UI or via API, optionally providing rationale.
6. **RETAIN & LEARN**: Feedback actions are sanitized and stored back into Hindsight as durable learnings that influence all subsequent reviews.

### Fallback Behavior When Hindsight is Unavailable
Hindsight operations are completely non-blocking and fault-tolerant:
* If Hindsight is unreachable, returns an error, or times out, the review **always succeeds** seamlessly as a standard code review.
* Reflection errors degrade gracefully back to raw recalled memories without failing the review.
* Feedback persistence failures are logged non-fatally and never disrupt the review experience.
* The frontend clearly and cleanly indicates memory status (`Memory Active`, `Reflected Patterns`, `First-Time Review`, or `Memory Offline`).

---

## 📁 Project Structure

```text
AI-code-review-agent/
├── frontend/
│   ├── index.html                 # Review dashboard with feedback actions ([Accept], [Reject], [Mark Fixed])
│   ├── developer_dashboard/       # Developer management screens
│   ├── review_history/            # History viewer
│   ├── api_documentation/         # Interactive documentation
│   ├── platform_documentation/    # Platform guides
│   ├── login/                     # Auth views
│   ├── create_account/            # Registration
│   └── pricing/                   # Pricing tier view
│
├── backend/
│   ├── main.py                    # FastAPI application, review & feedback endpoints
│   ├── config.py                  # Configuration with Phase 2 reflection & developer settings
│   ├── hindsight_service.py       # Hindsight client wrapper (recall, retain, reflect, status)
│   ├── memory_model.py            # Schemas for memories, feedback, sanitization & confidence calibration
│   ├── memory_context_builder.py  # Prompt assembly with reflection & rejected suggestion suppression
│   ├── requirements.txt           # Python dependencies
│   ├── .env.example               # Environment variable documentation
│   └── tests/                     # 48 comprehensive unit, integration & E2E tests
│       ├── conftest.py
│       ├── test_config.py
│       ├── test_memory_model.py
│       ├── test_memory_context_builder.py
│       ├── test_hindsight_service.py
│       ├── test_review_api.py
│       ├── test_e2e_memory_flow.py
│       ├── test_feedback.py
│       ├── test_reflection.py
│       ├── test_personalization.py
│       └── test_e2e_learning_workflow.py
│
├── pytest.ini                     # Pytest configuration
└── README.md
```

---

## ⚙️ Environment Variables

Copy `backend/.env.example` to `backend/.env`:

```env
# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# Hindsight Persistent Memory
HINDSIGHT_BASE_URL=http://localhost:8888
HINDSIGHT_API_KEY=
HINDSIGHT_BANK_ID=code-review-agent
HINDSIGHT_ENABLED=true
HINDSIGHT_TIMEOUT=10.0
HINDSIGHT_MAX_RECALL_RESULTS=5
DEFAULT_PROJECT_ID=default-project

# Phase 2: Learning, Reflection & Personalization
HINDSIGHT_REFLECT_ENABLED=true
HINDSIGHT_REFLECT_BUDGET=low
HINDSIGHT_MIN_MEMORIES_FOR_REFLECTION=2
HINDSIGHT_DEVELOPER_MEMORY_ENABLED=true
```

| Variable | Description | Default |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | Google Gemini API key from Google AI Studio | *Required* |
| `GEMINI_MODEL` | Gemini model name | `gemini-2.5-flash` |
| `HINDSIGHT_BASE_URL` | Base URL of running Hindsight instance | `http://localhost:8888` |
| `HINDSIGHT_API_KEY` | Optional auth token for secured/cloud Hindsight | `""` |
| `HINDSIGHT_BANK_ID` | Base namespace/bank identifier for memory | `code-review-agent` |
| `HINDSIGHT_ENABLED` | Enable/disable memory integration | `true` |
| `HINDSIGHT_TIMEOUT` | Network timeout for Hindsight calls in seconds | `10.0` |
| `HINDSIGHT_MAX_RECALL_RESULTS` | Max memory items injected per review | `5` |
| `DEFAULT_PROJECT_ID` | Default project scope identifier | `default-project` |
| `HINDSIGHT_REFLECT_ENABLED` | Enable Hindsight `reflect()` synthesis | `true` |
| `HINDSIGHT_REFLECT_BUDGET` | Reflection compute budget (`low`, `mid`, `high`) | `low` |
| `HINDSIGHT_MIN_MEMORIES_FOR_REFLECTION` | Minimum memories before invoking reflection | `2` |
| `HINDSIGHT_DEVELOPER_MEMORY_ENABLED` | Scope developer-specific habits when `developer_id` provided | `true` |

---

## 🚀 Run Locally

### 1. Clone Repository

```bash
git clone https://github.com/techy-ops/AI-code-review-agent.git
cd AI-code-review-agent
```

### 2. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Configure Environment

Create `backend/.env` with your Gemini API key:

```env
GEMINI_API_KEY=AIzaSy...
HINDSIGHT_ENABLED=true
HINDSIGHT_BASE_URL=http://localhost:8888
```

*(Optional)* Run a local Hindsight server via Docker:

```bash
docker run -p 8888:8888 vectorizeio/hindsight
```

### 4. Start Server

```bash
uvicorn main:app --reload
```

* **Frontend Dashboard:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
* **Interactive API Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **Memory Status Endpoint:** [http://127.0.0.1:8000/memory/status](http://127.0.0.1:8000/memory/status)

---

## 🧪 Running Tests

Execute the comprehensive test suite covering unit tests, contract preservation, failure fallbacks, developer & team memory isolation, reflection, negative feedback suppression, and the complete end-to-end learning lifecycle:

```bash
pytest backend/tests -v
```

All 48 tests run with fast deterministic mocks and require no active cloud credentials.

---

## 📡 API Reference

### `POST /review`
Analyze source code with Hindsight memory awareness, reflection synthesis, and developer personalization.

**Request:**
```json
{
  "code": "def get_user(db, id): return db.execute('SELECT * FROM users WHERE id = ' + id)",
  "language": "python",
  "project_id": "auth-service",
  "developer_id": "dev-alice"
}
```

**Response:**
```json
{
  "issues": {
    "critical": 1,
    "high": 0,
    "medium": 0,
    "low": 0
  },
  "details": [
    {
      "severity": "critical",
      "title": "SQL Injection Vulnerability",
      "description": "Raw string concatenation in SQL queries allows arbitrary query execution.",
      "suggestion": "Use parameterized queries with db.execute('SELECT * FROM users WHERE id = :id', {'id': id})."
    }
  ],
  "memory": {
    "status": "recalled",
    "project_id": "auth-service",
    "developer_id": "dev-alice",
    "memories_retrieved": 2,
    "memories_used": [
      {
        "text": "Project 'auth-service' convention: Always use repository pattern and parameterized SQL.",
        "category": "architecture"
      }
    ],
    "learning_context_applied": true,
    "reflection_applied": true,
    "reflection_summary": "Project strongly prefers repository-based database access and parameterized SQL queries.",
    "rejected_rules_count": 1,
    "memories_retained": 1
  }
}
```

### `POST /review/feedback`
Submit developer feedback on a specific review issue or recommendation to persist durable team learning.

**Request:**
```json
{
  "project_id": "auth-service",
  "developer_id": "dev-alice",
  "action": "reject",
  "issue_title": "Cache with Redis",
  "suggestion": "Use Redis distributed caching for session lookups.",
  "reason": "Project uses PostgreSQL UNLOGGED tables for caching, Redis is not permitted in our stack."
}
```

**Response:**
```json
{
  "status": "retained",
  "feedback_id": "fb_669f6e696ca74fc2",
  "action": "reject",
  "project_id": "auth-service",
  "developer_id": "dev-alice",
  "retained": true,
  "message": "Feedback recorded: reject for 'Cache with Redis'"
}
```

### `POST /memory/reflect`
Synthesize higher-level team conventions and coding patterns from accumulated memories using Hindsight's reflection engine.

**Request:**
```json
{
  "project_id": "auth-service",
  "developer_id": "dev-alice",
  "query": "coding conventions, architecture, and caching practices"
}
```

**Response:**
```json
{
  "status": "reflected",
  "project_id": "auth-service",
  "developer_id": "dev-alice",
  "summary": "Team consistently rejects Redis caching in favor of PostgreSQL unlogged tables, and enforces repository pattern for all database access.",
  "facts_count": 2
}
```

### `POST /rewrite`
Generate an optimized, idiomatic rewrite of the submitted code.

### `GET /memory/status`
Debug endpoint returning Hindsight connectivity, server version, and safe configuration.

### `POST /memory/recall-debug`
Inspect recalled memories and formatted prompt context for any project and query.

---

## 👨‍💻 Author

**Krishna Keerthana**
[GitHub](https://github.com/techy-ops)

<!-- contribution check -->
