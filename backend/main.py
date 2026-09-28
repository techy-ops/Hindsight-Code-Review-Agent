import os
import json
import logging
import hashlib
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai

from config import get_settings
from hindsight_service import get_hindsight_service
from memory_model import extract_durable_knowledge, sanitize_text, FeedbackRequest
from memory_context_builder import build_memory_context, enrich_review_explainability
from activity_tracker import get_activity_tracker

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("code_review_agent")

settings = get_settings()
tracker = get_activity_tracker()

app = FastAPI(
    title="AI Code Review & Rewrite Agent (Hindsight-Powered)",
    description="Intelligent code review agent featuring persistent memory, learning from feedback, and reflection via Hindsight.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend')

# NOTE: genai.configure() is intentionally NOT called here at module level.
# It is called inside get_gemini_model() on every use so that a fresh Uvicorn
# process always picks up the current key from .env — eliminating stale-key 403s.

def get_gemini_model() -> genai.GenerativeModel:
    """Return a configured GenerativeModel using the current settings.

    Calling genai.configure() here (rather than at module import time) ensures
    that each Uvicorn startup always uses the key present in .env at launch time
    and is never affected by a stale module-level global from a previous process.
    """
    current_settings = get_settings()
    current_key = current_settings.gemini_api_key
    if not current_key:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY is not set. Add it to backend/.env and restart the server.",
        )
    genai.configure(api_key=current_key)
    return genai.GenerativeModel(current_settings.gemini_model)


hindsight_service = get_hindsight_service()


@app.on_event("startup")
async def _log_startup_fingerprint():
    """Log safe Gemini key fingerprint at startup so stale-key issues are immediately visible."""
    key = settings.gemini_api_key
    if key:
        sha = hashlib.sha256(key.encode()).hexdigest()[:12]
        prefix = key[:6] + "..." if len(key) >= 6 else "(too short)"
        logger.info(
            "Gemini API key loaded: length=%d prefix=%s sha256[:12]=%s model=%s",
            len(key), prefix, sha, settings.gemini_model,
        )
    else:
        logger.warning("WARNING: GEMINI_API_KEY is not set. /review and /rewrite will return 500.")


class CodeRequest(BaseModel):
    code: str
    language: str
    project_id: Optional[str] = Field(
        default="default-project",
        description="Project or repository identifier for memory scoping"
    )
    developer_id: Optional[str] = Field(
        default=None,
        description="Optional developer identifier for personalized review learning"
    )


class RecallDebugRequest(BaseModel):
    query: str
    project_id: Optional[str] = "default-project"
    developer_id: Optional[str] = None
    language: Optional[str] = None


class ReflectDebugRequest(BaseModel):
    project_id: Optional[str] = "default-project"
    developer_id: Optional[str] = None
    query: Optional[str] = "What are the primary coding conventions and rejected suggestions?"


@app.get("/memory/status")
async def get_memory_status():
    """Developer/debug endpoint to inspect Hindsight connectivity and configuration."""
    health = await hindsight_service.check_health()
    safe_config = settings.safe_dict()
    return {
        "hindsight_health": health,
        "config": safe_config,
    }


@app.post("/memory/recall-debug")
async def recall_debug(request: RecallDebugRequest):
    """Developer endpoint to inspect retrieved memories for a given query and project."""
    project_id = request.project_id or settings.default_project_id
    memories = await hindsight_service.recall_memory(
        project_id=project_id,
        query=request.query,
        language=request.language,
        developer_id=request.developer_id,
    )
    context_preview = build_memory_context(
        memories=memories,
        project_id=project_id,
        language=request.language,
        developer_id=request.developer_id,
    )
    return {
        "project_id": project_id,
        "developer_id": request.developer_id,
        "memories_count": len(memories),
        "memories": memories,
        "formatted_context": context_preview,
    }


@app.post("/memory/reflect")
async def reflect_debug(request: ReflectDebugRequest):
    """Developer/inspection endpoint to trigger Hindsight reflect() and return synthesized patterns."""
    project_id = request.project_id or settings.default_project_id
    reflection = await hindsight_service.reflect_memory(
        project_id=project_id,
        query=request.query or "Synthesize team conventions and rejected patterns",
        developer_id=request.developer_id,
    )
    return {
        "project_id": project_id,
        "developer_id": request.developer_id,
        "reflection": reflection,
    }


