"""Memory model and knowledge extraction module for Hindsight-powered Code Review Agent.

Responsible for:
- Defining normalized memory schemas and feedback models (Phase 2)
- Sanitizing sensitive information (secrets, keys, tokens, passwords)
- Extracting high-value durable knowledge from code reviews and developer feedback for Hindsight retention
- Calibrating memory confidence and cautious evidence phrasing
"""

import re
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, field_validator


# Regular expressions for detecting and redacting secrets
SECRET_PATTERNS = [
    # API Keys & Tokens
    (r"(?i)(api[_-]?key|secret|token|password|auth|private[_-]?key)\s*[:=]\s*['\"][A-Za-z0-9_\-\.\+/=]{8,}['\"]", r"\1: '[REDACTED]'"),
    # Google API Key
    (r"AIzaSy[A-Za-z0-9_-]{33}", "[REDACTED_GEMINI_KEY]"),
    # Generic OpenAI / Anthropic / bearer tokens
    (r"sk-[A-Za-z0-9_-]{20,}", "[REDACTED_API_KEY]"),
    (r"Bearer\s+[A-Za-z0-9_\-\.\+/=]{15,}", "Bearer [REDACTED_TOKEN]"),
    # AWS Access Key
    (r"AKIA[0-9A-Z]{16}", "[REDACTED_AWS_KEY]"),
    # Private Key Headers
    (r"-----BEGIN [A-Z ]+PRIVATE KEY-----[\s\S]*?-----END [A-Z ]+PRIVATE KEY-----", "[REDACTED_PRIVATE_KEY]"),
    # Generic password assignments in code
    (r"(password|passwd|pwd)\s*=\s*['\"][^'\"]+['\"]", r'\1="[REDACTED]"'),
]


def sanitize_text(text: str) -> str:
    """Strip or redact sensitive secrets, keys, and tokens from content before retention or processing."""
    if not text:
        return ""
    sanitized = text
    for pattern, replacement in SECRET_PATTERNS:
        sanitized = re.sub(pattern, replacement, sanitized)
    return sanitized


class MemoryRecord(BaseModel):
    """Normalized memory record structure."""
    id: Optional[str] = None
    project_id: str
    developer_id: Optional[str] = None
    language: str
    category: str = Field(description="convention | vulnerability | performance | architecture | recommendation | rejected_recommendation | resolution")
    title: str
    content: str
    reasoning: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class FeedbackRequest(BaseModel):
    """Developer feedback payload for accepting, rejecting, or marking review items as fixed."""
    project_id: str = "default-project"
    developer_id: Optional[str] = None
    issue_title: str
    recommendation: str
    action: Literal["accept", "reject", "fixed"]
    reason: Optional[str] = None
    language: Optional[str] = "python"
    code_context: Optional[str] = None

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if cleaned not in ("accept", "reject", "fixed"):
            raise ValueError("action must be one of: 'accept', 'reject', 'fixed'")
        return cleaned


def calibrate_confidence_wording(
    text: str,
    frequency: int = 1,
    is_explicit_convention: bool = False
) -> str:
    """Calibrate confidence phrasing so weak evidence is not overstated as an absolute team rule."""
    cleaned = sanitize_text(text).strip()
    if is_explicit_convention or frequency >= 4:
        prefix = "Established team convention:"
    elif frequency >= 2:
        prefix = "Frequent project pattern:"
    else:
        prefix = "Observed in prior review:"
    
    # Avoid duplicate prefixes
    if any(cleaned.lower().startswith(p) for p in ["established", "frequent", "observed", "project"]):
        return cleaned
    return f"{prefix} {cleaned}"


