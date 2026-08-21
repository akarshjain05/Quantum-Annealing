import json
import time
import math
import matplotlib.pyplot as plt
import numpy as np

from qubo_builder import build_qubo, decode_solution
from solver import solve_with_custom_sa, solve_with_neal, solve_with_qaoa, is_feasible, best_feasible

def run_benchmark():
    bf_lot, bf_bits = 10_000, 4
    small = [
        {"name": "USD_INR", "volume": 80_000},
        {"name": "EUR_USD", "volume": 60_000},
    ]
    Qs, vi_s = build_qubo(small, lot_size=bf_lot, n_bits=bf_bits, n_slack_bits=bf_bits, budget=None)
    ns = len(small) * (bf_bits + bf_bits)
    
    results = {}
    
    # 1. Custom SA
    t0 = time.time()
    bits_sa, energy_sa = solve_with_custom_sa(Qs, ns, num_reads=20, num_sweeps=1500)
    time_sa = time.time() - t0
    feasible_sa, _ = is_feasible(bits_sa, vi_s, small, bf_lot, bf_bits)
    results["Custom SA"] = {"time": time_sa, "energy": energy_sa, "feasible": feasible_sa}
    
    # 2. Neal (D-Wave SA)
    t0 = time.time()
    neal_res = solve_with_neal(Qs, num_reads=200, num_sweeps=1000)
    time_neal = time.time() - t0
    best_neal_energy = neal_res[0][1]
    feasible_neal, _ = is_feasible(neal_res[0][0], vi_s, small, bf_lot, bf_bits)
    results["Neal"] = {"time": time_neal, "energy": best_neal_energy, "feasible": feasible_neal}
    
    # 3. QAOA
    # Run once for benchmark
    bits_q, energy_q, time_qaoa = solve_with_qaoa(Qs, ns, reps=1, shots=1024, optimizer_maxiter=50)
    feasible_qaoa, _ = is_feasible(bits_q, vi_s, small, bf_lot, bf_bits)
    results["QAOA"] = {"time": time_qaoa, "energy": energy_q, "feasible": feasible_qaoa}
    
    # Save JSON
    with open("benchmark_results.json", "w") as f:
        json.dump(results, f, indent=4)
        
    # Plot Chart
    labels = list(results.keys())
    times = [results[l]["time"] for l in labels]
    energies = [results[l]["energy"] for l in labels]
    
    x = np.arange(len(labels))
    width = 0.35
    
    fig, ax1 = plt.subplots(figsize=(8, 6))
    
    rects1 = ax1.bar(x - width/2, times, width, label='Wall Time (s)', color='skyblue')
    ax1.set_ylabel('Wall Time (seconds)')
    ax1.set_title('Solver Benchmark (2-Corridor Toy Instance)\nNote: QAOA is for correctness demonstration only, not speed.')
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels)
    
    ax2 = ax1.twinx()
    rects2 = ax2.bar(x + width/2, energies, width, label='Energy', color='salmon')
    ax2.set_ylabel('Energy')
    
    fig.legend(loc="upper right", bbox_to_anchor=(1,1), bbox_transform=ax1.transAxes)
    
    fig.tight_layout()
    plt.savefig("benchmark_chart.png")
    print("Benchmark complete. Created benchmark_chart.png and benchmark_results.json")

if __name__ == '__main__':
    run_benchmark()
