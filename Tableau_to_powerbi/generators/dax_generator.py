"""
DAX generator — converts Tableau calculated fields and worksheet
aggregations into DAX measures.

Two paths:
  1. Pattern-based: regex substitution on known Tableau formula patterns.
  2. LLM fallback:  for formulas that don't match any pattern.
"""
from __future__ import annotations

import re
import os
import logging
from tableau_to_pbi.utils.models import (
    TableauIR,
    TableauColumn,
    TableauWorksheet,
    TableauEncoding,
    DAXMeasure,
)
from tableau_to_pbi.utils.mappings import FORMULA_PATTERNS, AGG_MAP

log = logging.getLogger(__name__)

_DEFAULT_TABLE = "Data"   # fallback table name in DAX expressions

# ── Pattern-based translation ──────────────────────────────────────────────────

def _apply_pattern(formula: str, table: str) -> tuple[str, float, str] | None:
    """Try each pattern once. Returns None if nothing matches."""
    for pattern, template, confidence, note in FORMULA_PATTERNS:
        m = re.search(pattern, formula, re.IGNORECASE | re.DOTALL)
        if m:
            dax = template
            groups = m.groups()
            replacements = {
                "{table}":     table,
                "{field}":     groups[0] if len(groups) > 0 else "",
                "{n}":         groups[1] if len(groups) > 1 else "",
                "{start}":     groups[1] if len(groups) > 1 else "",
                "{len}":       groups[2] if len(groups) > 2 else "",
                "{substr}":    groups[1] if len(groups) > 1 else "",
                "{old}":       groups[1] if len(groups) > 1 else "",
                "{new}":       groups[2] if len(groups) > 2 else "",
                "{inner}":     groups[0] if len(groups) > 0 else "",
                "{arg1}":      groups[0] if len(groups) > 0 else "",
                "{arg2}":      groups[1] if len(groups) > 1 else "",
                "{dim}":       groups[0] if len(groups) > 0 else "",
                "{measure}":   groups[1] if len(groups) > 1 else "",
                "{f1}":        groups[0] if len(groups) > 0 else "",
                "{f2}":        groups[1] if len(groups) > 1 else "",
                "{condition}": groups[0] if len(groups) > 0 else "",
                "{true_val}":  groups[1] if len(groups) > 1 else "",
                "{false_val}": groups[2] if len(groups) > 2 else "",
            }
            for k, v in replacements.items():
                dax = dax.replace(k, v)
            return dax, confidence, note
    return None


def _translate_formula(formula: str, table: str = _DEFAULT_TABLE) -> tuple[str, float, str]:
    """
    Translate a Tableau formula to DAX.

    Strategy:
    1. Try a direct full-formula match first.
    2. Recursively substitute known sub-expressions (handles compound formulas
       like SUM([Profit])/SUM([Sales]) or IF ... THEN ... END with agg calls).
    3. Fall through to (0.0, todo comment) if nothing matches.
    """
    # Clean up XML-escaped chars common in .twb files
    formula = (
        formula
        .replace("&gt;", ">")
        .replace("&lt;", "<")
        .replace("&amp;", "&")
        .replace("&#39;", "'")
        .replace("&quot;", '"')
    )

    # Direct match
    result = _apply_pattern(formula, table)
    if result:
        return result

    # Recursive substitution: replace each recognisable sub-expression
    # with its DAX equivalent, track minimum confidence across all subs.
    working = formula
    min_conf = 1.0
    notes: list[str] = []
    changed = True
    max_passes = 10

    while changed and max_passes > 0:
        changed = False
        max_passes -= 1
        for pattern, template, confidence, note in FORMULA_PATTERNS:
            # FIX: capture loop variables in default args to avoid closure-over-loop-variable bug
            def _replacer(m: re.Match, _tmpl=template, _conf=confidence, _note=note) -> str:
                nonlocal min_conf, changed
                groups = m.groups()
                dax = _tmpl
                replacements = {
                    "{table}":     table,
                    "{field}":     groups[0] if len(groups) > 0 else "",
                    "{n}":         groups[1] if len(groups) > 1 else "",
                    "{start}":     groups[1] if len(groups) > 1 else "",
                    "{len}":       groups[2] if len(groups) > 2 else "",
                    "{substr}":    groups[1] if len(groups) > 1 else "",
                    "{old}":       groups[1] if len(groups) > 1 else "",
                    "{new}":       groups[2] if len(groups) > 2 else "",
                    "{inner}":     groups[0] if len(groups) > 0 else "",
                    "{arg1}":      groups[0] if len(groups) > 0 else "",
                    "{arg2}":      groups[1] if len(groups) > 1 else "",
                    "{dim}":       groups[0] if len(groups) > 0 else "",
                    "{measure}":   groups[1] if len(groups) > 1 else "",
                    "{f1}":        groups[0] if len(groups) > 0 else "",
                    "{f2}":        groups[1] if len(groups) > 1 else "",
                    "{condition}": groups[0] if len(groups) > 0 else "",
                    "{true_val}":  groups[1] if len(groups) > 1 else "",
                    "{false_val}": groups[2] if len(groups) > 2 else "",
                }
                for k, v in replacements.items():
                    dax = dax.replace(k, v)
                min_conf = min(min_conf, _conf)
                if _note and _note not in notes:
                    notes.append(_note)
                changed = True
                return dax

            new_working = re.sub(pattern, _replacer, working, flags=re.IGNORECASE | re.DOTALL)
            working = new_working

    # If the working formula changed at all, it's (partially) translated
    if working != formula:
        # Replace leftover [FieldName] column refs with table[FieldName]
        working = re.sub(r"\[([^\]]+)\]", lambda m: f"{table}[{m.group(1)}]", working)
        note_str = "; ".join(notes) if notes else ""
        return working, round(min_conf * 0.95, 2), note_str  # slight penalty for compound

    # Nothing matched at all
    return (
        f"/* TODO: translate manually */\n-- Original: {formula}",
        0.0,
        "No pattern matched — requires manual DAX translation",
    )


