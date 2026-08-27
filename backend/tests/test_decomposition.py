import pytest
import numpy as np

from app.optimization.decomposition import build_chunks, has_valid_decomposition, find_independent_blocks
from app.optimization.qubo import build_qubo, CorridorInput, DEFAULT_BUCKETS_MUSD

def test_base_decomposition_invariants():
    rng = np.random.default_rng(7)
    block_sizes = [8, 8, 8, 8]
    n = sum(block_sizes)
    Q = np.zeros((n, n))
    offsets = np.cumsum([0] + block_sizes)

    for i in range(4):
        a, b = offsets[i], offsets[i+1]
        B = rng.normal(size=(8, 8))
        Bs = (B + B.T) / 2
        Q[a:b, a:b] = Bs

    cross = rng.normal(size=(8, 8))
    Q[offsets[0]:offsets[1], offsets[1]:offsets[2]] = cross
    Q[offsets[1]:offsets[2], offsets[0]:offsets[1]] = cross.T

    components = find_independent_blocks(Q, block_sizes)
    assert sorted(components) == [[0, 1], [2], [3]]

def test_global_cap_no_decomposition():
    block_sizes2 = [8, 8, 8, 8, 32]
    n2 = sum(block_sizes2)
    rng = np.random.default_rng(7)
    Q2 = np.zeros((n2, n2))
    offsets2 = np.cumsum([0] + block_sizes2)
    for i in range(5):
        a, b = offsets2[i], offsets2[i+1]
        sz = block_sizes2[i]
        B = rng.normal(size=(sz, sz))
        Q2[a:b, a:b] = (B + B.T) / 2
        
    for i in range(5):
        for j in range(i+1, 5):
            ai, bi = offsets2[i], offsets2[i+1]
            aj, bj = offsets2[j], offsets2[j+1]
            cross2 = rng.normal(size=(block_sizes2[i], block_sizes2[j])) * 0.001 + 0.0001
            Q2[ai:bi, aj:bj] = cross2
            Q2[aj:bj, ai:bi] = cross2.T

    components2 = find_independent_blocks(Q2, block_sizes2)
    assert len(components2) == 1
    assert components2[0] == [0, 1, 2, 3, 4]

def test_production_qubo_decomposition_fallback():
    # 11 corridors * 8 buckets = 88 variables + slack variables
    # Let's generate a realistic QUBO
    buckets = [0.0, 1.0, 2.5, 5.0, 7.5, 10.0, 15.0, 20.0]
    corridors = []
    for i in range(11):
        corridors.append(CorridorInput(
            corridor_id=i, code=f"COR_{i}", mu=10.0, sigma=2.0, current_liquidity=15.0,
            opportunity_cost_rate=0.05, loss_given_shortfall=5.0, fx_cost_bps=8.0,
            operational_cost_rate=0.02, confidence_level=0.95, transactions=[]
        ))
        
    # With global liquidity cap enabled, it should couple ALL variables
    qubo = build_qubo(corridors, buckets=buckets, global_liquidity_cap_musd=100.0)
    assert qubo.num_vars >= 88
    
    chunks = build_chunks(qubo.Q, qubo.block_sizes)
    
    # has_valid_decomposition should return False because the cap couples everything
    assert not has_valid_decomposition(chunks, qubo.num_vars)
    
    # Without cap, it should successfully decompose
    qubo_no_cap = build_qubo(corridors, buckets=buckets, global_liquidity_cap_musd=None)
    chunks_no_cap = build_chunks(qubo_no_cap.Q, qubo_no_cap.block_sizes)
    # The default risk params without cap and with empty transactions should mean mostly independent blocks
    # (except for maybe FX netting, but without transactions there is no correlation)
    assert has_valid_decomposition(chunks_no_cap, qubo_no_cap.num_vars)
