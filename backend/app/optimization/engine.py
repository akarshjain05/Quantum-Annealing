import logging
logger = logging.getLogger(__name__)

"""
Orchestrates one full optimization run: build QUBO -> solve via simulated
annealing -> decode -> validate -> compute baselines -> compute financial
impact metrics -> generate structured (non-hallucinated) explanations.

This module is solver-agnostic at the interface level (OptimizationSolver
concept from spec §10): today only SimulatedAnnealingSolver is implemented.
A future QuantumAnnealingSolver would plug in at the same point without
changing the QUBO construction or downstream validation/reporting.
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from app.optimization.qubo import (
    build_qubo, CorridorInput, shortfall_probability, QuboModel, DEFAULT_BUCKETS_MUSD
)
from app.optimization.annealing import simulated_annealing, decode_assignment, local_search_refine, energy as qubo_energy


def static_buffer_liquidity(mu: float, sigma: float, z: float = 2.0) -> float:
    """Baseline 1 (spec §9): mean demand + z * std dev, fixed z regardless
    of the confidence level actually being optimized for."""
    return mu + z * sigma


def rule_based_liquidity(mu: float, multiplier: float = 1.5) -> float:
    """Baseline 2 (spec §9): predicted demand * configurable multiplier."""
    return mu * multiplier


def greedy_liquidity(mu: float, sigma: float, z: float, buckets: List[float]) -> float:
    """Baseline 3 (optional, spec §9): cheapest bucket that still clears
    the safety requirement."""
    req = mu + z * sigma
    feasible = [b for b in buckets if b >= req]
    return min(feasible) if feasible else max(buckets)


def validate_solution(assignment: Dict[int, int], qubo: QuboModel, corridors: List[CorridorInput], global_cap_musd: Optional[float] = None) -> List[Dict[str, Any]]:
    """Independent post-hoc validation (spec §31) - never trust the solver
    blindly. Flags one-hot violations and severe shortfalls."""
    violations = []
    id_to_corridor = {c.corridor_id: c for c in corridors}
    total_selected = 0.0
    for cid, i in qubo.corridor_index.items():
        c = id_to_corridor[cid]
        k = assignment[i]
        L = qubo.buckets[k]
        total_selected += L
        req = qubo.requirements[cid]
        if L < req * 0.5:
            violations.append({
                "corridor_code": c.code,
                "type": "SEVERE_SHORTFALL",
                "required_musd": round(req, 2),
                "selected_musd": L,
                "severity": "high",
            })
        elif L < req:
            violations.append({
                "corridor_code": c.code,
                "type": "BELOW_SAFETY_LEVEL",
                "required_musd": round(req, 2),
                "selected_musd": L,
                "severity": "low",
                "note": "Nearest available discrete bucket is below the exact safety level; consider finer bucket granularity.",
            })
            
    if global_cap_musd is not None and total_selected > global_cap_musd:
        violations.append({
            "corridor_code": "GLOBAL",
            "type": "GLOBAL_CAP_EXCEEDED",
            "required_musd": global_cap_musd,
            "selected_musd": round(total_selected, 2),
            "severity": "high",
            "note": "The total assigned liquidity exceeds the bank-wide capital ceiling.",
        })
    return violations


def generate_explanation(c: CorridorInput, req: float, chosen_L: float, current_L: float,
                          risk_before: float, risk_after: float, horizon_days: int = 7) -> Dict[str, Any]:
    """Structured, deterministic explanation generated FROM model outputs -
    not independently hallucinated by an LLM (spec §25)."""
    direction = "decrease" if chosen_L < current_L else ("increase" if chosen_L > current_L else "hold")
    reasons = [
        f"{horizon_days}-day expected payment demand is ${c.mu:.1f}M with volatility (std dev) of ${c.sigma:.1f}M",
        f"At the {int(c.confidence_level*100)}% confidence level, modeled safety liquidity requirement is ${req:.1f}M",
        f"Current nostro balance is ${current_L:.1f}M; recommended balance is ${chosen_L:.1f}M ({direction})",
        f"Opportunity cost of holding liquidity is modeled at {c.opportunity_cost_rate*100:.1f}% annually",
        f"Modeled settlement shortfall probability moves from {risk_before*100:.2f}% to {risk_after*100:.2f}% under the recommendation",
    ]
    return {
        "corridor_code": c.code,
        "headline": f"{c.code} nostro liquidity is recommended to {direction} from ${current_L:.1f}M to ${chosen_L:.1f}M.",
        "reasons": reasons,
        "regulatory_constraints": [],  # populated by caller from KnowledgeItem lookups
        "operational_constraints": [],
        "model_assumptions": [
            "Demand distributed approximately per historical daily volume statistics (mean/std dev)",
            "Shortfall probability modeled via normal CDF - illustrative, not a validated risk model (spec §6.6)",
            f"Liquidity discretized into fixed buckets: {['$'+str(b)+'M' for b in DEFAULT_BUCKETS_MUSD]}",
        ],
    }


@dataclass
class OptimizationOutcome:
    qubo: QuboModel
    annealing_runtime_ms: float
    initial_energy: float
    final_energy: float
    convergence_history: List[float]
    assignment: Dict[int, int]
    onehot_clean: bool
    constraint_violations: List[Dict[str, Any]]
    corridor_results: List[Dict[str, Any]]
    aggregate: Dict[str, Any]


def run_optimization(
    corridors: List[CorridorInput],
    iterations: int = 8000,
    initial_temperature: float = 1000.0,
    cooling_rate: float = 0.995,
    seed: int = 42,
    onehot_penalty: Optional[float] = None,
    weights: Optional[Dict[str, float]] = None,
    global_liquidity_cap_musd: Optional[float] = None,
) -> OptimizationOutcome:
    qubo = build_qubo(corridors, weights=weights, onehot_penalty=onehot_penalty, global_liquidity_cap_musd=global_liquidity_cap_musd)


    # 1. Initial wide search
    sa = simulated_annealing(
        qubo.Q, qubo.num_vars,
        iterations=iterations, initial_temp=initial_temperature,
        cooling_rate=cooling_rate, seed=seed, num_restarts=3,
    )
    
    # 2. Initial Refinement
    current_x, _ = local_search_refine(qubo.Q, sa.best_x, qubo.block_sizes)
    best_x, best_energy = current_x.copy(), qubo_energy(qubo.Q, current_x)
    
    full_history = sa.history + [best_energy]
    
    # 3. Reheating Loop (Iterated Local Search)
    # The initial SA often gets stuck in fictional "dirty" energy basins when Cap/Netting is enabled.
    # Reheating kicks the state out of local refined minimums with short bursts of thermal noise,
    # then strictly refines it again, tracking the best valid one-hot state across all cycles.
    num_reheats = 5
    for cycle in range(num_reheats):
        reheat_sa = simulated_annealing(
            qubo.Q, qubo.num_vars,
            iterations=1000, initial_temp=initial_temperature * 0.2,
            cooling_rate=0.99, seed=seed + 100 + cycle, num_restarts=1,
            initial_x=current_x
        )
        
        refined_x, _ = local_search_refine(qubo.Q, reheat_sa.best_x, qubo.block_sizes)
        e = qubo_energy(qubo.Q, refined_x)
        
        if e < best_energy:
            best_energy = e
            best_x = refined_x.copy()
            
        # Basin hopping: always continue from the newly refined state to explore new basins
        current_x = refined_x.copy()
        
        full_history.extend(reheat_sa.history)
        full_history.append(e)

    # Sanity check the absolute best state found
    offset = 0
    for block_size in qubo.block_sizes:
        active = sum(best_x[offset:offset+block_size] > 0.5)
        if active != 1:
            raise RuntimeError(f"block at {offset} (size {block_size}) has {active} active bits after refinement!")
        offset += block_size
        
    final_x, final_energy = best_x, best_energy
    
    assignment, onehot_clean = decode_assignment(final_x, qubo.block_sizes)
    violations = validate_solution(assignment, qubo, corridors, global_liquidity_cap_musd)

    corridor_results = []
    total_current = 0.0
    total_optimized = 0.0
    total_static = 0.0
    total_rule = 0.0
    total_greedy = 0.0

    for c in corridors:
        i = qubo.corridor_index[c.corridor_id]
        k = assignment[i]
        chosen_L = qubo.buckets[k]
        req = qubo.requirements[c.corridor_id]
        z = qubo.z_scores[c.corridor_id]

        risk_before = shortfall_probability(c.mu, c.sigma, c.current_liquidity)
        risk_after = shortfall_probability(c.mu, c.sigma, chosen_L)

        static_L = static_buffer_liquidity(c.mu, c.sigma, z=2.0)
        rule_L = rule_based_liquidity(c.mu, multiplier=1.5)
        greedy_L = greedy_liquidity(c.mu, c.sigma, z, qubo.buckets)

        total_current += c.current_liquidity
        total_optimized += chosen_L
        total_static += static_L
        total_rule += rule_L
        total_greedy += greedy_L

        explanation = generate_explanation(c, req, chosen_L, c.current_liquidity, risk_before, risk_after)

        corridor_results.append({
            "corridor_id": c.corridor_id,
            "corridor_code": c.code,
            "expected_demand_musd": round(c.mu, 2),
            "demand_std_musd": round(c.sigma, 2),
            "confidence_level": c.confidence_level,
            "z_score": round(z, 3),
            "required_liquidity_musd": round(req, 2),
            "current_liquidity_musd": round(c.current_liquidity, 2),
            "optimized_liquidity_musd": round(chosen_L, 2),
            "capital_released_musd": round(c.current_liquidity - chosen_L, 2),
            "risk_before": round(risk_before, 4),
            "risk_after": round(risk_after, 4),
            "annual_opportunity_cost_saved_musd": round((c.current_liquidity - chosen_L) * c.opportunity_cost_rate, 3),
            "baselines": {
                "static_buffer_musd": round(static_L, 2),
                "rule_based_musd": round(rule_L, 2),
                "greedy_musd": round(greedy_L, 2),
                "quantum_inspired_musd": round(chosen_L, 2),
            },
            "explanation": explanation,
        })

    capital_released = total_current - total_optimized
    aggregate = {
        "total_current_liquidity_musd": round(total_current, 2),
        "total_optimized_liquidity_musd": round(total_optimized, 2),
        "capital_released_musd": round(capital_released, 2),
        "capital_efficiency_pct": round((capital_released / total_current * 100.0) if total_current > 0 else 0.0, 2),
        "baseline_totals_musd": {
            "static_buffer": round(total_static, 2),
            "rule_based": round(total_rule, 2),
            "greedy": round(total_greedy, 2),
            "quantum_inspired": round(total_optimized, 2),
        },
        "num_corridors": len(corridors),
    }

    if global_liquidity_cap_musd is not None:
        slack_k = assignment[qubo.num_corridors]
        slack_offset = sum(qubo.block_sizes[:qubo.num_corridors])
        chosen_slack_value = qubo.var_meta[slack_offset + slack_k]["bucket_value_musd"]
        cap = global_liquidity_cap_musd
        from app.optimization.qubo import DEFAULT_CAP_PENALTY
        P_cap = DEFAULT_CAP_PENALTY
        cap_residual = total_optimized + chosen_slack_value - cap
        cap_penalty_contribution = P_cap * ((cap_residual / cap) ** 2)

        logger.debug(f"[CAP DEBUG] sum(L_i)          = {total_optimized}")
        logger.debug(f"[CAP DEBUG] chosen_slack      = {chosen_slack_value}")
        logger.debug(f"[CAP DEBUG] sum + slack       = {total_optimized + chosen_slack_value}   (target: {cap})")
        logger.debug(f"[CAP DEBUG] cap penalty       = {cap_penalty_contribution}")
        logger.debug(f"[CAP DEBUG] total final energy = {final_energy}")

    return OptimizationOutcome(
        qubo=qubo,
        annealing_runtime_ms=sa.runtime_ms,
        initial_energy=max(sa.initial_energy, final_energy),
        final_energy=final_energy,
        convergence_history=full_history,
        assignment=assignment,
        onehot_clean=onehot_clean,
        constraint_violations=violations,
        corridor_results=corridor_results,
        aggregate=aggregate,
    )
