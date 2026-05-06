"""
ContextEngine — the core intelligence layer.

This is what agents, the API, and human users call to get contextualised answers
about YourCompany's enterprise data. Every response cites its sources.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

import anthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.graph.embedder import Embedder
from src.graph.entity_store import EntityStore
from src.models.entities import Entity, ExpertDecision, Relationship
from src.models.enums import EntityType, RelationshipType
from src.reasoning.intent_classifier import QueryIntent, classify_intent, get_intent_decision_types
from src.reasoning.policy_engine import PolicyEngine
from src.reasoning.rules_engine import RulesEngine
from src.models.schemas import (
    ContextResponse,
    EntityContext,
    EntityRead,
    ICPProfile,
    PricingContext,
    PricingDataPoint,
    PricingQuery,
    QualityReport,
    RelationshipMap,
    RelationshipMapNode,
    RelationshipRead,
    SourceCitation,
)

logger = logging.getLogger(__name__)

CONTEXT_ASSEMBLY_PROMPT = """You are the intelligence layer for YourCompany, a managed office enterprise
operating 500K+ sq ft across NCR (Gurugram, Noida, Delhi/Aerocity), Mumbai, and Chennai.

Your role: answer questions about YourCompany's clients, buildings, vendors, brokers, deals,
and contacts using ONLY the context provided below. If the answer isn't in the context, say so.

ALWAYS cite which entities you used to form your answer.

Question: {question}

Context entities:
{context_text}

Recent relevant decisions:
{decisions_text}

{rules_text}

Instructions:
- Answer directly and factually
- Reference specific entity names, numbers, and dates from the context
- If confidence is low on some data points, say so
- If any rules above apply to this answer, mention which rule you applied and why
- End your response with: SOURCES: [comma-separated entity names you used]
"""

ICP_EXTRACTION_PROMPT = """You are analysing YourCompany's sales decision history to extract the Ideal Customer Profile (ICP).

Below are approved leads and closed deals with their context snapshots.

Decisions:
{decisions_json}

Extract:
1. Industries most commonly represented
2. Company size range (employee headcount)
3. Geographic preference (NCR / Mumbai / Chennai)
4. Seat count range
5. Common trigger signals ("recently funded", "expanding team", etc.)

