from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.api.deps import get_current_user
from app.schemas import ScenarioRunRequest
from app.optimization.engine import run_optimization
from app.services.optimization_service import corridor_inputs_from_db, persist_optimization_run, run_to_response
from app import models

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


@router.post("/run")
def run_scenario(req: ScenarioRunRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    base_inputs = corridor_inputs_from_db(db, req.corridors, confidence_level=0.95)
    scenario_inputs = corridor_inputs_from_db(
        db, req.corridors, confidence_level=req.confidence_level,
        demand_delta_pct=req.demand_delta_pct, volatility_delta_pct=req.volatility_delta_pct,
    )

    base_outcome = run_optimization(base_inputs, seed=settings.RANDOM_SEED)
    scenario_outcome = run_optimization(scenario_inputs, seed=settings.RANDOM_SEED)

    scenario_run = persist_optimization_run(
        db, scenario_outcome,
        params={"corridors": req.corridors, "confidence_level": req.confidence_level,
                "demand_delta_pct": req.demand_delta_pct, "volatility_delta_pct": req.volatility_delta_pct,
                "cutoff_delta_hours": req.cutoff_delta_hours},
        run_type="scenario", solver="simulated_annealing", seed=settings.RANDOM_SEED, actor=user.email,
    )

    scenario_record = models.ScenarioRun(
        name=req.label,
        overrides_json={"demand_delta_pct": req.demand_delta_pct, "volatility_delta_pct": req.volatility_delta_pct,
                         "confidence_level": req.confidence_level, "cutoff_delta_hours": req.cutoff_delta_hours},
        result_run_id=scenario_run.id,
    )
    db.add(scenario_record)
    db.commit()

    comparison = []
    for b, s in zip(base_outcome.corridor_results, scenario_outcome.corridor_results):
        comparison.append({
            "corridor_code": b["corridor_code"],
            "before_optimized_musd": b["optimized_liquidity_musd"],
            "after_optimized_musd": s["optimized_liquidity_musd"],
            "delta_musd": round(s["optimized_liquidity_musd"] - b["optimized_liquidity_musd"], 2),
            "risk_before": b["risk_after"], "risk_after": s["risk_after"],
        })

    return {
        "label": req.label,
        "overrides": scenario_record.overrides_json,
        "scenario_run_id": scenario_run.id,
        "comparison": comparison,
        "aggregate_before_musd": base_outcome.aggregate["total_optimized_liquidity_musd"],
        "aggregate_after_musd": scenario_outcome.aggregate["total_optimized_liquidity_musd"],
    }
