"""
Chunked QAOA benchmark for the Nostro QUBO.

Drop this in: backend/chunked_qaoa_benchmark.py
(same level as the existing backend/compare_solvers.py, which this
extends from a single 2-corridor toy instance to the full, real,
seeded corridor set - decomposed into QAOA-sized pieces rather than
truncated to fit the simulator.)

PIPELINE
  1. Build the real QUBO from live corridor data (app.optimization.qubo.build_qubo).
  2. Decompose it into independent chunks along its actual coupling graph
     (app.optimization.decomposition) - exact, not approximate, per the
     additivity property verified in test_decomposition.py.
  3. Guard: if the coupling graph doesn't actually decompose (e.g. a
     global liquidity cap is active, which couples every variable to
     every other), refuse the chunked path entirely and fall back to the
     existing full classical pipeline (app.optimization.engine.run_optimization).
  4. Solve each chunk independently:
       - qubits <= QAOA_QUBIT_LIMIT  -> real QAOA on Qiskit Aer (existing
         app.optimization.qaoa.solve_qaoa, unmodified - see _QuboView below)
       - qubits <= BRUTE_FORCE_LIMIT -> also compute the true optimum by
         exhaustive search, so we can report a real optimality gap instead
         of just an energy number
       - otherwise                  -> classical SA + refinement pass on
         that chunk's submatrix (app.optimization.annealing), flagged
         explicitly as a classical fallback
  5. Stitch every chunk's solution back into one global assignment vector.
     Sanity-check that stitched energy == sum of chunk energies (this
     must hold exactly, or the decomposition step has a bug).
  6. Decode + validate the stitched solution with the SAME validation the
     full classical pipeline uses (app.optimization.engine.validate_solution),
     so a chunked-QAOA run and a classical run are held to identical
     correctness standards.
  7. Run the existing full classical pipeline on the same corridors as a
     baseline, and report combined efficiency: per-chunk optimality gaps,
     ground-state hit rate, and global energy/capital-released comparison.

HONESTY NOTE (consistent with the rest of this codebase): QAOA here runs
on Qiskit Aer's local statevector simulator, not quantum hardware. No
quantum-advantage claim is made. What chunking buys is the ability to run
REAL QAOA against the ACTUAL seeded corridor data instead of a hand-picked
2-corridor toy instance (compare_solvers.py) - a stronger and more honest
comparison, not a bigger one.
"""
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np

from app.optimization.qubo import build_qubo, CorridorInput, QuboModel
from app.optimization.annealing import simulated_annealing, energy as qubo_energy, decode_assignment, local_search_refine
from app.optimization.qaoa import solve_qaoa
from app.optimization.engine import run_optimization, validate_solution
from app.optimization.decomposition import build_chunks, has_valid_decomposition, stitch_solution, Chunk

QAOA_QUBIT_LIMIT = 18       # matches the existing limit in hackathon_solver/solver.py
BRUTE_FORCE_LIMIT = 20      # ground-truth comparison; 2**20 states is still fast


@dataclass
class _QuboView:
    """Minimal duck-typed stand-in for QuboModel. app.optimization.qaoa.solve_qaoa
    only touches .num_vars and .Q, so this lets us feed it a chunk's
    submatrix directly without modifying that file at all."""
    Q: np.ndarray
    num_vars: int


def brute_force_optimal(Q: np.ndarray, num_vars: int):
    """Exhaustive search - only ever called on chunks small enough
    (<= BRUTE_FORCE_LIMIT) that this is fast."""
    best_x, best_energy = None, float("inf")
    for i in range(1 << num_vars):
        x = np.array([(i >> j) & 1 for j in range(num_vars)], dtype=np.float64)
        e = float(x @ (Q @ x))
        if e < best_energy:
            best_energy, best_x = e, x
    return best_x, best_energy