@app.post("/review/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    """Submit developer feedback on a review suggestion (accept, reject, or mark fixed).
    
    Persists feedback as durable Hindsight memory to influence future reviews.
    """
    project_id = feedback.project_id or settings.default_project_id
    retained = False

    if settings.hindsight_enabled:
        try:
            retained = await hindsight_service.retain_feedback(feedback)
            logger.info(
                "Feedback recorded for project '%s' (action: %s, retained: %s)",
                project_id,
                feedback.action,
                retained,
            )
        except Exception as e:
            logger.warning("Feedback retention failed: %s (non-fatal)", type(e).__name__)
            retained = False

    # Record in activity tracker
    tracker.record_feedback(
        project_id=project_id,
        action=feedback.action,
        issue_title=feedback.issue_title,
        recommendation=feedback.recommendation,
        reason=feedback.reason,
        developer_id=feedback.developer_id,
        retained=retained,
    )

    return {
        "status": "recorded",
        "action": feedback.action,
        "retained": retained,
        "project_id": project_id,
        "developer_id": feedback.developer_id,
        "issue_title": feedback.issue_title,
    }


@app.get("/dashboard/stats")
async def get_dashboard_stats():
    """Return truthful, real operational metrics from memory and review activity."""
    health = await hindsight_service.check_health()
    stats = tracker.get_stats()
    return {
        "status": "success",
        "hindsight_health": health,
        "stats": stats,
        "config": settings.safe_dict(),
    }


@app.get("/memory/explorer")
async def get_memory_explorer(
    project_id: Optional[str] = None,
    developer_id: Optional[str] = None,
    category: Optional[str] = None,
    source: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
):
    """Return genuine learned memories and conventions with filtering and search."""
    target_project = project_id or settings.default_project_id

    # Query Hindsight memory bank if online
    hindsight_memories = []
    if settings.hindsight_enabled:
        try:
            hindsight_memories = await hindsight_service.list_memories(
                project_id=target_project,
                search_query=search,
                limit=limit,
            )
        except Exception as e:
            logger.debug("list_memories notice: %s", e)
            hindsight_memories = []

    # Combine with tracker's local records
    local_records = tracker.get_explorer_memories(
        project_id=project_id,
        developer_id=developer_id,
        category=category,
        source=source,
        search=search,
        limit=limit,
    )

    # Deduplicate by text
    seen_texts = set()
    combined = []
    for m in hindsight_memories:
        txt = m.get("text", "")
        if txt and txt not in seen_texts:
            seen_texts.add(txt)
            combined.append({
                "id": m.get("id"),
                "text": txt,
                "category": m.get("category", "observation"),
                "source": "hindsight_bank",
                "project_id": target_project,
                "developer_id": developer_id,
                "confidence": "established_convention" if m.get("category") in ("convention", "architecture") else "isolated_observation",
                "created_at": m.get("created_at") or "Persisted in Hindsight Bank",
            })

    for m in local_records:
        txt = m.get("text", "")
        if txt and txt not in seen_texts:
            seen_texts.add(txt)
            combined.append(m)

    return {
        "total": len(combined),
        "project_id": project_id,
        "developer_id": developer_id,
        "memories": combined[:limit],
    }


@app.get("/learning/timeline")
async def get_learning_timeline(
    project_id: Optional[str] = None,
    limit: int = 50,
):
    """Return genuine chronological learning events (reviews, feedback, memories, reflection)."""
    events = tracker.get_timeline(project_id=project_id, limit=limit)
    return {
        "project_id": project_id or "all",
        "total": len(events),
        "events": events,
    }


@app.get("/demo/scenarios")
async def get_demo_scenarios():
    """Return predefined Before/After learning scenarios demonstrating real Hindsight adaptation."""
    return {
        "scenarios": [
            {
                "id": "caching_convention",
                "name": "Caching Convention (Redis vs PostgreSQL)",
                "description": "Demonstrates agent learning to avoid repeatedly proposing Redis when team standardizes on PostgreSQL unlogged caching.",
                "language": "python",
                "project_id": "cache-service-demo",
                "developer_id": "dev-alice",
                "step1": {
                    "title": "First Review (Baseline)",
                    "code": "def get_search_results(query):\n    # Query search index\n    results = execute_query(query)\n    return results\n",
                    "expected_suggestion": "Cache search results using Redis",
                },
                "step2": {
                    "title": "Developer Feedback",
                    "action": "reject",
                    "issue_title": "Cache search results",
                    "reason": "Project standardizes on PostgreSQL UNLOGGED tables for caching; Redis is not allowed in this deployment.",
                },
                "step3": {
                    "title": "Second Review (Personalized Learning)",
                    "code": "def get_user_dashboard(user_id):\n    # Retrieve heavy user dashboard metrics\n    data = compute_heavy_metrics(user_id)\n    return data\n",
                    "expected_learning": "Agent suppresses Redis suggestion, cites team decision, and recommends PostgreSQL unlogged cache.",
                }
            },
            {
                "id": "repository_pattern",
                "name": "Architectural Pattern (Repository Pattern)",
                "description": "Demonstrates agent enforcing repository abstraction over direct raw SQL queries across reviews.",
                "language": "python",
                "project_id": "auth-service-demo",
                "developer_id": "dev-bob",
                "step1": {
                    "title": "First Review",
                    "code": "def get_user_by_email(db, email):\n    return db.execute(f'SELECT * FROM users WHERE email = \\'{email}\\'')\n",
                    "expected_suggestion": "Use repository pattern with parameterized query",
                },
                "step2": {
                    "title": "Developer Feedback",
                    "action": "accept",
                    "issue_title": "Direct Database Access",
                    "reason": "Team enforces repository pattern for all database access.",
                },
                "step3": {
                    "title": "Second Review",
                    "code": "def get_order_by_id(db, order_id):\n    return db.execute('SELECT * FROM orders WHERE id = :id', {'id': order_id})\n",
                    "expected_learning": "Agent flags direct SQL as violating the project's established repository pattern.",
                }
            }
        ]
    }



@app.post("/review")
async def review_code(request: CodeRequest):
    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY environment variable is not set. Please set it or add a .env file to the backend directory."
        )

    project_id = request.project_id or settings.default_project_id
    developer_id = request.developer_id

    # ---------------------------------------------------------
    # STEP 1: RECALL - Retrieve relevant project & developer memory
    # ---------------------------------------------------------
    memories: List[Dict[str, Any]] = []
    memory_status = "unavailable"
    reflection_data = None
    memory_context_prompt = ""

    if settings.hindsight_enabled:
        try:
            memories = await hindsight_service.recall_memory(
                project_id=project_id,
                query=request.code,
                language=request.language,
                developer_id=developer_id,
            )
            if memories:
                memory_status = "recalled"

                # ---------------------------------------------------------
                # STEP 2: REFLECT - Synthesize higher-order patterns when useful
                # ---------------------------------------------------------
                if (
                    settings.hindsight_reflect_enabled
                    and len(memories) >= settings.hindsight_min_memories_for_reflection
                ):
                    try:
                        reflection_query = (
                            f"What are the established team conventions, accepted practices, "
                            f"and rejected suggestions for {request.language} code in project '{project_id}'?"
                        )
                        reflection_data = await hindsight_service.reflect_memory(
                            project_id=project_id,
                            query=reflection_query,
                            developer_id=developer_id,
                        )
                    except Exception as ref_err:
                        logger.warning("Hindsight reflection error: %s (continuing with recall)", type(ref_err).__name__)
                        reflection_data = None

                # Build combined LLM prompt context
                memory_context_prompt = build_memory_context(
                    memories=memories,
                    project_id=project_id,
                    language=request.language,
                    developer_id=developer_id,
                    reflection=reflection_data,
                )
            else:
                memory_status = "no_memories"
        except Exception as e:
            logger.warning("Hindsight recall failure: %s", type(e).__name__)
            memory_status = "error"
            memories = []

    # ---------------------------------------------------------
    # STEP 3: BUILD REVIEW PROMPT - Inject retrieved memory context
    # ---------------------------------------------------------
    memory_instructions = ""
    if memory_context_prompt:
        memory_instructions = f"""
{memory_context_prompt}

CRITICAL MEMORY INSTRUCTIONS:
- You have access to persistent historical memories and team decisions from prior reviews.
- DO NOT suggest recommendations that the team has explicitly REJECTED in the memory context above.
- Maintain consistency with established architectural patterns and reinforced project conventions.
- If code violates or contradicts an established pattern from memory, EXPLICITLY flag this and cite the project convention.
- Acknowledge developer-preferred patterns when applicable.
- Where evidence is an isolated observation, use cautious phrasing (e.g. 'Prior reviews noted...') rather than asserting an absolute rule.
"""

    prompt = f"""You are an expert code reviewer. Analyze the following {request.language} code for vulnerabilities, bugs, and performance issues.
{memory_instructions}
Code:
{request.code}

Return ONLY a JSON object with this exact structure (no markdown formatting, just raw JSON). Ensure valid JSON:
{{
  "issues": {{
    "critical": 0,
    "high": 0,
    "medium": 0,
    "low": 0
  }},
  "details": [
    {{
      "severity": "critical|high|medium|low",
      "title": "Short title",
      "description": "Detailed explanation",
      "suggestion": "How to fix"
    }}
  ]
}}
"""

    # ---------------------------------------------------------
    # STEP 4: REVIEW - LLM generation with resilience / retry loop
    # ---------------------------------------------------------
    data = None
    for attempt in range(4):
        try:
            model = get_gemini_model()
            response = await model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                )
            )
            data = json.loads(response.text)
            break
        except Exception as e:
            if "429" in str(e) and attempt < 3:
                import asyncio, random, re
                sleep_time = 2.0
                match = re.search(r"retry in ([\d\.]+)s", str(e))
                if match:
                    sleep_time = float(match.group(1)) + random.uniform(1.0, 3.0)
                else:
                    sleep_time = 16.0 + random.uniform(1.0, 3.0)
                await asyncio.sleep(sleep_time)
            else:
                raise HTTPException(status_code=500, detail=f"LLM Error: {str(e)}")

    if not data or not isinstance(data, dict):
        raise HTTPException(status_code=500, detail="Invalid response format received from LLM")

    # ---------------------------------------------------------
    # STEP 5: RETAIN - Extract and persist durable knowledge into Hindsight
    # ---------------------------------------------------------
    retained_count = 0
    if settings.hindsight_enabled:
        try:
            durable_records = extract_durable_knowledge(
                code=request.code,
                language=request.language,
                review_output=data,
                project_id=project_id,
                developer_id=developer_id,
            )
            if durable_records:
                retained_count = await hindsight_service.retain_knowledge_records(durable_records)
                tracker.record_retention(
                    project_id=project_id,
                    retained_count=retained_count,
                    developer_id=developer_id,
                    records=[
                        {
                            "id": getattr(r, "id", None) or f"rec_{i}",
                            "text": r.content,
                            "category": r.category,
                            "source": "review_finding",
                            "confidence": "isolated_observation",
                        }
                        for i, r in enumerate(durable_records)
                    ],
                )
        except Exception as e:
            logger.warning("Hindsight retain error: %s (review succeeded)", type(e).__name__)
            retained_count = 0

    # ---------------------------------------------------------
    # STEP 6: ENRICH REVIEW EXPLAINABILITY & CONVENTIONS
    # ---------------------------------------------------------
    explain_res = enrich_review_explainability(
        details=data.get("details", []),
        memories=memories,
        reflection=reflection_data,
    )
    data["details"] = explain_res["details"]
    data["explainability"] = explain_res["explainability"]

    # Record reflection event if occurred
    if reflection_data and reflection_data.get("text"):
        tracker.record_reflection(
            project_id=project_id,
            summary_text=reflection_data.get("text", ""),
            facts_count=len(reflection_data.get("based_on", [])),
            developer_id=developer_id,
        )

    # Record review event in tracker
    tracker.record_review(
        project_id=project_id,
        language=request.language,
        developer_id=developer_id,
        issues_count=len(data.get("details", [])),
        influenced_by_memory=bool(explain_res["explainability"]["learned_context_findings_count"] > 0 or memory_context_prompt),
        reflection_applied=bool(reflection_data and reflection_data.get("text")),
        memories_recalled_count=len(memories),
    )

    # ---------------------------------------------------------
    # STEP 7: ATTACH BACKWARD-COMPATIBLE MEMORY METADATA
    # ---------------------------------------------------------
    memories_summary = []
    for m in memories[:5]:
        memories_summary.append({
            "text": m.get("text", "")[:250],
            "category": m.get("category", "observation"),
        })

    data["memory"] = {
        "status": memory_status,
        "project_id": project_id,
        "developer_id": developer_id,
        "memories_retrieved": len(memories),
        "memories_used": memories_summary,
        "reflection_applied": bool(reflection_data and reflection_data.get("text")),
        "reflection_summary": reflection_data.get("text") if reflection_data else None,
        "learning_context_applied": bool(memory_context_prompt),
        "memories_retained": retained_count,
    }

    return data


@app.post("/rewrite")
async def rewrite_code(request: CodeRequest):
    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY environment variable is not set. Please set it or add a .env file to the backend directory."
        )
        
    prompt = f"""You are an expert code optimizing agent. Rewrite the following {request.language} code to be more efficient, secure, and idiomatic.

Code:
{request.code}

Return ONLY a JSON object with this exact structure (no markdown formatting, just raw JSON). Ensure valid JSON:
{{
  "optimized_code": "The full rewritten code here as a string",
  "metrics": {{
    "time_complexity": "e.g. O(n^2) -> O(n)",
    "memory_usage": "e.g. -20% Saved or N/A"
  }},
  "diff": [
    {{
      "type": "remove",
      "content": "- old line"
    }},
    {{
      "type": "add",
      "content": "+ new line"
    }}
  ]
}}
"""
    for attempt in range(4):
        try:
            model = get_gemini_model()
            response = await model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                )
            )
            data = json.loads(response.text)
            return data
        except Exception as e:
            if "429" in str(e) and attempt < 3:
                import asyncio, random, re
                sleep_time = 2.0
                match = re.search(r"retry in ([\d\.]+)s", str(e))
                if match:
                    sleep_time = float(match.group(1)) + random.uniform(1.0, 3.0)
                else:
                    sleep_time = 16.0 + random.uniform(1.0, 3.0)
                await asyncio.sleep(sleep_time)
            else:
                raise HTTPException(status_code=500, detail=f"LLM Error: {str(e)}")


# Mount the entire frontend directory as static files
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
