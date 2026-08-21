# NostroQ Synthetic Data

## ⚠️ IMPORTANT DISCLOSURE

**All data in this directory is SYNTHETIC.**

This data was generated programmatically for demonstration purposes only.
No real banking, customer, or transaction data was used or sourced.

## Data Files

| File | Description | Records |
|------|-------------|---------|
| `corridors.json` | Nostro corridor configurations | 11 corridors |
| `fx_rates.json` | FX rate data | 14 currency pairs |
| `bank_config.json` | Bank configuration | 1 config |
| `transactions.json` | Sample transactions | ~350 records |
| `audit_trail.json` | Audit trail records | 50 records |
| `stress_scenarios.json` | Stress test scenarios | 8 scenarios |
| `stress_results.json` | Stress test results | 2 result sets |
| `swift_messages/` | Sample SWIFT messages | ~20 messages |

## Generation

Data was generated using:

```bash
./scripts/run_data_generation.sh
```

Or individually:

```bash
python scripts/generate_synthetic_data.py
python scripts/generate_stress_scenarios.py
python scripts/generate_swift_messages.py
```

## Validation

To validate data integrity:

```bash
python scripts/validate_synthetic_data.py
```

## Data Characteristics

### Corridors
- 11 realistic currency corridors (USD/INR, EUR/INR, etc.)
- 90 days of historical demand data per corridor
- Includes weekly/monthly seasonality
- Random spikes for stress testing
- Realistic correspondent bank details

### Transactions
- 7 days of transaction history
- Log-normal distribution for amounts
- Realistic SWIFT-style references
- Linked to corridor IDs

### FX Rates
- Mid, bid, ask rates
- Realistic spread (5-20 bps)
- Based on approximate market rates

## Reproducibility
All random generation uses seed 42 for reproducibility. Running generation scripts multiple times will produce identical data.

## Usage

```python
import json
from pathlib import Path

# Load corridors
with open("data/corridors.json") as f:
    corridors = json.load(f)

# Access first corridor
corridor = corridors[0]
print(f"Corridor: {corridor['code']}")
print(f"Current Balance: ${corridor['current_balance']:,.2f}")
print(f"Recommended: ${corridor['recommended_balance']:,.2f}")
```

## License
This synthetic data is provided under the same license as the NostroQ project.
