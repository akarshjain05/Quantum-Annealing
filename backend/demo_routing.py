import sys
import logging

# Configure basic logging so we see the benchmark logs
logging.basicConfig(level=logging.INFO, format='%(message)s')
# Suppress Qiskit noise
logging.getLogger("qiskit").setLevel(logging.WARNING)

from app.optimization.qubo import build_qubo, CorridorInput
from app.optimization.quantum_solver import QuantumBenchmark, QUBOProblem, SolverRegistry, SolverType

def create_problem(num_corridors, buckets):
    corridors = []
    for i in range(num_corridors):
        corridors.append(
            CorridorInput(
                corridor_id=i+1, code=f"C{i+1}", mu=10.0, sigma=2.0, 
                current_liquidity=5.0, opportunity_cost_rate=0.05, 
                loss_given_shortfall=0.1, fx_cost_bps=10, operational_cost_rate=0.01
            )
        )
    qubo_model = build_qubo(corridors, buckets=buckets)
    return QUBOProblem(qubo_model.Q, [f"x_{i}" for i in range(qubo_model.num_vars)])

def main():
    benchmark = QuantumBenchmark(seed=42)
    # We will test just Brute-Force, Classical SA, and Qiskit QAOA for clarity
    test_solvers = [SolverType.CLASSICAL_SA_NUMPY, SolverType.QISKIT_QAOA]
    
    print("\n" + "="*70)
    print(" SCENARIO 1: SMALL INPUT (n <= 16)")
    print("="*70)
    # 2 corridors, 3 buckets = 6 variables
    small_problem = create_problem(2, [0.0, 5.0, 10.0])
    print(f"Problem Size: {small_problem.n} qubits")
    print("-" * 70)
    benchmark.run_benchmark(small_problem, solvers=test_solvers, skip_large_quantum=True)
    
    print("\n" + "="*70)
    print(" SCENARIO 2: LARGE INPUT (n > 16)")
    print("="*70)
    # 8 corridors, 8 buckets = 64 variables (exceeds QiskitQAOA max_variables=16)
    large_problem = create_problem(8, [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0])
    print(f"Problem Size: {large_problem.n} qubits")
    print("-" * 70)
    benchmark.run_benchmark(large_problem, solvers=test_solvers, skip_large_quantum=True)

if __name__ == "__main__":
    main()
