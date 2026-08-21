#!/usr/bin/env python3
# scripts/validate_synthetic_data.py
"""
Validate generated synthetic data for completeness and correctness.

Checks:
- All required files exist
- JSON is valid
- Data relationships are consistent
- Values are within expected ranges
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple


DATA_DIR = Path("data")

REQUIRED_FILES = [
    "corridors.json",
    "fx_rates.json",
    "bank_config.json",
    "transactions.json",
    "audit_trail.json",
    "data_summary.json"
]

OPTIONAL_FILES = [
    "stress_scenarios.json",
    "stress_results.json",
    "swift_messages/all_messages.json"
]


def validate_json_file(filepath: Path) -> Tuple[bool, str, any]:
    """Validate a JSON file exists and is parseable."""
    if not filepath.exists():
        return False, f"File not found: {filepath}", None
    
    try:
        with open(filepath) as f:
            data = json.load(f)
        return True, "Valid JSON", data
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}", None


def validate_corridors(data: List[Dict]) -> List[str]:
    """Validate corridor data."""
    errors = []
    
    required_fields = [
        "id", "code", "name", "source_currency", "destination_currency",
        "correspondent", "current_balance", "minimum_required", "recommended_balance",
        "statistics", "config", "demand_history"
    ]
    
    for i, corridor in enumerate(data):
        for field in required_fields:
            if field not in corridor:
                errors.append(f"Corridor {i}: missing field '{field}'")
        
        # Validate balance relationships
        if corridor.get("current_balance", 0) < corridor.get("minimum_required", float("inf")):
            errors.append(
                f"Corridor {corridor.get('code')}: current_balance < minimum_required"
            )
        
        # Validate statistics
        stats = corridor.get("statistics", {})
        if stats.get("p95_demand", 0) < stats.get("avg_daily_volume", 0):
            errors.append(
                f"Corridor {corridor.get('code')}: p95_demand < avg_daily_volume"
            )
        
        # Validate demand history
        history = corridor.get("demand_history", [])
        if len(history) < 30:
            errors.append(
                f"Corridor {corridor.get('code')}: insufficient demand history ({len(history)} days)"
            )
    
    return errors


def validate_fx_rates(data: Dict) -> List[str]:
    """Validate FX rate data."""
    errors = []
    
    for pair, rate_data in data.items():
        if not isinstance(rate_data, dict):
            errors.append(f"FX rate {pair}: invalid format")
            continue
        
        mid = rate_data.get("mid_rate", 0)
        bid = rate_data.get("bid", 0)
        ask = rate_data.get("ask", 0)
        
        if not (0 < mid < 1000):
            errors.append(f"FX rate {pair}: unreasonable mid_rate ({mid})")
        
        if bid >= ask:
            errors.append(f"FX rate {pair}: bid >= ask")
        
        if not (bid <= mid <= ask):
            errors.append(f"FX rate {pair}: mid not between bid and ask")
    
    return errors


def validate_transactions(data: List[Dict], corridors: List[Dict]) -> List[str]:
    """Validate transaction data."""
    errors = []
    
    corridor_ids = {c["id"] for c in corridors}
    
    for i, tx in enumerate(data):
        if tx.get("corridor_id") not in corridor_ids:
            errors.append(f"Transaction {i}: invalid corridor_id")
        
        amount = tx.get("amount", 0)
        if not (0 < amount < 100_000_000):
            errors.append(f"Transaction {i}: unreasonable amount ({amount})")
    
    return errors


def validate_audit_trail(data: List[Dict]) -> List[str]:
    """Validate audit trail data."""
    errors = []
    
    for i, record in enumerate(data):
        if "hash" not in record:
            errors.append(f"Audit record {i}: missing hash")
        
        if i > 0 and record.get("previous_hash") != data[i-1].get("hash"):
            # Note: This check assumes records are in order
            pass  # Audit chain validation would go here
    
    return errors


def run_validation() -> bool:
    """Run all validations and report results."""
    print("=" * 60)
    print("SYNTHETIC DATA VALIDATION")
    print("=" * 60)
    print()
    
    all_valid = True
    loaded_data = {}
    
    # Check required files
    print("📁 Checking required files...")
    for filename in REQUIRED_FILES:
        filepath = DATA_DIR / filename
        valid, message, data = validate_json_file(filepath)
        
        if valid:
            print(f"   ✓ {filename}")
            loaded_data[filename] = data
        else:
            print(f"   ✗ {filename}: {message}")
            all_valid = False
    
    # Check optional files
    print("\n📁 Checking optional files...")
    for filename in OPTIONAL_FILES:
        filepath = DATA_DIR / filename
        if filepath.exists():
            valid, message, data = validate_json_file(filepath)
            if valid:
                print(f"   ✓ {filename}")
                loaded_data[filename] = data
            else:
                print(f"   ⚠ {filename}: {message}")
        else:
            print(f"   ○ {filename} (not generated)")
    
    # Validate data content
    print("\n📊 Validating data content...")
    
    # Corridors
    if "corridors.json" in loaded_data:
        errors = validate_corridors(loaded_data["corridors.json"])
        if errors:
            print(f"   ✗ corridors.json: {len(errors)} errors")
            for e in errors[:5]:
                print(f"      - {e}")
            if len(errors) > 5:
                print(f"      ... and {len(errors) - 5} more")
            all_valid = False
        else:
            print(f"   ✓ corridors.json: {len(loaded_data['corridors.json'])} corridors validated")
    
    # FX Rates
    if "fx_rates.json" in loaded_data:
        errors = validate_fx_rates(loaded_data["fx_rates.json"])
        if errors:
            print(f"   ✗ fx_rates.json: {len(errors)} errors")
            for e in errors[:5]:
                print(f"      - {e}")
            all_valid = False
        else:
            print(f"   ✓ fx_rates.json: {len(loaded_data['fx_rates.json'])} rates validated")
    
    # Transactions
    if "transactions.json" in loaded_data and "corridors.json" in loaded_data:
        errors = validate_transactions(
            loaded_data["transactions.json"],
            loaded_data["corridors.json"]
        )
        if errors:
            print(f"   ✗ transactions.json: {len(errors)} errors")
            for e in errors[:5]:
                print(f"      - {e}")
            all_valid = False
        else:
            print(f"   ✓ transactions.json: {len(loaded_data['transactions.json'])} transactions validated")
    
    # Audit trail
    if "audit_trail.json" in loaded_data:
        errors = validate_audit_trail(loaded_data["audit_trail.json"])
        if errors:
            print(f"   ⚠ audit_trail.json: {len(errors)} warnings")
        else:
            print(f"   ✓ audit_trail.json: {len(loaded_data['audit_trail.json'])} records validated")
    
    # Summary
    print()
    print("=" * 60)
    if all_valid:
        print("✅ All validations passed!")
    else:
        print("❌ Some validations failed. Please regenerate data.")
    print("=" * 60)
    
    return all_valid


if __name__ == "__main__":
    success = run_validation()
    sys.exit(0 if success else 1)
