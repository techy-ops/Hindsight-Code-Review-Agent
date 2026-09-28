"""Memory Context Builder module for Hindsight-powered Code Review Agent.

Responsible for:
- Converting recalled Hindsight memory objects and reflection syntheses into a
  structured, bounded, and prompt-injection-safe context for the LLM.
- Incorporating team decisions, rejected suggestions (to avoid repeated unwanted advice),
  developer-specific preferences, and synthesized reflections.
- Calibrating evidence confidence levels.
- Completely decoupled from the Hindsight client and LLM caller.
"""

import re
from typing import List, Dict, Any, Optional
from memory_model import calibrate_confidence_wording

MAX_TOTAL_CONTEXT_CHARS = 3500
MAX_ITEM_CHARS = 350

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
    memories: Optional[List[Any]] = None,
    project_id: str = "default-project",
    language: Optional[str] = None,
    developer_id: Optional[str] = None,
    reflection: Optional[Dict[str, Any]] = None,
) -> str:
    """Convert raw or normalized recalled memories and reflections into a concise, LLM-ready prompt section.
    
    Args:
        memories: List of memory objects (dict, RecallResult, or MemoryRecord)
        project_id: Identifier of the repository or project
        language: Programming language context
        developer_id: Optional developer identifier for personalized review context
        reflection: Optional synthesized reflection output from Hindsight reflect()
        
    Returns:
        Formatted prompt section string, or empty string if no valid memories or reflection exist.
    """
    mem_list = memories or []

    conventions: List[str] = []
    rejected_recommendations: List[str] = []
    developer_preferences: List[str] = []
    vulnerabilities: List[str] = []
    architectural: List[str] = []
    performance: List[str] = []
    recommendations: List[str] = []

    for item in mem_list:
        text = ""
        category = "recommendation"
        tags = []
        item_dev_id = None
        
        # Handle dict or Hindsight RecallResult / MemoryRecord object
        if isinstance(item, dict):
            text = item.get("text") or item.get("content") or item.get("description") or ""
            category = item.get("category") or item.get("metadata", {}).get("category", "")
            tags = item.get("tags") or []
            item_dev_id = item.get("metadata", {}).get("developer_id") or item.get("developer_id")
        elif hasattr(item, "text"):
            text = getattr(item, "text", "")
            meta = getattr(item, "metadata", {}) or {}
            category = meta.get("category", "") if isinstance(meta, dict) else ""
            tags = getattr(item, "tags", []) or []
            item_dev_id = meta.get("developer_id") if isinstance(meta, dict) else None
        elif hasattr(item, "content"):
            text = getattr(item, "content", "")
            category = getattr(item, "category", "")
            tags = getattr(item, "tags", []) or []
            item_dev_id = getattr(item, "developer_id", None)

        cleaned_text = sanitize_memory_text(text)
        if not cleaned_text:
            continue

        cat_lower = (category or "").lower()
        text_lower = cleaned_text.lower()

        # Check for developer-specific memory
        is_dev_specific = False
        if developer_id and (
            item_dev_id == developer_id or 
            f"developer:{developer_id}" in tags or 
            f"developer '{developer_id}'" in text_lower
        ):
            is_dev_specific = True

        # Grouping logic
        if cat_lower == "rejected_recommendation" or "rejected" in text_lower or "[rejected]" in text_lower:
            rejected_recommendations.append(cleaned_text)
        elif is_dev_specific:
            developer_preferences.append(cleaned_text)
        elif cat_lower == "convention" or "accepted" in text_lower or "convention" in text_lower or "naming" in text_lower:
            conventions.append(calibrate_confidence_wording(cleaned_text, frequency=3, is_explicit_convention=True))
        elif cat_lower == "vulnerability" or "security" in text_lower or "injection" in text_lower:
            vulnerabilities.append(calibrate_confidence_wording(cleaned_text, frequency=1))
        elif cat_lower == "architecture" or "pattern" in text_lower or "repository" in text_lower:
            architectural.append(calibrate_confidence_wording(cleaned_text, frequency=2))
        elif cat_lower == "performance" or "complexity" in text_lower:
            performance.append(calibrate_confidence_wording(cleaned_text, frequency=2))
        else:
            recommendations.append(calibrate_confidence_wording(cleaned_text, frequency=1))

    # Reflection text
    reflection_text = ""
    if reflection and isinstance(reflection, dict):
        raw_ref = reflection.get("text", "")
        if raw_ref:
            reflection_text = sanitize_memory_text(raw_ref)

    total_items = (
        len(conventions) + len(rejected_recommendations) + len(developer_preferences) +
        len(vulnerabilities) + len(architectural) + len(performance) + len(recommendations)
    )

    if total_items == 0 and not reflection_text:
        return ""

    scope_header = f"Context Scope: Project '{project_id}'"
    if developer_id:
        scope_header += f" | Developer: '{developer_id}'"
    if language:
        scope_header += f" | Language: {language}"

    sections = [
        "=== BEGIN HISTORICAL PROJECT & TEAM MEMORY (HINDSIGHT) ===",
        scope_header,
        "Notice to Reviewer: The following context represents durable memories, past decisions, and team conventions.",
        "CRITICAL REVIEW POLICIES:",
        "1. DO NOT recommend practices that have been explicitly REJECTED by the team below without compelling justification.",
        "2. Reinforce established team conventions and acknowledge developer-preferred patterns.",
        "3. Where evidence is based on isolated observations, use cautious phrasing rather than asserting absolute team rules.\n"
    ]

    # 1. Negative Constraints / Rejected recommendations (Highest priority to avoid repetition)
    if rejected_recommendations:
        sections.append("[Team Decisions: REJECTED Suggestions (DO NOT REPEAT)]")
        sections.append("The team explicitly rejected the following recommendations for this project. Avoid making these suggestions:")
        for entry in rejected_recommendations[:4]:
            sections.append(f"- DO NOT RECOMMEND: {entry}")
        sections.append("")

    # 2. Synthesized Reflection from Hindsight reflect()
    if reflection_text:
        sections.append("[Synthesized Higher-Order Reflection (Hindsight Reflect)]")
        sections.append(f"- {reflection_text}")
        sections.append("")

    # 3. Developer-specific context
    if developer_preferences and developer_id:
        sections.append(f"[Developer Personalization ({developer_id})]")
        sections.append(f"Past feedback and preferred patterns observed for developer '{developer_id}':")
        for entry in developer_preferences[:3]:
            sections.append(f"- {entry}")
        sections.append("")

    # 4. Standard categorized sections
    def add_section(header: str, items: List[str]):
        if items:
            sections.append(f"[{header}]")
            for entry in items[:3]:
                sections.append(f"- {entry}")
            sections.append("")

    add_section("Established Project Conventions", conventions)
    add_section("Previous Vulnerabilities & Security Watchpoints", vulnerabilities)
    add_section("Architectural Patterns & Observations", architectural)
    add_section("Performance & Optimization Guidelines", performance)
    add_section("Previous Recommendations & Decisions", recommendations)

    sections.append("=== END HISTORICAL PROJECT & TEAM MEMORY ===")
    
    result = "\n".join(sections).strip()
    
    # Bounded in size
    if len(result) > MAX_TOTAL_CONTEXT_CHARS:
        result = result[:MAX_TOTAL_CONTEXT_CHARS] + "\n... [Context truncated for length]\n=== END HISTORICAL PROJECT & TEAM MEMORY ==="

    return result
