"""
Comparison script to generate the Classical vs. Quantum Comparison Chart
required for Track 2 submission (Section 8.7).

Evaluates a small instance of the Nostro Liquidity QUBO problem across:
1. Brute-Force (optimal baseline)
2. Classical Simulated Annealing (production heuristic)
3. QAOA on Qiskit Aer (Quantum simulator execution)
"""
import time
import numpy as np

from app.optimization.qubo import build_qubo, CorridorInput
from app.optimization.annealing import simulated_annealing
from app.optimization.qaoa import solve_qaoa

def run_brute_force(qubo_model):
    """Exhaustive search for the exact minimum."""
    t0 = time.perf_counter()
    n = qubo_model.num_vars
    best_x = None
    best_energy = float('inf')
    
    # 2^n space
    for i in range(1 << n):
        # Create bit array
        x = np.array([(i >> j) & 1 for j in range(n)], dtype=np.float64)
        
        # Calculate energy x^T Q x
        e = float(x @ (qubo_model.Q @ x))
        
        if e < best_energy:
            best_energy = e
            best_x = x.copy()
            
    runtime_ms = (time.perf_counter() - t0) * 1000.0
    return best_x, best_energy, runtime_ms


def main():
    print("Initializing small Nostro Liquidity QUBO instance (Tractable for QAOA simulator)...")
    # Reduced slice: 2 corridors x 3 buckets = 6 qubits
    # This is small enough to solve quickly on local Qiskit Aer statevector
    corridors = [
        CorridorInput(
            corridor_id=1, code="EUR", mu=10.0, sigma=2.0, 
            current_liquidity=5.0, opportunity_cost_rate=0.05, 
            loss_given_shortfall=0.1, fx_cost_bps=10, operational_cost_rate=0.01
        ),
        CorridorInput(
            corridor_id=2, code="GBP", mu=5.0, sigma=1.0, 
            current_liquidity=2.0, opportunity_cost_rate=0.06, 
            loss_given_shortfall=0.15, fx_cost_bps=12, operational_cost_rate=0.01
        )
    ]
    # 3 buckets
    buckets = [0.0, 5.0, 10.0]
    
    qubo_model = build_qubo(corridors, buckets=buckets)
    print(f"QUBO generated. Number of variables (qubits): {qubo_model.num_vars}")
    print("-" * 60)
    
    # 1. Brute-Force
    print("Running Brute-Force (Optimal Baseline)...")
    bf_x, bf_energy, bf_time = run_brute_force(qubo_model)
    
    # 2. Classical SA
    print("Running Classical Simulated Annealing...")
    sa_result = simulated_annealing(qubo_model.Q, qubo_model.num_vars, iterations=1000, num_restarts=3)
    
    # 3. QAOA on Qiskit Aer
    print("Running QAOA on Qiskit Aer (Local Quantum Simulator)...")
    qaoa_result = solve_qaoa(qubo_model, reps=1, maxiter=30)
    
    # Print Comparison Chart
    print("\n" + "=" * 60)
    print(" CLASSICAL VS. QUANTUM COMPARISON CHART (Track 2, Sec 8.7)")
    print("=" * 60)
    print(f"{'Solver':<25} | {'Solution Quality (Energy)':<25} | {'Time to Solution (ms)':<20}")
    print("-" * 75)
    print(f"{'Brute-Force (Optimal)':<25} | {bf_energy:<25.4f} | {bf_time:<20.2f}")
    print(f"{'Classical SA':<25} | {sa_result.best_energy:<25.4f} | {sa_result.runtime_ms:<20.2f}")
    print(f"{'QAOA (Qiskit Aer)':<25} | {qaoa_result.best_energy:<25.4f} | {qaoa_result.runtime_ms:<20.2f}")
    print("=" * 60)
    print("\nNote: QAOA execution time includes Qiskit circuit compilation and simulation overhead.")

    # Mixed in from hackathon_solver: Plot Chart
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        
        labels = ["Brute-Force", "Classical SA", "QAOA (Qiskit Aer)"]
        times = [bf_time, sa_result.runtime_ms, qaoa_result.runtime_ms]
        energies = [bf_energy, sa_result.best_energy, qaoa_result.best_energy]
        
        x = np.arange(len(labels))
        width = 0.35
        
        fig, ax1 = plt.subplots(figsize=(8, 6))
        
        rects1 = ax1.bar(x - width/2, times, width, label='Wall Time (ms)', color='skyblue')
        ax1.set_ylabel('Wall Time (ms)')
        ax1.set_title('Solver Benchmark (Nostro Liquidity QUBO)\nNote: QAOA is for correctness demonstration only, not speed.')
        ax1.set_xticks(x)
        ax1.set_xticklabels(labels)
        
        ax2 = ax1.twinx()
        rects2 = ax2.bar(x + width/2, energies, width, label='Energy', color='salmon')
        ax2.set_ylabel('Energy')
        
        fig.legend(loc="upper right", bbox_to_anchor=(1,1), bbox_transform=ax1.transAxes)
        
        fig.tight_layout()
        plt.savefig("benchmark_chart.png")
        print("\nBenchmark complete. Created benchmark_chart.png")
    except ImportError:
        print("\nNote: matplotlib is not installed, skipping benchmark_chart.png generation.")

if __name__ == "__main__":
    main()
