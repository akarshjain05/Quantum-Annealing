from fastapi import Query, APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.audit.chain import verify_chain
from app import models

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("/log")
def audit_log(limit: int = Query(50, le=200), db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.query(models.AuditLog).order_by(models.AuditLog.id.desc()).limit(limit).all()
    return [{
        "id": r.id, "event_type": r.event_type, "actor": r.actor, "created_at": str(r.created_at),
        "payload": r.payload_json, "prev_hash": r.prev_hash, "self_hash": r.self_hash,
    } for r in rows]


@router.get("/verify")
def verify_audit_chain(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.query(models.AuditLog).order_by(models.AuditLog.id.asc()).all()
    entries = [{"id": r.id, "prev_hash": r.prev_hash, "self_hash": r.self_hash, "payload": r.payload_json} for r in rows]
    return verify_chain(entries)


@router.get("/approvals")
def list_approvals(limit: int = Query(50, le=200), db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.query(models.HumanApproval).order_by(models.HumanApproval.id.desc()).limit(limit).all()
    return [{
        "id": r.id, "run_id": r.run_id, "decision": r.decision, "reason": r.reason,
        "created_at": str(r.created_at),
    } for r in rows]

@router.get("/decision-rationale/{run_id}")
def decision_rationale(run_id: int, db: Session = Depends(get_db)):
    run = db.get(models.OptimizationRun, run_id)
    if not run:
        return {"error": "not found"}
    
    approval = db.query(models.HumanApproval).filter(models.HumanApproval.run_id == run_id).first()
    audit = db.query(models.AuditLog).filter(models.AuditLog.event_type == "HUMAN_APPROVAL", models.AuditLog.payload_json["run_id"] == run_id).first()
        
    capital_released = sum(r.capital_released_musd for r in run.results) if run.results else 0
    
    c_level = run.params_json.get("confidence_level", 0.95) if run.params_json else 0.95
    s_buffer = run.params_json.get("safety_buffer", 0.05) if run.params_json else 0.05
    
    example_code = "UNKNOWN"
    p95_demand = 0.0
    fx_reserve = 0.0
    corr_margin = 0.0
    min_req = 0.0
    cur_bal = 0.0
    excess = 0.0

    if run.results:
        res = run.results[0]
        c = db.get(models.Corridor, res.corridor_id)
        if c:
            example_code = c.code
            from app.forecasting.forecast import compute_forecast
            txns = db.query(models.PaymentTransaction).filter(models.PaymentTransaction.corridor_id == c.id).all()
            pairs = [(t.ts, t.amount_musd) for t in txns]
            fc = compute_forecast(pairs, horizon_days=7)
            
            p95_demand = fc.ci_high_musd * 1_000_000
            cur_bal = res.current_liquidity_musd * 1_000_000
            
            # Illustrative breakdown matching frontend Corridors.jsx
            safety_buffer_val = p95_demand * 0.05
            fx_reserve = p95_demand * 0.075
            corr_margin = p95_demand * 0.02
            
            min_req = p95_demand + safety_buffer_val + fx_reserve + corr_margin
            excess = max(0.0, cur_bal - min_req)
        
    return {
        "run_number": run_id,
        "capital_released": capital_released * 1_000_000,
        "status": approval.decision if approval else (audit.payload_json.get("decision") if audit else "UNKNOWN"),
        "decided_at": (approval.created_at if approval else (audit.created_at if audit else run.created_at)).isoformat() + "Z",
        "confidence_level": c_level * 100,
        "safety_buffer": s_buffer,
        "example_corridor": {
            "code": example_code,
            "p95_demand": p95_demand,
            "safety_buffer": p95_demand * s_buffer,
            "fx_reserve": fx_reserve,
            "correspondent_margin": corr_margin,
            "minimum_required": min_req,
            "current_balance": cur_bal,
            "excess": excess
        },
        "approver_notes": approval.reason if approval else (audit.payload_json.get("notes", audit.payload_json.get("reason", "")) if audit else ""),
        "approved_by": audit.actor if audit else "system",
        "hash": audit.self_hash if audit else "N/A",
        "previous_hash": audit.prev_hash if audit else "N/A",
        "timestamp": audit.created_at.isoformat() + "Z" if audit else ""
    }
