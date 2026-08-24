import json
from pathlib import Path
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.forecasting.forecast import compute_forecast, time_of_day_profile
from app import models

router = APIRouter(prefix="/api", tags=["core-data"])


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), user=Depends(get_current_user)):
    accounts = db.query(models.NostroAccount).all()
    corridors = db.query(models.Corridor).all()
    total_liquidity = sum(a.current_balance_musd for a in accounts)
    by_currency = {}
    for a in accounts:
        by_currency[a.currency] = by_currency.get(a.currency, 0.0) + a.current_balance_musd

    latest_run = db.query(models.OptimizationRun).order_by(models.OptimizationRun.id.desc()).first()
    if latest_run and latest_run.results:
        total_recommended = sum(r.optimized_liquidity_musd for r in latest_run.results)
        capital_released_potential = sum(r.capital_released_musd for r in latest_run.results)
    else:
        total_recommended = total_liquidity
        capital_released_potential = 0.0

    return {
        "organization": "Demo Global Bank",
        "synthetic_data_notice": "Synthetic demonstration data - not production financial data.",
        "total_nostro_liquidity_musd": round(total_liquidity, 2),
        "num_corridors": len(corridors),
        "num_nostro_accounts": len(accounts),
        "liquidity_by_currency_musd": {k: round(v, 2) for k, v in by_currency.items()},
        "capital_released_potential_musd": round(capital_released_potential, 2),
        "total_recommended_musd": round(total_recommended, 2),
        "latest_optimization_run": {
            "id": latest_run.id, "created_at": str(latest_run.created_at),
            "capital_released_musd": round(capital_released_potential, 2),
        } if latest_run else None,
    }

@router.get("/dashboard/savings")
def get_savings_metrics(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Calculate annual savings opportunity."""
    accounts = db.query(models.NostroAccount).all()
    total_liquidity = sum(a.current_balance_musd for a in accounts)
    
    latest_run = db.query(models.OptimizationRun).order_by(models.OptimizationRun.id.desc()).first()
    if latest_run and latest_run.results:
        capital_released = sum(r.capital_released_musd for r in latest_run.results)
    else:
        capital_released = 0.0
    
    # Ideally from settings DB, hardcoded default for now
    opportunity_cost_rate = 0.05
    
    return {
        "totalNostroLiquidity": total_liquidity,
        "capitalReleased": capital_released,
        "opportunityCostRate": opportunity_cost_rate,
        "annualSavingsOpportunity": capital_released * opportunity_cost_rate,
        "efficiencyImprovement": (capital_released / total_liquidity * 100) if total_liquidity > 0 else 0,
        "operatingMode": "shadow"
    }


@router.get("/corridors")
def list_corridors(db: Session = Depends(get_db), user=Depends(get_current_user)):
    out = []
    latest_run = db.query(models.OptimizationRun).order_by(models.OptimizationRun.id.desc()).first()
    rec_map = {}
    if latest_run and latest_run.results:
        rec_map = {r.corridor_code: r.optimized_liquidity_musd for r in latest_run.results}

    for c in db.query(models.Corridor).all():
        accounts = db.query(models.NostroAccount).filter(models.NostroAccount.corridor_id == c.id).all()
        current_balance = sum(a.current_balance_musd for a in accounts)
        
        recommendedMin = rec_map.get(c.code, current_balance)
        
        efficiency_pct = (recommendedMin / current_balance) * 100 if current_balance > 0 else 100
        if efficiency_pct > 100:
            efficiency_pct = 100.0
            
        status = "Excess Capital" if efficiency_pct < 90 else "Optimal"

        out.append({
            "id": c.id,
            "code": c.code,
            "name": c.name,
            "source_currency": c.source_currency,
            "dest_currency": c.dest_currency,
            "settlement_window_utc": [c.settlement_window_start_hour_utc, c.settlement_window_end_hour_utc],
            "cutoff_hour_utc": c.cutoff_hour_utc,
            "current_balance_musd": round(current_balance, 2),
            "recommended_musd": round(recommendedMin, 2),
            "num_nostro_accounts": len(accounts),
            "efficiency_pct": round(efficiency_pct, 1),
            "status": status
        })
    return out


@router.get("/nostro")
def list_nostro_accounts(db: Session = Depends(get_db), user=Depends(get_current_user)):
    out = []
    for a in db.query(models.NostroAccount).all():
        corridor = db.get(models.Corridor, a.corridor_id)
        out.append({
            "id": a.id, "account_name": a.account_name, "institution_name": a.institution_name,
            "currency": a.currency, "current_balance_musd": a.current_balance_musd,
            "corridor_code": corridor.code if corridor else None,
        })
    return out


@router.get("/forecasts/{corridor_code}")
def get_forecast(corridor_code: str, horizon_days: int = 7, db: Session = Depends(get_db), user=Depends(get_current_user)):
    corridor = db.query(models.Corridor).filter(models.Corridor.code == corridor_code).first()
    if not corridor:
        return {"error": "corridor not found"}
    txns = db.query(models.PaymentTransaction).filter(models.PaymentTransaction.corridor_id == corridor.id).all()
    pairs = [(t.ts, t.amount_musd) for t in txns]
    fc = compute_forecast(pairs, horizon_days=horizon_days)
    profile = time_of_day_profile(pairs)
    return {
        "corridor_code": corridor_code,
        "expected_demand_musd": fc.expected_demand_musd,
        "std_dev_musd": fc.std_dev_musd,
        "ci_low_musd": fc.ci_low_musd,
        "ci_high_musd": fc.ci_high_musd,
        "model_used": fc.model_used,
        "horizon_days": horizon_days,
        "time_of_day_profile": profile,
        "transaction_count_90d": len(txns),
    }
