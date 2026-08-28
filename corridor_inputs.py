def corridor_inputs_from_db(
    db: Session, corridor_codes: Optional[List[str]], confidence_level: float,
    demand_delta_pct: float = 0.0, volatility_delta_pct: float = 0.0,
) -> List[CorridorInput]:
    q = db.query(models.Corridor)
    if corridor_codes:
        q = q.filter(models.Corridor.code.in_(corridor_codes))
    corridors = q.all()
    if not corridors:
        raise HTTPException(status_code=400, detail="No matching corridors found")

    inputs = []
    for c in corridors:
        from app.forecasting.forecast import compute_forecast
        txns = db.query(models.PaymentTransaction).filter(models.PaymentTransaction.corridor_id == c.id).all()
        pairs = [(t.ts, t.amount_musd) for t in txns]
        fc = compute_forecast(pairs, horizon_days=7)
        mu = fc.expected_demand_musd * (1 + demand_delta_pct / 100.0)
        sigma = max(fc.std_dev_musd * (1 + volatility_delta_pct / 100.0), 0.01)

        risk = db.query(models.RiskParameter).filter(models.RiskParameter.corridor_id == c.id).first()
        accounts = db.query(models.NostroAccount).filter(models.NostroAccount.corridor_id == c.id).all()
        current = sum(a.current_balance_musd for a in accounts)

        inputs.append(CorridorInput(
            corridor_id=c.id, code=c.code, mu=mu, sigma=sigma, current_liquidity=current,
            opportunity_cost_rate=risk.opportunity_cost_rate_annual if risk else 0.05,
            loss_given_shortfall=risk.loss_given_shortfall_musd if risk else 5.0,
            fx_cost_bps=risk.fx_cost_bps if risk else 8.0,
            operational_cost_rate=risk.operational_cost_rate if risk else 0.02,
            confidence_level=confidence_level,
            transactions=pairs,
        ))
    return inputs


def _latest_audit_hash(db: Session) -> str:
