"""
Agent tools. Each function is a discrete, independently callable capability
the orchestrator can invoke based on detected intent - mirroring the
tool-use loop pattern (plan -> call tool -> observe -> respond) rather than
a single free-text LLM completion. No tool here executes a financial
transaction; every tool is read-only or a recommendation-producing
computation (spec §27, agent safety).
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app import models
from app.optimization.qubo import CorridorInput
from app.optimization.engine import run_optimization
from app.forecasting.forecast import compute_forecast


def get_liquidity_snapshot(db: Session) -> Dict[str, Any]:
    accounts = db.query(models.NostroAccount).all()
    by_currency: Dict[str, float] = {}
    for a in accounts:
        by_currency[a.currency] = by_currency.get(a.currency, 0.0) + a.current_balance_musd
    total = sum(by_currency.values())
    return {"total_liquidity_musd": round(total, 2), "by_currency_musd": {k: round(v, 2) for k, v in by_currency.items()}}


def get_corridor_data(db: Session, corridor_code: Optional[str] = None) -> List[Dict[str, Any]]:
    q = db.query(models.Corridor)
    if corridor_code:
        q = q.filter(models.Corridor.code == corridor_code)
    out = []
    for c in q.all():
        accounts = db.query(models.NostroAccount).filter(models.NostroAccount.corridor_id == c.id).all()
        balance = sum(a.current_balance_musd for a in accounts)
        out.append({
            "corridor_id": c.id, "code": c.code, "name": c.name,
            "current_balance_musd": round(balance, 2),
            "cutoff_hour_utc": c.cutoff_hour_utc,
            "settlement_window_utc": [c.settlement_window_start_hour_utc, c.settlement_window_end_hour_utc],
        })
    return out


def get_payment_forecast(db: Session, corridor_id: int, horizon_days: int = 7) -> Dict[str, Any]:
    txns = db.query(models.PaymentTransaction).filter(models.PaymentTransaction.corridor_id == corridor_id).all()
    pairs = [(t.ts, t.amount_musd) for t in txns]
    fc = compute_forecast(pairs, horizon_days=horizon_days)
    return {
        "expected_demand_musd": fc.expected_demand_musd,
        "std_dev_musd": fc.std_dev_musd,
        "ci_low_musd": fc.ci_low_musd,
        "ci_high_musd": fc.ci_high_musd,
        "model_used": fc.model_used,
    }


def get_regulatory_constraints(db: Session, corridor_id: Optional[int] = None) -> List[Dict[str, Any]]:
    q = db.query(models.KnowledgeItem).filter(models.KnowledgeItem.source_type == "REGULATION")
    return [_knowledge_to_dict(k) for k in q.all()]


def get_settlement_practices(db: Session, corridor_id: Optional[int] = None) -> List[Dict[str, Any]]:
    q = db.query(models.KnowledgeItem).filter(models.KnowledgeItem.source_type == "SETTLEMENT_PRACTICE")
    return [_knowledge_to_dict(k) for k in q.all()]


def get_model_assumptions(db: Session) -> List[Dict[str, Any]]:
    q = db.query(models.KnowledgeItem).filter(models.KnowledgeItem.source_type == "MODEL_ASSUMPTION")
    return [_knowledge_to_dict(k) for k in q.all()]


def _knowledge_to_dict(k: models.KnowledgeItem) -> Dict[str, Any]:
    return {
        "source_type": k.source_type, "title": k.title, "content": k.content,
        "source_name": k.source_name, "jurisdiction": k.jurisdiction,
        "confidence": k.confidence, "citation": k.citation, "is_synthetic": k.is_synthetic,
    }


def get_audit_history(db: Session, limit: int = 10) -> List[Dict[str, Any]]:
    logs = db.query(models.AuditLog).order_by(desc(models.AuditLog.id)).limit(limit).all()
    return [{"event_type": l.event_type, "actor": l.actor, "created_at": str(l.created_at), "id": l.id} for l in logs]


def get_latest_run(db: Session) -> Optional[models.OptimizationRun]:
    return db.query(models.OptimizationRun).order_by(desc(models.OptimizationRun.id)).first()


def compare_optimization_runs(db: Session, run_id_a: int, run_id_b: int) -> Dict[str, Any]:
    ra = db.get(models.OptimizationRun, run_id_a)
    rb = db.get(models.OptimizationRun, run_id_b)
    if not ra or not rb:
        return {"error": "one or both run ids not found"}
    return {
        "run_a": {"id": ra.id, "final_energy": ra.final_energy, "created_at": str(ra.created_at)},
        "run_b": {"id": rb.id, "final_energy": rb.final_energy, "created_at": str(rb.created_at)},
    }
