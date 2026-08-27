import datetime
from typing import List, Optional, Dict, Any
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models
from app.core.config import settings
from app.audit.chain import compute_hash, GENESIS_HASH
from app.optimization.qubo import CorridorInput
from app.optimization.engine import OptimizationOutcome

def corridor_inputs_from_db(
    db: Session, corridor_codes: Optional[List[str]], confidence_level: float,
    demand_delta_pct: float = 0.0, volatility_delta_pct: float = 0.0,
) -> List[CorridorInput]:
    q = db.query(models.Corridor)
    if corridor_codes:
        q = q.filter(models.Corridor.code.in_(corridor_codes))
    corridors = q.all()
    if not corridors:
        raise HTTPException(status_code=400, detail="No matching corridors found")

    inputs = []
    for c in corridors:
        from app.forecasting.forecast import compute_forecast
        txns = db.query(models.PaymentTransaction).filter(models.PaymentTransaction.corridor_id == c.id).all()
        pairs = [(t.ts, t.amount_musd) for t in txns]
        fc = compute_forecast(pairs, horizon_days=7)
        mu = fc.expected_demand_musd * (1 + demand_delta_pct / 100.0)
        sigma = max(fc.std_dev_musd * (1 + volatility_delta_pct / 100.0), 0.01)

        risk = db.query(models.RiskParameter).filter(models.RiskParameter.corridor_id == c.id).first()
        accounts = db.query(models.NostroAccount).filter(models.NostroAccount.corridor_id == c.id).all()
        current = sum(a.current_balance_musd for a in accounts)

        inputs.append(CorridorInput(
            corridor_id=c.id, code=c.code, mu=mu, sigma=sigma, current_liquidity=current,
            opportunity_cost_rate=risk.opportunity_cost_rate_annual if risk else 0.05,
            loss_given_shortfall=risk.loss_given_shortfall_musd if risk else 5.0,
            fx_cost_bps=risk.fx_cost_bps if risk else 8.0,
            operational_cost_rate=risk.operational_cost_rate if risk else 0.02,
            confidence_level=confidence_level,
            transactions=pairs,
        ))
    return inputs

def _latest_audit_hash(db: Session) -> str:
    last = db.query(models.AuditLog).order_by(models.AuditLog.id.desc()).with_for_update().first()
    return last.self_hash if last else GENESIS_HASH

def persist_optimization_run(
    db: Session, outcome: OptimizationOutcome, params: dict, run_type: str, solver: str,
    seed: int, actor: str = "system",
) -> models.OptimizationRun:
    prev_hash = _latest_audit_hash(db)
    run = models.OptimizationRun(
        run_type=run_type, solver=solver, params_json=params,
        status="INVALID" if any(v["severity"] == "high" for v in outcome.constraint_violations) else "COMPLETED",
        total_variables=outcome.qubo.num_vars, total_terms=outcome.qubo.num_nonzero(),
        initial_energy=outcome.initial_energy, final_energy=outcome.final_energy,
        runtime_ms=outcome.annealing_runtime_ms, random_seed=seed,
        model_version=settings.MODEL_VERSION, qubo_version=settings.QUBO_VERSION,
        forecast_version=settings.FORECAST_VERSION, knowledge_version=settings.KNOWLEDGE_VERSION,
        convergence_json=outcome.convergence_history,
        constraint_violations_json=outcome.constraint_violations,
        onehot_clean=outcome.onehot_clean,
        global_liquidity_cap_musd=params.get("global_liquidity_cap_musd"),
        prev_hash=prev_hash,
    )
    db.add(run)
    db.flush()

    for r in outcome.corridor_results:
        db.add(models.OptimizationResult(
            run_id=run.id, corridor_id=r["corridor_id"],
            current_liquidity_musd=r["current_liquidity_musd"],
            optimized_liquidity_musd=r["optimized_liquidity_musd"],
            capital_released_musd=r["capital_released_musd"],
            risk_before=r["risk_before"], risk_after=r["risk_after"],
            chosen_bucket_musd=r["optimized_liquidity_musd"],
            explanation_json=r["explanation"],
        ))
        for method, val in r["baselines"].items():
            db.add(models.OptimizationBaseline(run_id=run.id, corridor_id=r["corridor_id"], method=method, liquidity_musd=val))

    run_hash_payload = {"run_id": run.id, "final_energy": outcome.final_energy, "aggregate": outcome.aggregate}
    run.self_hash = compute_hash(prev_hash, run_hash_payload)

    audit = models.AuditLog(
        event_type="OPTIMIZATION_RUN", actor=actor,
        payload_json={"run_id": run.id, "run_type": run_type, "aggregate": outcome.aggregate},
        prev_hash=prev_hash,
    )
    audit.self_hash = compute_hash(prev_hash, audit.payload_json)
    db.add(audit)
    db.commit()
    db.refresh(run)
    return run

def run_to_response(run: models.OptimizationRun, outcome: Optional[OptimizationOutcome] = None) -> dict:
    results = run.results
    baselines_by_corridor = {}
    for b in run.baselines:
        baselines_by_corridor.setdefault(b.corridor_id, {})[b.method] = b.liquidity_musd

    corridor_results = []
    for r in results:
        corridor_results.append({
            "corridor_id": r.corridor_id,
            "current_liquidity_musd": r.current_liquidity_musd,
            "optimized_liquidity_musd": r.optimized_liquidity_musd,
            "capital_released_musd": r.capital_released_musd,
            "risk_before": r.risk_before, "risk_after": r.risk_after,
            "baselines": baselines_by_corridor.get(r.corridor_id, {}),
            "explanation": r.explanation_json,
        })

    total_current = sum(r.current_liquidity_musd for r in results)
    total_optimized = sum(r.optimized_liquidity_musd for r in results)

    return {
        "run_id": run.id, "created_at": str(run.created_at), "run_type": run.run_type,
        "solver": run.solver, "status": run.status,
        "qubo_variables": run.total_variables, "qubo_terms": run.total_terms,
        "initial_energy": run.initial_energy, "final_energy": run.final_energy,
        "runtime_ms": run.runtime_ms, "random_seed": run.random_seed,
        "model_version": run.model_version, "qubo_version": run.qubo_version,
        "current_liquidity_musd": round(total_current, 2),
        "optimized_liquidity_musd": round(total_optimized, 2),
        "capital_released_musd": round(total_current - total_optimized, 2),
        "global_liquidity_cap_musd": run.global_liquidity_cap_musd,
        "constraint_violations": run.constraint_violations_json,
        "onehot_clean": run.onehot_clean,
        "corridor_results": corridor_results,
        "convergence_history": run.convergence_json,
        "self_hash": run.self_hash, "prev_hash": run.prev_hash,
    }

