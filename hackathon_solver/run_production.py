import json
import time
from solver import solve_with_neal, solve_with_custom_sa, best_feasible, is_feasible
from qubo_builder import build_qubo

def run_production():
    # 1. Load synthetic data
    with open("synthetic_data/corridors.json") as f:
        corridors = json.load(f)
        
    lot_size, n_bits, budget = 10_000, 7, 5_000_000
    
    Q, var_index = build_qubo(corridors, lot_size=lot_size, n_bits=n_bits, n_slack_bits=7, budget=budget)
    n_vars = len(corridors) * (n_bits + 7)
    
    results = {}
    
    # Run Neal
    t0 = time.time()
    neal_res = solve_with_neal(Q, num_reads=50, num_sweeps=500)
    time_neal = time.time() - t0
    picked_neal = best_feasible(neal_res, var_index, corridors, lot_size, n_bits, budget)
    results["Neal"] = {
        "time": time_neal,
        "feasible": picked_neal is not None,
        "total_funded": picked_neal[0] if picked_neal else None
    }
    
    # Run Custom SA
    t0 = time.time()
    bits_sa, energy_sa = solve_with_custom_sa(Q, n_vars, num_reads=10, num_sweeps=1000)
    time_sa = time.time() - t0
    feasible_sa, funded_sa = is_feasible(bits_sa, var_index, corridors, lot_size, n_bits, budget)
    results["Custom_SA"] = {
        "time": time_sa,
        "feasible": feasible_sa,
        "total_funded": sum(funded_sa.values()) if feasible_sa else None
    }
    
    with open("production_scale_results.json", "w") as f:
        json.dump(results, f, indent=4)
        
    print("Stage 4 complete. Saved to production_scale_results.json")

if __name__ == '__main__':
    run_production()
