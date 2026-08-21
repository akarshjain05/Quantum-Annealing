# QUBO Mathematics

This document is the authoritative reference for how NostroQ formulates and solves the liquidity allocation problem. Every claim here is backed by code in `backend/app/optimization/` and tests in `backend/tests/test_qubo.py` and `test_annealing.py`.

## 1. Decision variables

For each corridor `i` and discrete liquidity bucket `k`, a binary variable:

```
x_{i,k} in {0,1}      x_{i,k} = 1  <=>  corridor i is allocated bucket k
```

Buckets (configurable, default): `$0M, $1M, $2M, $5M, $10M, $20M, $50M, $100M`.

Selected liquidity: `L_i = sum_k B_k * x_{i,k}`.

## 2. One-hot constraint

Exactly one bucket per corridor: `sum_k x_{i,k} = 1`, enforced as a QUBO penalty:

```
P_onehot * (sum_k x_{i,k} - 1)^2
```

Expanding (using `x^2 = x` for binary variables):

```
(sum_k x_k - 1)^2 = -sum_k x_k + 2*sum_{k<k'} x_k*x_k' + 1
```

The `+1` constant is dropped from the Q matrix (standard QUBO practice - it doesn't affect the argmin) and tracked separately as `energy_offset` for display purposes. This means:

- **Diagonal** contribution per variable: `-P_onehot`
- **Off-diagonal** contribution per bucket pair `(k, k')` within the same corridor: `+P_onehot` on each of `Q[a,b]` and `Q[b,a]` (symmetric storage), which sums to `+2*P_onehot * x_k*x_k'` in the energy `x^T Q x`.

`tests/test_qubo.py::test_onehot_penalty_gap_matches_expected_property` verifies this directly: a two-hot state scores exactly `P_onehot` higher than a one-hot state, all else equal.

## 3. Why every cost term is linear once discretized

This is the key modeling simplification, and the spec we built against explicitly required it to be documented (its own §6.3).

Because liquidity is restricted to a **fixed, known set of buckets**, any cost function `C(L_i)` - however nonlinear in `L_i` - becomes a **precomputable scalar** once evaluated at each bucket value `B_k`. There is nothing left to "solve" nonlinearly: the choice is which single bucket to activate, and each bucket's cost is just a number we compute in advance. No auxiliary binary variables, no piecewise-linear tricks - every term below is a diagonal-only QUBO coefficient:

- **Capital / opportunity cost**: `opportunity_cost_rate_i * B_k`
- **Shortfall penalty**: `max(0, Req_i - B_k)^2`, where `Req_i = mu_i + z*sigma_i` (see §4)
- **Settlement risk cost**: `Phi((mu_i - B_k) / sigma_i) * Loss_i` (illustrative model, §5)
- **FX cost**: `(fx_cost_bps_i / 10000) * max(0, B_k - current_liquidity_i)`
- **Operational cost**: a small penalty when `B_k` sits below expected demand (proxy for frequent top-ups)

The one-hot constraint requires quadratic (off-diagonal) structure because it couples multiple `x_{i,k}` together within a single corridor.

**Global Capital Cap (Cross-Corridor Coupling):**
When the optional global capital cap (`global_liquidity_cap_musd`) is enabled, a real cross-corridor constraint is introduced. To ensure the total liquidity allocated across all corridors does not exceed a global cap `C`, we add an inequality constraint: `sum L_i <= C`.
This inequality is converted to an equality constraint using a **slack variable** `S >= 0`:
`sum L_i + S = C`
Because the solver only accepts binary variables, the continuous slack `S` is discretized into a new "slack corridor" (a block of binary variables `x_{slack, k}`) using the same one-hot encoding mechanism. The resulting equality constraint `(sum L_i + S - C)^2` creates dense off-diagonal cross-coupling terms between every corridor's bucket variables and the slack variables.

**Consequence**: When the global cap is disabled, the Q matrix remains **exactly block-diagonal across corridors** (motivating the exact refinement pass in §6). When the cap is enabled, the cross-corridor terms require the solver to use iterated local search (reheating) to escape local minima created by the dense coupling.

## 4. Demand uncertainty and the safety level

For each corridor, from trailing transaction history (`forecasting/forecast.py`):

```
mu_i    = expected demand over the horizon (moving-average/EWMA blend)
sigma_i = demand standard deviation over the horizon
```

Safety liquidity level at confidence `c`:

```
Req_i = mu_i + z(c) * sigma_i
```

where `z(c)` is the inverse standard normal CDF at confidence `c` (`scipy.stats.norm.ppf`) - e.g. `z(0.95) ≈ 1.645`, `z(0.99) ≈ 2.326`.

## 5. Settlement shortfall risk (illustrative)

```
P(shortfall | L) = Phi((mu - L) / sigma)
```

`Phi` is the standard normal CDF. **This is explicitly an illustrative model**, not a validated risk model - real settlement failure probability depends on operational factors (replenishment speed, correspondent behavior, netting) this simplification does not capture. Labeled as a `MODEL_ASSUMPTION` everywhere it surfaces in the UI/agent.

## 6. A bug we found and fixed: the one-hot barrier problem

During manual smoke-testing of the first working version of this solver, we found that 3 of 11 corridors converged to a **valid but non-optimal** bucket (e.g. `$100M` chosen when `$50M` had strictly lower cost with zero shortfall difference). We debugged this by pulling the actual QUBO diagonal via the `/api/qubo/{run_id}` inspector endpoint and confirming, by hand, that bucket 50 was in fact cheaper.

**Root cause**: moving between two valid one-hot states via single-bit Metropolis flips requires passing through a **two-hot intermediate state**, which - because of the one-hot penalty - has energy roughly `2 * P_onehot` higher than either endpoint. With `P_onehot = 40`, that's a ~44-80 unit barrier. Once the cooling schedule has annealed past the point where `exp(-barrier/T)` is non-negligible, the walk can get stuck in a locally-decent one-hot state without ever reaching the true minimum, even though the "trivial" 8-choice subproblem is tiny. This is a known, well-documented pathology of penalty-based one-hot encodings in bit-flip QUBO annealing (part of why some real quantum annealing formulations prefer domain-wall encodings instead).

**Fix**: a post-SA coordinate-descent refinement pass (`annealing.py::local_search_refine`). Because the current Q matrix is exactly block-diagonal (§3), the true optimum for a one-hot-valid solution is provably just `argmin_k` of each corridor's own diagonal term - not an approximation. The refinement is implemented as a general sweep (try every bucket for each corridor, holding others fixed, repeat until no improvement) rather than a one-shot argmin, so it continues to behave correctly if a future version introduces real cross-corridor coupling.

`tests/test_annealing.py::test_refinement_finds_true_block_optimum` reproduces this exact scenario (forces a bad starting state) and confirms the fix.

We're documenting this prominently rather than quietly patching it, because we think "we found a real bug in our own solver, understood why it happened, and fixed it in a way that's mathematically justified" is a stronger signal of engineering seriousness than a solver that happened not to hit the bug during a lucky demo run.

## 7. Objective function, assembled

```
Q_total = Q_cost + Q_shortfall + Q_risk + Q_fx + Q_operational + Q_onehot + Q_cap
```

with configurable weights `w_cost, w_shortfall, w_risk, w_fx, w_operational` and `P_onehot` (default 40.0), all exposed via the Optimizer UI and the `/api/optimization/run` request body. The `Q_cap` penalty term is only included if `global_liquidity_cap_musd` is set.

## 8. Simulated annealing

Standard Metropolis criterion: `P(accept) = exp(-dE / T)`, geometric cooling `T_{k+1} = alpha * T_k`. Implemented with **incremental energy tracking** (`Qx = Q @ x` maintained incrementally rather than recomputed from scratch each iteration - O(n) per flip). Correctness of the incremental tracking is checked in `test_annealing.py::test_incremental_energy_matches_direct_computation` by comparing against brute-force `x^T Q x` recomputation over 200 random flips.

Multiple restarts (default 3) with independent random seeds; the best solution across restarts is kept, then passed through the refinement pass in §6.

## 9. Baselines

Every run also computes:

- **Static buffer**: `mu_i + 2*sigma_i`, ignoring the selected confidence level
- **Rule-based**: `mu_i * 1.5`
- **Greedy**: cheapest bucket that clears the safety requirement

...for direct comparison against the QUBO/SA result in the UI and API response.

## 10. Quantum-readiness

The solver is accessed through a `run_optimization()` interface that is agnostic to what actually solves `min x^T Q x`. Today: `simulated_annealing()`. The QUBO construction itself (§1-§3) has no dependency on the solver - the same `Q` matrix this code builds today is exactly the input format a quantum annealer (D-Wave-style) or a QAOA circuit would need. We are not claiming quantum execution anywhere in this codebase; see `docs/limitations.md`.
