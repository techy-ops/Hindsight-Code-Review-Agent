"""Memory model and knowledge extraction module for Hindsight-powered Code Review Agent.

Responsible for:
- Defining normalized memory schemas
- Sanitizing sensitive information (secrets, keys, tokens, passwords)
- Extracting high-value durable knowledge from code reviews for Hindsight retention
"""

import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


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
    language: str
    category: str = Field(description="convention | vulnerability | performance | architecture | recommendation")
    title: str
    content: str
    reasoning: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


def extract_durable_knowledge(
    code: str,
    language: str,
    review_output: Dict[str, Any],
    project_id: str = "default-project"
) -> List[MemoryRecord]:
    """Extract durable, reusable knowledge units from code review output.
    
    Rather than dumping raw reviews, extracts clear architectural rules,
    conventions, security patterns, and recommendations that will benefit
    future reviews of this project.
    """
    memories: List[MemoryRecord] = []
    sanitized_code = sanitize_text(code[:1000])  # limit sample context
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

        # Construct clear, declarative knowledge statement for Hindsight
        memory_statement = (
            f"Project '{project_id}' ({language}) finding: {title}. "
            f"Context: {description} "
            f"Standard/Recommendation: {suggestion}"
        ).strip()

        record = MemoryRecord(
            project_id=project_id,
            language=language.lower(),
            category=category,
            title=title,
            content=memory_statement,
            reasoning=description,
            metadata={
                "severity": severity,
                "category": category,
                "project_id": project_id,
                "language": language.lower(),
            },
            tags=[
                f"project:{project_id}",
                f"lang:{language.lower()}",
                f"category:{category}",
                f"severity:{severity}",
            ]
        )
        memories.append(record)

    return memories
