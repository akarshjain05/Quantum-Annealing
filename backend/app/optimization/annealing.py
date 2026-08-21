"""
Bit-flip simulated annealing solver for QUBO problems: minimize x^T Q x
over x in {0,1}^n.

Standard Metropolis acceptance: P(accept) = exp(-dE / T), cooling schedule
T_{k+1} = alpha * T_k. Uses incremental energy tracking (O(n) per flip via
Qx = Q @ x, updated incrementally) rather than recomputing x^T Q x from
scratch every iteration - this is the standard efficient QUBO SA
implementation, and its correctness is checked in tests/test_annealing.py
by comparing incremental energy against brute-force recomputation.
"""
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np


@dataclass
class AnnealingResult:
    best_x: np.ndarray
    best_energy: float
    initial_energy: float
    history: List[float]
    iterations: int
    runtime_ms: float


def energy(Q: np.ndarray, x: np.ndarray) -> float:
    return float(x @ (Q @ x))


def simulated_annealing(
    Q: np.ndarray,
    num_vars: int,
    iterations: int = 8000,
    initial_temp: float = 1000.0,
    cooling_rate: float = 0.995,
    seed: int = 42,
    num_restarts: int = 3,
    record_every: int = 25,
    initial_x: Optional[np.ndarray] = None,
) -> AnnealingResult:
    import time

    t0 = time.perf_counter()
    best_x_overall: Optional[np.ndarray] = None
    best_energy_overall: Optional[float] = None
    initial_energy_overall: Optional[float] = None
    history_overall: List[float] = []

    for restart in range(max(1, num_restarts)):
        rng = np.random.default_rng(seed + restart)
        if initial_x is not None:
            x = initial_x.copy().astype(np.float64)
        else:
            x = rng.integers(0, 2, size=num_vars).astype(np.float64)
        Qx = Q @ x
        cur_energy = float(x @ Qx)
        if initial_energy_overall is None or restart == 0:
            initial_energy_overall = cur_energy if restart == 0 else initial_energy_overall

        best_x = x.copy()
        best_energy = cur_energy
        T = initial_temp
        history: List[float] = [cur_energy]

        for it in range(iterations):
            j = int(rng.integers(0, num_vars))
            xj = x[j]
            # delta E for flipping bit j: (1 - 2*x_j) * (Q_jj + 2*(Qx_j - Q_jj*x_j))
            delta = (1.0 - 2.0 * xj) * (Q[j, j] + 2.0 * (Qx[j] - Q[j, j] * xj))

            accept = delta <= 0 or rng.random() < np.exp(-delta / max(T, 1e-9))
            if accept:
                new_xj = 1.0 - xj
                Qx = Qx + (new_xj - xj) * Q[:, j]
                x[j] = new_xj
                cur_energy += delta
                if cur_energy < best_energy:
                    best_energy = cur_energy
                    best_x = x.copy()

            T *= cooling_rate
            if it % record_every == 0:
                history.append(cur_energy)

        if best_energy_overall is None or best_energy < best_energy_overall:
            best_energy_overall = best_energy
            best_x_overall = best_x
            history_overall = history

    runtime_ms = (time.perf_counter() - t0) * 1000.0
    return AnnealingResult(
        best_x=best_x_overall,
        best_energy=best_energy_overall,
        initial_energy=initial_energy_overall,
        history=history_overall,
        iterations=iterations * num_restarts,
        runtime_ms=runtime_ms,
    )


from typing import Tuple, Dict, Any, List

def decode_assignment(best_x: np.ndarray, block_sizes: List[int]) -> Tuple[Dict[int, int], bool]:
    """Decode the flat binary vector into one bucket-index per block."""
    assignment = {}
    clean_onehot = True
    offset = 0
    for i, size in enumerate(block_sizes):
        row = best_x[offset:offset+size]
        active = np.where(row > 0.5)[0]
        if len(active) != 1:
            clean_onehot = False
        assignment[i] = int(np.argmax(row))
        offset += size
    return assignment, clean_onehot


def local_search_refine(Q: np.ndarray, x: np.ndarray, block_sizes: List[int], max_sweeps: int = 5) -> Tuple[np.ndarray, bool]:
    """Post-SA coordinate-descent refinement over one-hot blocks."""
    x = x.copy()
    improved_any = False
    for sweep in range(max_sweeps):
        improved = False
        offset = 0
        for i, size in enumerate(block_sizes):
            row = x[offset:offset+size]
            best_k = int(np.argmax(row))
            best_energy = None
            for k in range(size):
                trial = x.copy()
                trial[offset:offset+size] = 0
                trial[offset+k] = 1
                e = float(trial @ (Q @ trial))
                if best_energy is None or e < best_energy:
                    best_energy = e
                    best_k = k
            if best_k != int(np.argmax(x[offset:offset+size])):
                improved = True
                improved_any = True
            x[offset:offset+size] = 0
            x[offset+best_k] = 1
            offset += size
        if not improved:
            break
    return x, improved_any


def solve_with_qaoa(Q: np.ndarray, num_vars: int, reps: int = 2, shots: int = 1024, optimizer_maxiter: int = 100, seed: Optional[int] = None) -> AnnealingResult:
    """
    Solves Q via QAOA on Qiskit's statevector/sampler simulator (NOT real hardware).
    Only intended for small num_vars (<= ~16-18) -- caller is responsible for
    restricting problem size before calling this.
    """
    import time
    if num_vars > 18:
        raise ValueError("QAOA path only supports small instances — reduce corridors/buckets before calling")

    t0 = time.perf_counter()
    
    from qiskit_optimization import QuadraticProgram
    from qiskit_algorithms import QAOA
    from qiskit_algorithms.optimizers import COBYLA
    from qiskit_optimization.algorithms import MinimumEigenOptimizer
    from qiskit.primitives import StatevectorSampler as Sampler
    
    qp = QuadraticProgram()
    for i in range(num_vars):
        qp.binary_var(f"x_{i}")
        
    linear = {}
    quadratic = {}
    
    for i in range(num_vars):
        for j in range(num_vars):
            w = Q[i, j]
            if w == 0:
                continue
            name_i = f"x_{i}"
            name_j = f"x_{j}"
            if i == j:
                linear[name_i] = linear.get(name_i, 0) + float(w)
            else:
                if i < j:
                    quadratic[(name_i, name_j)] = quadratic.get((name_i, name_j), 0) + float(w)
                else:
                    quadratic[(name_j, name_i)] = quadratic.get((name_j, name_i), 0) + float(w)

    qp.minimize(linear=linear, quadratic=quadratic)
    
    sampler = Sampler()
    if seed is not None:
        sampler.set_options(seed=seed)
        
    optimizer = COBYLA(maxiter=optimizer_maxiter)
    qaoa = QAOA(sampler=sampler, optimizer=optimizer, reps=reps)
    
    optimizer_algo = MinimumEigenOptimizer(qaoa)
    result = optimizer_algo.solve(qp)
    
    best_x = np.array([int(result.x[i]) for i in range(num_vars)], dtype=np.float64)
    best_energy = float(result.fval)
    runtime_ms = (time.perf_counter() - t0) * 1000.0
    
    return AnnealingResult(
        best_x=best_x,
        best_energy=best_energy,
        initial_energy=best_energy,
        history=[best_energy],
        iterations=optimizer_maxiter,
        runtime_ms=runtime_ms,
    )
