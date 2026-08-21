from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.audit.chain import verify_chain
from app import models

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("/log")
def audit_log(limit: int = 50, db: Session = Depends(get_db), user=Depends(get_current_user)):
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
def list_approvals(limit: int = 50, db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.query(models.HumanApproval).order_by(models.HumanApproval.id.desc()).limit(limit).all()
    return [{
        "id": r.id, "run_id": r.run_id, "decision": r.decision, "reason": r.reason,
        "created_at": str(r.created_at),
    } for r in rows]
