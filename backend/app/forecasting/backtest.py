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

# Hardcoded for Phase 3 test (Aug 15 is a major holiday in INR/EUR)
HOLIDAYS = {
    "INR": {dt.date(2026, 8, 15)},
    "EUR": {dt.date(2026, 8, 15)}
}

def is_holiday_adjacent(date: dt.date, currency1: str, currency2: str) -> bool:
    # Check if date, date-1, or date+1 is a holiday for either currency
    dates_to_check = [date - dt.timedelta(days=1), date, date + dt.timedelta(days=1)]
    for d in dates_to_check:
        if d in HOLIDAYS.get(currency1, set()) or d in HOLIDAYS.get(currency2, set()):
            return True
    return False

def run_backtest_phase3(horizon_days: int = 1, confidence_level: float = 0.95):
    txs, corridors_data = load_data()
    
    corridor_txs = defaultdict(list)
    for tx in txs:
        ts = dt.datetime.fromisoformat(tx['timestamp'])
        corridor_txs[tx['corridor_code']].append((ts, tx['amount']))
        
    z_score = 1.645 if confidence_level == 0.95 else 2.326
    
    results = {
        'gaussian': {'breaches': 0, 'windows': 0},
        'empirical_unified': {'breaches': 0, 'windows': 0},
        'empirical_holiday_split': {'breaches': 0, 'windows': 0}
    }
    
    for code, history in corridor_txs.items():
        history.sort(key=lambda x: x[0])
        if not history:
            continue
            
        c1, c2 = code.split('_')
        min_date = history[0][0].date()
        max_date = history[-1][0].date()
        total_days = (max_date - min_date).days + 1
        
        if total_days <= horizon_days:
            continue
            
        for t_offset in range(1, total_days - horizon_days + 1):
            t = min_date + dt.timedelta(days=t_offset)
            is_holiday_regime = is_holiday_adjacent(t, c1, c2)
            
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
            
            # Build empirical residuals
            residuals_all = []
            residuals_holiday = []
            residuals_normal = []
            
            for past_t_offset in range(1, t_offset):
                past_t = min_date + dt.timedelta(days=past_t_offset)
                past_is_holiday = is_holiday_adjacent(past_t, c1, c2)
                
                past_hist = [(ts, amt) for ts, amt in history if ts.date() < past_t]
                if not past_hist:
                    continue
                past_end = past_t + dt.timedelta(days=horizon_days)
                past_act = sum(amt for ts, amt in history if past_t <= ts.date() < past_end) / 1e6
                past_fcst = compute_forecast([(ts, amt/1e6) for ts, amt in past_hist], horizon_days=horizon_days, model_type="baseline")
                
                res = past_act - past_fcst.expected_demand_musd
                residuals_all.append(res)
                if past_is_holiday:
                    residuals_holiday.append(res)
                else:
                    residuals_normal.append(res)
            
            # 2. Empirical Unified
            if residuals_all:
                emp_margin = float(np.quantile(residuals_all, confidence_level))
                ci_high_unified = mu + max(0, emp_margin)
            else:
                ci_high_unified = ci_high_gaussian
                
            if act_t_musd > ci_high_unified:
                results['empirical_unified']['breaches'] += 1
            results['empirical_unified']['windows'] += 1
            
            # 3. Empirical Holiday Split
            target_residuals = residuals_holiday if is_holiday_regime else residuals_normal
            if target_residuals:
                emp_split_margin = float(np.quantile(target_residuals, confidence_level))
                ci_high_split = mu + max(0, emp_split_margin)
            elif residuals_all: # fallback to unified if regime pool is empty
                emp_split_margin = float(np.quantile(residuals_all, confidence_level))
                ci_high_split = mu + max(0, emp_split_margin)
            else:
                ci_high_split = ci_high_gaussian
                
            if act_t_musd > ci_high_split:
                results['empirical_holiday_split']['breaches'] += 1
            results['empirical_holiday_split']['windows'] += 1
            
    return results

if __name__ == "__main__":
    print("Running Phase 3 Holiday Calibration Backtest...")
    res = run_backtest_phase3(horizon_days=1)
    
    g_breach = res['gaussian']['breaches'] / res['gaussian']['windows']
    eu_breach = res['empirical_unified']['breaches'] / res['empirical_unified']['windows']
    es_breach = res['empirical_holiday_split']['breaches'] / res['empirical_holiday_split']['windows']
    
    print("\nBreach Rate Comparison (Target: 5.0%):")
    print(f"Gaussian Parametric:       {g_breach:.1%} (Breaches: {res['gaussian']['breaches']}/{res['gaussian']['windows']})")
    print(f"Empirical Unified:         {eu_breach:.1%} (Breaches: {res['empirical_unified']['breaches']}/{res['empirical_unified']['windows']})")
    print(f"Empirical Holiday-Split:   {es_breach:.1%} (Breaches: {res['empirical_holiday_split']['breaches']}/{res['empirical_holiday_split']['windows']})")
    
    if es_breach < eu_breach and es_breach < g_breach:
        print("\n=> Splitting holiday regimes improved calibration!")
    else:
        print("\n=> Holiday-splitting failed to improve calibration on this sparse dataset.")
        print("=> Splitting a 7-day dataset into two even smaller pools destroys statistical significance.")
        print("=> As per instructions: this is real information, do not ship the code to production.")

