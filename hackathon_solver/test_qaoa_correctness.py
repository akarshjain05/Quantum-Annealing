import math
from qubo_builder import build_qubo, decode_solution
from solver import solve_with_custom_sa, solve_with_qaoa, is_feasible

def run_tests():
    bf_lot, bf_bits = 10_000, 4
    small = [
        {"name": "USD_INR", "volume": 80_000},
        {"name": "EUR_USD", "volume": 60_000},
    ]
    Qs, vi_s = build_qubo(small, lot_size=bf_lot, n_bits=bf_bits, n_slack_bits=bf_bits, budget=None)
    ns = len(small) * (bf_bits + bf_bits)
    
    # Brute-force
    best_bf, best_bf_e = None, math.inf
    import time
    t0 = time.time()
    for combo in range(2 ** ns):
        bits_bf = [(combo >> k) & 1 for k in range(ns)]
        e = sum(w * bits_bf[i] * (bits_bf[j] if i != j else 1) for (i, j), w in Qs.items())
        if e < best_bf_e:
            best_bf_e, best_bf = e, bits_bf
    bf_time = time.time() - t0
    feasible_bf, funded_bf = is_feasible(best_bf, vi_s, small, bf_lot, bf_bits)
    
    # Custom SA
    t0 = time.time()
    bits_sa, energy_sa = solve_with_custom_sa(Qs, ns, num_reads=20, num_sweeps=1500)
    sa_time = time.time() - t0
    feasible_sa, funded_sa = is_feasible(bits_sa, vi_s, small, bf_lot, bf_bits)
    
    # QAOA
    best_qaoa_energy = math.inf
    best_qaoa_bits = None
    qaoa_time_total = 0
    for _ in range(3):
        bits_q, energy_q, wall_time_q = solve_with_qaoa(Qs, ns, reps=1, shots=1024, optimizer_maxiter=50)
        qaoa_time_total += wall_time_q
        if energy_q < best_qaoa_energy:
            best_qaoa_energy = energy_q
            best_qaoa_bits = bits_q
            
    feasible_qaoa, funded_qaoa = is_feasible(best_qaoa_bits, vi_s, small, bf_lot, bf_bits)
    
    # Print results
    print(f"{'Solver':<15} | {'Feasible':<10} | {'Total Funded':<15} | {'Energy':<10} | {'Wall Time (s)':<15}")
    print("-" * 75)
    print(f"{'Brute-Force':<15} | {str(feasible_bf):<10} | {sum(funded_bf.values()):<15} | {best_bf_e:<10.2f} | {bf_time:<15.4f}")
    print(f"{'Custom SA':<15} | {str(feasible_sa):<10} | {sum(funded_sa.values()):<15} | {energy_sa:<10.2f} | {sa_time:<15.4f}")
    print(f"{'QAOA':<15} | {str(feasible_qaoa):<10} | {sum(funded_qaoa.values()):<15} | {best_qaoa_energy:<10.2f} | {qaoa_time_total:<15.4f}")

    assert sum(funded_bf.values()) == sum(funded_sa.values()), "SA did not match brute force"
    assert sum(funded_bf.values()) == sum(funded_qaoa.values()), "QAOA did not match brute force"

if __name__ == '__main__':
    run_tests()
