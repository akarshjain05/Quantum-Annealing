import math
import random
import time
from qubo_builder import build_qubo, decode_solution

# ---------------------------------------------------------------------
# 1. Production solver: D-Wave's neal (pip install dwave-neal dimod)
# ---------------------------------------------------------------------
def solve_with_neal(Q, num_reads=200, num_sweeps=1000, seed=None):
    import dimod
    import neal

    bqm = dimod.BinaryQuadraticModel.from_qubo(Q)
    sampler = neal.SimulatedAnnealingSampler()
    sampleset = sampler.sample(
        bqm, num_reads=num_reads, num_sweeps=num_sweeps, seed=seed
    )
    # sampleset is sorted by energy already; return list of (bits, energy)
    n = bqm.num_variables
    results = []
    for sample, energy in sampleset.data(fields=["sample", "energy"]):
        bits = [int(sample[i]) for i in range(n)]
        results.append((bits, energy))
    return results

# ---------------------------------------------------------------------
# 2. From-scratch SA -- efficient single-bit-flip local search
# ---------------------------------------------------------------------
def _neighbors(Q, n):
    adj = [[] for _ in range(n)]
    diag = [0.0] * n
    for (i, j), w in Q.items():
        if i == j:
            diag[i] += w
        else:
            adj[i].append((j, w))
            adj[j].append((i, w))
    return diag, adj

def _local_field(i, x, diag, adj):
    total = diag[i]
    for j, w in adj[i]:
        total += w * x[j]
    return total

def solve_with_custom_sa(Q, n_vars, num_reads=20, num_sweeps=2000,
                          t_start=None, t_end=1e-2, seed=None):
    rng = random.Random(seed)
    diag, adj = _neighbors(Q, n_vars)

    if t_start is None:
        max_coeff = max((abs(w) for w in Q.values()), default=1.0)
        t_start = max(max_coeff * 0.05, 1.0)

    best_bits, best_energy = None, math.inf

    for _ in range(num_reads):
        x = [rng.randint(0, 1) for _ in range(n_vars)]
        for sweep in range(num_sweeps):
            frac = sweep / max(num_sweeps - 1, 1)
            T = t_start * (t_end / t_start) ** frac
            for i in rng.sample(range(n_vars), n_vars):
                dE = (1 - 2 * x[i]) * _local_field(i, x, diag, adj)
                if dE <= 0 or rng.random() < math.exp(-dE / T):
                    x[i] = 1 - x[i]

        e = sum(w * x[i] * (x[j] if i != j else 1) for (i, j), w in Q.items())
        if e < best_energy:
            best_energy, best_bits = e, x[:]

    return best_bits, best_energy

# ---------------------------------------------------------------------
# 3. QAOA Quantum Solver
# ---------------------------------------------------------------------
def solve_with_qaoa(Q, n_vars, reps=2, shots=1024, optimizer_maxiter=100, seed=None):
    """
    Returns: (bits: list[int], energy: float, wall_time_seconds: float)
    Solves Q via QAOA on Qiskit's statevector/sampler simulator (NOT real hardware).
    Only intended for small n_vars (<= ~16-18) -- caller is responsible for
    restricting problem size before calling this.
    """
    if n_vars > 18:
        raise ValueError("QAOA path only supports small instances — reduce corridors/n_bits before calling")

    t0 = time.time()
    
    from qiskit_optimization import QuadraticProgram
    from qiskit_algorithms import QAOA
    from qiskit_algorithms.optimizers import COBYLA
    from qiskit_optimization.algorithms import MinimumEigenOptimizer
    from qiskit.primitives import StatevectorSampler as Sampler
    
    qp = QuadraticProgram()
    for i in range(n_vars):
        qp.binary_var(f"x_{i}")
        
    linear = {}
    quadratic = {}
    
    for (i, j), w in Q.items():
        name_i = f"x_{i}"
        name_j = f"x_{j}"
        if i == j:
            linear[name_i] = linear.get(name_i, 0) + w
        else:
            if i < j:
                quadratic[(name_i, name_j)] = quadratic.get((name_i, name_j), 0) + w
            else:
                quadratic[(name_j, name_i)] = quadratic.get((name_j, name_i), 0) + w

    qp.minimize(linear=linear, quadratic=quadratic)
    
    sampler = Sampler()
    if seed is not None:
        sampler.set_options(seed=seed)
        
    optimizer = COBYLA(maxiter=optimizer_maxiter)
    qaoa = QAOA(sampler=sampler, optimizer=optimizer, reps=reps)
    
    optimizer_algo = MinimumEigenOptimizer(qaoa)
    result = optimizer_algo.solve(qp)
    
    bits = [int(result.x[i]) for i in range(n_vars)]
    energy = result.fval
    elapsed_time = time.time() - t0
    
    return bits, energy, elapsed_time