def create_feedback_memory_record(feedback: FeedbackRequest) -> MemoryRecord:
    """Transform developer review feedback into a durable, sanitized MemoryRecord for Hindsight."""
    project_id = sanitize_text(feedback.project_id or "default-project")
    developer_id = sanitize_text(feedback.developer_id or "").strip() or None
    title = sanitize_text(feedback.issue_title)
    rec = sanitize_text(feedback.recommendation)
    reason = sanitize_text(feedback.reason or "").strip()
    lang = (feedback.language or "code").lower()
    dev_suffix = f" (by developer '{developer_id}')" if developer_id else ""

    tags = [
        f"project:{project_id}",
        f"action:{feedback.action}",
        f"lang:{lang}",
    ]
    if developer_id:
        tags.append(f"developer:{developer_id}")

    if feedback.action == "reject":
        category = "rejected_recommendation"
        reason_text = reason or "Team decided against this suggestion for project architecture."
        content = (
            f"Project '{project_id}' team decision [REJECTED]: Suggestion '{rec}' for issue '{title}' was REJECTED{dev_suffix}. "
            f"Reason: {reason_text}. "
            f"Policy: Do NOT suggest '{rec}' in project '{project_id}' unless compelling context demands it."
        )
        tags.append("category:rejected_recommendation")
    elif feedback.action == "accept":
        category = "convention"
        reason_text = reason or "Approved and adopted as standard practice."
        content = (
            f"Project '{project_id}' team convention [ACCEPTED]: Suggestion '{rec}' for issue '{title}' was ACCEPTED{dev_suffix}. "
            f"Context: {reason_text}. "
            f"Standard: Reinforce '{rec}' in project '{project_id}'."
        )
        tags.append("category:convention")
    else:  # fixed
        category = "resolution"
        reason_text = reason or "Resolved adhering to project standard."
        content = (
            f"Project '{project_id}' issue resolution [FIXED]: '{title}' was RESOLVED{dev_suffix} following guideline: '{rec}'. "
            f"Details: {reason_text}."
        )
        tags.append("category:resolution")

    return MemoryRecord(
        project_id=project_id,
        developer_id=developer_id,
        language=lang,
        category=category,
        title=f"Feedback [{feedback.action.upper()}]: {title}",
        content=content,
        reasoning=reason,
        metadata={
            "action": feedback.action,
            "category": category,
            "project_id": project_id,
            "developer_id": developer_id or "",
            "language": lang,
            "issue_title": title,
            "recommendation": rec,
        },
        tags=tags,
    )


def extract_durable_knowledge(
    code: str,
    language: str,
    review_output: Dict[str, Any],
    project_id: str = "default-project",
    developer_id: Optional[str] = None
) -> List[MemoryRecord]:
    """Extract durable, reusable knowledge units from code review output.
    
    Rather than dumping raw reviews, extracts clear architectural rules,
    conventions, security patterns, and recommendations that will benefit
    future reviews of this project and developer.
    """
    memories: List[MemoryRecord] = []
    details = review_output.get("details", [])

    if not isinstance(details, list):
        return memories

    for issue in details:
        if not isinstance(issue, dict):
            continue

        severity = issue.get("severity", "medium").lower()
        title = sanitize_text(issue.get("title", "")).strip()
        description = sanitize_text(issue.get("description", "")).strip()
        suggestion = sanitize_text(issue.get("suggestion", "")).strip()

        if not title and not description:
            continue
        if not title:
            title = "Review Finding"

        # Categorize finding
        title_lower = title.lower() + " " + description.lower()
        if any(w in title_lower for w in ["security", "injection", "vulnerability", "auth", "xss", "csrf", "sanitize", "leak", "sensitive"]):
            category = "vulnerability"
        elif any(w in title_lower for w in ["performance", "complexity", "slow", "memory", "o(n", "efficiency", "bottleneck"]):
            category = "performance"
        elif any(w in title_lower for w in ["architecture", "pattern", "repository", "decouple", "modularity", "solid", "dry"]):
            category = "architecture"
        elif any(w in title_lower for w in ["convention", "naming", "idiomatic", "style", "docstring", "type annotation"]):
            category = "convention"
        else:
            category = "recommendation"

        memory_statement = (
            f"Project '{project_id}' ({language}) finding: {title}. "
            f"Context: {description} "
            f"Standard/Recommendation: {suggestion}"
        ).strip()

        tags = [
            f"project:{project_id}",
            f"lang:{language.lower()}",
            f"category:{category}",
            f"severity:{severity}",
        ]
        if developer_id:
            tags.append(f"developer:{developer_id}")

        record = MemoryRecord(
            project_id=project_id,
            developer_id=developer_id,
            language=language.lower(),
            category=category,
            title=title,
            content=memory_statement,
            reasoning=description,
            metadata={
                "severity": severity,
                "category": category,
                "project_id": project_id,
                "developer_id": developer_id or "",
                "language": language.lower(),
            },
            tags=tags,
        )
        memories.append(record)

    return memories
