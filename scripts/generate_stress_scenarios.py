#!/usr/bin/env python3
# scripts/generate_stress_scenarios.py
"""
Generate stress test scenarios for NostroQ.

Creates realistic stress scenarios:
- Market stress (FX volatility spikes)
- Liquidity stress (demand surges)
- Operational stress (settlement delays)
- Combined scenarios

DISCLOSURE: All scenarios are synthetic for demonstration.
"""

import json
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Seed for reproducibility
random.seed(42)

OUTPUT_DIR = Path("data")


def generate_stress_scenarios() -> List[Dict[str, Any]]:
    """Generate comprehensive stress test scenarios."""
    
    scenarios = []
    
    # ==========================================================================
    # 1. Market Stress Scenarios
    # ==========================================================================
    
    scenarios.append({
        "id": "stress_001",
        "name": "USD/INR Flash Crash",
        "category": "market",
        "severity": "high",
        "probability": "low",
        "description": "Sudden 5% depreciation in INR against USD within 24 hours",
        "triggers": [
            "Unexpected RBI policy announcement",
            "Global risk-off event",
            "Emerging market contagion"
        ],
        "impacts": {
            "fx_shock": {"USD_INR": 0.05, "EUR_INR": 0.04, "GBP_INR": 0.04},
            "volatility_multiplier": 3.0,
            "demand_surge": 0.30,
            "settlement_delay_hours": 2
        },
        "affected_corridors": ["USD_INR", "EUR_INR", "GBP_INR"],
        "mitigation_actions": [
            "Increase INR corridor buffers by 20%",
            "Activate contingent liquidity lines",
            "Reduce intraday settlement windows"
        ],
        "historical_precedent": "2013 Taper Tantrum, 2018 EM Crisis",
        "created_at": datetime.utcnow().isoformat(),
        "synthetic": True
    })
    
    scenarios.append({
        "id": "stress_002",
        "name": "EUR/USD Parity Break",
        "category": "market",
        "severity": "medium",
        "probability": "medium",
        "description": "EUR falls to parity with USD (1:1 exchange rate)",
        "triggers": [
            "ECB emergency rate cut",
            "European banking crisis",
            "Energy supply disruption"
        ],
        "impacts": {
            "fx_shock": {"EUR_USD": -0.08, "EUR_INR": -0.06, "GBP_EUR": 0.05},
            "volatility_multiplier": 2.5,
            "demand_surge": 0.20,
            "settlement_delay_hours": 1
        },
        "affected_corridors": ["USD_EUR", "EUR_USD", "EUR_INR", "GBP_EUR"],
        "mitigation_actions": [
            "Rebalance EUR exposure",
            "Increase EUR corridor minimums",
            "Hedge EUR positions"
        ],
        "historical_precedent": "2022 EUR/USD near-parity",
        "created_at": datetime.utcnow().isoformat(),
        "synthetic": True
    })
    
    # ==========================================================================
    # 2. Liquidity Stress Scenarios
    # ==========================================================================
    
    scenarios.append({
        "id": "stress_003",
        "name": "Month-End Liquidity Surge",
        "category": "liquidity",
        "severity": "medium",
        "probability": "high",
        "description": "2.5x normal demand on last 3 business days of month",
        "triggers": [
            "Salary payments",
            "Corporate treasury rebalancing",
            "Regulatory reporting deadlines"
        ],
        "impacts": {
            "fx_shock": {},
            "volatility_multiplier": 1.2,
            "demand_surge": 1.50,
            "settlement_delay_hours": 0
        },
        "affected_corridors": ["USD_INR", "EUR_INR", "GBP_INR", "AED_INR"],
        "mitigation_actions": [
            "Pre-position additional liquidity 2 days before month-end",
            "Extend settlement windows",
            "Activate standby credit lines"
        ],
        "historical_precedent": "Recurring monthly pattern",
        "created_at": datetime.utcnow().isoformat(),
        "synthetic": True
    })
    
    scenarios.append({
        "id": "stress_004",
        "name": "Correspondent Bank Failure",
        "category": "liquidity",
        "severity": "critical",
        "probability": "very_low",
        "description": "Major correspondent bank unable to process settlements",
        "triggers": [
            "Bank insolvency",
            "Regulatory intervention",
            "Cyber attack on correspondent"
        ],
        "impacts": {
            "fx_shock": {},
            "volatility_multiplier": 1.5,
            "demand_surge": 0.50,
            "settlement_delay_hours": 24,
            "corridor_unavailable": True
        },
        "affected_corridors": ["Variable - depends on correspondent"],
        "mitigation_actions": [
            "Activate backup correspondent relationships",
            "Reroute payments through alternative corridors",
            "Invoke contingency credit facilities"
        ],
        "historical_precedent": "2023 US regional bank crisis",
        "created_at": datetime.utcnow().isoformat(),
        "synthetic": True
    })
    
    # ==========================================================================
    # 3. Operational Stress Scenarios
    # ==========================================================================
    
    scenarios.append({
        "id": "stress_005",
        "name": "SWIFT Network Disruption",
        "category": "operational",
        "severity": "high",
        "probability": "low",
        "description": "4-hour SWIFT network outage affecting all corridors",
        "triggers": [
            "Technical failure",
            "Cyber attack",
            "Natural disaster at data center"
        ],
        "impacts": {
            "fx_shock": {},
            "volatility_multiplier": 1.0,
            "demand_surge": 0.0,
            "settlement_delay_hours": 4,
            "all_corridors_affected": True
        },
        "affected_corridors": ["ALL"],
        "mitigation_actions": [
            "Queue payments for batch processing",
            "Activate alternative messaging channels",
            "Communicate with counterparties"
        ],
        "historical_precedent": "2020 SWIFT outage (2 hours)",
        "created_at": datetime.utcnow().isoformat(),
        "synthetic": True
    })
    
    scenarios.append({
        "id": "stress_006",
        "name": "Holiday Settlement Squeeze",
        "category": "operational",
        "severity": "low",
        "probability": "high",
        "description": "Extended settlement cycle due to overlapping holidays",
        "triggers": [
            "Diwali + US Thanksgiving overlap",
            "Christmas + Japan holiday",
            "Eid + European holiday"
        ],
        "impacts": {
            "fx_shock": {},
            "volatility_multiplier": 1.1,
            "demand_surge": 0.20,
            "settlement_delay_hours": 48
        },
        "affected_corridors": ["USD_INR", "JPY_INR", "EUR_INR"],
        "mitigation_actions": [
            "Pre-fund corridors before holiday period",
            "Adjust minimum balances +30%",
            "Front-load settlements"
        ],
        "historical_precedent": "Recurring annual pattern",
        "created_at": datetime.utcnow().isoformat(),
        "synthetic": True
    })
    
    # ==========================================================================
    # 4. Combined Scenarios
    # ==========================================================================
    
    scenarios.append({
        "id": "stress_007",
        "name": "Global Risk-Off Event",
        "category": "combined",
        "severity": "critical",
        "probability": "low",
        "description": "Combined market, liquidity, and operational stress",
        "triggers": [
            "Geopolitical crisis",
            "Global pandemic",
            "Major sovereign default"
        ],
        "impacts": {
            "fx_shock": {
                "USD_INR": 0.08,
                "EUR_INR": 0.06,
                "GBP_INR": 0.07,
                "AED_INR": 0.03,
                "SGD_INR": 0.04
            },
            "volatility_multiplier": 4.0,
            "demand_surge": 0.80,
            "settlement_delay_hours": 8
        },
        "affected_corridors": ["ALL"],
        "mitigation_actions": [
            "Invoke crisis management protocol",
            "Increase all corridor buffers to 99th percentile",
            "Activate all contingent liquidity",
            "Daily senior management review"
        ],
        "historical_precedent": "2020 COVID-19 market stress",
        "created_at": datetime.utcnow().isoformat(),
        "synthetic": True
    })
    
    scenarios.append({
        "id": "stress_008",
        "name": "Regulatory Capital Call",
        "category": "combined",
        "severity": "medium",
        "probability": "medium",
        "description": "Unexpected increase in regulatory capital requirements",
        "triggers": [
            "Basel IV implementation acceleration",
            "Local regulator intervention",
            "Stress test failure"
        ],
        "impacts": {
            "fx_shock": {},
            "volatility_multiplier": 1.0,
            "demand_surge": 0.0,
            "settlement_delay_hours": 0,
            "capital_requirement_increase": 0.25
        },
        "affected_corridors": ["ALL"],
        "mitigation_actions": [
            "Review and optimize capital allocation",
            "Reduce low-yield corridor exposures",
            "Accelerate capital raising"
        ],
        "historical_precedent": "Post-2008 regulatory changes",
        "created_at": datetime.utcnow().isoformat(),
        "synthetic": True
    })
    
    return scenarios