def _llm_translate(formula: str, table: str) -> tuple[str, float, str]:
    """
    Call an LLM (OpenAI / Anthropic) to translate a Tableau formula to DAX.
    Falls back gracefully if no API key is configured.
    """
    # Try Anthropic first (matches project stack)
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    prompt = (
        f"Convert this Tableau calculated field formula to a DAX measure expression.\n"
        f"Table name in the data model: {table}\n"
        f"Tableau formula:\n{formula}\n\n"
        f"Return ONLY the DAX expression, no explanation."
    )

    if anthropic_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key)
            msg = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            dax = msg.content[0].text.strip()
            return dax, 0.70, "LLM-translated (Anthropic) — review recommended"
        except Exception as e:
            log.warning("Anthropic LLM translation failed: %s", e)

    if openai_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=512,
            )
            dax = resp.choices[0].message.content.strip()
            return dax, 0.70, "LLM-translated (OpenAI) — review recommended"
        except Exception as e:
            log.warning("OpenAI LLM translation failed: %s", e)

    return (
        f"/* TODO: translate manually */\n-- Original: {formula}",
        0.0,
        "No pattern matched and no LLM key configured",
    )


# ── Column → DAX Measure ──────────────────────────────────────────────────────

def _col_to_dax(col: TableauColumn, table: str, use_llm: bool) -> DAXMeasure:
    dax, confidence, note = _translate_formula(col.formula, table)

    if confidence == 0.0 and use_llm:
        dax, confidence, note = _llm_translate(col.formula, table)

    return DAXMeasure(
        name=col.caption or col.name,
        expression=dax,
        table=table,
        source_formula=col.formula,
        confidence=confidence,
        needs_review=confidence < 0.70,
        review_reason=note,
    )


# ── Encoding → implicit DAX measure ──────────────────────────────────────────

def _encoding_to_dax(enc: TableauEncoding, table: str) -> DAXMeasure | None:
    """
    For worksheet encodings that aggregate a raw (non-calculated) field,
    emit a simple DAX measure like SUM(Table[Field]).
    """
    agg = enc.aggregation.upper()
    if agg in ("NONE", "", "ATTR"):
        return None
    dax_agg = AGG_MAP.get(agg, agg)
    if not dax_agg:
        return None

    measure_name = f"{agg} of {enc.field}"
    dax_expr = f"{dax_agg}({table}[{enc.field}])"

    return DAXMeasure(
        name=measure_name,
        expression=dax_expr,
        table=table,
        confidence=0.90,
        needs_review=False,
    )


# ── Public API ─────────────────────────────────────────────────────────────────

def generate_dax_measures(ir: TableauIR, use_llm: bool = True) -> list[DAXMeasure]:
    measures: list[DAXMeasure] = []
    seen_names: set[str] = set()

    # 1. Calculated fields from datasources
    for ds in ir.datasources:
        table = ds.caption or ds.name
        for col in ds.columns:
            if not col.is_calculated or not col.formula:
                continue
            m = _col_to_dax(col, table, use_llm)
            if m.name not in seen_names:
                measures.append(m)
                seen_names.add(m.name)
                log.debug(
                    "DAX measure [%s] confidence=%.2f review=%s",
                    m.name, m.confidence, m.needs_review,
                )

    # 2. Implicit aggregations from worksheet encodings
    for ws in ir.worksheets:
        # Determine table for this worksheet
        table = ws.datasource or (ir.datasources[0].caption if ir.datasources else _DEFAULT_TABLE)
        for enc in ws.encodings:
            m = _encoding_to_dax(enc, table)
            if m and m.name not in seen_names:
                measures.append(m)
                seen_names.add(m.name)

    log.info(
        "Generated %d DAX measures (%d need review)",
        len(measures),
        sum(1 for m in measures if m.needs_review),
    )
    return measures
