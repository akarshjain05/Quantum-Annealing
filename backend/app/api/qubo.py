from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.optimization.qubo import build_qubo
from app.api.optimization import corridor_inputs_from_db
from app import models

router = APIRouter(prefix="/api/qubo", tags=["qubo"])


@router.get("/{run_id}")
def inspect_qubo(run_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Rebuilds the exact QUBO formulation used for a given run from its
    stored parameters (the formulation is a deterministic function of
    corridor selection, confidence level, and weights - so this is not an
    approximation). Kept to a bounded, judge-manageable matrix size."""
    run = db.get(models.OptimizationRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    params = run.params_json or {}
    inputs = corridor_inputs_from_db(
        db, params.get("corridors"), params.get("confidence_level", 0.95),
        demand_delta_pct=params.get("demand_delta_pct", 0.0),
        volatility_delta_pct=params.get("volatility_delta_pct", 0.0),
    )
    qubo = build_qubo(
        inputs, 
        weights=params.get("weights"), 
        onehot_penalty=params.get("onehot_penalty"),
        global_liquidity_cap_musd=params.get("global_liquidity_cap_musd")
    )

    return {
        "run_id": run_id,
        "num_variables": qubo.num_vars,
        "num_corridors": qubo.num_corridors,
        "buckets_musd": qubo.buckets,
        "penalty_onehot": qubo.penalty_onehot,
        "weights": qubo.weights,
        "num_nonzero_terms": qubo.num_nonzero(),
        "matrix_dimension": [qubo.num_vars, qubo.num_vars],
        "sparsity_pct": round(100.0 * (1 - qubo.num_nonzero() / (qubo.num_vars ** 2)), 2),
        "variable_map": qubo.var_meta,
        "requirements_musd": {str(k): round(v, 3) for k, v in qubo.requirements.items()},
        "z_scores": {str(k): round(v, 3) for k, v in qubo.z_scores.items()},
        "energy_offset": qubo.energy_offset,
        "matrix": qubo.Q.round(4).tolist(),
        "solver": run.solver,
        "final_energy": run.final_energy,
        "note": "Matrix intentionally bounded (num_variables = num_corridors x num_buckets) for judge inspection, per spec §7/§24.",
    }