def solve_chunk(chunk: Chunk, reps: int = 1, maxiter: int = 50) -> Dict[str, Any]:
    """Solve one chunk with QAOA if it fits the simulator, else classical
    SA + refinement. Also computes the true optimum via brute force when
    the chunk is small enough, so we can report a real optimality gap."""
    t0 = time.perf_counter()

    if chunk.num_vars <= QAOA_QUBIT_LIMIT:
        method = "qaoa"
        result = solve_qaoa(_QuboView(Q=chunk.Q_sub, num_vars=chunk.num_vars), reps=reps, maxiter=maxiter)
        best_x, best_energy = result.best_x, result.best_energy
    else:
        method = "classical_fallback (oversized for QAOA simulator)"
        sa = simulated_annealing(chunk.Q_sub, chunk.num_vars, iterations=6000, num_restarts=3)
        refined_x, _ = local_search_refine(chunk.Q_sub, sa.best_x, chunk.block_sizes)
        best_x, best_energy = refined_x, qubo_energy(chunk.Q_sub, refined_x)

    runtime_ms = (time.perf_counter() - t0) * 1000.0

    ground_truth_energy = None
    gap_pct = None
    if chunk.num_vars <= BRUTE_FORCE_LIMIT:
        _, ground_truth_energy = brute_force_optimal(chunk.Q_sub, chunk.num_vars)
        denom = abs(ground_truth_energy) if abs(ground_truth_energy) > 1e-9 else 1.0
        gap_pct = 100.0 * (best_energy - ground_truth_energy) / denom

    return {
        "block_indices": chunk.block_indices,
        "num_vars": chunk.num_vars,
        "method": method,
        "energy": best_energy,
        "best_x": best_x,
        "runtime_ms": runtime_ms,
        "ground_truth_energy": ground_truth_energy,
        "gap_pct": gap_pct,
    }


def run_chunked_qaoa_pipeline(
    corridors: List[CorridorInput],
    global_liquidity_cap_musd: Optional[float] = None,
    classical_seed: int = 42,
) -> Dict[str, Any]:
    qubo: QuboModel = build_qubo(corridors, global_liquidity_cap_musd=global_liquidity_cap_musd)
    chunks = build_chunks(qubo.Q, qubo.block_sizes)

    if not has_valid_decomposition(chunks, qubo.num_vars):
        return {
            "status": "FELL_BACK_TO_CLASSICAL",
            "reason": (
                "Coupling graph does not decompose into independent chunks "
                "(most likely a global liquidity cap is active, which couples "
                "every variable to every other). Chunked QAOA buys nothing here "
                "- running the existing full classical pipeline instead."
            ),
            "num_chunks_found": len(chunks),
            "largest_chunk_vars": max((c.num_vars for c in chunks), default=0),
            "total_vars": qubo.num_vars,
            "classical_outcome": run_optimization(corridors, seed=classical_seed, global_liquidity_cap_musd=global_liquidity_cap_musd),
        }

    # --- solve every chunk independently (embarrassingly parallel - see note below) ---
    chunk_results = [solve_chunk(c) for c in chunks]

    # --- stitch back into one global solution ---
    x_global = stitch_solution(qubo.num_vars, [
        (c.var_indices, r["best_x"]) for c, r in zip(chunks, chunk_results)
    ])

    # sanity check: this MUST hold exactly (within float tolerance) or the
    # decomposition has a bug - see test_decomposition.py for the proof
    # this holds in general.
    stitched_energy = qubo_energy(qubo.Q, x_global)
    sum_chunk_energy = sum(r["energy"] for r in chunk_results)
    assert abs(stitched_energy - sum_chunk_energy) < 1e-6, (
        f"decomposition invariant violated: stitched={stitched_energy} "
        f"sum_of_chunks={sum_chunk_energy}"
    )

    assignment, onehot_clean = decode_assignment(x_global, qubo.block_sizes)
    violations = validate_solution(assignment, qubo, corridors, global_liquidity_cap_musd)

    # --- baseline: the existing, fully classical pipeline on the same corridors ---
    classical_outcome = run_optimization(corridors, seed=classical_seed, global_liquidity_cap_musd=global_liquidity_cap_musd)

    # --- combined efficiency report ---
    qaoa_chunks = [r for r in chunk_results if r["method"] == "qaoa"]
    scored_chunks = [r for r in qaoa_chunks if r["ground_truth_energy"] is not None]
    ground_state_hits = sum(1 for r in scored_chunks if abs(r["gap_pct"]) < 1e-6)
    
    # flag unverified chunks
    unverified_chunks = [r for r in chunk_results if r["ground_truth_energy"] is None]

    serial_runtime_ms = sum(r["runtime_ms"] for r in chunk_results)
    parallel_runtime_ms = max((r["runtime_ms"] for r in chunk_results), default=0.0)  # chunks are independent -> could run concurrently

    energy_gap_pct = None
    if abs(classical_outcome.final_energy) > 1e-9:
        energy_gap_pct = 100.0 * (stitched_energy - classical_outcome.final_energy) / abs(classical_outcome.final_energy)

    report = {
        "status": "COMPLETED",
        "num_chunks": len(chunks),
        "chunk_sizes": [c.num_vars for c in chunks],
        "num_qaoa_chunks": len(qaoa_chunks),
        "num_classical_fallback_chunks": len(chunk_results) - len(qaoa_chunks),
        "num_unverified_chunks": len(unverified_chunks),
        "onehot_clean": onehot_clean,
        "constraint_violations": violations,
        "chunked_total_energy": stitched_energy,
        "classical_full_energy": classical_outcome.final_energy,
        "energy_gap_pct_vs_classical": energy_gap_pct,
        "ground_state_hit_rate": (ground_state_hits / len(scored_chunks)) if scored_chunks else None,
        "chunks_scored_against_brute_force": len(scored_chunks),
        "serial_runtime_ms": serial_runtime_ms,
        "parallel_upper_bound_runtime_ms": parallel_runtime_ms,
        "classical_full_runtime_ms": classical_outcome.annealing_runtime_ms,
        "per_chunk": chunk_results,
        "classical_outcome": classical_outcome,
    }
    return report


