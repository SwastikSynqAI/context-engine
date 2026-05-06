"""
Embedder — generates vector embeddings for entities and stores them in the embeddings table.

Strategy:
  - We use the Anthropic API (Claude) to generate a rich text summary of each entity,
    then embed that summary using OpenAI's text-embedding-3-small (1536 dims).
  - This two-step approach means the embedding captures semantic context assembled by
    Claude, not just raw field values concatenated together.
  - If no OpenAI key is available we fall back to a simple concatenation + a placeholder
    embedding (zero vector) so the pipeline doesn't break during development.

Note: Anthropic does not expose a standalone embedding endpoint. The industry standard
for production embedding with Claude-assembled context is to use OpenAI ada-002 or
text-embedding-3-small for the vector generation step.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from typing import Any

import anthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.models.entities import Embedding, Entity
from src.models.enums import ContentType

logger = logging.getLogger(__name__)

ENTITY_SUMMARY_PROMPT = """You are a data intelligence assistant for YourCompany, a managed office enterprise.

Produce a concise but information-rich summary of the following entity that captures:
1. What this entity IS (type, name, key identifiers)
2. What it DOES or represents in the context of a managed office business
3. Key attributes that would help answer questions about it
4. Any notable facts from the attributes

Entity type: {entity_type}
Entity name: {entity_name}
Attributes: {attributes}

Write a single paragraph (3-5 sentences). Do not use bullet points. Be specific and factual.
Include numbers and names where present in the attributes."""


class Embedder:
    def __init__(self, settings: Settings, db: AsyncSession) -> None:
        self.settings = settings
        self.db = db
        self._anthropic = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._openai_client = None

    def _get_openai_client(self):
        """Lazy-init OpenAI client for embedding generation."""
        if self._openai_client is None:
            try:
                from openai import OpenAI
                self._openai_client = OpenAI()
            except ImportError:
                logger.warning("openai package not installed — using fallback embeddings")
        return self._openai_client

    async def embed_entity(self, entity: Entity) -> bool:
        """
        Generate and store an embedding for an entity.
        Returns True if a new embedding was created, False if it already existed and was fresh.
        """
        # Check if we already have a fresh embedding
        existing = await self._get_existing_embedding(entity.id, ContentType.ENTITY_SUMMARY)
        content_text = await self._build_entity_summary(entity)
        content_hash = hashlib.sha256(content_text.encode()).hexdigest()

        if existing and existing.emb_metadata.get("content_hash") == content_hash:
            return False  # Embedding is current — skip

        vector = await self._generate_vector(content_text)
        if vector is None:
            return False

        if existing:
            existing.content_text = content_text
            existing.embedding = vector
            existing.emb_metadata = {"content_hash": content_hash, "entity_type": entity.type}
            await self.db.flush()
        else:
            embedding = Embedding(
                id=str(uuid.uuid4()),
                entity_id=entity.id,
                content_type=ContentType.ENTITY_SUMMARY,
                content_text=content_text,
                embedding=vector,
                emb_metadata={"content_hash": content_hash, "entity_type": entity.type},
            )
            self.db.add(embedding)
            await self.db.flush()

        return True

    async def embed_entities_bulk(self, entities: list[Entity]) -> int:
        """Embed a batch of entities. Returns count of new/updated embeddings."""
        count = 0
        for entity in entities:
            try:
                updated = await self.embed_entity(entity)
                if updated:
                    count += 1
            except Exception as exc:
                logger.error("Failed to embed entity %s (%s): %s", entity.name, entity.id[:8], exc)
        return count

    async def similarity_search(
        self,
        query_text: str,
        limit: int = 10,
        entity_type: str | None = None,
    ) -> list[tuple[Embedding, float]]:
        """
        Search embeddings by cosine similarity to query_text.
        Returns list of (Embedding, similarity_score) sorted by score descending.
        """
        query_vector = await self._generate_vector(query_text)
        if query_vector is None:
            return []

        # pgvector cosine distance: 1 - cosine_similarity, so lower = more similar
        query = (
            select(
                Embedding,
                Embedding.embedding.cosine_distance(query_vector).label("distance"),
            )
            .order_by("distance")
            .limit(limit)
        )

        if entity_type:
            query = query.where(Embedding.emb_metadata["entity_type"].astext == entity_type)

        result = await self.db.execute(query)
        rows = result.all()
        return [(row.Embedding, 1.0 - row.distance) for row in rows]

    # ── Private ───────────────────────────────────────────────────────────────

    async def _build_entity_summary(self, entity: Entity) -> str:
        """Ask Claude to write a semantic summary of the entity."""
        if not self.settings.anthropic_api_key:
            # Fallback: plain text concatenation
            attrs = json.dumps(entity.attributes, ensure_ascii=False)
            return f"{entity.type}: {entity.name}. Attributes: {attrs}"

        prompt = ENTITY_SUMMARY_PROMPT.format(
            entity_type=entity.type,
            entity_name=entity.name,
            attributes=json.dumps(entity.attributes, ensure_ascii=False, indent=2),
        )

        message = self._anthropic.messages.create(
            model=self.settings.anthropic_model,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()

    async def _generate_vector(self, text: str) -> list[float] | None:
        """Generate a 1536-dim embedding vector for text."""
        openai = self._get_openai_client()
        if openai is None:
            # Development fallback: deterministic pseudo-vector based on text hash
            logger.debug("Using fallback embedding (no OpenAI client)")
            return self._fallback_vector(text)

        try:
            response = openai.embeddings.create(
                model="text-embedding-3-small",
                input=text,
                dimensions=1536,
            )
            return response.data[0].embedding
        except Exception as exc:
            logger.error("OpenAI embedding failed: %s — using fallback", exc)
            return self._fallback_vector(text)

    def _fallback_vector(self, text: str) -> list[float]:
        """
        Deterministic pseudo-embedding for development (no real semantic meaning).
        Uses the text hash to seed a pseudo-random 1536-dim unit vector.
        """
        import struct
        h = hashlib.sha256(text.encode()).digest()
        # Repeat the 32-byte hash to fill 1536 floats (32 * 4 bytes = 128 bytes per repeat)
        repeats = (1536 * 4 // 32) + 1
        raw = (h * repeats)[: 1536 * 4]
        floats = list(struct.unpack(f"{1536}f", raw))
        # Normalise to unit vector
        magnitude = sum(x ** 2 for x in floats) ** 0.5
        if magnitude == 0:
            return [0.0] * 1536
        return [x / magnitude for x in floats]

    async def _get_existing_embedding(
        self, entity_id: str, content_type: ContentType
    ) -> Embedding | None:
        result = await self.db.execute(
            select(Embedding).where(
                Embedding.entity_id == entity_id,
                Embedding.content_type == content_type,
            )
        )
        return result.scalar_one_or_none()
