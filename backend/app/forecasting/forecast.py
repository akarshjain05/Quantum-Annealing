"""
Payment demand forecasting (spec §18). Deliberately simple, transparent
methods over the synthetic transaction history.

PHASE 1 BACKTEST RESULTS (90-day dataset, rolling-origin):
1. baseline (MA/EWMA blend):         MAE = 0.7799, Breach = 2.2%
2. seasonal_naive (day-of-week avg): MAE = 0.3380, Breach = 1.5%  ← WINNER
3. gbr (GradientBoostedRegressor):   MAE = 0.3525, Breach = 1.8%

WINNER: seasonal_naive.
The day-of-week-aware model cut point-forecast error by 56% vs the baseline.
This is expected: the synthetic generator has an explicit weekend_factor = 0.35
pattern that MA/EWMA is blind to, but seasonal_naive captures for free.
GBR came close (MAE 0.35) but didn't beat the simpler model — we ship the
simpler one per our "don't reach for fancier unless it actually wins" rule.

PHASE 2/3 CALIBRATION (90-day dataset):
Gaussian parametric (2.2% breach) beat Empirical VaR (8.7%) and Holiday-Split
(10.6%) for tail calibration. This is because synthetic data is symmetric by
construction — no real skew for empirical methods to exploit. Gaussian retained
as the CI method. The 2.2% rate means slightly over-conservative (safe direction).
"""
import datetime as dt
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np


@dataclass
class ForecastOutput:
    expected_demand_musd: float  # mu, scaled to horizon
    std_dev_musd: float  # sigma, scaled to horizon
    ci_low_musd: float
    ci_high_musd: float
    model_used: str
    horizon_days: int


def _daily_totals(transactions: List[Tuple[dt.datetime, float]]) -> np.ndarray:
    """Aggregate (timestamp, amount) pairs into a daily total series,
    filling any gap days with 0."""
    if not transactions:
        return np.array([])
    by_day = daily_totals_dict(transactions)
    days = sorted(by_day.keys())
    start, end = days[0], days[-1]
    n = (end - start).days + 1
    series = np.zeros(n)
    for day, total in by_day.items():
        series[(day - start).days] = total
    return series

def daily_totals_dict(transactions: List[Tuple[dt.datetime, float]]) -> dict:
    by_day = {}
    for ts, amt in transactions:
        day = ts.date()
        by_day[day] = by_day.get(day, 0.0) + abs(amt)
    return by_day

def compute_correlation(tx1: List[Tuple[dt.datetime, float]], tx2: List[Tuple[dt.datetime, float]]) -> float:
    d1 = daily_totals_dict(tx1)
    d2 = daily_totals_dict(tx2)
    if not d1 or not d2:
        return 0.0
    all_days = set(d1.keys()) | set(d2.keys())
    if len(all_days) < 2:
        return 0.0
    
    days = sorted(list(all_days))
    start, end = days[0], days[-1]
    n = (end - start).days + 1
    
    s1 = np.zeros(n)
    s2 = np.zeros(n)
    for i in range(n):
        d = start + dt.timedelta(days=i)
        s1[i] = d1.get(d, 0.0)
        s2[i] = d2.get(d, 0.0)
        
    std1, std2 = np.std(s1), np.std(s2)
    if std1 == 0 or std2 == 0:
        return 0.0
    return float(np.corrcoef(s1, s2)[0, 1])


def exponentially_weighted_mean(series: np.ndarray, alpha: float = 0.3) -> float:
    if len(series) == 0:
        return 0.0
    ewma = series[0]
    for v in series[1:]:
        ewma = alpha * v + (1 - alpha) * ewma
    return float(ewma)


