import json
import datetime as dt
from collections import defaultdict
import numpy as np
from pathlib import Path
import sys

# Add the parent directory to sys.path so we can import app modules
# assuming this is run as `python backend/app/forecasting/backtest.py`
sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.forecasting.forecast import compute_forecast

def load_data():
    data_dir = Path(__file__).resolve().parents[3] / "data"
    if not data_dir.exists():
        data_dir = Path("/app/data") # Docker fallback
        
    with open(data_dir / "transactions.json") as f:
        txs = json.load(f)
    
    with open(data_dir / "corridors.json") as f:
        corridors = json.load(f)
        
    return txs, corridors

def run_backtest(horizon_days: int = 1, confidence_level: float = 0.95):
    txs, corridors_data = load_data()
    
    # Group by corridor
    corridor_txs = defaultdict(list)
    for tx in txs:
        # Convert timestamp to datetime
        ts = dt.datetime.fromisoformat(tx['timestamp'])
        corridor_txs[tx['corridor_code']].append((ts, tx['amount']))
        
    z_score = 1.96 if confidence_level == 0.95 else 1.645 # simplify for now
    
    results = {}
    
    for code, history in corridor_txs.items():
        history.sort(key=lambda x: x[0])
        if not history:
            continue
            
        min_date = history[0][0].date()
        max_date = history[-1][0].date()
        
        # We need at least one day of history to forecast the next day
        total_days = (max_date - min_date).days + 1
        
        if total_days <= horizon_days:
            # Cannot do a rolling backtest if data is shorter than horizon
            continue
            
        # Metrics
        errors = []
        actuals = []
        predictions = []
        breaches = 0
        total_windows = 0
        
        # Roll through time
        # At day t, we use data up to t-1 to forecast [t, t+horizon)
        for t_offset in range(1, total_days - horizon_days + 1):
            t = min_date + dt.timedelta(days=t_offset)
            
            # History strictly before t
            hist_t = [(ts, amt) for ts, amt in history if ts.date() < t]
            if not hist_t:
                continue
                
            # Actuals in [t, t+horizon)
            end_t = t + dt.timedelta(days=horizon_days)
            act_t = sum(amt for ts, amt in history if t <= ts.date() < end_t)
            
            # Forecast
            # compute_forecast normally returns MUSD, but our raw data is full scale (or is it?)
            # Let's check amounts. The amounts in transactions.json are full scale, e.g., 222475.93
            # compute_forecast expects the scale it will return. 
            # Oh wait, compute_forecast doesn't scale inputs down, it just aggregates them.
            # But the dataclass fields are named expected_demand_musd. If we feed full scale, it returns full scale.
            # Let's feed MUSD to be consistent with the field names.
            hist_t_musd = [(ts, amt / 1e6) for ts, amt in hist_t]
            act_t_musd = act_t / 1e6
            
            fcst = compute_forecast(hist_t_musd, horizon_days=horizon_days)
            
            mu = fcst.expected_demand_musd
            sigma = fcst.std_dev_musd
            ci_high = mu + z_score * sigma
            
            errors.append(abs(mu - act_t_musd))
            actuals.append(act_t_musd)
            predictions.append(mu)
            
            if act_t_musd > ci_high:
                breaches += 1
            total_windows += 1
            
        if total_windows > 0:
            mae = np.mean(errors)
            rmse = np.sqrt(np.mean(np.array(errors)**2))
            
            # MAPE can blow up if actuals are near zero
            safe_actuals = np.array(actuals)
            safe_actuals[safe_actuals < 1e-6] = 1e-6
            mape = np.mean(np.array(errors) / safe_actuals) * 100
            
            breach_rate = breaches / total_windows
            
            results[code] = {
                "windows": total_windows,
                "mae": round(mae, 3),
                "rmse": round(rmse, 3),
                "mape": round(mape, 3),
                "breach_rate": round(breach_rate, 4)
            }
            
    return results

if __name__ == "__main__":
    print("Running Backtest Harness (Phase 0)...\n")
    # Using 1-day horizon because synthetic data only has 7 days total.
    # Normally this would be 7, but rolling over 7 days of data with a 7-day horizon yields 0 windows.
    res = run_backtest(horizon_days=1, confidence_level=0.95)
    
    print(f"{'Corridor':<12} | {'Windows':<7} | {'MAE':<8} | {'RMSE':<8} | {'MAPE %':<8} | {'Breach Rate'}")
    print("-" * 65)
    for code, r in res.items():
        print(f"{code:<12} | {r['windows']:<7} | {r['mae']:<8.3f} | {r['rmse']:<8.3f} | {r['mape']:<8.2f} | {r['breach_rate']:.1%}")
    
    avg_breach = np.mean([r['breach_rate'] for r in res.values()]) if res else 0
    print(f"\nAverage Breach Rate: {avg_breach:.1%} (Target at 95% CI is ~5.0%)")