def print_report(report: Dict[str, Any]) -> None:
    if report["status"] == "FELL_BACK_TO_CLASSICAL":
        print("STATUS: fell back to full classical pipeline")
        print(f"  reason: {report['reason']}")
        print(f"  largest connected chunk: {report['largest_chunk_vars']} / {report['total_vars']} variables")
        return

    print("=" * 70)
    print(" CHUNKED QAOA - COMBINED EFFICIENCY REPORT")
    print("=" * 70)
    print(f"Chunks found:              {report['num_chunks']}  (sizes: {report['chunk_sizes']})")
    print(f"  solved via QAOA:         {report['num_qaoa_chunks']}")
    print(f"  classical fallback:      {report['num_classical_fallback_chunks']}")
    if report.get("num_unverified_chunks", 0) > 0:
        print(f"  unverified chunks:       {report['num_unverified_chunks']} *** (too large for brute-force ground truth)")
    print(f"One-hot clean:             {report['onehot_clean']}")
    print(f"Constraint violations:     {len(report['constraint_violations'])}")
    print("-" * 70)
    print(f"Chunked total energy:      {report['chunked_total_energy']:.4f}")
    print(f"Classical full energy:     {report['classical_full_energy']:.4f}")
    if report["energy_gap_pct_vs_classical"] is not None:
        print(f"Gap vs classical:          {report['energy_gap_pct_vs_classical']:+.3f}%")
    if report["ground_state_hit_rate"] is not None:
        print(f"Ground-state hit rate:     {report['ground_state_hit_rate']*100:.1f}%  "
              f"({report['chunks_scored_against_brute_force']} chunks checked against brute force)")
    print("-" * 70)
    print(f"Serial runtime (sum):      {report['serial_runtime_ms']:.1f} ms")
    print(f"Parallel upper bound:      {report['parallel_upper_bound_runtime_ms']:.1f} ms  (chunks are independent - could run concurrently)")
    print(f"Classical full runtime:    {report['classical_full_runtime_ms']:.1f} ms")
    print("-" * 70)
    for r in report["per_chunk"]:
        if r["gap_pct"] is not None:
            gap = f"{r['gap_pct']:+.3f}%"
            warn = ""
        else:
            gap = "n/a"
            warn = " *** [NO GROUND TRUTH]"
        print(f"  blocks {r['block_indices']}: {r['num_vars']}q via {r['method']:>10s} | "
              f"energy={r['energy']:.3f} | gap_vs_true_optimum={gap}{warn} | {r['runtime_ms']:.1f}ms")
    print("=" * 70)


if __name__ == "__main__":
    from app.core.database import SessionLocal
    from app.api.optimization import corridor_inputs_from_db
    
    print("Fetching live corridor data from database...")
    db = SessionLocal()
    try:
        # Pass confidence_level to match optimization API requirements
        corridors = corridor_inputs_from_db(db, corridor_codes=None, confidence_level=0.95)
        print(f"Found {len(corridors)} corridors. Decomposing and running chunked QAOA pipeline...")
        report = run_chunked_qaoa_pipeline(corridors)
        print_report(report)
    finally:
        db.close()
