"""
RulesEngine — applies human-encoded rules during context assembly and entity evaluation.

This is the "conflict resolution + rule" step from the Dialect demo:
  1. Human sees something wrong or makes a judgment call
  2. They encode it as a Rule with a condition + action
  3. On every future query/entity evaluation, the engine checks all active rules
     and applies the ones whose conditions match
  4. Applied rules are cited in the response (transparency) and their fire_count incremented

Rules are intentionally kept as simple JSONB conditions — not code — so non-engineers
(the admin) can create and read them through the API or a future UI.

Condition keys supported:
  entity_type          — matches entities of this type
  field_name           — matches a specific attribute field
  field_value          — matches when that field equals this value
  field_contains       — matches when that field contains this substring
  sources_conflict     — true = matches when two sources disagree
  deal_seats_gte       — matches deals with seats >= N
  industry             — matches entities with this industry attribute
  location             — matches entities with this location/city attribute
  confidence_lte       — matches entities with confidence <= N
  source               — matches entities from this data source

Action keys supported:
  prefer_source        — when merging conflicting data, trust this source
  override_field       — set field to override_value regardless of source
  override_value       — value to set when override_field is used
  priority             — tag the entity/deal as high/medium/low priority
  flag_for             — notify this person (admin/team)
  icp_signal           — mark as strong/weak ICP signal
  apply_pricing_tier   — tag the deal with enterprise/mid-market/smb
  exclude_option       — rule out this option (e.g. "surgical_biopsy" equivalent)
  recommend            — suggest this option instead
  note                 — free-text note to attach to the context response
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import Rule

logger = logging.getLogger(__name__)


class RulesEngine:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_active_rules(self) -> list[Rule]:
        result = await self.db.execute(
            select(Rule).where(Rule.is_active == True).order_by(Rule.fire_count.desc())
        )
        return list(result.scalars().all())

    async def evaluate_entity(self, entity_attrs: dict[str, Any], entity_type: str) -> list[RuleApplication]:
        """
        Check all active rules against an entity. Returns a list of applied rules
        with the actions to take. The caller decides what to do with the actions.
        """
        rules = await self.get_active_rules()
        applied: list[RuleApplication] = []

        for rule in rules:
            if self._condition_matches(rule.condition, entity_attrs, entity_type):
                applied.append(RuleApplication(rule=rule, matched_on=entity_attrs))
                await self._increment_fire_count(rule.id)

        return applied

    async def evaluate_query_context(
        self, question: str, entities: list[dict[str, Any]]
    ) -> list[RuleApplication]:
        """
        Check rules against the context being assembled for a query.
        Returns rules that are relevant to this query and should be applied.
        """
        rules = await self.get_active_rules()
        applied: list[RuleApplication] = []

        for rule in rules:
            # Check if any entity in context matches this rule's condition
            for entity in entities:
                entity_type = entity.get("type", "")
                if self._condition_matches(rule.condition, entity, entity_type):
                    applied.append(RuleApplication(rule=rule, matched_on=entity))
                    await self._increment_fire_count(rule.id)
                    break  # one application per rule per query

        return applied

    def format_rules_for_prompt(self, applied_rules: list["RuleApplication"]) -> str:
        """Format applied rules as text to inject into the Claude prompt."""
        if not applied_rules:
            return ""

        lines = ["Applicable rules (encoded expert judgment — apply these):"]
        for app in applied_rules:
            rule = app.rule
            action_text = self._action_to_text(rule.action)
            lines.append(
                f"- RULE '{rule.name}': {action_text}\n"
                f"  Reasoning: {rule.reasoning}"
            )
        return "\n".join(lines)

    def apply_source_preference(
        self,
        field_values: dict[str, str],  # {source: value}
        applied_rules: list["RuleApplication"],
    ) -> tuple[str, str | None]:
        """
        Given multiple source values for a field, apply source-preference rules.
        Returns (winning_value, rule_name_that_decided | None).
        """
        for app in applied_rules:
            preferred_source = app.rule.action.get("prefer_source")
            if preferred_source and preferred_source in field_values:
                return field_values[preferred_source], app.rule.name

        # No rule — return the value from the highest-confidence source
        # (order: hubspot > google_sheets > gmail > document > inferred)
        source_priority = ["hubspot", "google_sheets", "document", "gmail", "manual", "inferred"]
        for source in source_priority:
            if source in field_values:
                return field_values[source], None

        # Fallback: return the first value
        first_val = next(iter(field_values.values())) if field_values else ""
        return first_val, None

    # ── Private ───────────────────────────────────────────────────────────────

    def _condition_matches(
        self, condition: dict[str, Any], entity_attrs: dict[str, Any], entity_type: str
    ) -> bool:
        """Evaluate whether a rule condition matches the given entity context."""
        if not condition:
            return True  # Empty condition = always applies (use sparingly)

        for key, expected in condition.items():
            if key == "entity_type":
                if entity_type != expected:
                    return False

            elif key == "field_name":
                if expected not in entity_attrs:
                    return False

            elif key == "field_value":
                # Needs field_name to be set too
                field = condition.get("field_name")
                if field:
                    actual = str(entity_attrs.get(field, "")).lower()
                    if actual != str(expected).lower():
                        return False

            elif key == "field_contains":
                field = condition.get("field_name")
                if field:
                    actual = str(entity_attrs.get(field, "")).lower()
                    if str(expected).lower() not in actual:
                        return False

            elif key == "industry":
                actual_industry = str(entity_attrs.get("industry", "")).lower()
                if str(expected).lower() not in actual_industry:
                    return False

            elif key == "location":
                actual_loc = str(
                    entity_attrs.get("location") or
                    entity_attrs.get("city") or
                    entity_attrs.get("building", "")
                ).lower()
                if str(expected).lower() not in actual_loc:
                    return False

            elif key == "deal_seats_gte":
                seats = entity_attrs.get("seats") or entity_attrs.get("seat_count") or 0
                try:
                    if int(seats) < int(expected):
                        return False
                except (ValueError, TypeError):
                    return False

            elif key == "confidence_lte":
                conf = entity_attrs.get("confidence", 1.0)
                try:
                    if float(conf) > float(expected):
                        return False
                except (ValueError, TypeError):
                    pass

            elif key == "source":
                if entity_attrs.get("source") != expected:
                    return False

        return True

    def _action_to_text(self, action: dict[str, Any]) -> str:
        parts = []
        if "prefer_source" in action:
            parts.append(f"prefer data from '{action['prefer_source']}'")
        if "override_field" in action:
            parts.append(f"set {action['override_field']} = {action.get('override_value', '?')}")
        if "priority" in action:
            parts.append(f"mark as {action['priority']} priority")
        if "flag_for" in action:
            parts.append(f"flag for {action['flag_for']}")
        if "icp_signal" in action:
            parts.append(f"ICP signal: {action['icp_signal']}")
        if "apply_pricing_tier" in action:
            parts.append(f"apply {action['apply_pricing_tier']} pricing")
        if "exclude_option" in action:
            parts.append(f"exclude option: {action['exclude_option']}")
        if "recommend" in action:
            parts.append(f"recommend: {action['recommend']}")
        if "note" in action:
            parts.append(f"note: {action['note']}")
        return "; ".join(parts) if parts else str(action)

    async def _increment_fire_count(self, rule_id: str) -> None:
        await self.db.execute(
            update(Rule).where(Rule.id == rule_id).values(fire_count=Rule.fire_count + 1)
        )


class RuleApplication:
    """A rule that matched — carries the rule and what it matched against."""
    def __init__(self, rule: Rule, matched_on: dict[str, Any]) -> None:
        self.rule = rule
        self.matched_on = matched_on
