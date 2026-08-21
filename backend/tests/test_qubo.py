import numpy as np
from app.optimization.qubo import build_qubo, CorridorInput, shortfall_probability, safety_liquidity_level


def make_corridor(cid=1, code="TEST_CCY", mu=10.0, sigma=2.0, current=15.0, confidence=0.95):
    return CorridorInput(
        corridor_id=cid, code=code, mu=mu, sigma=sigma, current_liquidity=current,
        opportunity_cost_rate=0.05, loss_given_shortfall=5.0, fx_cost_bps=8.0,
        operational_cost_rate=0.02, confidence_level=confidence,
    )


def test_qubo_dimensions():
    corridors = [make_corridor(1), make_corridor(2)]
    qubo = build_qubo(corridors, buckets=[0, 1, 2, 5, 10, 20, 50, 100])
    assert qubo.num_vars == 2 * 8
    assert qubo.Q.shape == (16, 16)


def test_qubo_matrix_is_symmetric():
    corridors = [make_corridor(1)]
    qubo = build_qubo(corridors)
    assert np.allclose(qubo.Q, qubo.Q.T)


def test_onehot_penalty_gap_matches_expected_property():
    """A one-hot-valid state (exactly one bucket active) must score exactly
    `penalty_onehot` lower than a two-hot (invalid) state, all else equal -
    this directly verifies the penalty expansion derived in qubo.py's
    module docstring, per spec §6.2's requirement to document the
    transformation."""
    corridors = [make_corridor(1, mu=0.0, sigma=1.0, current=0.0)]
    # zero out cost weights so only the one-hot penalty contributes
    qubo = build_qubo(corridors, buckets=[0, 1, 2], weights={"cost": 0, "risk": 0, "shortfall": 0, "fx": 0, "operational": 0}, onehot_penalty=40.0)

    valid = np.array([1.0, 0.0, 0.0])
    invalid_two_hot = np.array([1.0, 1.0, 0.0])

    e_valid = float(valid @ qubo.Q @ valid)
    e_invalid = float(invalid_two_hot @ qubo.Q @ invalid_two_hot)

    assert np.isclose(e_invalid - e_valid, qubo.penalty_onehot)


def test_shortfall_probability_bounds():
    # far below mean -> shortfall probability near 1; far above -> near 0
    assert shortfall_probability(mu=10, sigma=2, L=0) > 0.99
    assert shortfall_probability(mu=10, sigma=2, L=30) < 0.01


def test_safety_level_increases_with_confidence():
    low_conf, _ = safety_liquidity_level(mu=10, sigma=2, confidence_level=0.90)
    high_conf, _ = safety_liquidity_level(mu=10, sigma=2, confidence_level=0.999)
    assert high_conf > low_conf
