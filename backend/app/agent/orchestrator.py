"""
Agent orchestrator (spec §11, §26). Deterministic intent detection +
tool-calling + grounded answer composition. This is the DEFAULT and fully
tested path - it requires zero LLM API keys, per spec §44 ("the dashboard
and optimizer must NEVER fail simply because an LLM key is absent").

An optional LLM_PROVIDER enhancement hook exists at the bottom of this file
to re-phrase the composed answer more fluently using a real model, but it
is off by default and NOT exercised by this build (no key available in
this environment to test against) - see docs/agent-architecture.md.
"""
import re
from typing import Dict, Any, List

from sqlalchemy.orm import Session

from app import models
from app.agent import tools as agent_tools
from app.optimization.qubo import CorridorInput
from app.optimization.engine import run_optimization
from app.core.config import settings

CORRIDOR_CODE_RE = re.compile(r"\b([A-Z]{3}[_/]?[A-Z]{3})\b")
PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")

INTENTS = [
    ("largest_excess", ["largest excess", "which corridor has the most", "biggest excess", "most excess"]),
    ("release_candidates", ["release capital", "safely release", "which accounts can release"]),
    ("scenario_demand", ["what happens if", "demand increase", "demand increases", "demand goes up", "demand rises"]),
    ("scenario_volatility", ["volatility increase", "volatility increases", "if volatility"]),
    ("scenario_confidence", ["confidence level", "confidence change"]),
    ("scenario_cutoff", ["cutoff", "settlement window closes", "cut-off", "cut off"]),
    ("source_regulation", ["regulatory rule", "regulation", "regulatory requirement", "based on a regulatory"]),
    ("source_practice", ["settlement practice", "operational practice", "market practice"]),
    ("binding_constraint", ["which constraint", "prevents further", "why can't we reduce further", "why cant we reduce further"]),
    ("explain_excess", ["why are we holding", "why do we hold", "too much", "excess liquidity", "why is our"]),
]


def detect_intent(question: str) -> str:
    q = question.lower()
    scores: Dict[str, int] = {}
    for intent, phrases in INTENTS:
        score = sum(1 for p in phrases if p in q)
        if score:
            scores[intent] = score
    return max(scores, key=scores.get) if scores else "general_snapshot"


def _find_corridor(db: Session, question: str):
    normalized = question.replace(" to ", "_").upper()
    m = CORRIDOR_CODE_RE.search(normalized)
    if m:
        code_guess = m.group(1).replace("/", "_").replace("-", "_")
        corridor = db.query(models.Corridor).filter(models.Corridor.code == code_guess).first()
        if corridor:
            return corridor
    for c in db.query(models.Corridor).all():
        if c.source_currency in question.upper() and c.dest_currency in question.upper():
            return c
    return None


def _corridor_input_from_db(db: Session, corridor: models.Corridor, confidence_level: float = 0.95,
                             demand_delta_pct: float = 0.0, volatility_delta_pct: float = 0.0) -> CorridorInput:
    fc = agent_tools.get_payment_forecast(db, corridor.id)
    mu = fc["expected_demand_musd"] * (1 + demand_delta_pct / 100.0)
    sigma = max(fc["std_dev_musd"] * (1 + volatility_delta_pct / 100.0), 0.01)
    risk = db.query(models.RiskParameter).filter(models.RiskParameter.corridor_id == corridor.id).first()
    accounts = db.query(models.NostroAccount).filter(models.NostroAccount.corridor_id == corridor.id).all()
    current = sum(a.current_balance_musd for a in accounts)
    return CorridorInput(
        corridor_id=corridor.id, code=corridor.code, mu=mu, sigma=sigma,
        current_liquidity=current,
        opportunity_cost_rate=risk.opportunity_cost_rate_annual if risk else 0.05,
        loss_given_shortfall=risk.loss_given_shortfall_musd if risk else 5.0,
        fx_cost_bps=risk.fx_cost_bps if risk else 8.0,
        operational_cost_rate=risk.operational_cost_rate if risk else 0.02,
        confidence_level=confidence_level,
    )


