"""
Deterministic synthetic demo data generator (spec §17, §38).

Generates: 8 currencies, 11 corridors (exceeds the 10-corridor minimum),
11 nostro accounts, ~90 days of transaction history per corridor
(several thousand transactions total), risk parameters, dual-corpus
knowledge items, and a demo user.

Nostro balances are deliberately seeded above the modeled safety
requirement (a realistic "conservative static buffer" starting point) so
the optimizer has genuine excess to find - this is not hardcoded into the
optimization result, it falls out of the actual QUBO solve.

ALL data here is synthetic and clearly labeled as such wherever it
surfaces in the API/UI (spec §78).
"""
import datetime as dt
import numpy as np

from app.core.database import SessionLocal, engine, Base
from app.core.config import settings
from app.core.security import hash_password
from app import models
from app.agent.knowledge_seed import KNOWLEDGE_ITEMS

CURRENCIES = [
    ("USD", "US Dollar", "$"), ("EUR", "Euro", "€"), ("GBP", "British Pound", "£"),
    ("INR", "Indian Rupee", "₹"), ("SGD", "Singapore Dollar", "S$"), ("AED", "UAE Dirham", "AED"),
    ("JPY", "Japanese Yen", "¥"), ("CHF", "Swiss Franc", "CHF"),
]

# code, name, source_ccy, dest_ccy, settlement_window(start,end) UTC, cutoff_hour_utc,
# base_daily_volume_musd, daily_volatility_fraction, txn_hour_bias(list of preferred UTC hours or None)
CORRIDORS = [
    ("USD_INR", "USD to INR", "USD", "INR", 3, 18, 12, 4.5, 0.18, None),
    ("EUR_INR", "EUR to INR", "EUR", "INR", 4, 17, 11, 2.2, 0.20, None),
    ("GBP_INR", "GBP to INR", "GBP", "INR", 5, 16, 11, 0.9, 0.35, None),
    ("AED_INR", "AED to INR", "AED", "INR", 2, 12, 9, 1.5, 0.16, [3, 4, 5, 6, 7, 8, 9]),
    ("SGD_INR", "SGD to INR", "SGD", "INR", 0, 9, 6, 1.1, 0.22, [0, 1, 2, 3, 4, 5]),
    ("JPY_INR", "JPY to INR", "JPY", "INR", 0, 8, 5, 0.8, 0.28, [0, 1, 2, 3]),
    ("USD_EUR", "USD to EUR", "USD", "EUR", 6, 20, 15, 6.0, 0.10, None),
    ("EUR_USD", "EUR to USD", "EUR", "USD", 6, 20, 15, 5.8, 0.10, None),
    ("USD_GBP", "USD to GBP", "USD", "GBP", 7, 19, 14, 3.0, 0.15, None),
    ("GBP_EUR", "GBP to EUR", "GBP", "EUR", 6, 18, 13, 2.0, 0.18, None),
    ("USD_CHF", "USD to CHF", "USD", "CHF", 6, 19, 14, 1.8, 0.12, None),
]

INSTITUTIONS = [
    "Meridian Correspondent Bank", "Anchorpoint Global Bank", "Silverline International",
    "Continental Settlement Bank", "Harborview Bank N.A.",
]


def _generate_transactions(rng: np.random.Generator, corridor_id: int, base_vol: float,
                            vol_frac: float, hour_bias, days: int = 90):
    now = dt.datetime.now(dt.timezone.utc)
    start = now - dt.timedelta(days=days)
    rows = []
    for d in range(days):
        day_date = start + dt.timedelta(days=d)
        weekday = day_date.weekday()  # 0=Mon .. 6=Sun
        weekend_factor = 0.35 if weekday >= 5 else 1.0
        n_txns = max(1, int(rng.poisson(5) * weekend_factor))
        day_total_target = max(0.05, rng.normal(base_vol, base_vol * vol_frac)) * weekend_factor
        if n_txns == 0:
            continue
        splits = rng.dirichlet(np.ones(n_txns)) * day_total_target
        for amt in splits:
            if hour_bias:
                hour = int(rng.choice(hour_bias))
            else:
                hour = int(rng.integers(0, 24))
            minute = int(rng.integers(0, 60))
            ts = day_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            direction = "outbound" if rng.random() < 0.6 else "inbound"
            rows.append(models.PaymentTransaction(
                corridor_id=corridor_id, ts=ts, amount_musd=round(float(amt), 4), direction=direction,
            ))
    return rows