# ---------------------------------------------------------------------
# Feasibility filtering
# ---------------------------------------------------------------------
def is_feasible(bits, var_index, corridors, lot_size, n_bits, budget=None):
    funded = decode_solution(bits, var_index, corridors, lot_size, n_bits)
    for c in corridors:
        if funded[c["name"]] < c["volume"]:
            return False, funded
    if budget is not None and sum(funded.values()) > budget:
        return False, funded
    return True, funded

def best_feasible(results, var_index, corridors, lot_size, n_bits, budget=None):
    best = None
    for bits, energy in results:
        feasible, funded = is_feasible(bits, var_index, corridors, lot_size, n_bits, budget)
        if not feasible:
            continue
        total = sum(funded.values())
        if best is None or total < best[0]:
            best = (total, funded, bits)
    return best

if __name__ == "__main__":
    corridors = [
        {"name": "USD_INR", "volume": 820_000},
        {"name": "EUR_USD", "volume": 640_000},
        {"name": "GBP_USD", "volume": 390_000},
        {"name": "AED_INR", "volume": 210_000},
        {"name": "SGD_USD", "volume": 175_000},
    ]
    lot_size, n_bits, budget = 10_000, 7, 2_500_000
    
    # We pass n_slack_bits=7 for the actual model
    Q, var_index = build_qubo(corridors, lot_size=lot_size, n_bits=n_bits, n_slack_bits=7, budget=budget)
    n_vars = len(corridors) * (n_bits + 7)  # n_bits + n_slack_bits
    
    print(f"Problem size: {n_vars} binary variables, {len(Q)} QUBO terms\n")

    t0 = time.time()
    results = solve_with_neal(Q, num_reads=200)
    t1 = time.time()
    picked = best_feasible(results, var_index, corridors, lot_size, n_bits, budget)
    print(f"[neal]   {t1 - t0:.2f}s for 200 reads")
    if picked:
        total, funded, _ = picked
        print(f"[neal]   feasible solution found, total funded = ${total:,.0f}")
        for c in corridors:
            print(f"           {c['name']:8s}  funded ${funded[c['name']]:>9,.0f}  "
                  f"required ${c['volume']:>9,.0f}")
    else:
        print("[neal]   no feasible solution in this batch of reads")

    t0 = time.time()
    bits, energy = solve_with_custom_sa(Q, n_vars, num_reads=20, num_sweeps=1500)
    t1 = time.time()
    feasible, funded = is_feasible(bits, var_index, corridors, lot_size, n_bits, budget)
    print(f"\n[custom] {t1 - t0:.2f}s for 20 reads x 1500 sweeps")
    print(f"[custom] feasible={feasible}, total funded = ${sum(funded.values()):,.0f}")

    # --- brute-force sanity check on a tiny dedicated test case ---
    bf_lot, bf_bits = 10_000, 4
    small = [
        {"name": "USD_INR", "volume": 80_000},
        {"name": "EUR_USD", "volume": 60_000},
    ]
    Qs, vi_s = build_qubo(small, lot_size=bf_lot, n_bits=bf_bits, n_slack_bits=bf_bits, budget=None)
    ns = len(small) * (bf_bits + bf_bits)
    best_bf, best_bf_e = None, math.inf
    for combo in range(2 ** ns):
        bits_bf = [(combo >> k) & 1 for k in range(ns)]
        e = sum(w * bits_bf[i] * (bits_bf[j] if i != j else 1) for (i, j), w in Qs.items())
        if e < best_bf_e:
            best_bf_e, best_bf = e, bits_bf
    feasible_bf, funded_bf = is_feasible(best_bf, vi_s, small, bf_lot, bf_bits)
    print(f"\n[brute-force check, 2 corridors, {ns} vars, {2**ns} combos]")
    print(f"  feasible={feasible_bf}, funded={funded_bf}")