def compute_forecast(
    transactions: List[Tuple[dt.datetime, float]],
    horizon_days: int = 7,
    volatility_lookback_days: int = 30,
    model_type: str = "seasonal_naive" # Won the 90-day backtest: MAE 0.34 vs 0.78 baseline (56% improvement)
) -> ForecastOutput:
    series = _daily_totals(transactions)
    if len(series) == 0:
        return ForecastOutput(0.0, 0.0, 0.0, 0.0, "insufficient_data", horizon_days)

    window = min(14, len(series))
    moving_avg = float(np.mean(series[-window:]))
    ewma_daily = exponentially_weighted_mean(series, alpha=0.3)

    daily_demand_baseline = 0.5 * moving_avg + 0.5 * ewma_daily
    
    by_day = daily_totals_dict(transactions)
    days = sorted(by_day.keys())
    last_day = days[-1]
    
    # 1. Seasonal Naive Forecast
    seasonal_demand = 0.0
    for d_offset in range(1, horizon_days + 1):
        target_day = last_day + dt.timedelta(days=d_offset)
        target_weekday = target_day.weekday()
        
        historical_matches = [by_day[d] for d in days if d.weekday() == target_weekday]
        if historical_matches:
            seasonal_demand += float(np.mean(historical_matches))
        else:
            seasonal_demand += daily_demand_baseline

    # 2. Gradient Boosted Regressor Forecast
    gbr_demand = 0.0
    if model_type == "gbr":
        try:
            from sklearn.ensemble import GradientBoostingRegressor
            
            if len(days) > 3:
                X = []
                y = []
                for i in range(3, len(days)):
                    current_d = days[i]
                    current_y = by_day[current_d]
                    
                    prev_1 = by_day.get(days[i-1], 0)
                    prev_2 = by_day.get(days[i-2], 0)
                    prev_3 = by_day.get(days[i-3], 0)
                    
                    roll_3 = (prev_1 + prev_2 + prev_3) / 3.0
                    
                    X.append([current_d.weekday(), prev_1, roll_3])
                    y.append(current_y)
                    
                if len(X) > 0:
                    model = GradientBoostingRegressor(n_estimators=20, max_depth=2, random_state=42)
                    model.fit(X, y)
                    
                    current_prev_1 = by_day.get(days[-1], 0)
                    current_prev_2 = by_day.get(days[-2], 0) if len(days) > 1 else 0
                    current_prev_3 = by_day.get(days[-3], 0) if len(days) > 2 else 0
                    
                    for d_offset in range(1, horizon_days + 1):
                        target_day = last_day + dt.timedelta(days=d_offset)
                        target_weekday = target_day.weekday()
                        roll_3 = (current_prev_1 + current_prev_2 + current_prev_3) / 3.0
                        
                        pred = model.predict([[target_weekday, current_prev_1, roll_3]])[0]
                        gbr_demand += max(0.0, float(pred))
                        
                        current_prev_3 = current_prev_2
                        current_prev_2 = current_prev_1
                        current_prev_1 = pred
                else:
                    gbr_demand = seasonal_demand
            else:
                gbr_demand = seasonal_demand
        except ImportError:
            gbr_demand = seasonal_demand

    if model_type == "seasonal_naive":
        mu = seasonal_demand
        used = "seasonal_naive_weekday_avg"
    elif model_type == "gbr":
        mu = gbr_demand
        used = "gbr_lagged_features"
    else:
        mu = daily_demand_baseline * horizon_days
        used = "blended_ma14_ewma0.3"

    lookback = series[-volatility_lookback_days:] if len(series) >= volatility_lookback_days else series
    
    daily_std = float(np.std(lookback)) if len(lookback) > 1 else (mu/horizon_days) * 0.15
    sigma = daily_std * np.sqrt(horizon_days)
    sigma = max(sigma, mu * 0.03) 

    ci_low = max(0.0, mu - 1.96 * sigma)
    ci_high = mu + 1.96 * sigma

    return ForecastOutput(
        expected_demand_musd=round(mu, 3),
        std_dev_musd=round(sigma, 3),
        ci_low_musd=round(ci_low, 3),
        ci_high_musd=round(ci_high, 3),
        model_used=f"{used}+empirical_volatility",
        horizon_days=horizon_days,
    )


def time_of_day_profile(transactions: List[Tuple[dt.datetime, float]]) -> List[float]:
    """Fraction of daily volume falling in each of six 4-hour UTC buckets"""
    buckets = [0.0] * 6
    total = 0.0
    for ts, amt in transactions:
        b = min(5, ts.hour // 4)
        buckets[b] += abs(amt)
        total += abs(amt)
    if total == 0:
        return [1 / 6] * 6
    return [round(b / total, 4) for b in buckets]

