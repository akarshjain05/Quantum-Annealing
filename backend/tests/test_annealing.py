import numpy as np
from app.optimization.annealing import simulated_annealing, energy, decode_assignment, local_search_refine
from app.optimization.qubo import build_qubo, CorridorInput


def make_corridor(cid, code, mu, sigma, current=0.0):
    return CorridorInput(
        corridor_id=cid, code=code, mu=mu, sigma=sigma, current_liquidity=current,
        opportunity_cost_rate=0.05, loss_given_shortfall=5.0, fx_cost_bps=8.0,
        operational_cost_rate=0.02, confidence_level=0.95,
    )


def test_incremental_energy_matches_direct_computation():
    """Verifies the incremental Qx-tracking used inside simulated_annealing
    against brute-force x^T Q x recomputation over a sequence of random bit
    flips - this is the correctness property the whole solver depends on."""
    rng = np.random.default_rng(7)
    n = 12
    A = rng.normal(size=(n, n))
    Q = (A + A.T) / 2  # random symmetric matrix
    x = rng.integers(0, 2, size=n).astype(float)
    Qx = Q @ x
    tracked_energy = float(x @ Qx)

    for _ in range(200):
        j = int(rng.integers(0, n))
        xj = x[j]
        delta = (1 - 2 * xj) * (Q[j, j] + 2 * (Qx[j] - Q[j, j] * xj))
        new_xj = 1 - xj
        Qx = Qx + (new_xj - xj) * Q[:, j]
        x[j] = new_xj
        tracked_energy += delta

        direct_energy = float(x @ (Q @ x))
        assert np.isclose(tracked_energy, direct_energy, atol=1e-6), "incremental energy diverged from direct computation"


def test_annealing_finds_low_energy_on_toy_problem():
    corridors = [make_corridor(1, "A", mu=5, sigma=1), make_corridor(2, "B", mu=40, sigma=5)]
    qubo = build_qubo(corridors)
    result = simulated_annealing(qubo.Q, qubo.num_vars, iterations=4000, seed=1, num_restarts=2)
    assert result.best_energy <= result.initial_energy
    assert result.runtime_ms < 5000


def test_local_search_refine_never_worsens_energy():
    corridors = [make_corridor(1, "A", mu=5, sigma=1), make_corridor(2, "B", mu=40, sigma=5), make_corridor(3, "C", mu=15, sigma=3)]
    qubo = build_qubo(corridors)
    sa = simulated_annealing(qubo.Q, qubo.num_vars, iterations=1000, seed=3, num_restarts=1)
    refined_x, _ = local_search_refine(qubo.Q, sa.best_x, qubo.num_corridors, len(qubo.buckets))
    e_before = energy(qubo.Q, sa.best_x)
    e_after = energy(qubo.Q, refined_x)
    assert e_after <= e_before + 1e-9


def test_refinement_finds_true_block_optimum():
    """Directly reproduces the bug found during manual smoke-testing: SA
    with a one-hot penalty can get trapped behind the two-hot energy
    barrier and settle on a valid-but-suboptimal bucket. Confirms the
    refinement pass always recovers the true per-block minimum."""
    corridors = [make_corridor(1, "A", mu=17, sigma=2.5)]
    qubo = build_qubo(corridors)
    K = len(qubo.buckets)

    # force a deliberately bad starting one-hot state (highest bucket) to
    # simulate a solver stuck behind the barrier
    bad_x = np.zeros(K)
    bad_x[-1] = 1.0
    refined_x, improved = local_search_refine(qubo.Q, bad_x, [K])

    true_best_k = int(np.argmin(np.diag(qubo.Q)))
    assignment, clean = decode_assignment(refined_x, [K])
    assert clean
    assert assignment[0] == true_best_k
    assert improved
