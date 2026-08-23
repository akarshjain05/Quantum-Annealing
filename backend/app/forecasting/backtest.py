import json
import datetime as dt
from collections import defaultdict
import numpy as np
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.forecasting.forecast import compute_forecast

def load_data():
    data_dir = Path(__file__).resolve().parents[3] / "data"
    if not data_dir.exists():
        data_dir = Path("/app/data")
        
    with open(data_dir / "transactions.json") as f:
        txs = json.load(f)
    
    with open(data_dir / "corridors.json") as f:
        corridors = json.load(f)
        
    return txs, corridors

def run_backtest_phase2(horizon_days: int = 1, confidence_level: float = 0.95):
    txs, corridors_data = load_data()
    
    corridor_txs = defaultdict(list)
    for tx in txs:
        ts = dt.datetime.fromisoformat(tx['timestamp'])
        corridor_txs[tx['corridor_code']].append((ts, tx['amount']))
        
    z_score = 1.96 if confidence_level == 0.95 else 1.645
    
    # We will test two methods: 'gaussian' and 'empirical'
    results = {
        'gaussian': {'breaches': 0, 'windows': 0},
        'empirical': {'breaches': 0, 'windows': 0}
    }
    
    for code, history in corridor_txs.items():
        history.sort(key=lambda x: x[0])
        if not history:
            continue
            
        min_date = history[0][0].date()
        max_date = history[-1][0].date()
        total_days = (max_date - min_date).days + 1
        
        if total_days <= horizon_days:
            continue
            
        # To compute empirical residuals, we need to track past predictions vs actuals
        # Since we are doing a rolling origin, we can simulate what the model would have predicted
        # at each point in the past to build the residual history.
        # For simplicity in this script, we will just use the naive error of previous days 
        # as a proxy for the residual distribution.
        
        for t_offset in range(1, total_days - horizon_days + 1):
            t = min_date + dt.timedelta(days=t_offset)
            
            hist_t = [(ts, amt) for ts, amt in history if ts.date() < t]
            if not hist_t:
                continue
                
            end_t = t + dt.timedelta(days=horizon_days)
            act_t = sum(amt for ts, amt in history if t <= ts.date() < end_t)
            
            hist_t_musd = [(ts, amt / 1e6) for ts, amt in hist_t]
            act_t_musd = act_t / 1e6
            
            fcst = compute_forecast(hist_t_musd, horizon_days=horizon_days, model_type="baseline")
            
            mu = fcst.expected_demand_musd
            sigma = fcst.std_dev_musd
            
            # 1. Gaussian Parametric
            ci_high_gaussian = mu + z_score * sigma
            if act_t_musd > ci_high_gaussian:
                results['gaussian']['breaches'] += 1
            results['gaussian']['windows'] += 1
            
            # 2. Empirical Historical Simulation
            # Build empirical residuals by testing every single day in hist_t 
            # against its own trailing history.
            residuals = []
            for past_t_offset in range(1, t_offset):
                past_t = min_date + dt.timedelta(days=past_t_offset)
                past_hist = [(ts, amt) for ts, amt in history if ts.date() < past_t]
                if not past_hist:
                    continue
                past_end = past_t + dt.timedelta(days=horizon_days)
                past_act = sum(amt for ts, amt in history if past_t <= ts.date() < past_end) / 1e6
                past_fcst = compute_forecast([(ts, amt/1e6) for ts, amt in past_hist], horizon_days=horizon_days, model_type="baseline")
                residuals.append(past_act - past_fcst.expected_demand_musd)
            
            # If we don't have residuals, fall back to gaussian for this step
            if residuals:
                # Instead of 60 threshold, we use what we have to see if it works
                emp_margin = float(np.quantile(residuals, confidence_level))
                ci_high_empirical = mu + max(0, emp_margin) # margin can't be negative for safety
            else:
                ci_high_empirical = ci_high_gaussian
                
            if act_t_musd > ci_high_empirical:
                results['empirical']['breaches'] += 1
            results['empirical']['windows'] += 1
            
    return results

if __name__ == "__main__":
    print("Running Phase 2 Calibration Backtest...")
    res = run_backtest_phase2(horizon_days=1)
    
    g_breach = res['gaussian']['breaches'] / res['gaussian']['windows'] if res['gaussian']['windows'] > 0 else 0
    e_breach = res['empirical']['breaches'] / res['empirical']['windows'] if res['empirical']['windows'] > 0 else 0
    
    print("\nBreach Rate Comparison (Target: 5.0%):")
    print(f"Gaussian Parametric: {g_breach:.1%} (Breaches: {res['gaussian']['breaches']}/{res['gaussian']['windows']})")
    print(f"Empirical Simulation: {e_breach:.1%} (Breaches: {res['empirical']['breaches']}/{res['empirical']['windows']})")
    
    if e_breach < g_breach:
        print("\n=> Empirical simulation improved calibration!")
    else:
        print("\n=> Empirical simulation DID NOT improve calibration on this dataset.")
        print("=> As per instructions: this is real information, do not ship it.")

