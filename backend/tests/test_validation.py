from app.optimization.engine import validate_solution
from app.optimization.qubo import build_qubo, CorridorInput
from app.audit.chain import compute_hash, verify_chain, GENESIS_HASH


def test_validate_solution_flags_severe_shortfall():
    corridor = CorridorInput(
        corridor_id=1, code="X", mu=100.0, sigma=10.0, current_liquidity=5.0,
        opportunity_cost_rate=0.05, loss_given_shortfall=5.0, fx_cost_bps=8.0,
        operational_cost_rate=0.02, confidence_level=0.95,
    )
    qubo = build_qubo([corridor])
    # force bucket index 0 ($0M) - a severe shortfall against a ~$116M requirement
    forced_assignment = {0: 0}
    violations = validate_solution(forced_assignment, qubo, [corridor])
    assert any(v["type"] == "SEVERE_SHORTFALL" for v in violations)


def test_validate_solution_no_violation_when_covered():
    corridor = CorridorInput(
        corridor_id=1, code="X", mu=5.0, sigma=1.0, current_liquidity=5.0,
        opportunity_cost_rate=0.05, loss_given_shortfall=5.0, fx_cost_bps=8.0,
        operational_cost_rate=0.02, confidence_level=0.95,
    )
    qubo = build_qubo([corridor])
    forced_assignment = {0: 6}  # bucket value 50, well above requirement (~6.6)
    violations = validate_solution(forced_assignment, qubo, [corridor])
    assert violations == []


def test_hash_chain_detects_tampering():
    payload_a = {"event": "A", "value": 1}
    hash_a = compute_hash(GENESIS_HASH, payload_a)
    payload_b = {"event": "B", "value": 2}
    hash_b = compute_hash(hash_a, payload_b)

    entries = [
        {"id": 1, "prev_hash": GENESIS_HASH, "self_hash": hash_a, "payload": payload_a},
        {"id": 2, "prev_hash": hash_a, "self_hash": hash_b, "payload": payload_b},
    ]
    result = verify_chain(entries)
    assert result["valid"] is True

    # tamper with entry 1's payload after the fact without recomputing hashes
    entries[0]["payload"] = {"event": "A", "value": 999}
    tampered_result = verify_chain(entries)
    assert tampered_result["valid"] is False
    assert tampered_result["broken_at_id"] == 1
