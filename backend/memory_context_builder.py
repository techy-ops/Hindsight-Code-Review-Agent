"""Memory Context Builder module for Hindsight-powered Code Review Agent.

Responsible for:
- Converting recalled Hindsight memory objects into a structured, bounded,
  and prompt-injection-safe context for the LLM.
- Completely decoupled from the Hindsight client and LLM caller.
"""

import re
from typing import List, Dict, Any, Optional

MAX_TOTAL_CONTEXT_CHARS = 2500
MAX_ITEM_CHARS = 300

# Patterns that might attempt to hijack system prompts or override instructions
INJECTION_PATTERNS = [
    (r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+instructions", "[BLOCKED_INSTRUCTION]"),
    (r"(?i)system\s*:\s*", "System Note: "),
    (r"(?i)you\s+are\s+now\s+a", "context describes: a"),
    (r"```", "'''"),  # Prevent escaping backticks
]


def sanitize_memory_text(text: str) -> str:
    """Sanitize retrieved memory text to prevent prompt injection or markdown breaking."""
    if not text:
        return ""
    cleaned = text.strip()
    for pattern, replacement in INJECTION_PATTERNS:
        cleaned = re.sub(pattern, replacement, cleaned)
    # Truncate single item if excessive
    if len(cleaned) > MAX_ITEM_CHARS:
        cleaned = cleaned[:MAX_ITEM_CHARS] + "..."
    return cleaned


def build_memory_context(
    memories: List[Any],
    project_id: str = "default-project",
    language: Optional[str] = None
) -> str:
    """Convert raw or normalized recalled memories into a concise, LLM-ready prompt section.
    
    Args:
        memories: List of memory objects (dict, RecallResult, or MemoryRecord)
        project_id: Identifier of the repository or project
        language: Programming language context
        
    Returns:
        Formatted prompt section string, or empty string if no valid memories exist.
    """
    if not memories:
        return ""

    conventions: List[str] = []
    vulnerabilities: List[str] = []
    architectural: List[str] = []
    performance: List[str] = []
    recommendations: List[str] = []

    for item in memories:
        text = ""
        category = "recommendation"
        
        # Handle dict or Hindsight RecallResult / MemoryRecord object
        if isinstance(item, dict):
            text = item.get("text") or item.get("content") or item.get("description") or ""
            category = item.get("category") or item.get("metadata", {}).get("category", "")
        elif hasattr(item, "text"):
            text = getattr(item, "text", "")
            meta = getattr(item, "metadata", {}) or {}
            category = meta.get("category", "") if isinstance(meta, dict) else ""
        elif hasattr(item, "content"):
            text = getattr(item, "content", "")
            category = getattr(item, "category", "")

        cleaned_text = sanitize_memory_text(text)
        if not cleaned_text:
            continue

        cat_lower = (category or "").lower()
        text_lower = cleaned_text.lower()
        
        if cat_lower == "convention" or "convention" in text_lower or "naming" in text_lower or "style" in text_lower:
            conventions.append(cleaned_text)
        elif cat_lower == "vulnerability" or "vulnerability" in text_lower or "security" in text_lower or "injection" in text_lower:
            vulnerabilities.append(cleaned_text)
        elif cat_lower == "architecture" or "architecture" in text_lower or "pattern" in text_lower or "repository" in text_lower:
            architectural.append(cleaned_text)
        elif cat_lower == "performance" or "performance" in text_lower or "complexity" in text_lower:
            performance.append(cleaned_text)
        else:
            recommendations.append(cleaned_text)

    # Check if any categories received items
    total_items = len(conventions) + len(vulnerabilities) + len(architectural) + len(performance) + len(recommendations)
    if total_items == 0:
        return ""

    sections = [
        "=== BEGIN HISTORICAL PROJECT MEMORY (HINDSIGHT) ===",
        f"Context Scope: Project '{project_id}'" + (f" | Language: {language}" if language else ""),
        "Important: The following context represents durable knowledge and conventions learned from prior reviews.",
        "Maintain consistency with these established patterns and explicitly reference or reinforce them where applicable.\n"
    ]

    def add_section(header: str, items: List[str]):
        if items:
            sections.append(f"[{header}]")
            for entry in items[:3]:  # Top 3 per category to stay concise
                sections.append(f"- {entry}")
            sections.append("")

    add_section("Established Project Conventions", conventions)
    add_section("Previous Vulnerabilities & Security Watchpoints", vulnerabilities)
    add_section("Architectural Patterns & Observations", architectural)
    add_section("Performance & Optimization Guidelines", performance)
    add_section("Previous Recommendations & Decisions", recommendations)

    sections.append("=== END HISTORICAL PROJECT MEMORY ===")
    
    result = "\n".join(sections).strip()
    
    # Bounded in size
    if len(result) > MAX_TOTAL_CONTEXT_CHARS:
        result = result[:MAX_TOTAL_CONTEXT_CHARS] + "\n... [Context truncated for length]\n=== END HISTORICAL PROJECT MEMORY ==="

    return result
