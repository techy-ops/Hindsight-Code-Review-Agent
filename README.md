# 🤖 AI Code Review & Rewrite Agent (Hindsight-Powered)

> **An AI-powered developer tool that reviews, detects, and improves source code using Google Gemini AI and learns across reviews using Hindsight persistent agent memory.**

AI Code Review & Rewrite Agent helps developers identify **bugs, security vulnerabilities, performance issues, and code-quality problems**, while also generating optimized code automatically. Featuring persistent memory powered by **Hindsight**, the agent retains durable architectural conventions, coding rules, and past findings, allowing previous review insights to genuinely inform subsequent code evaluations.

---

## ✨ Features

* 🧠 **Hindsight Persistent Memory** — Retains project-level coding conventions and architectural patterns across reviews
* 🔄 **Recall → Review → Retain Pipeline** — Contextually recalls prior learnings to evaluate new code revisions
* 🛡️ **Secret & Token Sanitization** — Automatically redacts API keys, passwords, and tokens before retention
* 🔍 **AI Code Review** — Analyze code and receive intelligent feedback powered by Gemini 2.5 Flash
* 🐛 **Bug & Vulnerability Detection** — Identify logical errors, security flaws, and performance bottlenecks
* ⚡ **Performance Optimization** — Find inefficient algorithms and suggest optimized implementations
* ✍️ **AI Code Rewrite** — Generate cleaner, secure, and idiomatic code with diff breakdown
* 🌐 **Multi-Language Support** — Review Python, JavaScript, TypeScript, Rust, and Go
* 📊 **Developer Dashboard** — Interactive code review interface with memory visibility
* 🛡️ **Graceful Degradation** — Always functions as a standard review agent even if memory services are offline

---

## 🛠️ Tech Stack

* **Frontend:** HTML5 • TailwindCSS • Modern Vanilla JavaScript • Glassmorphism UI
* **Backend:** Python 3.12 • FastAPI • Pydantic v2 • Uvicorn
* **Agent Memory:** [Hindsight](https://github.com/vectorize-io/hindsight) (`hindsight-client`)
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

### Memory Pipeline: RECALL → USE MEMORY → REVIEW → RETAIN

1. **RECALL**: Before reviewing new code, the agent queries Hindsight using the target project ID (`project_id`) and code snippet to retrieve relevant past memories (conventions, previous architectural decisions, and known vulnerability patterns).
2. **USE MEMORY**: The `MemoryContextBuilder` sanitizes retrieved memories against prompt injection and constructs a concise, structured memory block (`Established Project Conventions`, `Architectural Patterns`, `Previous Vulnerabilities`).
3. **REVIEW**: Gemini generates the code review with explicit instructions to maintain consistency with established project patterns and flag regressions.
4. **RETAIN**: High-value findings and suggestions are extracted into normalized, secret-sanitized memory units and asynchronously persisted into Hindsight via `retain()`.

### Fallback Behavior When Hindsight is Unavailable
Hindsight operations are completely non-blocking and fault-tolerant:
* If Hindsight is unreachable, returns an error, or times out, the review **always succeeds** seamlessly as a standard code review.
* The frontend clearly and cleanly indicates memory status (`Memory Active`, `First-Time Review`, or `Memory Offline`) without disrupting the developer experience.

---

## 📁 Project Structure

```text
AI-code-review-agent/
├── frontend/
│   ├── index.html                 # Main review dashboard with Hindsight memory panel
│   ├── developer_dashboard/       # Developer management screens
│   ├── review_history/            # History viewer
│   ├── api_documentation/         # Interactive documentation
│   ├── platform_documentation/    # Platform guides
│   ├── login/                     # Auth views
│   ├── create_account/            # Registration
│   └── pricing/                   # Pricing tier view
│
├── backend/
│   ├── main.py                    # FastAPI application & review endpoints
│   ├── config.py                  # Centralized configuration with safe secret masking
│   ├── hindsight_service.py       # Dedicated Hindsight service abstraction
│   ├── memory_model.py            # Normalized memory schema, knowledge extraction & secret sanitizer
│   ├── memory_context_builder.py  # Prompt-injection safe context builder for LLM
│   ├── requirements.txt           # Python dependencies
│   ├── .env.example               # Environment variable documentation
│   └── tests/                     # Comprehensive test suite
│       ├── conftest.py
│       ├── test_config.py
│       ├── test_memory_model.py
│       ├── test_memory_context_builder.py
│       ├── test_hindsight_service.py
│       ├── test_review_api.py
│       └── test_e2e_memory_flow.py
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

Execute the comprehensive test suite covering unit tests, contract preservation, failure fallbacks, and the end-to-end memory lifecycle:

```bash
pytest backend/tests -v
```

All 29 tests run with fast deterministic mocks and require no active cloud credentials.

---

## 📡 API Reference

### `POST /review`
Analyze source code with Hindsight memory awareness.

**Request:**
```json
{
  "code": "def get_user(db, id): return db.execute('SELECT * FROM users WHERE id = ' + id)",
  "language": "python",
  "project_id": "auth-service"
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
    "memories_retrieved": 1,
    "memories_used": [
      {
        "text": "Project 'auth-service' convention: Always use repository pattern and parameterized SQL.",
        "category": "architecture"
      }
    ],
    "learning_context_applied": true,
    "memories_retained": 1
  }
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