def run_seed(reset: bool = True):
    # create_all is idempotent (only creates missing tables) so this is safe
    # to run even if `alembic upgrade head` already created the schema - it
    # never drops or alters existing tables, unlike drop_all.
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    rng = np.random.default_rng(settings.RANDOM_SEED)

    try:
        if reset:
            # Clear existing DATA (not schema) in dependency order, so
            # re-running seed is idempotent without disturbing Alembic's
            # own version-tracking table.
            for model in (models.HumanApproval, models.AgentMessage, models.AuditLog,
                          models.StressTestResult, models.ScenarioRun,
                          models.OptimizationBaseline, models.OptimizationResult, models.OptimizationRun,
                          models.KnowledgeItem, models.RiskParameter, models.PaymentForecast,
                          models.PaymentTransaction, models.NostroAccount, models.Corridor,
                          models.Currency, models.User, models.Organization):
                db.query(model).delete()
            db.commit()
        org = models.Organization(name="Demo Global Bank")
        db.add(org)
        db.flush()

        user = models.User(
            email="treasury@demo-bank.com",
            hashed_password=hash_password("DemoPassword123!"),
            full_name="Demo Treasury Analyst",
            role="treasury_admin",
            organization_id=org.id,
            is_demo_account=True,
        )
        db.add(user)

        for code, name, symbol in CURRENCIES:
            db.add(models.Currency(code=code, name=name, symbol=symbol))
        db.flush()

        corridor_objs = {}
        for i, (code, name, src, dst, ws, we, cutoff, base_vol, vol_frac, hour_bias) in enumerate(CORRIDORS):
            c = models.Corridor(
                code=code, name=name, source_currency=src, dest_currency=dst,
                settlement_window_start_hour_utc=ws, settlement_window_end_hour_utc=we,
                cutoff_hour_utc=cutoff,
                description=f"Synthetic demo corridor: {name}. Base daily volume ~${base_vol}M, "
                            f"illustrative daily volatility ~{int(vol_frac*100)}%.",
            )
            db.add(c)
            db.flush()
            corridor_objs[code] = c

            # Transactions
            txns = _generate_transactions(rng, c.id, base_vol, vol_frac, hour_bias)
            db.add_all(txns)

            # 7-day mean/std estimate (rough, for seeding a realistic starting balance)
            daily_amounts = [t.amount_musd for t in txns]
            approx_daily_mu = float(np.mean(daily_amounts)) * (len(daily_amounts) / 90.0) if daily_amounts else base_vol
            approx_7d_mu = base_vol * 7
            approx_7d_sigma = base_vol * vol_frac * np.sqrt(7)
            approx_safety = approx_7d_mu + 1.96 * approx_7d_sigma  # ~95% static estimate

            # Deliberately conservative starting balance: 1.4x-1.9x the rough safety
            # estimate, i.e. a bank following a static-buffer-style policy today.
            over_buffer_mult = float(rng.uniform(1.4, 1.9))
            starting_balance = round(approx_safety * over_buffer_mult, 2)

            db.add(models.NostroAccount(
                corridor_id=c.id, currency=dst,
                account_name=f"NOSTRO-{code}-01",
                institution_name=INSTITUTIONS[i % len(INSTITUTIONS)],
                current_balance_musd=starting_balance,
            ))

            db.add(models.RiskParameter(
                corridor_id=c.id,
                opportunity_cost_rate_annual=round(float(rng.uniform(0.035, 0.07)), 4),
                loss_given_shortfall_musd=round(base_vol * float(rng.uniform(1.2, 2.5)), 2),
                fx_cost_bps=round(float(rng.uniform(4, 15)), 2),
                operational_cost_rate=round(float(rng.uniform(0.01, 0.03)), 4),
            ))

        for item in KNOWLEDGE_ITEMS:
            db.add(models.KnowledgeItem(**item))

        db.commit()

        n_txns = db.query(models.PaymentTransaction).count()
        n_corridors = db.query(models.Corridor).count()
        n_accounts = db.query(models.NostroAccount).count()
        n_currencies = db.query(models.Currency).count()
        print(f"Seed complete: {n_currencies} currencies, {n_corridors} corridors, "
              f"{n_accounts} nostro accounts, {n_txns} transactions, "
              f"{len(KNOWLEDGE_ITEMS)} knowledge items, 1 demo user.")
    finally:
        db.close()


if __name__ == "__main__":
    run_seed(reset=True)
