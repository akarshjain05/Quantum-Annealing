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

DEFAULT_BUCKETS_MUSD = [0.0, 1.0, 2.5, 5.0, 7.5, 10.0, 15.0, 20.0, 25.0, 30.0, 40.0, 50.0, 75.0, 100.0, 150.0]


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
    transactions: Optional[List[Any]] = None


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
    block_sizes: List[int] = field(default_factory=list)

    def num_nonzero(self) -> int:
        return int(np.count_nonzero(self.Q))


def build_qubo(
    corridors: List[CorridorInput],
    buckets: Optional[List[float]] = None,
    weights: Optional[Dict[str, float]] = None,
    onehot_penalty: Optional[float] = None,
    global_liquidity_cap_musd: Optional[float] = None,
    cap_penalty: float = 200000.0,
) -> QuboModel:
    buckets = buckets or DEFAULT_BUCKETS_MUSD
    default_weights = {
        "cost": 1.0,
        "risk": 1.0,
        "shortfall": 1.0,
        "fx": 0.3,
        "operational": 0.2,
    }
    if weights is not None:
        default_weights.update(weights)
    weights = default_weights
    P = onehot_penalty if onehot_penalty is not None else 40.0
    P_cap = cap_penalty  # Penalty multiplier for the global capital cap

    N = len(corridors)
    K = len(buckets)
    has_cap = global_liquidity_cap_musd is not None
    slack_K = 32 if has_cap else 0
    num_blocks = N + (1 if has_cap else 0)
    num_vars = (N * K) + slack_K
    Q = np.zeros((num_vars, num_vars))
    var_meta: List[Dict[str, Any]] = [None] * num_vars
    corridor_index: Dict[int, int] = {}
    requirements: Dict[int, float] = {}
    z_scores: Dict[int, float] = {}
    energy_offset = 0.0
    block_sizes = [K] * N

    # 1. Map values for all variables (corridors + slack)
    var_values = np.zeros(num_vars)

    for i, c in enumerate(corridors):
        corridor_index[c.corridor_id] = i
        req, z = safety_liquidity_level(c.mu, c.sigma, c.confidence_level)
        requirements[c.corridor_id] = req
        z_scores[c.corridor_id] = z

        for k, B_k in enumerate(buckets):
            idx = i * K + k
            var_values[idx] = B_k
            var_meta[idx] = {
                "var_name": f"x_{c.code}_{k}",
                "corridor_id": c.corridor_id,
                "corridor_code": c.code,
                "bucket_index": k,
                "bucket_value_musd": B_k,
                "block_type": "corridor",
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

    # 2. Add Slack block if capital cap is enabled
    if has_cap:
        block_sizes.append(slack_K)
        slack_buckets = np.linspace(0, global_liquidity_cap_musd, slack_K).tolist()
        base_idx = N * K
        for k, S_k in enumerate(slack_buckets):
            idx = base_idx + k
            var_values[idx] = S_k
            var_meta[idx] = {
                "var_name": f"s_slack_{k}",
                "corridor_id": -1,
                "corridor_code": "SLACK",
                "bucket_index": k,
                "bucket_value_musd": S_k,
                "block_type": "slack",
            }
            Q[idx, idx] += -P  # one-hot penalty diagonal contribution for slack

    # 2.5 FX Netting Groups
    # Group by mirror pairs sharing currency leg (e.g. USD_EUR / EUR_USD)
    code_to_idx = {c.code: i for i, c in enumerate(corridors)}
    grouped = set()
    netting_groups = []
    for i, c in enumerate(corridors):
        if i in grouped:
            continue
        parts = c.code.split('_')
        if len(parts) == 2:
            mirror = f"{parts[1]}_{parts[0]}"
            if mirror in code_to_idx:
                j = code_to_idx[mirror]
                if j not in grouped:
                    netting_groups.append([i, j])
                    grouped.add(i)
                    grouped.add(j)

    from app.forecasting.forecast import compute_correlation
    P_netting = 1.0  # Derived to punish 5M deviation with ~250 energy

    for G in netting_groups:
        # compute Req_G
        mu_G = sum(corridors[i].mu for i in G)
        sigma_sq = 0.0
        for i in G:
            sigma_sq += corridors[i].sigma ** 2
        for i_idx in range(len(G)):
            for j_idx in range(i_idx + 1, len(G)):
                i, j = G[i_idx], G[j_idx]
                tx1 = corridors[i].transactions or []
                tx2 = corridors[j].transactions or []
                rho = compute_correlation(tx1, tx2)
                sigma_sq += 2 * rho * corridors[i].sigma * corridors[j].sigma
        sigma_G = np.sqrt(max(0.0, sigma_sq))
        
        # We use a combined z-score, approximating it as max or average. Let's just use 1.96 (95%)
        # or average of the group's z-scores.
        z = sum(z_scores[corridors[i].corridor_id] for i in G) / len(G)
        Req_G = mu_G + z * sigma_G
        
        energy_offset += P_netting * (Req_G ** 2)

        # Apply QUBO terms for this group
        for i in G:
            for k in range(K):
                idx = i * K + k
                B_k = buckets[k]
                Q[idx, idx] += P_netting * (B_k ** 2 - 2 * Req_G * B_k)
                
        bucket_outer = P_netting * np.outer(buckets, buckets)
        for i_idx in range(len(G)):
            for j_idx in range(i_idx + 1, len(G)):
                i, j = G[i_idx], G[j_idx]
                Q[i*K:(i+1)*K, j*K:(j+1)*K] += bucket_outer
                Q[j*K:(j+1)*K, i*K:(i+1)*K] += bucket_outer

    # 3. Add one-hot penalty off-diagonal terms for ALL blocks (corridors + slack)
    base_idx = 0
    for block_size in block_sizes:
        energy_offset += P
        Q[base_idx:base_idx+block_size, base_idx:base_idx+block_size] += P
        np.fill_diagonal(
            Q[base_idx:base_idx+block_size, base_idx:base_idx+block_size],
            Q.diagonal()[base_idx:base_idx+block_size] - P
        )
        base_idx += block_size

    # 4. Add Normalized Capital Cap Penalty Terms: P_cap * ((sum L_i + Sl - C_total) / C_total)^2
    if has_cap:
        C_total = global_liquidity_cap_musd
        energy_offset += P_cap * 1.0  # (C_total/C_total)^2 = 1.0
        
        v_norm = np.array(var_values) / C_total
        Q += P_cap * np.outer(v_norm, v_norm)
        np.fill_diagonal(Q, Q.diagonal() - 2.0 * P_cap * v_norm)

    return QuboModel(
        Q=Q,
        num_vars=num_vars,
        num_corridors=N,
        buckets=buckets,
        var_meta=var_meta,
        corridor_index=corridor_index,
        penalty_onehot=P,
        weights=weights,
        energy_offset=energy_offset,
        requirements=requirements,
        z_scores=z_scores,
        block_sizes=block_sizes,
    )
