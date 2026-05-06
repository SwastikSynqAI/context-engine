"""
BaseIngester — abstract base class all ingesters must subclass.

Contract:
- ingest() fetches raw data from the source and upserts entities + relationships
- Every ingester must declare which entity types it produces
- Every ingester must report a IngestionResult (counts + errors)
"""

from __future__ import annotations

import abc
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.graph.entity_store import EntityStore
from src.graph.relationship_mapper import RelationshipMapper

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    source: str
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    entities_created: int = 0
    entities_updated: int = 0
    relationships_created: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    def finish(self) -> None:
        self.finished_at = datetime.now(UTC)

    def add_error(self, msg: str) -> None:
        logger.error("[%s] ingestion error: %s", self.source, msg)
        self.errors.append(msg)

    def __str__(self) -> str:
        duration = (
            f"{(self.finished_at - self.started_at).total_seconds():.1f}s"
            if self.finished_at
            else "running"
        )
        return (
            f"[{self.source}] +{self.entities_created} entities, "
            f"~{self.entities_updated} updated, "
            f"+{self.relationships_created} relationships, "
            f"{len(self.errors)} errors — {duration}"
        )


class BaseIngester(abc.ABC):
    """
    Subclass this for each data source. Implement `_fetch_raw()` and `_transform()`.
    The `ingest()` method orchestrates the full pipeline.
    """

    source_name: str  # Must be set by subclass — matches DataSource enum value

    def __init__(self, settings: Settings, db: AsyncSession) -> None:
        self.settings = settings
        self.db = db
        self.entity_store = EntityStore(db)
        self.relationship_mapper = RelationshipMapper(db)
        self.logger = logging.getLogger(f"ingester.{self.source_name}")

    async def ingest(self) -> IngestionResult:
        result = IngestionResult(source=self.source_name)
        self.logger.info("Starting ingestion from %s", self.source_name)
        try:
            raw_records = await self._fetch_raw()
            self.logger.info("Fetched %d raw records from %s", len(raw_records), self.source_name)
            for raw in raw_records:
                try:
                    await self._process_record(raw, result)
                except Exception as exc:
                    result.add_error(f"Record processing failed: {exc}")
        except Exception as exc:
            result.add_error(f"Fetch failed: {exc}")
        finally:
            result.finish()
        self.logger.info("Ingestion complete: %s", result)
        return result

    @abc.abstractmethod
    async def _fetch_raw(self) -> list[dict[str, Any]]:
        """Fetch raw records from the source. Return a list of dicts."""
        ...

    @abc.abstractmethod
    async def _process_record(self, record: dict[str, Any], result: IngestionResult) -> None:
        """
        Transform one raw record into entity/relationship upserts.
        Mutate `result` to track counts.
        """
        ...
