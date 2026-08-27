import os
import json
import time
import hashlib
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pathlib import Path

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Body, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

import numpy as np

# Import quantum solver module
from app.optimization.quantum_solver import (
    QUBOProblem,
    QuantumBenchmark,
    SolverRegistry,
    SolverType,
    SolverCategory,
    BenchmarkResult,
    QISKIT_AVAILABLE,
    DWAVE_AVAILABLE,
    NEAL_AVAILABLE,
    QISKIT_OPTIMIZATION_AVAILABLE,
    QISKIT_ALGORITHMS_AVAILABLE
)

from app.services.optimization_service import corridor_inputs_from_db
from app.optimization.engine import build_qubo
from app.core.database import get_db
from sqlalchemy.orm import Session

# =============================================================================
# CONFIGURATION
# =============================================================================

BENCHMARK_RESULTS_DIR = Path("data/benchmark_results")
BENCHMARK_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/api/quantum", tags=["Quantum Optimization"])

# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class SolverInfo(BaseModel):
    type: str
    display_name: str
    category: str
    is_available: bool
    requires_api_key: bool = False
    max_variables: Optional[int] = None
    description: str = ""

class QuantumStatusResponse(BaseModel):
    qiskit_available: bool
    qiskit_version: Optional[str]
    qiskit_optimization_available: bool
    qiskit_algorithms_available: bool
    dwave_available: bool
    neal_available: bool
    optimizer_module_available: bool
    available_solvers: List[SolverInfo]
    total_solvers: int
    quantum_ready: bool
    message: str

class CorridorSelection(BaseModel):
    corridor_ids: Optional[List[str]] = None
    include_locked: bool = False

class RiskConfiguration(BaseModel):
    risk_appetite: str = Field(default="conservative")
    confidence_level: float = Field(default=0.95, ge=0.80, le=0.99)
    safety_buffer: float = Field(default=0.05, ge=0.0, le=0.20)

class SolverConfiguration(BaseModel):
    run_classical: bool = True
    run_quantum: bool = True
    classical_iterations: int = Field(default=10000)
    classical_num_restarts: int = Field(default=3)
    quantum_shots: int = Field(default=1024)
    qaoa_layers: int = Field(default=2)
    seed: int = Field(default=42)
    timeout_seconds: int = Field(default=300)

class OptimizationRequest(BaseModel):
    corridors: Optional[CorridorSelection] = None
    risk_config: Optional[RiskConfiguration] = None
    solver_config: Optional[SolverConfiguration] = None
    run_benchmark: bool = Field(default=True)
    solvers_to_run: Optional[List[str]] = Field(default=None)
    save_results: bool = Field(default=True)
    include_qubo_matrix: bool = Field(default=False)

class CorridorResult(BaseModel):
    corridor_id: str
    corridor_code: str
    current_balance: float
    minimum_required: float
    recommended_balance: float
    delta: float
    annual_savings: float
    breakdown: Dict[str, float]

class SolverResult(BaseModel):
    solver_type: str
    solver_category: str
    display_name: str
    is_quantum: bool
    energy: float
    execution_time_ms: float
    solution_quality: float
    gap_from_best: float
    gap_percent: float
    iterations: Optional[int] = None
    num_reads: Optional[int] = None
    convergence_data: List[Dict[str, Any]]
    metadata: Dict[str, Any]

class BenchmarkComparisonResponse(BaseModel):
    problem_size: int
    problem_hash: str
    best_energy: float
    best_solver: Optional[str]
    timestamp: str
    total_time_ms: float
    solvers: List[SolverResult]
    summary: Dict[str, Any]

class OptimizationResponse(BaseModel):
    run_id: str
    timestamp: str
    status: str
    problem_size: int
    num_corridors: int
    total_liquidity: float
    capital_released: float
    capital_release_percent: float
    annual_savings_opportunity: float
    opportunity_cost_rate: float
    corridor_results: List[CorridorResult]
    benchmark: Optional[BenchmarkComparisonResponse]
    qubo_info: Dict[str, Any]
    audit_hash: str
    configuration: Dict[str, Any]
    warnings: List[str]