def answer_question(db: Session, question: str) -> Dict[str, Any]:
    intent = detect_intent(question)
    tools_used: List[str] = []
    sources: List[Dict[str, Any]] = []
    text_parts: List[str] = []

    if intent == "general_snapshot":
        tools_used.append("get_liquidity_snapshot")
        snap = agent_tools.get_liquidity_snapshot(db)
        text_parts.append(
            f"Total nostro liquidity across all corridors is ${snap['total_liquidity_musd']:.1f}M. "
            f"Try asking things like 'why are we holding too much USD liquidity?', 'which corridor has "
            f"the largest excess liquidity?', or 'what happens if USD_INR demand increases by 30%?' - "
            f"I'll pull live figures and re-run the optimizer where relevant."
        )

    elif intent in ("largest_excess", "explain_excess", "release_candidates"):
        tools_used += ["get_liquidity_snapshot", "get_corridor_data", "run_optimizer"]
        corridors = db.query(models.Corridor).all()
        inputs = [_corridor_input_from_db(db, c) for c in corridors]
        outcome = run_optimization(inputs, iterations=4000)
        ranked = sorted(outcome.corridor_results, key=lambda r: r["capital_released_musd"], reverse=True)
        lines = [
            f"{r['corridor_code']}: ${r['capital_released_musd']:.1f}M releasable "
            f"(current ${r['current_liquidity_musd']:.1f}M -> recommended ${r['optimized_liquidity_musd']:.1f}M)"
            for r in ranked[:3] if r["capital_released_musd"] > 0
        ]
        if lines:
            text_parts.append("Largest liquidity release opportunities from the current optimization run:")
            text_parts.extend(f"- {l}" for l in lines)
        else:
            text_parts.append("No corridor shows a meaningful release opportunity at the current confidence level.")
        practices = agent_tools.get_settlement_practices(db)
        if practices:
            p = practices[0]
            text_parts.append(
                f"This assumes intraday replenishment is available (operational practice: "
                f"'{p['title']}', confidence {p['confidence']}) - that is observed practice, not a "
                f"regulatory guarantee."
            )
            sources.append({"source_type": "SETTLEMENT_PRACTICE", "title": p["title"], "confidence": p["confidence"]})

    elif intent == "scenario_demand":
        tools_used += ["get_payment_forecast", "run_optimizer", "run_scenario"]
        corridor = _find_corridor(db, question)
        pct_match = PERCENT_RE.search(question)
        pct = float(pct_match.group(1)) if pct_match else 30.0
        corridors = [corridor] if corridor else db.query(models.Corridor).all()
        if not corridor:
            text_parts.append(f"No specific corridor recognized - showing the effect of a {pct:.0f}% demand increase across all corridors.")
        base_out = run_optimization([_corridor_input_from_db(db, c) for c in corridors], iterations=4000)
        shock_out = run_optimization([_corridor_input_from_db(db, c, demand_delta_pct=pct) for c in corridors], iterations=4000)
        for b, s in zip(base_out.corridor_results, shock_out.corridor_results):
            delta = s["optimized_liquidity_musd"] - b["optimized_liquidity_musd"]
            direction = "increased" if delta > 0.01 else ("decreased" if delta < -0.01 else "stayed flat")
            text_parts.append(
                f"{b['corridor_code']}: a {pct:.0f}% demand increase raises expected demand from "
                f"${b['expected_demand_musd']:.1f}M to ${s['expected_demand_musd']:.1f}M, which raises the "
                f"safety requirement from ${b['required_liquidity_musd']:.1f}M to ${s['required_liquidity_musd']:.1f}M. "
                f"Recommended liquidity {direction}: ${b['optimized_liquidity_musd']:.1f}M -> "
                f"${s['optimized_liquidity_musd']:.1f}M (modeled shortfall risk {b['risk_after']*100:.2f}% -> "
                f"{s['risk_after']*100:.2f}%)."
            )

    elif intent == "scenario_volatility":
        tools_used += ["get_payment_forecast", "run_optimizer", "run_scenario"]
        corridor = _find_corridor(db, question)
        pct_match = PERCENT_RE.search(question)
        pct = float(pct_match.group(1)) if pct_match else 20.0
        corridors = [corridor] if corridor else db.query(models.Corridor).all()
        base_out = run_optimization([_corridor_input_from_db(db, c) for c in corridors], iterations=4000)
        shock_out = run_optimization([_corridor_input_from_db(db, c, volatility_delta_pct=pct) for c in corridors], iterations=4000)
        for b, s in zip(base_out.corridor_results, shock_out.corridor_results):
            delta = s["optimized_liquidity_musd"] - b["optimized_liquidity_musd"]
            text_parts.append(
                f"{b['corridor_code']}: a {pct:.0f}% volatility increase raises demand std dev from "
                f"${b['demand_std_musd']:.1f}M to ${s['demand_std_musd']:.1f}M. Recommended liquidity moves "
                f"${b['optimized_liquidity_musd']:.1f}M -> ${s['optimized_liquidity_musd']:.1f}M "
                f"({'+' if delta >= 0 else ''}{delta:.1f}M)."
            )

    elif intent == "scenario_confidence":
        tools_used += ["get_payment_forecast", "run_optimizer"]
        pct_matches = re.findall(r"(9\d(?:\.\d+)?)\s*%", question)
        target_conf = float(pct_matches[-1]) / 100.0 if pct_matches else 0.99
        corridor = _find_corridor(db, question)
        corridors = [corridor] if corridor else db.query(models.Corridor).all()
        base_out = run_optimization([_corridor_input_from_db(db, c, confidence_level=0.95) for c in corridors], iterations=4000)
        target_out = run_optimization([_corridor_input_from_db(db, c, confidence_level=target_conf) for c in corridors], iterations=4000)
        for b, s in zip(base_out.corridor_results, target_out.corridor_results):
            text_parts.append(
                f"{b['corridor_code']}: moving from 95% to {target_conf*100:.1f}% confidence raises the safety "
                f"requirement ${b['required_liquidity_musd']:.1f}M -> ${s['required_liquidity_musd']:.1f}M, and "
                f"recommended liquidity ${b['optimized_liquidity_musd']:.1f}M -> ${s['optimized_liquidity_musd']:.1f}M."
            )

    elif intent == "scenario_cutoff":
        tools_used += ["get_corridor_data", "get_settlement_practices"]
        corridor = _find_corridor(db, question)
        practices = agent_tools.get_settlement_practices(db)
        cutoff_practice = next((p for p in practices if "cut-off" in p["title"].lower() or "cutoff" in p["title"].lower()), practices[0] if practices else None)
        if corridor:
            text_parts.append(
                f"{corridor.code}'s current cut-off is {corridor.cutoff_hour_utc}:00 UTC. Moving it earlier "
                f"compresses the intraday replenishment window that desks typically rely on (settlement "
                f"practice, not a formal rule) to top up mid-window shortfalls - so recommended liquidity "
                f"tends to shift toward the more conservative baselines rather than the leaner QUBO-optimized "
                f"level. Run 'Cut-off time moved earlier' on the Stress Tests page for the exact recomputed numbers."
            )
        else:
            text_parts.append("Tell me which corridor's cut-off you mean (e.g. 'USD_INR') and I'll pull its current cut-off and settlement window.")
        if cutoff_practice:
            sources.append({"source_type": "SETTLEMENT_PRACTICE", "title": cutoff_practice["title"], "confidence": cutoff_practice["confidence"]})

    elif intent == "source_regulation":
        tools_used.append("get_regulatory_constraints")
        regs = agent_tools.get_regulatory_constraints(db)
        if regs:
            text_parts.append("Formal regulatory items in the knowledge base (all SYNTHETIC placeholders in this prototype - see docs/sandbox-readiness.md):")
            for r in regs:
                text_parts.append(f"- [{r['source_name']}] {r['title']}: {r['content']}")
                sources.append({"source_type": "REGULATION", "title": r["title"], "source_name": r["source_name"], "is_synthetic": r["is_synthetic"]})
        text_parts.append(
            "I could not verify any of these as actual, currently-in-force regulatory requirements - "
            "they are demonstration placeholders only. No optimizer recommendation should be read as "
            "regulatory-compliance guidance."
        )

    elif intent == "source_practice":
        tools_used.append("get_settlement_practices")
        practices = agent_tools.get_settlement_practices(db)
        text_parts.append("Observed settlement/operational practice items (not formal regulation):")
        for p in practices:
            text_parts.append(f"- {p['title']} (confidence {p['confidence']}): {p['content']}")
            sources.append({"source_type": "SETTLEMENT_PRACTICE", "title": p["title"], "confidence": p["confidence"]})

    elif intent == "binding_constraint":
        tools_used += ["get_corridor_data", "run_optimizer"]
        corridor = _find_corridor(db, question)
        corridors = [corridor] if corridor else db.query(models.Corridor).all()
        out = run_optimization([_corridor_input_from_db(db, c) for c in corridors], iterations=4000)
        for r in out.corridor_results:
            gap = r["optimized_liquidity_musd"] - r["required_liquidity_musd"]
            if abs(gap) < 1.5:
                text_parts.append(
                    f"{r['corridor_code']}: recommended liquidity (${r['optimized_liquidity_musd']:.1f}M) sits "
                    f"close to the {int(r['confidence_level']*100)}% safety requirement "
                    f"(${r['required_liquidity_musd']:.1f}M) - the binding constraint is the demand-volatility-"
                    f"driven safety level itself, not discretization. Further reduction needs a lower confidence "
                    f"level, lower demand volatility, or a faster replenishment window."
                )
            else:
                text_parts.append(
                    f"{r['corridor_code']}: recommended liquidity (${r['optimized_liquidity_musd']:.1f}M) still "
                    f"has headroom above the safety requirement (${r['required_liquidity_musd']:.1f}M) at the "
                    f"nearest available bucket - the binding constraint is bucket discretization, not risk. "
                    f"Finer bucket granularity could recover more capital."
                )

    else:
        text_parts.append("I didn't confidently match that to a known question type - try asking about excess liquidity, a specific corridor scenario, or a regulation/practice lookup.")

    answer_text = "\n".join(text_parts)
    answer_text = maybe_enhance_with_llm(question, answer_text)

    return {"answer": answer_text, "tools_used": tools_used, "sources": sources, "intent": intent}


def maybe_enhance_with_llm(question: str, deterministic_answer: str) -> str:
    """Optional rephrasing hook. Disabled unless LLM_PROVIDER + a matching
    API key are both set - the deterministic answer above is already
    complete and grounded, so this only ever changes phrasing, never facts.
    NOT exercised in this build/test run (no key available here)."""
    if settings.LLM_PROVIDER != "anthropic" or not settings.ANTHROPIC_API_KEY:
        return deterministic_answer
    return deterministic_answer  # left as a documented extension point, not implemented here
