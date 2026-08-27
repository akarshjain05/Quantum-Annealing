from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.api.deps import get_current_user
from app.schemas import (
    OptimizationRunRequest, ApprovalRequest, OptimizationConfigRequest,
    SubmitApprovalRequest, ApprovalDecisionRequest
)
from app.optimization.qubo import CorridorInput
from app.optimization.engine import run_optimization, OptimizationOutcome
from app.audit.chain import compute_hash, GENESIS_HASH
from app import models

router = APIRouter(prefix="/api/optimization", tags=["optimization"])


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
    last = db.query(models.AuditLog).order_by(models.AuditLog.id.desc()).first()
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


@router.post("/run")
def run_optimization_endpoint(req: OptimizationRunRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    seed = req.random_seed if req.random_seed is not None else settings.RANDOM_SEED
    inputs = corridor_inputs_from_db(
        db, req.corridors, req.confidence_level,
        demand_delta_pct=req.demand_delta_pct, volatility_delta_pct=req.volatility_delta_pct,
    )
    outcome = run_optimization(
        inputs, iterations=req.iterations, initial_temperature=req.initial_temperature,
        cooling_rate=req.cooling_rate, seed=seed, onehot_penalty=req.onehot_penalty, weights=req.weights,
        global_liquidity_cap_musd=req.global_liquidity_cap_musd,
    )
    run = persist_optimization_run(
        db, outcome, params=req.model_dump(), run_type=req.run_type, solver=req.solver, seed=seed,
        actor=user.email,
    )
    return run_to_response(run, outcome)


@router.get("/runs")
def list_runs(limit: int = 20, db: Session = Depends(get_db), user=Depends(get_current_user)):
    runs = db.query(models.OptimizationRun).order_by(models.OptimizationRun.id.desc()).limit(limit).all()
    return [{
        "run_id": r.id, "created_at": str(r.created_at), "run_type": r.run_type, "status": r.status,
        "final_energy": r.final_energy, "capital_released_musd": round(sum(x.capital_released_musd for x in r.results), 2),
    } for r in runs]


@router.get("/runs/{run_id}")
def get_run(run_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    run = db.get(models.OptimizationRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run_to_response(run)


@router.post("/approve")
def approve_run(req: ApprovalRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    run = db.get(models.OptimizationRun, req.run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if req.decision not in ("APPROVED", "REJECTED", "RECALCULATION_REQUESTED"):
        raise HTTPException(status_code=400, detail="Invalid decision")
    approval = models.HumanApproval(run_id=run.id, decision=req.decision, reason=req.reason, user_id=user.id)
    db.add(approval)

    prev_hash = _latest_audit_hash(db)
    payload = {"run_id": run.id, "decision": req.decision, "reason": req.reason, "user": user.email}
    audit = models.AuditLog(event_type="HUMAN_APPROVAL", actor=user.email, payload_json=payload, prev_hash=prev_hash)
    audit.self_hash = compute_hash(prev_hash, payload)
    db.add(audit)
    db.commit()
    return {"status": "recorded", "decision": req.decision, "note": "Decision-support prototype. No live financial transaction is executed."}

@router.post("/configure")
def configure_optimization(request: OptimizationConfigRequest):
    """Convert risk appetite to technical parameters."""
    RISK_MAP = {
        "very_conservative": {"confidence": 0.99, "safety_buffer": 0.10},
        "conservative": {"confidence": 0.95, "safety_buffer": 0.05},
        "balanced": {"confidence": 0.90, "safety_buffer": 0.03},
        "efficient": {"confidence": 0.85, "safety_buffer": 0.02},
        "very_efficient": {"confidence": 0.80, "safety_buffer": 0.01},
    }
    params = RISK_MAP.get(request.risk_appetite, RISK_MAP["conservative"])
    return {
        "riskAppetite": request.risk_appetite,
        "corridorsIncluded": request.corridors,
        "technicalParams": {
            "confidence_level": params["confidence"],
            "safety_buffer": params["safety_buffer"],
            "iterations": request.iterations or 8000,
            "initial_temperature": request.initial_temperature or 1000,
            "cooling_rate": request.cooling_rate or 0.995,
        }
    }

@router.post("/runs/{run_id}/submit-for-approval")
def submit_for_approval(run_id: str, request: SubmitApprovalRequest, db: Session = Depends(get_db)):
    """Submit optimization run for human approval."""
    prev_hash = _latest_audit_hash(db)
    payload = {
        "run_id": run_id,
        "submitted_by": request.submitted_by,
        "notes": request.notes,
        "confirmations": request.confirmations
    }
    audit = models.AuditLog(
        event_type="approval_submitted",
        actor=request.submitted_by,
        payload_json=payload,
        prev_hash=prev_hash
    )
    audit.self_hash = compute_hash(prev_hash, payload)
    db.add(audit)
    db.commit()
    
    return {
        "status": "pending_approval",
        "runId": run_id,
        "submittedAt": datetime.utcnow().isoformat(),
        "auditHash": audit.self_hash
    }

@router.post("/runs/{run_id}/decide")
def decide_approval_new(run_id: str, request: ApprovalDecisionRequest, db: Session = Depends(get_db)):
    """Record approval decision."""
    prev_hash = _latest_audit_hash(db)
    payload = {
        "run_id": run_id,
        "decision": request.decision,
        "decided_by": request.decided_by,
        "notes": request.notes,
        "rejection_reason": request.rejection_reason
    }
    audit = models.AuditLog(
        event_type="approval_decided",
        actor=request.decided_by,
        payload_json=payload,
        prev_hash=prev_hash
    )
    audit.self_hash = compute_hash(prev_hash, payload)
    db.add(audit)
    db.commit()
    
    return {
        "status": request.decision,
        "runId": run_id,
        "decidedAt": datetime.utcnow().isoformat(),
        "auditHash": audit.self_hash
    }

@router.get("/approvals/pending")
def list_pending_approvals(db: Session = Depends(get_db)):
    """List runs waiting for human approval."""
    # We will simulate this by checking recent runs that don't have a decision yet.
    # In a real app we would have an "Approval" table or a status field like "PENDING_APPROVAL".
    # Here, we'll return the latest 3 runs to mock the queue for demo purposes.
    runs = db.query(models.OptimizationRun).order_by(models.OptimizationRun.id.desc()).limit(3).all()
    
    pending = []
    for r in runs:
        # Check if already decided in audit log or human_approvals table
        has_decision = db.query(models.HumanApproval).filter(models.HumanApproval.run_id == r.id).first()
        if not has_decision:
            capital_released = sum(res.capital_released_musd for res in r.results) if r.results else 0
            pending.append({
                "runId": str(r.id),
                "runNumber": r.id,
                "submittedAt": r.created_at.isoformat() + "Z",
                "submittedBy": "system_auto",
                "summary": {
                    "corridorCount": len(r.results) if r.results else 0,
                    "capitalRelease": capital_released * 1_000_000,
                    "annualSavings": capital_released * 0.05 * 1_000_000,
                    "allSafetyMet": r.status != "INVALID"
                },
                "notes": "Generated by daily scheduled optimization task."
            })
            
    return pending

from pydantic import BaseModel
class OptimizationBenchmarkRequest(BaseModel):
    corridors: List[str]
    confidence_level: float = 0.95

@router.get("/quantum/status")
async def quantum_status():
    from app.optimization.quantum_solver import QuantumBenchmark
    benchmark = QuantumBenchmark()
    return benchmark.get_solver_status()

@router.post("/quantum/benchmark")
def run_benchmark_endpoint(request: OptimizationBenchmarkRequest, db: Session = Depends(get_db)):
    from app.optimization.engine import build_qubo
    from app.optimization.quantum_solver import QuantumBenchmark, QUBOProblem
    
    inputs = corridor_inputs_from_db(db, request.corridors, request.confidence_level)
    qubo = build_qubo(inputs)
    problem = QUBOProblem(qubo.Q, [f"x_{i}" for i in range(qubo.num_vars)])
    benchmark = QuantumBenchmark(seed=42)
    result = benchmark.run_benchmark(problem)
    return benchmark.generate_chart_data(result)


@router.get("/loss-sensitivity")
def get_loss_sensitivity(db: Session = Depends(get_db)):
    """
    Phase B: Sensitivity analysis for loss_given_shortfall
    """
    from app.optimization.sensitivity import run_loss_sensitivity_analysis
    return run_loss_sensitivity_analysis(db)
