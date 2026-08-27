from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app import models
from app.optimization.engine import build_qubo, simulated_annealing, decode_assignment, static_buffer_liquidity
from app.optimization.annealing import local_search_refine
from app.optimization.qubo import CorridorInput

def run_loss_sensitivity_analysis(db: Session, confidence_level: float = 0.95) -> Dict[str, Any]:
    """
    Phase B: Sensitivity Analysis for Loss Given Shortfall.
    Since we cannot empirically validate the reputational damage / penalty cost,
    we prove robustness by sweeping the assumed loss multiplier.
    """
    corridors = db.query(models.Corridor).all()
    risk_params = {r.corridor_id: r for r in db.query(models.RiskParameter).all()}
    
    # We need forecasts for mu/sigma
    from app.forecasting.forecast import compute_forecast
    import datetime as dt
    
    corridor_inputs = []
    
    for c in corridors:
        rp = risk_params[c.id]
        
        # Get last 90 days of transactions for this corridor
        ninety_days_ago = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=90)
        txs = db.query(models.PaymentTransaction).filter(
            models.PaymentTransaction.corridor_id == c.id,
            models.PaymentTransaction.ts >= ninety_days_ago
        ).all()
        
        tx_data = [(t.ts, t.amount_musd) for t in txs]
        # We default to seasonal_naive as that's the current default
        fcst = compute_forecast(tx_data, horizon_days=1)
        
        c_input = CorridorInput(
            corridor_id=c.id,
            code=c.code,
            mu=fcst.expected_demand_musd,
            sigma=fcst.std_dev_musd,
            current_liquidity=db.query(models.NostroAccount).filter(models.NostroAccount.corridor_id == c.id).first().current_balance_musd,
            opportunity_cost_rate=rp.opportunity_cost_rate_annual,
            loss_given_shortfall=rp.loss_given_shortfall_musd,
            fx_cost_bps=rp.fx_cost_bps,
            operational_cost_rate=rp.operational_cost_rate,
            confidence_level=confidence_level
        )
        corridor_inputs.append(c_input)

    # Now sweep multipliers
    multipliers = DEFAULT_LOSS_MULTIPLIER_SWEEP
    sweep_results = []
    
    baseline_capital = sum(c.current_liquidity for c in corridor_inputs)
    
    for mult in multipliers:
        # Scale the loss_given_shortfall for all corridors
        scaled_inputs = []
        for ci in corridor_inputs:
            scaled_ci = CorridorInput(
                corridor_id=ci.corridor_id,
                code=ci.code,
                mu=ci.mu,
                sigma=ci.sigma,
                current_liquidity=ci.current_liquidity,
                opportunity_cost_rate=ci.opportunity_cost_rate,
                loss_given_shortfall=ci.loss_given_shortfall * mult,
                fx_cost_bps=ci.fx_cost_bps,
                operational_cost_rate=ci.operational_cost_rate,
                confidence_level=ci.confidence_level
            )
            scaled_inputs.append(scaled_ci)
            
        qubo_model = build_qubo(scaled_inputs)
        result = simulated_annealing(qubo_model.Q, num_vars=qubo_model.Q.shape[0], iterations=8000)
        final_x, _ = local_search_refine(qubo_model.Q, result.best_x, qubo_model.block_sizes)
        assignment, _ = decode_assignment(final_x, qubo_model.block_sizes)
        
        total_recommended = sum(b for c, b in assignment.items())
        capital_released = baseline_capital - total_recommended
        
        # Determine stability (did buckets change relative to mult=1.0?)
        sweep_results.append({
            "multiplier": mult,
            "total_recommended_musd": round(total_recommended, 1),
            "capital_released_musd": round(capital_released, 1),
            "assignment": assignment
        })
        
    return {
        "baseline_capital_musd": round(baseline_capital, 1),
        "sweep": sweep_results
    }