def generate_scenario_results() -> List[Dict[str, Any]]:
    """Generate sample stress test results."""
    
    results = []
    
    results.append({
        "id": "result_001",
        "scenario_id": "stress_001",
        "run_date": "2024-08-15",
        "status": "completed",
        "summary": {
            "corridors_tested": 11,
            "corridors_passed": 8,
            "corridors_failed": 3,
            "capital_shortfall": 12_500_000,
            "remediation_required": True
        },
        "corridor_results": [
            {"corridor": "USD_INR", "status": "fail", "shortfall": 8_200_000, "current_buffer": 0.15, "required_buffer": 0.25},
            {"corridor": "EUR_INR", "status": "fail", "shortfall": 3_100_000, "current_buffer": 0.12, "required_buffer": 0.20},
            {"corridor": "GBP_INR", "status": "fail", "shortfall": 1_200_000, "current_buffer": 0.10, "required_buffer": 0.18},
            {"corridor": "AED_INR", "status": "pass", "shortfall": 0, "current_buffer": 0.18, "required_buffer": 0.15},
            {"corridor": "SGD_INR", "status": "pass", "shortfall": 0, "current_buffer": 0.20, "required_buffer": 0.15},
        ],
        "recommendations": [
            "Increase USD_INR buffer to 25% minimum",
            "Review EUR_INR correspondent credit lines",
            "Consider FX hedging for INR exposure"
        ],
        "approved_by": "R. Sharma",
        "approval_date": "2024-08-16",
        "synthetic": True
    })
    
    results.append({
        "id": "result_002",
        "scenario_id": "stress_003",
        "run_date": "2024-08-20",
        "status": "completed",
        "summary": {
            "corridors_tested": 11,
            "corridors_passed": 11,
            "corridors_failed": 0,
            "capital_shortfall": 0,
            "remediation_required": False
        },
        "corridor_results": [
            {"corridor": "USD_INR", "status": "pass", "shortfall": 0, "current_buffer": 0.22, "required_buffer": 0.20},
            {"corridor": "EUR_INR", "status": "pass", "shortfall": 0, "current_buffer": 0.18, "required_buffer": 0.18},
        ],
        "recommendations": [
            "Current buffers adequate for month-end stress",
            "Continue monitoring month-end patterns"
        ],
        "approved_by": "R. Sharma",
        "approval_date": "2024-08-21",
        "synthetic": True
    })
    
    return results


def main():
    """Generate stress scenario data."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("Generating stress test scenarios...")
    
    # Generate scenarios
    scenarios = generate_stress_scenarios()
    scenarios_file = OUTPUT_DIR / "stress_scenarios.json"
    with open(scenarios_file, "w") as f:
        json.dump(scenarios, f, indent=2)
    print(f"  ✓ Generated {len(scenarios)} scenarios")
    
    # Generate results
    results = generate_scenario_results()
    results_file = OUTPUT_DIR / "stress_results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"  ✓ Generated {len(results)} result records")
    
    print("\n✅ Stress scenario generation complete!")


if __name__ == "__main__":
    main()
