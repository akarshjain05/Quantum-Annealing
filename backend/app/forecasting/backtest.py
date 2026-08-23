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

def run_backtest(model_type: str, horizon_days: int = 1, confidence_level: float = 0.95):
    txs, corridors_data = load_data()
    
    corridor_txs = defaultdict(list)
    for tx in txs:
        ts = dt.datetime.fromisoformat(tx['timestamp'])
        corridor_txs[tx['corridor_code']].append((ts, tx['amount']))
        
    z_score = 1.96 if confidence_level == 0.95 else 1.645
    results = {}
    
    for code, history in corridor_txs.items():
        history.sort(key=lambda x: x[0])
        if not history:
            continue
            
        min_date = history[0][0].date()
        max_date = history[-1][0].date()
        
        total_days = (max_date - min_date).days + 1
        if total_days <= horizon_days:
            continue
            
        errors = []
        actuals = []
        breaches = 0
        total_windows = 0
        
        for t_offset in range(1, total_days - horizon_days + 1):
            t = min_date + dt.timedelta(days=t_offset)
            
            hist_t = [(ts, amt) for ts, amt in history if ts.date() < t]
            if not hist_t:
                continue
                
            end_t = t + dt.timedelta(days=horizon_days)
            act_t = sum(amt for ts, amt in history if t <= ts.date() < end_t)
            
            hist_t_musd = [(ts, amt / 1e6) for ts, amt in hist_t]
            act_t_musd = act_t / 1e6
            
            fcst = compute_forecast(hist_t_musd, horizon_days=horizon_days, model_type=model_type)
            
            mu = fcst.expected_demand_musd
            sigma = fcst.std_dev_musd
            ci_high = mu + z_score * sigma
            
            errors.append(abs(mu - act_t_musd))
            actuals.append(act_t_musd)
            
            if act_t_musd > ci_high:
                breaches += 1
            total_windows += 1
            
        if total_windows > 0:
            mae = np.mean(errors)
            rmse = np.sqrt(np.mean(np.array(errors)**2))
            breach_rate = breaches / total_windows
            
            results[code] = {
                "windows": total_windows,
                "mae": mae,
                "rmse": rmse,
                "breach_rate": breach_rate
            }
            
    return results

if __name__ == "__main__":
    print("Running Phase 1 Model Competition...\n")
    models = ["baseline", "seasonal_naive", "gbr"]
    
    overall_results = {}
    
    for model in models:
        res = run_backtest(model_type=model, horizon_days=1)
        
        if not res:
            overall_results[model] = {"mae": float('inf'), "rmse": float('inf'), "breach": 1.0}
            continue
            
        avg_mae = np.mean([r['mae'] for r in res.values()])
        avg_rmse = np.mean([r['rmse'] for r in res.values()])
        avg_breach = np.mean([r['breach_rate'] for r in res.values()])
        
        overall_results[model] = {
            "mae": avg_mae,
            "rmse": avg_rmse,
            "breach": avg_breach
        }
        
    print(f"{'Model':<20} | {'Avg MAE':<10} | {'Avg RMSE':<10} | {'Avg Breach'}")
    print("-" * 55)
    for model, r in overall_results.items():
        print(f"{model:<20} | {r['mae']:<10.3f} | {r['rmse']:<10.3f} | {r['breach']:.1%}")
        
    best_model = min(overall_results.keys(), key=lambda k: overall_results[k]['mae'])
    
    print(f"\n=> WINNER (Lowest MAE): {best_model}")
    print("Updating forecast.py to set this as the default if not already...")

