import uuid
from typing import Optional, List
from fastapi import Query, APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.api.deps import get_current_user
from app.optimization.engine import run_optimization
from app.optimization.qubo import shortfall_probability
from app.services.optimization_service import corridor_inputs_from_db
from app import models

router = APIRouter(prefix="/api/stress-tests", tags=["stress-tests"])


class StressTestRequest(BaseModel):
    corridors: Optional[List[str]] = None


# name, demand_delta_pct, volatility_delta_pct, confidence_level_override(or None)
SCENARIOS = [
    ("Demand +10%", 10.0, 0.0, None),
    ("Demand +25%", 25.0, 0.0, None),
    ("Demand +50%", 50.0, 0.0, None),
    ("Volatility +20%", 0.0, 20.0, None),
    ("Volatility +50%", 0.0, 50.0, None),
    ("Combined demand +25% and volatility +30%", 25.0, 30.0, None),
    ("Confidence raised to 99.9%", 0.0, 0.0, 0.999),
    ("Major currency holiday (demand +40%, volatility +35%)", 40.0, 35.0, None),
]


@router.post("/run")
def run_stress_tests(req: StressTestRequest = StressTestRequest(), db: Session = Depends(get_db), user=Depends(get_current_user)):
    corridors = req.corridors
    batch_id = str(uuid.uuid4())[:8]
    baseline_inputs = corridor_inputs_from_db(db, corridors, confidence_level=0.95)
    baseline = run_optimization(baseline_inputs, seed=settings.RANDOM_SEED)
    baseline_total = baseline.aggregate["total_optimized_liquidity_musd"]

    results = []
    for name, demand_pct, vol_pct, conf_override in SCENARIOS:
        conf = conf_override if conf_override is not None else 0.95
        inputs = corridor_inputs_from_db(
            db, corridors, confidence_level=conf, demand_delta_pct=demand_pct, volatility_delta_pct=vol_pct,
        )
        outcome = run_optimization(inputs, seed=settings.RANDOM_SEED)
        required_total = sum(outcome.qubo.requirements.values())
        recommended_total = outcome.aggregate["total_optimized_liquidity_musd"]
        coverage = recommended_total / required_total if required_total > 0 else 1.0

        risks = []
        for c in inputs:
            k = outcome.assignment[outcome.qubo.corridor_index[c.corridor_id]]
            L = outcome.qubo.buckets[k]
            risks.append(shortfall_probability(c.mu, c.sigma, L))
        avg_shortfall_prob = sum(risks) / len(risks) if risks else 0.0

        row = models.StressTestResult(
            batch_id=batch_id, scenario_name=name,
            required_liquidity_musd=round(required_total, 2),
            recommended_liquidity_musd=round(recommended_total, 2),
            capital_released_musd=round(baseline_total - recommended_total, 2),
            capital_required_musd=round(max(0.0, recommended_total - baseline_total), 2),
            settlement_coverage=round(coverage, 4),
            shortfall_probability=round(avg_shortfall_prob, 4),
            risk_score=round(avg_shortfall_prob * required_total, 2),
        )
        db.add(row)
        results.append({
            "scenario_name": name, "demand_delta_pct": demand_pct, "volatility_delta_pct": vol_pct,
            "confidence_level": conf,
            "required_liquidity_musd": row.required_liquidity_musd,
            "recommended_liquidity_musd": row.recommended_liquidity_musd,
            "baseline_liquidity_musd": round(baseline_total, 2),
            "delta_vs_baseline_musd": round(recommended_total - baseline_total, 2),
            "settlement_coverage": row.settlement_coverage,
            "shortfall_probability": row.shortfall_probability,
            "risk_score": row.risk_score,
        })

    db.commit()
    return {"batch_id": batch_id, "baseline_liquidity_musd": round(baseline_total, 2), "scenarios": results}


@router.get("/history")
def stress_test_history(limit: int = Query(50, le=200), db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.query(models.StressTestResult).order_by(models.StressTestResult.id.desc()).limit(limit).all()
    return [{
        "batch_id": r.batch_id, "scenario_name": r.scenario_name,
        "required_liquidity_musd": r.required_liquidity_musd,
        "recommended_liquidity_musd": r.recommended_liquidity_musd,
        "capital_released_musd": r.capital_released_musd,
        "settlement_coverage": r.settlement_coverage,
        "created_at": str(r.created_at),
    } for r in rows]
