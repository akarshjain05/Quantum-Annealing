"""
Quantum Approximate Optimization Algorithm (QAOA) solver for the Nostro QUBO.
Executes on Qiskit Aer local simulator.
"""
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
from qiskit_algorithms import QAOA
from qiskit_algorithms.optimizers import COBYLA
from qiskit_optimization import QuadraticProgram
from qiskit_optimization.algorithms import MinimumEigenOptimizer
from qiskit.primitives import StatevectorSampler as Sampler

from app.optimization.qubo import QuboModel

@dataclass
class QaoaResult:
    best_x: np.ndarray
    best_energy: float
    runtime_ms: float
    probabilities: Dict[str, float]

def solve_qaoa(
    qubo_model: QuboModel, 
    reps: int = 1,
    maxiter: int = 50,
) -> QaoaResult:
    """
    Solve the Nostro QUBO using QAOA on a local Qiskit simulator.
    """
    t0 = time.perf_counter()
    
    # 1. Build Qiskit QuadraticProgram
    qp = QuadraticProgram("Nostro_QUBO")
    
    # Add binary variables matching the QUBO vars
    for i in range(qubo_model.num_vars):
        qp.binary_var(f"x_{i}")
        
    # Energy is x^T Q x.
    # Note: Q is symmetric. `qp.minimize` accepts a matrix for the quadratic term.
    qp.minimize(quadratic=qubo_model.Q)
    
    # 2. Setup QAOA optimizer
    optimizer = COBYLA(maxiter=maxiter)
    sampler = Sampler() # Local statevector/simulator sampler
    
    qaoa = QAOA(sampler=sampler, optimizer=optimizer, reps=reps)
    qaoa_optimizer = MinimumEigenOptimizer(qaoa)
    
    # 3. Solve
    result = qaoa_optimizer.solve(qp)
    runtime_ms = (time.perf_counter() - t0) * 1000.0
    
    # 4. Extract probabilities and best state
    probabilities = {}
    if result.samples:
        for sample in result.samples:
            state_str = "".join(str(int(bit)) for bit in sample.x)
            probabilities[state_str] = sample.probability
            
    return QaoaResult(
        best_x=np.array(result.x),
        best_energy=result.fval,
        runtime_ms=runtime_ms,
        probabilities=probabilities,
    )
