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
) -> AnnealingResult:
    import time

    t0 = time.perf_counter()
    best_x_overall: Optional[np.ndarray] = None
    best_energy_overall: Optional[float] = None
    initial_energy_overall: Optional[float] = None
    history_overall: List[float] = []

    for restart in range(max(1, num_restarts)):
        rng = np.random.default_rng(seed + restart)
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


def decode_assignment(best_x: np.ndarray, num_corridors: int, num_buckets: int):
    """Decode the flat binary vector into one bucket-index per corridor.
    Uses argmax within each corridor's K-slice, which is robust even if the
    one-hot penalty didn't fully converge to a clean one-hot state (this is
    exactly the case optimization/validate.py checks for and flags)."""
    x = best_x.reshape(num_corridors, num_buckets)
    assignment = {}
    clean_onehot = True
    for i in range(num_corridors):
        row = x[i]
        active = np.where(row > 0.5)[0]
        if len(active) != 1:
            clean_onehot = False
        k = int(np.argmax(row))
        assignment[i] = k
    return assignment, clean_onehot


def local_search_refine(Q: np.ndarray, x: np.ndarray, num_corridors: int, num_buckets: int, max_sweeps: int = 5):
    """Post-SA coordinate-descent refinement over one-hot blocks.

    Bit-flip Metropolis SA with a *penalty* one-hot constraint has a known
    pathology: moving from one valid one-hot state to another requires
    passing through a higher-energy two-hot intermediate (an energy barrier
    of roughly 2x the one-hot penalty weight), which the cooling schedule
    may already be too cold to cross by the time it matters. The result is
    a solution that is one-hot-VALID per block but not block-optimal.

    Because each corridor's block of K variables is independent in this
    formulation (no cross-corridor terms in Q), the true optimum for a
    one-hot-valid solution is simply argmin_k of each block's diagonal
    term - exact, not approximate, for the current QUBO. Implemented as a
    general coordinate-descent sweep (rather than a one-shot argmin) so it
    still behaves sensibly if a future version adds cross-corridor coupling
    terms (e.g. a shared collateral pool - see docs/roadmap.md).
    """
    x = x.copy()
    xr = x.reshape(num_corridors, num_buckets)
    improved_any = False
    for sweep in range(max_sweeps):
        improved = False
        for i in range(num_corridors):
            base = i * num_buckets
            best_k = int(np.argmax(xr[i]))
            best_energy = None
            for k in range(num_buckets):
                trial = xr[i].copy()
                trial[:] = 0
                trial[k] = 1
                x_full = x.copy().reshape(num_corridors, num_buckets)
                x_full[i] = trial
                flat = x_full.reshape(-1)
                e = float(flat @ (Q @ flat))
                if best_energy is None or e < best_energy:
                    best_energy = e
                    best_k = k
            if best_k != int(np.argmax(xr[i])):
                improved = True
                improved_any = True
            xr[i] = 0
            xr[i][best_k] = 1
        if not improved:
            break
    return x.reshape(-1), improved_any
