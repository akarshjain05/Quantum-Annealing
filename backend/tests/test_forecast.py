import datetime as dt
from app.forecasting.forecast import compute_forecast, _daily_totals, time_of_day_profile


def test_empty_transactions_returns_zero_forecast():
    result = compute_forecast([])
    assert result.expected_demand_musd == 0.0
    assert result.model_used == "insufficient_data"


def test_daily_totals_aggregates_by_day():
    base = dt.datetime(2026, 1, 1)
    txns = [
        (base + dt.timedelta(hours=1), 2.0),
        (base + dt.timedelta(hours=10), 3.0),
        (base + dt.timedelta(days=1, hours=2), 5.0),
    ]
    totals = _daily_totals(txns)
    assert list(totals) == [5.0, 5.0]


def test_forecast_scales_roughly_with_horizon():
    base = dt.datetime(2026, 1, 1)
    txns = [(base + dt.timedelta(days=d, hours=6), 4.0) for d in range(60)]
    fc_7d = compute_forecast(txns, horizon_days=7)
    fc_14d = compute_forecast(txns, horizon_days=14)
    assert fc_14d.expected_demand_musd > fc_7d.expected_demand_musd
    # roughly double, allowing slack for the moving-average/EWMA blend
    assert 1.5 < (fc_14d.expected_demand_musd / fc_7d.expected_demand_musd) < 2.5


def test_time_of_day_profile_sums_to_one():
    base = dt.datetime(2026, 1, 1)
    txns = [(base.replace(hour=h), 1.0) for h in [1, 5, 9, 13, 17, 21]]
    profile = time_of_day_profile(txns)
    assert len(profile) == 6
    assert abs(sum(profile) - 1.0) < 1e-3  # rounding each bucket to 4dp allows a small cumulative drift
