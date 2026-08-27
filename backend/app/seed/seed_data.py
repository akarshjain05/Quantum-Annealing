import json
import datetime as dt
from pathlib import Path
import os
from app.core.database import SessionLocal, engine, Base
from app.core.config import settings
from app.core.security import hash_password
from app import models
from app.agent.knowledge_seed import KNOWLEDGE_ITEMS

def get_data_dir():
    # In docker, it's at /app/data
    if Path("/app/data").exists():
        return Path("/app/data")
    # Locally, it's at repo_root/data
    return Path(__file__).resolve().parents[3] / "data"

def run_seed(reset: bool = True):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    try:
        if not reset and db.query(models.Organization).first():
            print('Database already seeded. Skipping.')
            return
        if reset:
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

        data_dir = get_data_dir()

        with open(data_dir / "corridors.json") as f:
            corridors_data = json.load(f)
            
        currencies = set()
        for c in corridors_data:
            currencies.add(c["source_currency"])
            currencies.add(c["destination_currency"])
            
        for code in currencies:
            db.add(models.Currency(code=code, name=code, symbol=code))
        db.flush()

        corridor_objs = {}
        for c_data in corridors_data:
            c = models.Corridor(
                code=c_data["code"],
                name=c_data["name"],
                source_currency=c_data["source_currency"],
                dest_currency=c_data["destination_currency"],
                settlement_window_start_hour_utc=int(c_data["settlement_window"]["start_time"].split(":")[0]),
                settlement_window_end_hour_utc=int(c_data["settlement_window"]["end_time"].split(":")[0]),
                cutoff_hour_utc=int(c_data["settlement_window"]["cutoff_time"].split(":")[0]),
                description=f"Static demo corridor from JSON",
            )
            db.add(c)
            db.flush()
            corridor_objs[c_data["code"]] = c

            db.add(models.NostroAccount(
                corridor_id=c.id,
                currency=c_data["destination_currency"],
                account_name=f"NOSTRO-{c_data['code']}-01",
                institution_name=c_data["correspondent"]["name"],
                current_balance_musd=c_data["current_balance"] / 1_000_000,
            ))

            # Phase A: Decomposed Loss Parameters
            import random
            
            # Using current_balance as a rough proxy for scale since base_vol is gone
            scale = (c_data["current_balance"] / 1_000_000) * 0.1
            
            # Contractual penalty (e.g. overdraft fees) - plausibly estimable
            penalty_fee = round(scale * random.uniform(0.1, 0.5), 2)
            
            # Operational / manual intervention cost - roughly estimable
            ops_cost = round(random.uniform(0.01, 0.05), 3)
            
            # Reputational risk - MODEL_ASSUMPTION, hard to quantify
            reputational = round(scale * random.uniform(1.0, 2.0), 2)
            
            total_loss = penalty_fee + ops_cost + reputational

            db.add(models.RiskParameter(
                corridor_id=c.id,
                opportunity_cost_rate_annual=0.05,
                loss_given_shortfall_musd=total_loss,
                correspondent_penalty_fee=penalty_fee,
                operational_remediation_cost=ops_cost,
                reputational_risk_proxy=reputational,
                fx_cost_bps=10.0,
                operational_cost_rate=0.02,
            ))

        with open(data_dir / "transactions.json") as f:
            transactions_data = json.load(f)
            
        for t_data in transactions_data:
            c = corridor_objs.get(t_data["corridor_code"])
            if not c:
                continue
            ts = dt.datetime.fromisoformat(t_data["timestamp"].replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=dt.timezone.utc)
            db.add(models.PaymentTransaction(
                corridor_id=c.id,
                ts=ts,
                amount_musd=t_data["amount"] / 1_000_000,
                direction="outbound" if t_data["type"] == "PAYMENT" else "inbound",
            ))

        for item in KNOWLEDGE_ITEMS:
            db.add(models.KnowledgeItem(**item))

        db.commit()

        print(f"Seed complete using static JSON files from {data_dir}.")
    finally:
        db.close()

if __name__ == "__main__":
    run_seed(reset=False)
