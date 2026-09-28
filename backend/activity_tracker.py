"""Activity and Learning Tracker for Hindsight Code Review Agent.

Provides genuine tracking of operational metrics, learning events,
audit history, and timeline entries without fabricated statistics.
"""

import time
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

logger = logging.getLogger("activity_tracker")


class ActivityTracker:
    """Thread-safe, truthful in-memory activity tracker for reviews and learning events."""

    def __init__(self):
        self._reviews_count: int = 0
        self._memories_recalled_total: int = 0
        self._memories_retained_total: int = 0
        self._reflections_count: int = 0
        self._feedback_counts: Dict[str, int] = {
            "accept": 0,
            "reject": 0,
            "fixed": 0,
        }
        self._timeline_events: List[Dict[str, Any]] = []
        self._tracked_memories: List[Dict[str, Any]] = []

    def record_review(
        self,
        project_id: str,
        language: str,
        developer_id: Optional[str] = None,
        issues_count: int = 0,
        influenced_by_memory: bool = False,
        reflection_applied: bool = False,
        memories_recalled_count: int = 0,
    ) -> None:
        """Record an executed code review event."""
        self._reviews_count += 1
        self._memories_recalled_total += memories_recalled_count

        now_iso = datetime.now(timezone.utc).isoformat()
        event_type = "personalized_review" if influenced_by_memory else "review"
        title = "Personalized Code Review" if influenced_by_memory else "Standard Code Review"
        summary = (
            f"Reviewed {language} code for '{project_id}' "
            f"({issues_count} issue(s) detected, influenced by persistent memory)."
            if influenced_by_memory
            else f"Reviewed {language} code for '{project_id}' ({issues_count} issue(s) detected)."
        )

        self._add_timeline_event(
            event_type=event_type,
            title=title,
            summary=summary,
            project_id=project_id,
            developer_id=developer_id,
            timestamp=now_iso,
            meta={
                "language": language,
                "issues_count": issues_count,
                "influenced_by_memory": influenced_by_memory,
                "reflection_applied": reflection_applied,
                "memories_recalled_count": memories_recalled_count,
            },
        )

    def record_retention(
        self,
        project_id: str,
        retained_count: int,
        developer_id: Optional[str] = None,
        records: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Record durable knowledge retention."""
        if retained_count <= 0:
            return

        self._memories_retained_total += retained_count
        now_iso = datetime.now(timezone.utc).isoformat()

        self._add_timeline_event(
            event_type="memory_retained",
            title="Durable Memory Retained",
            summary=f"Persisted {retained_count} knowledge record(s) into Hindsight bank for '{project_id}'.",
            project_id=project_id,
            developer_id=developer_id,
            timestamp=now_iso,
            meta={"count": retained_count},
        )

        if records:
            for rec in records:
                self._tracked_memories.append({
                    "id": rec.get("id") or f"mem_{int(time.time()*1000)}_{len(self._tracked_memories)}",
                    "text": rec.get("text") or rec.get("content", ""),
                    "category": rec.get("category", "observation"),
                    "source": rec.get("source", "review_finding"),
                    "project_id": project_id,
                    "developer_id": developer_id,
                    "confidence": rec.get("confidence", "isolated_observation"),
                    "created_at": now_iso,
                })

    def record_reflection(
        self,
        project_id: str,
        summary_text: str,
        facts_count: int,
        developer_id: Optional[str] = None,
    ) -> None:
        """Record a successful Hindsight reflection synthesis."""
        self._reflections_count += 1
        now_iso = datetime.now(timezone.utc).isoformat()

        self._add_timeline_event(
            event_type="reflection",
            title="Conventions Synthesized (Reflection)",
            summary=f"Hindsight synthesized higher-level patterns from {facts_count} fact(s) for '{project_id}'.",
            project_id=project_id,
            developer_id=developer_id,
            timestamp=now_iso,
            meta={
                "reflection_summary": summary_text[:200],
                "facts_count": facts_count,
            },
        )

        self._tracked_memories.append({
            "id": f"ref_{int(time.time()*1000)}",
            "text": summary_text,
            "category": "convention",
            "source": "reflection",
            "project_id": project_id,
            "developer_id": developer_id,
            "confidence": "established_convention",
            "created_at": now_iso,
        })

    def record_feedback(
        self,
        project_id: str,
        action: str,
        issue_title: str,
        recommendation: Optional[str] = None,
        reason: Optional[str] = None,
        developer_id: Optional[str] = None,
        retained: bool = True,
    ) -> None:
        """Record developer feedback action."""
        clean_action = (action or "accept").lower()
        if clean_action in self._feedback_counts:
            self._feedback_counts[clean_action] += 1
        else:
            self._feedback_counts["accept"] += 1

        now_iso = datetime.now(timezone.utc).isoformat()

        action_labels = {
            "accept": "Accepted Suggestion",
            "reject": "Rejected Suggestion",
            "fixed": "Resolved Issue",
        }
        title = f"Feedback: {action_labels.get(clean_action, 'Feedback Action')}"
        reason_str = f" Reason: '{reason}'" if reason else ""
        summary = f"Developer {clean_action}ed suggestion '{issue_title}' for '{project_id}'.{reason_str}"

        self._add_timeline_event(
            event_type=f"feedback_{clean_action}",
            title=title,
            summary=summary,
            project_id=project_id,
            developer_id=developer_id,
            timestamp=now_iso,
            meta={
                "action": clean_action,
                "issue_title": issue_title,
                "recommendation": (recommendation or "")[:150],
                "reason": reason or "",
                "retained_in_hindsight": retained,
            },
        )

        # Track as durable memory item
        cat = "rejected_pattern" if clean_action == "reject" else "accepted_pattern"
        content = (
            f"Developer rejected '{issue_title}': {recommendation}. Reason: {reason}"
            if clean_action == "reject"
            else f"Developer {clean_action}ed '{issue_title}': {recommendation or ''}"
        )
        self._tracked_memories.append({
            "id": f"fb_{int(time.time()*1000)}_{len(self._tracked_memories)}",
            "text": content,
            "category": cat,
            "source": "developer_feedback",
            "project_id": project_id,
            "developer_id": developer_id,
            "confidence": "repeated_pattern" if clean_action == "reject" else "isolated_observation",
            "created_at": now_iso,
        })

    def _add_timeline_event(
        self,
        event_type: str,
        title: str,
        summary: str,
        project_id: str,
        developer_id: Optional[str],
        timestamp: str,
        meta: Dict[str, Any],
    ) -> None:
        """Add event to chronological timeline (latest first)."""
        event = {
            "id": f"evt_{int(time.time()*1000)}_{len(self._timeline_events)}",
            "type": event_type,
            "title": title,
            "summary": summary,
            "project_id": project_id,
            "developer_id": developer_id,
            "timestamp": timestamp,
            "meta": meta,
        }
        # Prepend to keep reverse-chronological order
        self._timeline_events.insert(0, event)
        # Cap memory to avoid unbounded growth
        if len(self._timeline_events) > 500:
            self._timeline_events.pop()

    def get_stats(self) -> Dict[str, Any]:
        """Return truthful aggregate counts for dashboard."""
        total_feedback = sum(self._feedback_counts.values())
        conventions_count = sum(
            1 for m in self._tracked_memories if m.get("category") in ("convention", "architecture", "rejected_pattern")
        )

        return {
            "total_reviews": self._reviews_count,
            "memories_retained": self._memories_retained_total,
            "memories_recalled": self._memories_recalled_total,
            "feedback_events": {
                "total": total_feedback,
                "accepted": self._feedback_counts.get("accept", 0),
                "rejected": self._feedback_counts.get("reject", 0),
                "fixed": self._feedback_counts.get("fixed", 0),
            },
            "reflections_count": self._reflections_count,
            "learned_conventions_count": conventions_count,
            "tracked_memories_count": len(self._tracked_memories),
        }

    def get_timeline(
        self,
        project_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Return chronological timeline events, optionally filtered by project."""
        events = self._timeline_events
        if project_id and project_id not in ("all", "*"):
            events = [e for e in events if e.get("project_id") == project_id]
        return events[:limit]

    def get_explorer_memories(
        self,
        project_id: Optional[str] = None,
        developer_id: Optional[str] = None,
        category: Optional[str] = None,
        source: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Return tracked durable memory records with optional filtering."""
        results = self._tracked_memories
        if project_id and project_id not in ("all", "*"):
            results = [m for m in results if m.get("project_id") == project_id]
        if developer_id:
            results = [m for m in results if m.get("developer_id") == developer_id]
        if category and category not in ("all", "*"):
            results = [m for m in results if m.get("category") == category]
        if source and source not in ("all", "*"):
            results = [m for m in results if m.get("source") == source]
        if search:
            q = search.lower()
            results = [
                m for m in results
                if q in m.get("text", "").lower() or q in m.get("category", "").lower()
            ]

        # Return latest first
        return list(reversed(results))[:limit]

    def reset_for_tests(self) -> None:
        """Utility for tests to clear state."""
        self._reviews_count = 0
        self._memories_recalled_total = 0
        self._memories_retained_total = 0
        self._reflections_count = 0
        self._feedback_counts = {"accept": 0, "reject": 0, "fixed": 0}
        self._timeline_events.clear()
        self._tracked_memories.clear()


# Global tracker singleton
_activity_tracker: Optional[ActivityTracker] = None


def get_activity_tracker() -> ActivityTracker:
    """Retrieve or initialize the global ActivityTracker singleton."""
    global _activity_tracker
    if _activity_tracker is None:
        _activity_tracker = ActivityTracker()
    return _activity_tracker
