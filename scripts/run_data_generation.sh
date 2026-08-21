#!/bin/bash
# scripts/run_data_generation.sh
# Complete data generation pipeline

set -e

echo "========================================"
echo "NostroQ Synthetic Data Generation"
echo "========================================"
echo ""
echo "⚠️  DISCLOSURE: All data is synthetic."
echo "    No real banking data is used."
echo ""

# Change to project root
cd "$(dirname "$0")/.."

# Create data directory
mkdir -p data

# Step 1: Generate main data
echo "Step 1: Generating core data..."
python scripts/generate_synthetic_data.py --output data

# Step 2: Generate stress scenarios
echo ""
echo "Step 2: Generating stress scenarios..."
python scripts/generate_stress_scenarios.py

# Step 3: Generate SWIFT messages
echo ""
echo "Step 3: Generating SWIFT messages..."
python scripts/generate_swift_messages.py

# Step 4: Validate all data
echo ""
echo "Step 4: Validating generated data..."
python scripts/validate_synthetic_data.py

echo ""
echo "========================================"
echo "Data generation complete!"
echo "========================================"
echo ""
echo "Generated files:"
ls -la data/
echo ""
echo "To use this data, ensure your backend loads from the 'data/' directory."
