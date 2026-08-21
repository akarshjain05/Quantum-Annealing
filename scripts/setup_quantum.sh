#!/bin/bash
# scripts/setup_quantum.sh
# Setup script for quantum solver dependencies

echo "========================================"
echo "NostroQ Quantum Solver Setup"
echo "========================================"

# Check Python version
python_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
echo "Python version: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

echo ""
echo "Installing core dependencies..."
pip install numpy scipy

echo ""
echo "Installing Qiskit ecosystem..."
pip install qiskit qiskit-aer

# Try to install qiskit-algorithms (may fail on some systems)
echo ""
echo "Installing Qiskit algorithms (optional)..."
pip install qiskit-algorithms || echo "⚠ qiskit-algorithms failed, continuing..."

# Try to install qiskit-optimization (may fail on some systems)
echo ""
echo "Installing Qiskit optimization (optional)..."
pip install qiskit-optimization || echo "⚠ qiskit-optimization failed, continuing..."

echo ""
echo "Installing D-Wave ecosystem..."
pip install dimod dwave-neal

echo ""
echo "Installing additional dependencies..."
pip install matplotlib pytest faker

echo ""
echo "========================================"
echo "Verifying installation..."
echo "========================================"

python3 -c "
import sys
print(f'Python: {sys.version}')

try:
    import numpy as np
    print(f'✓ NumPy: {np.__version__}')
except ImportError as e:
    print(f'✗ NumPy: {e}')

try:
    import qiskit
    print(f'✓ Qiskit: {qiskit.__version__}')
except ImportError as e:
    print(f'✗ Qiskit: {e}')

try:
    from qiskit_aer import AerSimulator
    print(f'✓ Qiskit Aer: available')
except ImportError as e:
    print(f'✗ Qiskit Aer: {e}')

try:
    from qiskit_algorithms import QAOA
    print(f'✓ Qiskit Algorithms: available')
except ImportError as e:
    print(f'⚠ Qiskit Algorithms: {e}')

try:
    from qiskit_optimization import QuadraticProgram
    print(f'✓ Qiskit Optimization: available')
except ImportError as e:
    print(f'⚠ Qiskit Optimization: {e}')

try:
    import dimod
    print(f'✓ D-Wave dimod: {dimod.__version__}')
except ImportError as e:
    print(f'✗ D-Wave dimod: {e}')

try:
    from neal import SimulatedAnnealingSampler
    print(f'✓ D-Wave Neal: available')
except ImportError as e:
    print(f'✗ D-Wave Neal: {e}')
"

echo ""
echo "========================================"
echo "Running quick test..."
echo "========================================"

cd backend
python3 -c "
from app.optimization.quantum_solver import demo
demo()
"

echo ""
echo "========================================"
echo "Setup complete!"
echo "========================================"
echo ""
echo "To activate the environment:"
echo "  source venv/bin/activate"
echo ""
echo "To run the quantum solver demo:"
echo "  cd backend && python -c 'from app.optimization.quantum_solver import demo; demo()'"
echo ""
echo "To run tests:"
echo "  cd backend && python -m pytest test_quantum_solver.py -v"