Return as JSON with keys: industries (list), company_size_range ({min, max}),
geographies (list), seat_range ({min, max}), signals (list), description (string)
"""


class ContextEngine:
    def __init__(self, settings: Settings, db: AsyncSession) -> None:
        self.settings = settings
        self.db = db
        self.store = EntityStore(db)
        self.embedder = Embedder(settings, db)
        self.rules_engine = RulesEngine(db)
        self.policy_engine = PolicyEngine(db)
        self._anthropic = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    # ── Primary API ───────────────────────────────────────────────────────────

    async def query(
        self,
        question: str,
        entity_id: str | None = None,
        context_type: str | None = None,
        max_context_entities: int = 10,
    ) -> ContextResponse:
        """
        Answer a natural language question about the enterprise.

        Pipeline:
          1. Classify intent (keyword-based, <1ms) — shapes decision retrieval
          2. Semantic search for relevant entities
          3. Assemble context text
          4. Fetch intent-filtered decisions (RLHF examples)
          5. Evaluate active rules
          6. Call Claude
          7. Policy check — block/warn/flag before returning
        """
        # Step 1: classify intent — shapes which decisions we pull for context
        intent = classify_intent(question)
        intent_decision_types = get_intent_decision_types(intent)

        # Step 2: find relevant entities via similarity search
        similar = await self.embedder.similarity_search(question, limit=max_context_entities)

        # Step 3: if entity_id given, always include that entity's context
        pinned_entity: Entity | None = None
        if entity_id:
            pinned_entity = await self.store.get_entity_by_id(entity_id)

        # Step 4: assemble context text
        entities_used = []
        context_parts = []

        if pinned_entity:
            context_parts.append(self._format_entity_context(pinned_entity))
            entities_used.append(pinned_entity)

        for embedding, score in similar:
            entity = await self.store.get_entity_by_id(embedding.entity_id)
            if entity and entity not in entities_used:
                context_parts.append(
                    f"[similarity: {score:.2f}]\n{self._format_entity_context(entity)}"
                )
                entities_used.append(entity)

        # Step 5: fetch intent-filtered decisions for richer context
        recent_decisions = await self._fetch_recent_decisions(
            limit=5, decision_types=intent_decision_types
        )
        decisions_text = self._format_decisions(recent_decisions)

        if not context_parts:
            return ContextResponse(
                answer="I don't have enough context in the knowledge graph to answer this question. "
                       "Please ensure the relevant data has been ingested.",
                citations=[],
                confidence=0.0,
                context_entities_used=0,
                intent=intent.value,
            )

        # Step 6: evaluate active rules against entities in context
        entity_dicts = [
            {**e.attributes, "type": e.type, "source": e.source, "confidence": e.confidence}
            for e in entities_used
        ]
        applied_rules = await self.rules_engine.evaluate_query_context(question, entity_dicts)
        rules_text = self.rules_engine.format_rules_for_prompt(applied_rules)

        # Step 7: ask Claude to synthesise
        context_text = "\n\n---\n\n".join(context_parts)
        prompt = CONTEXT_ASSEMBLY_PROMPT.format(
            question=question,
            context_text=context_text,
            decisions_text=decisions_text or "No recent decisions recorded.",
            rules_text=rules_text or "",
        )

        answer_text, reasoning = await self._call_claude(prompt)

        # Extract citations and strip SOURCES block
        citations = self._extract_citations(answer_text, entities_used)
        clean_answer = answer_text.split("SOURCES:")[0].strip() if "SOURCES:" in answer_text else answer_text

        # Confidence = average similarity score of top-3 entities used
        top_scores = [score for _, score in similar[:3]]
        confidence = sum(top_scores) / len(top_scores) if top_scores else 0.5
        confidence = round(confidence, 2)

        # Step 8: run policy checks — may block or append disclaimers
        policy_result = await self.policy_engine.check(
            question=question,
            answer=clean_answer,
            confidence=confidence,
            context_entities_used=len(entities_used),
        )

        if policy_result.is_blocked:
            blocked_violation = next(
                v for v in policy_result.violations if v.severity == "block"
            )
            return ContextResponse(
                answer=blocked_violation.message,
                citations=[],
                confidence=0.0,
                context_entities_used=len(entities_used),
                intent=intent.value,
                policy_violations=[v.policy_name for v in policy_result.violations],
            )

        # Append warn-level disclaimers
        if policy_result.appended_disclaimers:
            clean_answer += "\n\n" + "\n".join(policy_result.appended_disclaimers)

        return ContextResponse(
            answer=clean_answer,
            citations=citations,
            confidence=confidence,
            reasoning_trace=reasoning,
            context_entities_used=len(entities_used),
            intent=intent.value,
            policy_violations=[v.policy_name for v in policy_result.violations],
        )

    async def get_entity_context(self, name_or_id: str) -> EntityContext | None:
        """Full profile of any entity with all relationships, history, decisions."""
        # Try by ID first
        entity = await self.store.get_entity_by_id(name_or_id)
        if not entity:
            # Fall back to name search
            candidates = await self.store.search_entities_by_name(name_or_id)
            if not candidates:
                return None
            entity = candidates[0]

        relationships = await self.store.get_relationships(entity.id, direction="both")

        # Fetch related entity objects
        related_ids = set()
        for rel in relationships:
            related_ids.add(rel.from_entity_id)
            related_ids.add(rel.to_entity_id)
        related_ids.discard(entity.id)

        related_entities = []
        for eid in related_ids:
            e = await self.store.get_entity_by_id(eid)
            if e:
                related_entities.append(e)

        # Recent decisions about this entity
        result = await self.db.execute(
            select(ExpertDecision)
            .where(ExpertDecision.primary_entity_id == entity.id)
            .order_by(ExpertDecision.timestamp.desc())
            .limit(10)
        )
        recent_decisions = list(result.scalars().all())

        # Quality flags
        quality_flags = await self._get_quality_flags(entity)

        # Generate a context summary
        summary = await self._summarise_entity_context(entity, relationships, related_entities)

        return EntityContext(
            entity=EntityRead.model_validate(entity),
            relationships=[RelationshipRead.model_validate(r) for r in relationships],
            related_entities=[EntityRead.model_validate(e) for e in related_entities],
            recent_decisions=[self._decision_to_schema(d) for d in recent_decisions],
            quality_flags=quality_flags,
            context_summary=summary,
        )

    async def get_icp(self) -> ICPProfile:
        """Learned ICP based on approved leads and closed deals."""
        result = await self.db.execute(
            select(ExpertDecision).where(
                ExpertDecision.decision_type.in_(["lead_approval", "deal_closure"])
            ).order_by(ExpertDecision.timestamp.desc()).limit(100)
        )
        decisions = list(result.scalars().all())

        if not decisions:
            return ICPProfile(
                description="No decisions recorded yet. Approve leads and close deals to build the ICP.",
                industries=[],
                company_size_range={"min": 0, "max": 0},
                geographies=["NCR", "Mumbai", "Chennai"],
                seat_range={"min": 0, "max": 0},
                signals=[],
                based_on_decisions=0,
                confidence=0.0,
                generated_at=datetime.now(UTC),
            )

        decisions_json = json.dumps(
            [
                {
                    "type": d.decision_type,
                    "action": d.human_action,
                    "context": d.context_snapshot,
                    "outcome": d.outcome,
                }
                for d in decisions
            ],
            ensure_ascii=False,
            indent=2,
        )

        prompt = ICP_EXTRACTION_PROMPT.format(decisions_json=decisions_json)
        # ICP extraction is complex multi-step reasoning — use extended thinking
        raw, _ = await self._call_claude(prompt, max_tokens=800, use_extended_thinking=True)

        # Parse JSON from Claude's response
        try:
            # Claude may wrap JSON in markdown code fences
            json_str = raw
            if "```" in raw:
                json_str = raw.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
            icp_data = json.loads(json_str.strip())
        except (json.JSONDecodeError, IndexError):
            logger.warning("Failed to parse ICP JSON from Claude response")
            icp_data = {}

        return ICPProfile(
            description=icp_data.get("description", "ICP extraction incomplete."),
            industries=icp_data.get("industries", []),
            company_size_range=icp_data.get("company_size_range", {"min": 50, "max": 500}),
            geographies=icp_data.get("geographies", ["NCR"]),
            seat_range=icp_data.get("seat_range", {"min": 10, "max": 200}),
            signals=icp_data.get("signals", []),
            based_on_decisions=len(decisions),
            confidence=min(0.4 + len(decisions) * 0.01, 0.95),  # grows with decision count
            generated_at=datetime.now(UTC),
        )

    async def get_pricing_context(self, query: PricingQuery) -> PricingContext:
        """Historical pricing patterns for deals matching the query parameters."""
        # Fetch all closed deals
        result = await self.db.execute(
            select(ExpertDecision).where(
                ExpertDecision.decision_type == "deal_closure"
            ).order_by(ExpertDecision.timestamp.desc()).limit(50)
        )
        decisions = list(result.scalars().all())

        data_points = []
        prices = []

        for d in decisions:
            ctx = d.context_snapshot
            deal_seats = ctx.get("seats") or ctx.get("deal_seats")
            deal_location = ctx.get("location") or ctx.get("city", "")
            price_per_seat = ctx.get("price_per_seat")
            total_value = ctx.get("deal_value") or ctx.get("total_value")
            client_name = ctx.get("client_name") or ctx.get("company_name", "Unknown")

            # Filter by location similarity and seat count proximity (±50%)
            location_match = (
                query.location.lower() in deal_location.lower()
                or deal_location.lower() in query.location.lower()
            ) if deal_location else False

            if not location_match and deal_seats:
                continue

            if deal_seats:
                try:
                    deal_seats_int = int(deal_seats)
                    seat_ratio = deal_seats_int / query.seats
                    if seat_ratio < 0.5 or seat_ratio > 2.0:
                        continue
                except (ValueError, TypeError):
                    pass

            dp = PricingDataPoint(
                deal_id=d.id,
                client_name=client_name,
                seats=int(deal_seats) if deal_seats else query.seats,
                location=deal_location or query.location,
                price_per_seat=float(price_per_seat) if price_per_seat else None,
                total_value=float(total_value) if total_value else None,
                closed_at=d.timestamp,
            )
            data_points.append(dp)
            if price_per_seat:
                prices.append(float(price_per_seat))

        if prices:
            prices_sorted = sorted(prices)
            recommended = {
                "min": prices_sorted[0],
                "max": prices_sorted[-1],
                "median": prices_sorted[len(prices_sorted) // 2],
            }
            notes = f"Based on {len(prices)} comparable deals in similar locations."
            conf = min(0.5 + len(prices) * 0.05, 0.9)
        else:
            recommended = {"min": 0, "max": 0, "median": 0}
            notes = "No comparable deals found. Insufficient data for pricing recommendation."
            conf = 0.1

        return PricingContext(
            recommended_range=recommended,
            comparable_deals=data_points[:10],
            pricing_notes=notes,
            confidence=conf,
        )

    async def get_relationship_map(self, entity_id: str, depth: int = 2) -> RelationshipMap | None:
        """Everyone and everything connected to this entity (up to depth hops)."""
        root = await self.store.get_entity_by_id(entity_id)
        if not root:
            return None

        visited_ids: set[str] = {entity_id}
        nodes: list[RelationshipMapNode] = []
        all_edges: list[Relationship] = []
        current_frontier = [entity_id]

        for d in range(1, depth + 1):
            next_frontier = []
            for eid in current_frontier:
                rels = await self.store.get_relationships(eid, direction="both")
                for rel in rels:
                    all_edges.append(rel)
                    for neighbour_id in (rel.from_entity_id, rel.to_entity_id):
                        if neighbour_id not in visited_ids:
                            visited_ids.add(neighbour_id)
                            neighbour = await self.store.get_entity_by_id(neighbour_id)
                            if neighbour:
                                rel_label = (
                                    rel.relationship_type
                                    if rel.from_entity_id == entity_id
                                    else f"←{rel.relationship_type}"
                                )
                                nodes.append(
                                    RelationshipMapNode(
                                        entity=EntityRead.model_validate(neighbour),
                                        relationship_to_root=rel_label,
                                        depth=d,
                                    )
                                )
                                next_frontier.append(neighbour_id)
            current_frontier = next_frontier

        # Deduplicate edges
        seen_edge_ids = set()
        unique_edges = []
        for e in all_edges:
            if e.id not in seen_edge_ids:
                seen_edge_ids.add(e.id)
                unique_edges.append(e)

        return RelationshipMap(
            root_entity=EntityRead.model_validate(root),
            nodes=nodes,
            edges=[RelationshipRead.model_validate(e) for e in unique_edges],
        )

    async def capture_decision(self, decision: ExpertDecision) -> None:
        """Log a human decision as a permanent training signal."""
        self.db.add(decision)
        await self.db.flush()

    async def run_quality_check(self) -> QualityReport:
        """Run proactive anomaly detection. Delegates to quality.monitor."""
        from src.quality.monitor import QualityMonitor
        monitor = QualityMonitor(self.settings, self.db)
        return await monitor.run()

    # ── Private helpers ───────────────────────────────────────────────────────

    def _format_entity_context(self, entity: Entity) -> str:
        attrs = json.dumps(entity.attributes, ensure_ascii=False)
        return (
            f"Entity: {entity.name}\n"
            f"Type: {entity.type}\n"
            f"Source: {entity.source}\n"
            f"Confidence: {entity.confidence:.2f}\n"
            f"Attributes: {attrs}"
        )

    def _format_decisions(self, decisions: list[ExpertDecision]) -> str:
        if not decisions:
            return ""
        parts = []
        for d in decisions:
            parts.append(
                f"- [{d.decision_type}] {d.actor}: {d.human_action} "
                f"(outcome: {d.outcome or 'pending'}) — {d.timestamp.strftime('%Y-%m-%d')}"
            )
        return "\n".join(parts)

    async def _fetch_recent_decisions(
        self, limit: int = 5, decision_types: list[str] | None = None
    ) -> list[ExpertDecision]:
        """
        Fetch recent decisions, optionally filtered by type.
        When intent is known, pass decision_types to surface the most relevant
        examples (e.g., closed deals for pricing queries).
        Falls back to pure recency if no types specified or no matches found.
        """
        query = select(ExpertDecision).order_by(ExpertDecision.timestamp.desc())
        if decision_types:
            query = query.where(ExpertDecision.decision_type.in_(decision_types))
        result = await self.db.execute(query.limit(limit))
        decisions = list(result.scalars().all())

        # If intent-filtered query returned nothing, fall back to recency
        if not decisions and decision_types:
            fallback = await self.db.execute(
                select(ExpertDecision)
                .order_by(ExpertDecision.timestamp.desc())
                .limit(limit)
            )
            decisions = list(fallback.scalars().all())

        return decisions

    def _extract_citations(
        self, answer_text: str, entities: list[Entity]
    ) -> list[SourceCitation]:
        citations = []
        # Check which entity names appear in the answer
        for entity in entities:
            if entity.name.lower() in answer_text.lower():
                citations.append(
                    SourceCitation(
                        entity_id=entity.id,
                        entity_name=entity.name,
                        entity_type=entity.type,
                        source=entity.source,
                        relevance_score=entity.confidence,
                    )
                )
        return citations

    async def _summarise_entity_context(
        self,
        entity: Entity,
        relationships: list[Relationship],
        related_entities: list[Entity],
    ) -> str:
        rel_summary = ", ".join(
            f"{r.relationship_type} → {next((e.name for e in related_entities if e.id == r.to_entity_id), r.to_entity_id)}"
            for r in relationships[:5]
        )
        attrs = json.dumps(entity.attributes, ensure_ascii=False)
        prompt = (
            f"Summarise this YourCompany entity in 2-3 sentences for an executive reader.\n\n"
            f"Type: {entity.type}\nName: {entity.name}\nAttributes: {attrs}\n"
            f"Key relationships: {rel_summary or 'none recorded'}"
        )
        summary, _ = await self._call_claude(prompt, max_tokens=200)
        return summary

    async def _get_quality_flags(self, entity: Entity) -> list[str]:
        from src.models.entities import DataQualityLog
        result = await self.db.execute(
            select(DataQualityLog).where(
                DataQualityLog.entity_id == entity.id,
                DataQualityLog.resolved == False,
            )
        )
        logs = list(result.scalars().all())
        return [log.anomaly_description or log.check_type for log in logs]

    def _decision_to_schema(self, d: ExpertDecision):
        from src.models.schemas import ExpertDecisionRead
        return ExpertDecisionRead.model_validate(d)

    async def _call_claude(
        self,
        prompt: str,
        max_tokens: int = 1000,
        use_extended_thinking: bool = False,
    ) -> tuple[str, str | None]:
        """
        Call Claude Sonnet 4.6 with:
        - Prompt caching on the system context (cuts latency + cost on repeated calls)
        - Few-shot RLHF examples: the 3 most recent decisions with positive outcomes
          are injected as assistant examples so Claude learns the admin's style
        - Extended thinking for complex multi-step reasoning (optional, costs more tokens)
        """
        if not self.settings.anthropic_api_key:
            return "Claude API key not configured.", None

        # Build the cached system prompt
        system_blocks = [
            {
                "type": "text",
                "text": (
                    "You are the intelligence layer for YourCompany, a managed office enterprise "
                    "operating 500K+ sq ft across NCR (Gurugram, Noida, Delhi/Aerocity), Mumbai, and Chennai.\n\n"
                    "You answer questions about clients, buildings, vendors, brokers, deals, and contacts "
                    "using only the data provided. Be factual, specific, and cite your sources.\n\n"
                    "When data has low confidence (< 0.7), flag it explicitly.\n"
                    "When a rule applies, say which rule and why.\n"
                    "Never guess — if the data isn't in context, say so."
                ),
                "cache_control": {"type": "ephemeral"},
            }
        ]

        # Build the few-shot RLHF message history from positive-outcome decisions
        rlhf_examples = await self._build_rlhf_examples()
        messages = rlhf_examples + [{"role": "user", "content": prompt}]

        try:
            kwargs: dict = {
                "model": self.settings.anthropic_model,  # always claude-sonnet-4-6
                "max_tokens": max_tokens,
                "system": system_blocks,
                "messages": messages,
            }

            # Extended thinking: use for complex multi-hop reasoning (ICP, pricing analysis)
            # Requires a higher token budget — only enable when explicitly requested
            if use_extended_thinking:
                kwargs["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": 5000,
                }
                kwargs["max_tokens"] = max(max_tokens, 8000)

            message = self._anthropic.messages.create(**kwargs)

            # Extract thinking trace if present
            reasoning_trace = None
            answer_text = ""
            for block in message.content:
                if block.type == "thinking":
                    reasoning_trace = block.thinking
                elif block.type == "text":
                    answer_text = block.text.strip()

            return answer_text, reasoning_trace

        except anthropic.APIError as exc:
            logger.error("Claude API error: %s", exc)
            return f"Error calling Claude: {exc}", None

    async def _build_rlhf_examples(self) -> list[dict]:
        """
        Build few-shot examples from the 3 most recent decisions with positive outcomes.
        These are injected as user/assistant pairs before the real prompt so Claude
        learns the reasoning style and quality bar the admin expect.

        This is the RLHF signal: Claude's behaviour on new queries is shaped by
        what got labelled 'positive' by the humans in the loop.
        """
        result = await self.db.execute(
            select(ExpertDecision)
            .where(
                ExpertDecision.feedback_signal == "positive",
                ExpertDecision.human_reasoning.isnot(None),
            )
            .order_by(ExpertDecision.timestamp.desc())
            .limit(3)
        )
        positive_decisions = list(result.scalars().all())

        examples = []
        for d in positive_decisions:
            ctx = d.context_snapshot
            # Synthetic user turn: describe the situation from the context snapshot
            user_turn = (
                f"[Example from {d.timestamp.strftime('%Y-%m-%d')}]\n"
                f"Decision type: {d.decision_type}\n"
                f"Context: {json.dumps(ctx, ensure_ascii=False)[:500]}"
            )
            # Synthetic assistant turn: the human's actual reasoning (the gold label)
            assistant_turn = (
                f"Decision: {d.human_action}\n"
                f"Reasoning: {d.human_reasoning}\n"
                f"Outcome: {d.outcome or 'pending'}"
            )
            examples.append({"role": "user", "content": user_turn})
            examples.append({"role": "assistant", "content": assistant_turn})

        return examples
