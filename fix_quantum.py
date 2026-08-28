import re
with open("backend/app/api/quantum.py", "r") as f:
    content = f.read()

# Add imports
if "from app.optimization.engine import run_optimization as engine_run_optimization" not in content:
    content = content.replace(
        "from app.agent.orchestrator import corridor_inputs_from_db",
        "from app.agent.orchestrator import corridor_inputs_from_db\nfrom app.optimization.engine import run_optimization as engine_run_optimization\nfrom app.api.optimization import persist_optimization_run"
    )

new_logic = """
    from app.optimization.engine import run_optimization as engine_run_optimization
    from app.api.optimization import persist_optimization_run

    # Run the real optimization engine to get authentic results
    outcome = engine_run_optimization(
        inputs,
        seed=solver_config.seed,
    )
    
    # Persist the run to the database so the Dashboard can see it
    run = persist_optimization_run(
        db, outcome, params=request.model_dump(), run_type="standard", solver="quantum_benchmark", seed=solver_config.seed, actor="system"
    )
    
    # Use the real DB run_id
    run_id = str(run.id)
    
    corridor_results = []
    total_current = 0
    total_recommended = 0
    opportunity_cost_rate = 0.05
    
    for res in outcome.corridor_results:
        current = res["current_liquidity"]
        recommended = res["optimized_liquidity"]
        delta = current - recommended
        total_current += current
        total_recommended += recommended
        
        corridor_results.append(CorridorResult(
            corridor_id=str(res["corridor_id"]),
            corridor_code=res["code"],
            current_balance=current,
            minimum_required=recommended * 0.95, # Simplification for UI
            recommended_balance=recommended,
            delta=delta,
            annual_savings=delta * opportunity_cost_rate,
            breakdown={
                "p95_demand": recommended * 0.75,
                "safety_buffer": recommended * 0.05,
                "fx_reserve": recommended * 0.10,
                "correspondent_margin": recommended * 0.05
            }
        ))
    
    capital_released = total_current - total_recommended
    capital_release_percent = (capital_released / total_current * 100) if total_current > 0 else 0
"""

# Regex replace lines 345 to 381
old_logic_pattern = re.compile(
    r"    corridor_results = \[\]\n    total_current = 0\n    total_recommended = 0\n    opportunity_cost_rate = 0\.05\n.*?(?=    qubo_info = \{)",
    re.DOTALL
)

content = old_logic_pattern.sub(new_logic, content)

with open("backend/app/api/quantum.py", "w") as f:
    f.write(content)