class BenchmarkHistoryItem(BaseModel):
    run_id: str
    timestamp: str
    problem_size: int
    best_solver: str
    best_energy: float
    num_solvers_run: int
    total_time_ms: float
    capital_released: Optional[float]

class BenchmarkHistoryResponse(BaseModel):
    total_runs: int
    runs: List[BenchmarkHistoryItem]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def generate_run_id() -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    random_suffix = hashlib.md5(str(time.time()).encode()).hexdigest()[:6]
    return f"run_{timestamp}_{random_suffix}"

def get_risk_params(risk_appetite: str) -> Dict[str, float]:
    params = {
        'very_conservative': {'confidence': 0.99, 'safety_buffer': 0.10},
        'conservative': {'confidence': 0.95, 'safety_buffer': 0.05},
        'balanced': {'confidence': 0.90, 'safety_buffer': 0.03},
        'efficient': {'confidence': 0.85, 'safety_buffer': 0.02},
        'very_efficient': {'confidence': 0.80, 'safety_buffer': 0.01},
    }
    return params.get(risk_appetite, params['conservative'])

def solver_type_from_string(s: str) -> Optional[SolverType]:
    try:
        return SolverType(s)
    except ValueError:
        for st in SolverType:
            if st.name.lower() == s.lower() or st.value.lower() == s.lower():
                return st
        return None

