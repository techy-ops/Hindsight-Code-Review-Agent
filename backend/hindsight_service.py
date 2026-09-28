"""Hindsight Memory Service for AI Code Review Agent.

Provides a clean, centralized abstraction over the Hindsight Python SDK.
Handles:
- Memory Bank creation / resolution per project (isolation scoping)
- Knowledge retention (retain_memory, retain_feedback)
- Contextual recall (recall_memory with project and developer scoping)
- Reflection synthesis (reflect_memory) using Hindsight areflect()
- Graceful degradation when Hindsight is unavailable or encounters errors
- Safe logging without credentials or sensitive data
"""

import logging
import re
from typing import List, Dict, Any, Optional
from hindsight_client import Hindsight
from config import Settings, get_settings
from memory_model import sanitize_text, MemoryRecord, FeedbackRequest, create_feedback_memory_record

logger = logging.getLogger("hindsight_service")


def sanitize_identifier(name: str) -> str:
    """Sanitize bank and project identifiers for safe naming in Hindsight."""
    if not name:
        return "default"
    # Keep only alphanumeric and hyphens/underscores
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "-", name).strip("-_").lower()
    return cleaned[:64] or "default"


class HindsightService:
    """Dedicated service for persistent memory operations via Hindsight."""

    def __init__(self, config: Optional[Settings] = None):
        self.config = config or get_settings()
        self._client: Optional[Hindsight] = None
        self._initialized_banks: set[str] = set()

    def _get_client(self) -> Optional[Hindsight]:
        """Lazily initialize and return the Hindsight client."""
        if not self.config.is_hindsight_configured():
            return None
        if self._client is None:
            try:
                self._client = Hindsight(
                    base_url=self.config.hindsight_base_url,
                    api_key=self.config.hindsight_api_key or None,
                    timeout=self.config.hindsight_timeout,
                )
            except Exception as e:
                logger.warning("Failed to initialize Hindsight client: %s", type(e).__name__)
                self._client = None
        return self._client

    def resolve_bank_id(self, project_id: str) -> str:
        """Resolve an isolated memory bank identifier for a given project.
        
        Guarantees repository/project-level scoping to prevent cross-project contamination.
        """
        base_bank = sanitize_identifier(self.config.hindsight_bank_id)
        proj_clean = sanitize_identifier(project_id)
        if proj_clean in ("default", "main", base_bank):
            return base_bank
        return f"{base_bank}_{proj_clean}"

    async def _ensure_bank_exists(self, client: Hindsight, bank_id: str) -> None:
        """Ensure the specified memory bank is registered in Hindsight."""
        if bank_id in self._initialized_banks:
            return
        try:
            # Attempt to create bank with review-tailored mission
            await client.acreate_bank(
                bank_id=bank_id,
                name=f"Code Review Agent ({bank_id})",
                mission="Store and recall programming conventions, architectural patterns, vulnerabilities, and code quality standards.",
                retain_mission="Extract software engineering guidelines, security findings, and reusable architecture conventions.",
            )
            self._initialized_banks.add(bank_id)
            logger.info("Successfully created/verified Hindsight memory bank: %s", bank_id)
        except Exception as e:
            # If bank already exists (e.g. HTTP 409) or server auto-provisions, record as initialized
            logger.debug("Bank provision notice for '%s': %s", bank_id, type(e).__name__)
            self._initialized_banks.add(bank_id)

    async def check_health(self) -> Dict[str, Any]:
        """Perform a non-throwing health check against the Hindsight server."""
        if not self.config.hindsight_enabled:
            return {
                "status": "disabled",
                "message": "Hindsight memory is disabled by configuration (HINDSIGHT_ENABLED=false)",
                "base_url": self.config.hindsight_base_url,
            }

        client = self._get_client()
        if not client:
            return {
                "status": "unconfigured",
                "message": "Hindsight client is not configured",
                "base_url": self.config.hindsight_base_url,
            }

        try:
            version_resp = await client.aget_version()
            version_str = getattr(version_resp, "version", "connected")
            return {
                "status": "healthy",
                "version": version_str,
                "base_url": self.config.hindsight_base_url,
                "bank_id": self.config.hindsight_bank_id,
            }
        except Exception as e:
            logger.warning("Hindsight health check failed: %s", type(e).__name__)
            return {
                "status": "unavailable",
                "message": f"Hindsight server unavailable: {type(e).__name__}",
                "base_url": self.config.hindsight_base_url,
            }

    async def recall_memory(
        self,
        project_id: str = "default-project",
        query: str = "",
        language: Optional[str] = None,
        developer_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Recall relevant historical memories for a given project and query.
        
        Optionally scopes to developer-specific memories when developer_id is provided.
        Fails gracefully to an empty list on any network/server failure.
        """
        if not self.config.hindsight_enabled:
            return []

        client = self._get_client()
        if not client:
            return []

        bank_id = self.resolve_bank_id(project_id)
        limit = limit or self.config.hindsight_max_recall_results

        # Construct query: combine language and query text, sanitized
        query_text = sanitize_text(query[:500]).strip()
        if not query_text:
            query_text = f"Coding conventions and review findings for {language or 'code'}"

        tags = [f"project:{project_id}"]
        if language:
            tags.append(f"lang:{language.lower()}")
        if developer_id and self.config.hindsight_developer_memory_enabled:
            tags.append(f"developer:{developer_id}")

        try:
            response = await client.arecall(
                bank_id=bank_id,
                query=query_text,
                tags=tags,
                tags_match="any",
                max_tokens=2048,
                budget="low",  # fast recall for interactive code review
            )

            results: List[Dict[str, Any]] = []
            raw_results = getattr(response, "results", []) or []

            for r in raw_results:
                try:
                    text = getattr(r, "text", "") or ""
                    if not text and isinstance(r, dict):
                        text = r.get("text", "")

                    if not text:
                        continue

                    meta = getattr(r, "metadata", {}) or {}
                    if not isinstance(meta, dict):
                        meta = {}

                    category = meta.get("category", "observation")
                    results.append({
                        "id": getattr(r, "id", None) or (r.get("id") if isinstance(r, dict) else None),
                        "text": text,
                        "category": category,
                        "metadata": meta,
                        "tags": getattr(r, "tags", []) or [],
                    })
                except Exception as parse_err:
                    logger.debug("Skipping malformed memory item: %s", parse_err)
                    continue

            logger.info(
                "Hindsight recall succeeded for project '%s' (dev: %s): %d memories retrieved",
                project_id,
                developer_id or "none",
                len(results),
            )
            return results[:limit]

        except Exception as e:
            logger.warning(
                "Hindsight recall failed for project '%s' (%s): returning fallback empty memory",
                project_id,
                type(e).__name__,
            )
            return []

    async def reflect_memory(
        self,
        project_id: str,
        query: str,
        developer_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Synthesize higher-level project, team, and developer patterns using Hindsight reflect().
        
        Returns dict with reflection text, facts it was based on, and metadata,
        or None on failure or when disabled.
        """
        if not self.config.hindsight_enabled or not self.config.hindsight_reflect_enabled:
            return None

        client = self._get_client()
        if not client:
            return None

        bank_id = self.resolve_bank_id(project_id)
        merged_tags = [f"project:{project_id}"]
        if developer_id and self.config.hindsight_developer_memory_enabled:
            merged_tags.append(f"developer:{developer_id}")
        if tags:
            merged_tags.extend(tags)
        merged_tags = list(dict.fromkeys(merged_tags))

        try:
            response = await client.areflect(
                bank_id=bank_id,
                query=query,
                tags=merged_tags,
                tags_match="any",
                budget=self.config.hindsight_reflect_budget,
            )
            text = getattr(response, "text", "") or ""
            if not text and isinstance(response, dict):
                text = response.get("text", "")

            if not text:
                return None

            based_on_facts: List[str] = []
            raw_facts = getattr(response, "based_on", []) or []
            for f in raw_facts:
                fact_text = getattr(f, "text", "") if hasattr(f, "text") else (f.get("text", "") if isinstance(f, dict) else str(f))
                if fact_text:
                    based_on_facts.append(fact_text)

            logger.info(
                "Hindsight reflection succeeded for project '%s' (dev: %s, %d facts)",
                project_id,
                developer_id or "none",
                len(based_on_facts),
            )
            return {
                "text": text,
                "based_on": based_on_facts,
                "project_id": project_id,
                "developer_id": developer_id,
            }
        except Exception as e:
            logger.warning(
                "Hindsight reflection failed for project '%s' (%s): continuing without reflection",
                project_id,
                type(e).__name__,
            )
            return None

    async def retain_memory(
        self,
        project_id: str,
        language: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> bool:
        """Store a single durable knowledge item into Hindsight persistent memory.
        
        Returns True on success, False on failure. Never raises an unhandled exception.
        """
        if not self.config.hindsight_enabled:
            return False

        client = self._get_client()
        if not client:
            return False

        bank_id = self.resolve_bank_id(project_id)
        cleaned_content = sanitize_text(content)
        if not cleaned_content:
            return False

        merged_tags = [f"project:{project_id}", f"lang:{language.lower()}"]
        if tags:
            merged_tags.extend(tags)
        # Deduplicate tags
        merged_tags = list(dict.fromkeys(merged_tags))

        # Safe metadata: string values only as expected by Hindsight SDK
        safe_meta: Dict[str, str] = {
            "project_id": str(project_id),
            "language": str(language.lower()),
        }
        if metadata:
            for k, v in metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    safe_meta[str(k)] = str(v)

        try:
            await self._ensure_bank_exists(client, bank_id)
            await client.aretain(
                bank_id=bank_id,
                content=cleaned_content,
                metadata=safe_meta,
                tags=merged_tags,
                retain_async=True,  # async background processing in Hindsight
            )
            logger.info("Hindsight retain succeeded for project '%s'", project_id)
            return True
        except Exception as e:
            logger.warning(
                "Hindsight retain failed for project '%s' (%s): continuing normal review",
                project_id,
                type(e).__name__,
            )
            return False

    async def retain_knowledge_records(
        self,
        records: List[MemoryRecord],
    ) -> int:
        """Persist a batch of extracted MemoryRecord items.
        
        Returns the count of successfully persisted records.
        """
        if not records or not self.config.hindsight_enabled:
            return 0

        retained_count = 0
        for rec in records:
            success = await self.retain_memory(
                project_id=rec.project_id,
                language=rec.language,
                content=rec.content,
                metadata=rec.metadata,
                tags=rec.tags,
            )
            if success:
                retained_count += 1
        return retained_count

    async def retain_feedback(self, feedback: FeedbackRequest) -> bool:
        """Persist review feedback (accept/reject/fixed) into Hindsight durable memory."""
        record = create_feedback_memory_record(feedback)
        return await self.retain_memory(
            project_id=record.project_id,
            language=record.language,
            content=record.content,
            metadata=record.metadata,
            tags=record.tags,
        )

    async def close(self) -> None:
        """Gracefully release client resources if applicable."""
        if self._client and hasattr(self._client, "aclose"):
            try:
                await self._client.aclose()
            except Exception:
                pass
            self._client = None


# Global service singleton
_hindsight_service_instance: Optional[HindsightService] = None


def get_hindsight_service() -> HindsightService:
    """Retrieve or initialize the global HindsightService singleton."""
    global _hindsight_service_instance
    if _hindsight_service_instance is None:
        _hindsight_service_instance = HindsightService()
    return _hindsight_service_instance
