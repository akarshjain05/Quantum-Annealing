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
from app.services.optimization_service import corridor_inputs_from_db, persist_optimization_run, run_to_response, _latest_audit_hash
from app.optimization.engine import run_optimization, OptimizationOutcome
from app.audit.chain import compute_hash, GENESIS_HASH
from app import models

router = APIRouter(prefix="/api/optimization", tags=["optimization"])


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