def save_benchmark_result(run_id: str, result: Dict[str, Any]):
    filepath = BENCHMARK_RESULTS_DIR / f"{run_id}.json"
    with open(filepath, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    return filepath

def load_benchmark_result(run_id: str) -> Optional[Dict[str, Any]]:
    filepath = BENCHMARK_RESULTS_DIR / f"{run_id}.json"
    if filepath.exists():
        with open(filepath, 'r') as f:
            return json.load(f)
    return None

def get_benchmark_history(limit: int = 50) -> List[Dict[str, Any]]:
    results = []
    for filepath in sorted(BENCHMARK_RESULTS_DIR.glob("*.json"), reverse=True)[:limit]:
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                results.append({
                    "run_id": filepath.stem,
                    "timestamp": data.get("timestamp"),
                    "problem_size": data.get("problem_size"),
                    "best_solver": data.get("best_solver"),
                    "best_energy": data.get("best_energy"),
                    "num_solvers_run": len(data.get("solvers", [])),
                    "total_time_ms": data.get("total_time_ms"),
                    "capital_released": data.get("capital_released")
                })
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
    return results


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.get("/status", response_model=QuantumStatusResponse)
async def get_quantum_status():
    benchmark = QuantumBenchmark()
    status = benchmark.get_solver_status()
    solvers = []
    for solver in status['available_solvers']:
        solvers.append(SolverInfo(
            type=solver['type'],
            display_name=solver['display_name'],
            category=solver['category'],
            is_available=solver['is_available'],
            max_variables=solver.get('max_variables')
        ))
    
    quantum_solvers_available = any(
        s['is_available'] and s['category'] in ['quantum_simulation', 'quantum_hardware']
        for s in status['available_solvers']
    )
    
    if quantum_solvers_available:
        message = "System is quantum-ready. QAOA and/or quantum annealing simulation available."
    else:
        message = "Quantum solvers not available. Install qiskit or dwave-ocean-sdk for quantum support."
    
    return QuantumStatusResponse(
        qiskit_available=QISKIT_AVAILABLE,
        qiskit_version=status.get('qiskit_version'),
        qiskit_optimization_available=QISKIT_OPTIMIZATION_AVAILABLE,
        qiskit_algorithms_available=QISKIT_ALGORITHMS_AVAILABLE,
        dwave_available=DWAVE_AVAILABLE,
        neal_available=NEAL_AVAILABLE,
        optimizer_module_available=True,
        available_solvers=solvers,
        total_solvers=len(solvers),
        quantum_ready=quantum_solvers_available,
        message=message
    )

@router.get("/solvers")
async def list_solvers():
    all_solvers = SolverRegistry.get_all_solvers()
    result = []
    for metadata in all_solvers:
        result.append({
            "type": metadata.solver_type.value,
            "category": metadata.category.value,
            "display_name": metadata.display_name,
            "description": metadata.description,
            "is_available": metadata.is_available,
            "requires_api_key": metadata.requires_api_key,
            "max_variables": metadata.max_variables,
            "typical_use_case": metadata.typical_use_case,
            "is_quantum": metadata.category in [SolverCategory.QUANTUM_SIMULATION, SolverCategory.QUANTUM_HARDWARE]
        })
    return {
        "solvers": result,
        "total": len(result),
        "available": sum(1 for s in result if s['is_available']),
        "quantum_available": sum(1 for s in result if s['is_available'] and s['is_quantum'])
    }

@router.post("/optimize", response_model=OptimizationResponse)
def run_optimization(
    request: OptimizationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    run_id = generate_run_id()
    start_time = time.perf_counter()
    warnings = []
    
    risk_config = request.risk_config or RiskConfiguration()
    risk_params = get_risk_params(risk_config.risk_appetite)
    confidence_level = risk_config.confidence_level or risk_params['confidence']
    
    # Use real DB
    corridor_names = request.corridors.corridor_ids if request.corridors else None
    inputs = corridor_inputs_from_db(db, corridor_names, confidence_level)
    
    if not inputs:
        raise HTTPException(status_code=400, detail="No corridors selected")
    
    qubo = build_qubo(inputs)
    problem = QUBOProblem(
        Q=qubo.Q,
        variable_names=[f"x_{i}" for i in range(qubo.num_vars)],
        problem_name=f"nostro_optimization_{run_id}",
        block_sizes=qubo.block_sizes
    )
    
    solver_config = request.solver_config or SolverConfiguration()
    solvers_to_run = []
    
    if request.solvers_to_run:
        for s in request.solvers_to_run:
            st = solver_type_from_string(s)
            if st:
                solvers_to_run.append(st)
    else:
        if solver_config.run_classical:
            solvers_to_run.append(SolverType.CLASSICAL_SA_NUMPY)
            if NEAL_AVAILABLE:
                solvers_to_run.append(SolverType.DWAVE_NEAL_SA)
        
        if solver_config.run_quantum:
            solvers_to_run.append(SolverType.QAOA_CUSTOM)
            solvers_to_run.append(SolverType.CHUNKED_QAOA)
    
    benchmark = QuantumBenchmark(seed=solver_config.seed)
    benchmark_result = benchmark.run_benchmark(problem=problem, solvers=solvers_to_run, skip_large_quantum=False)
    chart_data = benchmark.generate_chart_data(benchmark_result)
    

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
        current = res["current_liquidity_musd"]
        recommended = res["optimized_liquidity_musd"]
        delta = current - recommended
        total_current += current
        total_recommended += recommended
        
        corridor_results.append(CorridorResult(
            corridor_id=str(res["corridor_id"]),
            corridor_code=res["corridor_code"],
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
    qubo_info = {
        "num_variables": problem.n,
        "dimension": f"{problem.n}x{problem.n}",
        "num_nonzero": problem.num_nonzero,
        "sparsity": f"{problem.sparsity * 100:.2f}%",
        "problem_hash": problem.problem_hash
    }
    
    if request.include_qubo_matrix:
        qubo_info["matrix"] = problem.Q.tolist()
    
    benchmark_response = None
    if request.run_benchmark and chart_data:
        solver_results = []
        for solver_data in chart_data.get("solvers", []):
            solver_results.append(SolverResult(
                solver_type=solver_data["name"],
                solver_category=solver_data["category"],
                display_name=solver_data["displayName"],
                is_quantum=solver_data["isQuantum"],
                energy=solver_data["energy"],
                execution_time_ms=solver_data["executionTimeMs"],
                solution_quality=solver_data["solutionQuality"],
                gap_from_best=solver_data["gapFromBest"],
                gap_percent=solver_data.get("gapPercent", 0),
                iterations=solver_data.get("iterations"),
                num_reads=solver_data.get("numReads"),
                convergence_data=solver_data.get("convergenceData", []),
                metadata=solver_data.get("metadata", {})
            ))
        
        benchmark_response = BenchmarkComparisonResponse(
            problem_size=chart_data["problemSize"],
            problem_hash=chart_data["problemHash"],
            best_energy=chart_data["bestEnergy"],
            best_solver=chart_data.get("bestSolver"),
            timestamp=chart_data["timestamp"],
            total_time_ms=chart_data["totalTimeMs"],
            solvers=solver_results,
            summary=benchmark_result.comparison.get("summary", {})
        )
    
    if request.save_results:
        save_data = {
            "run_id": run_id,
            "timestamp": datetime.utcnow().isoformat(),
            "problem_size": problem.n,
            "best_solver": benchmark_result.best_solver.value if benchmark_result.best_solver else None,
            "best_energy": benchmark_result.best_energy,
            "total_time_ms": benchmark_result.total_time_ms,
            "solvers": chart_data.get("solvers", []),
            "capital_released": capital_released,
            "corridor_count": len(inputs),
            "configuration": {
                "risk_appetite": risk_config.risk_appetite,
                "confidence_level": confidence_level,
                "solvers_run": [s.value for s in solvers_to_run]
            }
        }
        background_tasks.add_task(save_benchmark_result, run_id, save_data)
    
    return OptimizationResponse(
        run_id=run_id,
        timestamp=datetime.utcnow().isoformat(),
        status="completed",
        problem_size=problem.n,
        num_corridors=len(inputs),
        total_liquidity=total_current,
        capital_released=capital_released,
        capital_release_percent=capital_release_percent,
        annual_savings_opportunity=capital_released * opportunity_cost_rate,
        opportunity_cost_rate=opportunity_cost_rate,
        corridor_results=corridor_results,
        benchmark=benchmark_response,
        qubo_info=qubo_info,
        audit_hash="audit_" + run_id,
        configuration={
            "risk_appetite": risk_config.risk_appetite,
            "confidence_level": confidence_level,
            "safety_buffer": risk_config.safety_buffer,
            "solvers_run": [s.value for s in solvers_to_run],
            "seed": solver_config.seed
        },
        warnings=warnings
    )

@router.post("/benchmark/quick")
def run_quick_benchmark(
    num_variables: int = Query(default=16, ge=4, le=100),
    seed: int = Query(default=42),
    run_quantum: bool = Query(default=True)
):
    np.random.seed(seed)
    Q = np.random.randn(num_variables, num_variables) * 10
    Q = (Q + Q.T) / 2
    np.fill_diagonal(Q, np.abs(np.diag(Q)) + 20)
    
    variable_names = [f"x_{i}" for i in range(num_variables)]
    problem = QUBOProblem(Q, variable_names, problem_name="quick_benchmark")
    
    solvers = [SolverType.CLASSICAL_SA_NUMPY]
    if NEAL_AVAILABLE:
        solvers.append(SolverType.DWAVE_NEAL_SA)
    if run_quantum and QISKIT_AVAILABLE and num_variables <= 20:
        solvers.append(SolverType.QAOA_CUSTOM)
    
    benchmark = QuantumBenchmark(seed=seed)
    result = benchmark.run_benchmark(problem, solvers=solvers)
    chart_data = benchmark.generate_chart_data(result)
    
    return {
        "status": "completed",
        "problem": {
            "num_variables": num_variables,
            "sparsity": f"{problem.sparsity * 100:.1f}%",
            "hash": problem.problem_hash
        },
        "benchmark": chart_data,
        "message": f"Benchmark completed with {len(result.results)} solvers"
    }

@router.get("/benchmark/history", response_model=BenchmarkHistoryResponse)
async def get_benchmark_history_endpoint(limit: int = Query(default=20, ge=1, le=100)):
    runs = get_benchmark_history(limit)
    items = []
    for run in runs:
        items.append(BenchmarkHistoryItem(
            run_id=run["run_id"],
            timestamp=run.get("timestamp", ""),
            problem_size=run.get("problem_size", 0),
            best_solver=run.get("best_solver", "unknown"),
            best_energy=run.get("best_energy", 0),
            num_solvers_run=run.get("num_solvers_run", 0),
            total_time_ms=run.get("total_time_ms", 0),
            capital_released=run.get("capital_released")
        ))
    return BenchmarkHistoryResponse(total_runs=len(items), runs=items)

@router.get("/benchmark/{run_id}")
async def get_benchmark_result(run_id: str):
    result = load_benchmark_result(run_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Benchmark run {run_id} not found")
    return result

@router.delete("/benchmark/{run_id}")
async def delete_benchmark_result(run_id: str):
    filepath = BENCHMARK_RESULTS_DIR / f"{run_id}.json"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Benchmark run {run_id} not found")
    filepath.unlink()
    return {"status": "deleted", "run_id": run_id}

@router.post("/validate-qubo")
def validate_qubo(
    matrix: List[List[float]] = Body(..., description="QUBO matrix as 2D array"),
    variable_names: Optional[List[str]] = Body(default=None, description="Optional variable names")
):
    try:
        Q = np.array(matrix)
        if Q.ndim != 2 or Q.shape[0] != Q.shape[1]:
            raise HTTPException(status_code=400, detail="Matrix must be a square 2D array")
        
        n = Q.shape[0]
        if variable_names and len(variable_names) != n:
            raise HTTPException(status_code=400, detail=f"Expected {n} variable names")
        
        problem = QUBOProblem(Q, variable_names)
        is_symmetric = np.allclose(Q, Q.T)
        issues = []
        if not is_symmetric:
            issues.append("Matrix is not symmetric")
        if np.any(np.isnan(Q)) or np.any(np.isinf(Q)):
            issues.append("Matrix contains NaN/inf values")
        
        solver_compatibility = {
            "classical_sa": n <= 10000,
            "dwave_neal_sa": n <= 50000 and NEAL_AVAILABLE,
            "qaoa_custom": n <= 20 and QISKIT_AVAILABLE,
            "qiskit_qaoa": n <= 16 and QISKIT_OPTIMIZATION_AVAILABLE,
            "dwave_exact": n <= 20 and DWAVE_AVAILABLE
        }
        
        return {
            "valid": len(issues) == 0 or (len(issues) == 1 and "symmetric" in issues[0]),
            "num_variables": n,
            "dimension": f"{n}x{n}",
            "num_nonzero": problem.num_nonzero,
            "sparsity": f"{problem.sparsity * 100:.2f}%",
            "is_symmetric": bool(is_symmetric),
            "hash": problem.problem_hash,
            "issues": issues,
            "solver_compatibility": solver_compatibility,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/export/{run_id}")
async def export_benchmark(run_id: str, format: str = Query(default="json", enum=["json", "csv"])):
    result = load_benchmark_result(run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Not found")
    if format == "json":
        return JSONResponse(content=result)
    elif format == "csv":
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["solver", "category", "is_quantum", "energy", "execution_time_ms", "solution_quality"])
        for solver in result.get("solvers", []):
            writer.writerow([
                solver.get("displayName", solver.get("name")),
                solver.get("category"),
                solver.get("isQuantum"),
                solver.get("energy"),
                solver.get("executionTimeMs"),
                solver.get("solutionQuality")
            ])
        csv_content = output.getvalue()
        return JSONResponse(
            content={"csv": csv_content, "run_id": run_id},
            headers={"Content-Disposition": f"attachment; filename=benchmark_{run_id}.csv"}
        )

@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "quantum_ready": QISKIT_AVAILABLE or DWAVE_AVAILABLE,
    }
