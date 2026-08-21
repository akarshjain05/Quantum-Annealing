"""
Payment demand forecasting (spec §18). Deliberately simple, transparent
methods over the synthetic transaction history - moving average, EWMA,
and empirical volatility. This is explicitly NOT presented as
production-grade ML; the goal is a legible, testable demand/uncertainty
estimate that the optimizer can consume.
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
) -> ForecastOutput:
    series = _daily_totals(transactions)
    if len(series) == 0:
        return ForecastOutput(0.0, 0.0, 0.0, 0.0, "insufficient_data", horizon_days)

    window = min(14, len(series))
    moving_avg = float(np.mean(series[-window:]))
    ewma_daily = exponentially_weighted_mean(series, alpha=0.3)

    # Blend MA and EWMA for the daily demand estimate, then scale to horizon.
    daily_demand = 0.5 * moving_avg + 0.5 * ewma_daily
    mu = daily_demand * horizon_days

    lookback = series[-volatility_lookback_days:] if len(series) >= volatility_lookback_days else series
    daily_std = float(np.std(lookback)) if len(lookback) > 1 else daily_demand * 0.15
    # Volatility scales with sqrt(horizon) under an independence assumption across days.
    sigma = daily_std * np.sqrt(horizon_days)
    sigma = max(sigma, mu * 0.03)  # floor to avoid unrealistically tight distributions

    ci_low = max(0.0, mu - 1.96 * sigma)
    ci_high = mu + 1.96 * sigma

    return ForecastOutput(
        expected_demand_musd=round(mu, 3),
        std_dev_musd=round(sigma, 3),
        ci_low_musd=round(ci_low, 3),
        ci_high_musd=round(ci_high, 3),
        model_used="blended_ma14_ewma0.3+empirical_volatility",
        horizon_days=horizon_days,
    )


def time_of_day_profile(transactions: List[Tuple[dt.datetime, float]]) -> List[float]:
    """Fraction of daily volume falling in each of six 4-hour UTC buckets
    (spec §6.8). Returns a 6-element list summing to ~1.0."""
    buckets = [0.0] * 6
    total = 0.0
    for ts, amt in transactions:
        b = min(5, ts.hour // 4)
        buckets[b] += abs(amt)
        total += abs(amt)
    if total == 0:
        return [1 / 6] * 6
    return [round(b / total, 4) for b in buckets]
