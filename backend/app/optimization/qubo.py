"""
QUBO formulation for nostro liquidity allocation.

Decision variables: x_{i,k} in {0,1} - corridor i selects discrete liquidity
bucket k. Exactly one bucket per corridor is enforced via a one-hot penalty
(soft constraint, validated post-hoc rather than trusted blindly - see
optimization/validate in engine.py, spec §31).

KEY MODELING NOTE (spec §6.3 requires this transformation to be documented):
Because liquidity is discretized into a fixed set of buckets B_k, every cost
term that is a function of L_i alone - however nonlinear in L_i (capital
cost, shortfall penalty, probabilistic shortfall risk, FX cost) - becomes a
LINEAR (diagonal-only) QUBO coefficient once evaluated at each bucket value.
No auxiliary binary variables are needed for these terms: the "cost of
choosing bucket k for corridor i" is just a precomputed scalar. The ONLY
term that requires quadratic (off-diagonal) structure is the one-hot
constraint itself, since it couples multiple x_{i,k} within a corridor.

Energy convention: Q is stored symmetric (Q[a,b] == Q[b,a]), so
E(x) = x^T Q x. The one-hot penalty P*(sum_k x_k - 1)^2 expands to
  -P * sum_k x_k  +  2P * sum_{k<k'} x_k x_k'  +  P
The constant +P per corridor is dropped from Q (standard QUBO practice -
it doesn't affect argmin) and tracked separately as `energy_offset` for
reporting a "true" penalty value in the UI.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

import numpy as np
from scipy.stats import norm

DEFAULT_BUCKETS_MUSD = [0, 1, 2, 5, 10, 20, 50, 100]


def shortfall_probability(mu: float, sigma: float, L: float) -> float:
    """P(shortfall | L) = Phi((mu - L) / sigma) - illustrative model per spec §6.6."""
    if sigma <= 1e-9:
        return 1.0 if L < mu else 0.0
    return float(norm.cdf((mu - L) / sigma))


def safety_liquidity_level(mu: float, sigma: float, confidence_level: float) -> float:
    z = float(norm.ppf(confidence_level))
    return mu + z * sigma, z


@dataclass
class CorridorInput:
    corridor_id: int
    code: str
    mu: float  # expected demand, $M
    sigma: float  # demand std dev, $M
    current_liquidity: float  # $M
    opportunity_cost_rate: float
    loss_given_shortfall: float
    fx_cost_bps: float
    operational_cost_rate: float
    confidence_level: float = 0.95


@dataclass
class QuboModel:
    Q: np.ndarray
    num_vars: int
    num_corridors: int
    buckets: List[float]
    var_meta: List[Dict[str, Any]]
    corridor_index: Dict[int, int]  # corridor_id -> row block index i
    penalty_onehot: float
    weights: Dict[str, float]
    energy_offset: float
    requirements: Dict[int, float]  # corridor_id -> Req_i (safety level)
    z_scores: Dict[int, float]

    def num_nonzero(self) -> int:
        return int(np.count_nonzero(self.Q))


def build_qubo(
    corridors: List[CorridorInput],
    buckets: Optional[List[float]] = None,
    weights: Optional[Dict[str, float]] = None,
    onehot_penalty: Optional[float] = None,
) -> QuboModel:
    buckets = buckets or DEFAULT_BUCKETS_MUSD
    weights = {
        "cost": 1.0,
        "risk": 1.0,
        "shortfall": 1.0,
        "fx": 0.3,
        "operational": 0.2,
        **(weights or {}),
    }
    P = onehot_penalty if onehot_penalty is not None else 40.0

    N = len(corridors)
    K = len(buckets)
    num_vars = N * K
    Q = np.zeros((num_vars, num_vars))
    var_meta: List[Dict[str, Any]] = [None] * num_vars
    corridor_index: Dict[int, int] = {}
    requirements: Dict[int, float] = {}
    z_scores: Dict[int, float] = {}

    for i, c in enumerate(corridors):
        corridor_index[c.corridor_id] = i
        req, z = safety_liquidity_level(c.mu, c.sigma, c.confidence_level)
        requirements[c.corridor_id] = req
        z_scores[c.corridor_id] = z

        for k, B_k in enumerate(buckets):
            idx = i * K + k
            var_meta[idx] = {
                "var_name": f"x_{c.code}_{k}",
                "corridor_id": c.corridor_id,
                "corridor_code": c.code,
                "bucket_index": k,
                "bucket_value_musd": B_k,
            }

            capital_cost = c.opportunity_cost_rate * B_k
            shortfall_gap = max(0.0, req - B_k)
            shortfall_cost = shortfall_gap ** 2
            p_shortfall = shortfall_probability(c.mu, c.sigma, B_k)
            risk_cost = p_shortfall * c.loss_given_shortfall
            fx_cost = (c.fx_cost_bps / 10000.0) * max(0.0, B_k - c.current_liquidity)
            op_cost = c.operational_cost_rate * (2.0 if B_k < c.mu else 0.0)

            diag = (
                weights["cost"] * capital_cost
                + weights["shortfall"] * shortfall_cost
                + weights["risk"] * risk_cost
                + weights["fx"] * fx_cost
                + weights["operational"] * op_cost
            )
            diag += -P  # one-hot penalty diagonal contribution
            Q[idx, idx] += diag

        # one-hot penalty off-diagonal terms (within corridor i only)
        for k1 in range(K):
            for k2 in range(k1 + 1, K):
                a, b = i * K + k1, i * K + k2
                Q[a, b] += P
                Q[b, a] += P

    return QuboModel(
        Q=Q,
        num_vars=num_vars,
        num_corridors=N,
        buckets=buckets,
        var_meta=var_meta,
        corridor_index=corridor_index,
        penalty_onehot=P,
        weights=weights,
        energy_offset=N * P,
        requirements=requirements,
        z_scores=z_scores,
    )
