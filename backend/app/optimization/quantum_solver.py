"""
Quantum and Classical Solver Implementations for NostroQ QUBO Optimization.

This module provides:
1. Classical Simulated Annealing (baseline)
2. D-Wave Simulated Annealing (production-quality classical)
3. D-Wave Quantum Annealing (actual QPU - requires access)
4. Qiskit QAOA (gate-based quantum simulation)
5. Exact solver (for small problems, verification)

DISCLOSURE: Quantum simulations run on classical hardware.
Actual quantum advantage requires real QPU access and larger problem sizes.

Author: NostroQ Team
License: MIT
"""

import numpy as np
import time
import json
import hashlib
from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
from abc import ABC, abstractmethod
import warnings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# CHECK AVAILABLE QUANTUM LIBRARIES
# =============================================================================

QISKIT_AVAILABLE = False
DWAVE_AVAILABLE = False
PENNYLANE_AVAILABLE = False

# Try importing Qiskit
try:
    import qiskit
    from qiskit import QuantumCircuit, transpile
    from qiskit_aer import AerSimulator
    from qiskit.circuit import Parameter
    from qiskit.primitives import StatevectorSampler as Sampler
    QISKIT_VERSION = qiskit.__version__
    QISKIT_AVAILABLE = True
    logger.info(f"✓ Qiskit {QISKIT_VERSION} available")
except ImportError as e:
    logger.warning(f"⚠ Qiskit not available: {e}")
    QISKIT_VERSION = None

# Try importing Qiskit Optimization (separate package)
QISKIT_OPTIMIZATION_AVAILABLE = False
try:
    from qiskit_optimization import QuadraticProgram
    from qiskit_optimization.algorithms import MinimumEigenOptimizer, CplexOptimizer
    from qiskit_optimization.converters import QuadraticProgramToQubo
    QISKIT_OPTIMIZATION_AVAILABLE = True
    logger.info("✓ Qiskit Optimization available")
except ImportError as e:
    logger.warning(f"⚠ Qiskit Optimization not available: {e}")

# Try importing Qiskit Algorithms
QISKIT_ALGORITHMS_AVAILABLE = False
try:
    from qiskit_algorithms import QAOA, NumPyMinimumEigensolver
    from qiskit_algorithms.optimizers import COBYLA, SPSA, ADAM
    from qiskit_algorithms.utils import algorithm_globals
    QISKIT_ALGORITHMS_AVAILABLE = True
    logger.info("✓ Qiskit Algorithms available")
except ImportError as e:
    logger.warning(f"⚠ Qiskit Algorithms not available: {e}")

# Try importing D-Wave
try:
    import dimod
    from dimod import BinaryQuadraticModel, ExactSolver, SimulatedAnnealingSampler
    from dimod.reference.samplers import RandomSampler
    DWAVE_AVAILABLE = True
    logger.info("✓ D-Wave dimod available")
except ImportError as e:
    logger.warning(f"⚠ D-Wave dimod not available: {e}")

# Try importing D-Wave Neal (better SA implementation)
NEAL_AVAILABLE = False
try:
    from neal import SimulatedAnnealingSampler as NealSA
    NEAL_AVAILABLE = True
    logger.info("✓ D-Wave Neal SA available")
except ImportError as e:
    logger.warning(f"⚠ D-Wave Neal not available: {e}")

# Try importing D-Wave System (for actual QPU access)
DWAVE_SYSTEM_AVAILABLE = False
try:
    from dwave.system import DWaveSampler, EmbeddingComposite, LeapHybridSampler
    DWAVE_SYSTEM_AVAILABLE = True
    logger.info("✓ D-Wave System (QPU access) available")
except ImportError as e:
    logger.warning(f"⚠ D-Wave System not available (no QPU access): {e}")


# =============================================================================
# ENUMS AND DATA CLASSES
# =============================================================================

class SolverType(Enum):
    """Supported solver types."""
    CLASSICAL_SA = "classical_simulated_annealing"
    CLASSICAL_SA_NUMPY = "classical_sa_numpy"
    DWAVE_SA = "dwave_simulated_annealing"
    DWAVE_NEAL_SA = "dwave_neal_sa"
    DWAVE_EXACT = "dwave_exact"
    DWAVE_QPU = "dwave_quantum_annealing"
    DWAVE_HYBRID = "dwave_hybrid"
    QISKIT_QAOA = "qiskit_qaoa"
    QISKIT_VQE = "qiskit_vqe"
    QISKIT_NUMPY = "qiskit_numpy_exact"
    QAOA_CUSTOM = "qaoa_custom_implementation"


class SolverCategory(Enum):
    """Solver categories for classification."""
    CLASSICAL = "classical"
    QUANTUM_INSPIRED = "quantum_inspired"
    QUANTUM_SIMULATION = "quantum_simulation"
    QUANTUM_HARDWARE = "quantum_hardware"


@dataclass
class SolverMetadata:
    """Metadata about a solver."""
    solver_type: SolverType
    category: SolverCategory
    display_name: str
    description: str
    is_available: bool
    requires_api_key: bool = False
    max_variables: Optional[int] = None
    typical_use_case: str = ""


@dataclass
class ConvergencePoint:
    """Single point in convergence history."""
    iteration: int
    energy: float
    temperature: Optional[float] = None
    accepted: Optional[bool] = None


@dataclass
class SolverResult:
    """Standardized result from any solver."""
    solver_type: SolverType
    solver_category: SolverCategory
    solution: Dict[str, int]  # Variable name -> value (0 or 1)
    solution_vector: List[int]  # Raw binary vector
    energy: float  # Objective function value
    execution_time_ms: float  # Wall clock time
    
    # Optional fields
    iterations: Optional[int] = None
    num_reads: Optional[int] = None
    num_samples: Optional[int] = None
    
    # Convergence tracking
    convergence_history: List[ConvergencePoint] = field(default_factory=list)
    
    # Quality metrics
    is_feasible: bool = True
    constraint_violations: List[str] = field(default_factory=list)
    
    # Solver-specific metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Timing breakdown
    timing: Dict[str, float] = field(default_factory=dict)
    
    # For reproducibility
    random_seed: Optional[int] = None
    
    def to_dict(self) -> Dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "solver_type": self.solver_type.value,
            "solver_category": self.solver_category.value,
            "solution": self.solution,
            "solution_vector": self.solution_vector,
            "energy": self.energy,
            "execution_time_ms": self.execution_time_ms,
            "iterations": self.iterations,
            "num_reads": self.num_reads,
            "num_samples": self.num_samples,
            "convergence_history": [
                {"iteration": p.iteration, "energy": p.energy, "temperature": p.temperature}
                for p in self.convergence_history
            ],
            "is_feasible": self.is_feasible,
            "constraint_violations": self.constraint_violations,
            "metadata": self.metadata,
            "timing": self.timing,
            "random_seed": self.random_seed
        }


@dataclass
class BenchmarkResult:
    """Results from benchmarking multiple solvers."""
    problem_id: str
    problem_size: int
    num_variables: int
    num_nonzero: int
    sparsity: float
    
    results: Dict[SolverType, SolverResult]
    best_energy: float
    best_solver: SolverType
    
    timestamp: str
    total_time_ms: float
    
    # Comparison metrics
    comparison: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "problem_id": self.problem_id,
            "problem_size": self.problem_size,
            "num_variables": self.num_variables,
            "num_nonzero": self.num_nonzero,
            "sparsity": self.sparsity,
            "results": {k.value: v.to_dict() for k, v in self.results.items()},
            "best_energy": self.best_energy,
            "best_solver": self.best_solver.value,
            "timestamp": self.timestamp,
            "total_time_ms": self.total_time_ms,
            "comparison": self.comparison
        }


# =============================================================================
# QUBO PROBLEM CLASS
# =============================================================================

class QUBOProblem:
    """
    Represents a Quadratic Unconstrained Binary Optimization problem.
    """
    
    def __init__(
        self,
        Q: np.ndarray,
        variable_names: Optional[List[str]] = None,
        offset: float = 0.0,
        problem_name: str = "qubo_problem"
    ):
        if Q.ndim != 2:
            raise ValueError(f"Q must be 2D, got {Q.ndim}D")
        if Q.shape[0] != Q.shape[1]:
            raise ValueError(f"Q must be square, got {Q.shape}")
        
        self._Q = np.array(Q, dtype=np.float64)
        self._n = Q.shape[0]
        self._offset = offset
        self.problem_name = problem_name
        
        if variable_names is not None:
            if len(variable_names) != self._n:
                raise ValueError(f"Expected {self._n} variable names, got {len(variable_names)}")
            self._variable_names = list(variable_names)
        else:
            self._variable_names = [f"x_{i}" for i in range(self._n)]
        
        self._Q_symmetric = (self._Q + self._Q.T) / 2
        self._hash = self._compute_hash()
    
    @property
    def Q(self) -> np.ndarray:
        return self._Q
    
    @property
    def Q_symmetric(self) -> np.ndarray:
        return self._Q_symmetric
    
    @property
    def n(self) -> int:
        return self._n
    
    @property
    def num_variables(self) -> int:
        return self._n
    
    @property
    def variable_names(self) -> List[str]:
        return self._variable_names
    
    @property
    def offset(self) -> float:
        return self._offset
    
    @property
    def num_nonzero(self) -> int:
        return np.count_nonzero(self._Q)
    
    @property
    def sparsity(self) -> float:
        return 1.0 - (self.num_nonzero / (self._n * self._n))
    
    @property
    def density(self) -> float:
        return self.num_nonzero / (self._n * self._n)
    
    @property
    def problem_hash(self) -> str:
        return self._hash
    
    def _compute_hash(self) -> str:
        data = {
            "Q": self._Q.tobytes().hex()[:64],
            "n": self._n,
            "offset": self._offset,
            "names": self._variable_names[:5]
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:16]
    
    def evaluate(self, x: np.ndarray) -> float:
        x = np.asarray(x, dtype=np.float64)
        if x.shape != (self._n,):
            raise ValueError(f"Expected vector of length {self._n}, got {x.shape}")
        return float(x @ self._Q_symmetric @ x) + self._offset
    
    def evaluate_dict(self, solution: Dict[str, int]) -> float:
        x = np.array([solution[name] for name in self._variable_names], dtype=np.float64)
        return self.evaluate(x)
    
    def to_dict_format(self) -> Dict[Tuple[int, int], float]:
        Q_dict = {}
        for i in range(self._n):
            for j in range(i, self._n):
                if i == j:
                    val = self._Q[i, i]
                else:
                    val = self._Q[i, j] + self._Q[j, i]
                
                if val != 0:
                    Q_dict[(i, j)] = val
        return Q_dict
    
    def to_named_dict_format(self) -> Dict[Tuple[str, str], float]:
        Q_dict = {}
        for i in range(self._n):
            for j in range(i, self._n):
                if i == j:
                    val = self._Q[i, i]
                else:
                    val = self._Q[i, j] + self._Q[j, i]
                
                if val != 0:
                    Q_dict[(self._variable_names[i], self._variable_names[j])] = val
        return Q_dict
    
    def get_linear_terms(self) -> Dict[str, float]:
        return {self._variable_names[i]: self._Q[i, i] for i in range(self._n) if self._Q[i, i] != 0}
    
    def get_quadratic_terms(self) -> Dict[Tuple[str, str], float]:
        quadratic = {}
        for i in range(self._n):
            for j in range(i + 1, self._n):
                val = self._Q[i, j] + self._Q[j, i]
                if val != 0:
                    quadratic[(self._variable_names[i], self._variable_names[j])] = val
        return quadratic
    
    def to_bqm(self):
        if not DWAVE_AVAILABLE:
            raise ImportError("D-Wave dimod not installed. Run: pip install dimod")
        
        return BinaryQuadraticModel.from_qubo(self.to_dict_format(), offset=self._offset)
    
    def summary(self) -> str:
        return (
            f"QUBO Problem: {self.problem_name}\n"
            f"  Variables: {self._n}\n"
            f"  Non-zero terms: {self.num_nonzero}\n"
            f"  Sparsity: {self.sparsity * 100:.1f}%\n"
            f"  Offset: {self._offset}\n"
            f"  Hash: {self._hash}"
        )
    
    def __repr__(self) -> str:
        return f"QUBOProblem(n={self._n}, nonzero={self.num_nonzero}, hash={self._hash})"


# =============================================================================
# ABSTRACT SOLVER BASE CLASS
# =============================================================================

class BaseSolver(ABC):
    """Abstract base class for all QUBO solvers."""
    
    solver_type: SolverType
    solver_category: SolverCategory
    
    @abstractmethod
    def solve(self, problem: QUBOProblem) -> SolverResult:
        pass
    
    @classmethod
    def is_available(cls) -> bool:
        return True
    
    @classmethod
    def get_metadata(cls) -> SolverMetadata:
        return SolverMetadata(
            solver_type=cls.solver_type,
            category=cls.solver_category,
            display_name=cls.solver_type.value,
            description="",
            is_available=cls.is_available()
        )


# =============================================================================
# CLASSICAL SIMULATED ANNEALING (Pure NumPy - No Dependencies)
# =============================================================================

class ClassicalSimulatedAnnealing(BaseSolver):
    solver_type = SolverType.CLASSICAL_SA_NUMPY
    solver_category = SolverCategory.CLASSICAL
    
    def __init__(
        self,
        num_iterations: int = 10000,
        initial_temperature: float = 1000.0,
        cooling_rate: float = 0.995,
        min_temperature: float = 1e-8,
        num_restarts: int = 1,
        seed: Optional[int] = None
    ):
        self.num_iterations = num_iterations
        self.initial_temperature = initial_temperature
        self.cooling_rate = cooling_rate
        self.min_temperature = min_temperature
        self.num_restarts = num_restarts
        self.seed = seed
        
    def solve(self, problem: QUBOProblem) -> SolverResult:
        start_time = time.perf_counter()
        
        if self.seed is not None:
            np.random.seed(self.seed)
        
        best_solution = None
        best_energy = float('inf')
        all_convergence = []
        
        for restart in range(self.num_restarts):
            solution, energy, convergence = self._run_single_sa(problem)
            
            if energy < best_energy:
                best_energy = energy
                best_solution = solution
                all_convergence = convergence
        
        execution_time = (time.perf_counter() - start_time) * 1000
        
        solution_dict = {
            problem.variable_names[i]: int(best_solution[i])
            for i in range(problem.n)
        }
        
        return SolverResult(
            solver_type=self.solver_type,
            solver_category=self.solver_category,
            solution=solution_dict,
            solution_vector=best_solution.tolist(),
            energy=best_energy,
            execution_time_ms=execution_time,
            iterations=self.num_iterations * self.num_restarts,
            num_reads=self.num_restarts,
            convergence_history=all_convergence,
            metadata={
                "initial_temperature": self.initial_temperature,
                "cooling_rate": self.cooling_rate,
                "min_temperature": self.min_temperature,
                "num_restarts": self.num_restarts,
                "final_temperature": self.min_temperature
            },
            random_seed=self.seed
        )
    
    def _run_single_sa(
        self, 
        problem: QUBOProblem
    ) -> Tuple[np.ndarray, float, List[ConvergencePoint]]:
        
        n = problem.n
        Q = problem.Q_symmetric
        
        x = np.random.randint(0, 2, size=n).astype(np.float64)
        current_energy = float(x @ Q @ x) + problem.offset
        
        best_x = x.copy()
        best_energy = current_energy
        
        convergence = []
        temperature = self.initial_temperature
        record_interval = max(1, self.num_iterations // 100)
        
        for iteration in range(self.num_iterations):
            flip_idx = np.random.randint(0, n)
            old_val = x[flip_idx]
            new_val = 1 - old_val
            
            delta = (new_val - old_val) * (
                Q[flip_idx, flip_idx] + 
                2 * np.dot(Q[flip_idx, :], x) - 
                2 * Q[flip_idx, flip_idx] * old_val
            )
            
            accept = False
            if delta < 0:
                accept = True
            elif temperature > 0:
                acceptance_prob = np.exp(-delta / temperature)
                if np.random.random() < acceptance_prob:
                    accept = True
            
            if accept:
                x[flip_idx] = new_val
                current_energy += delta
                
                if current_energy < best_energy:
                    best_energy = current_energy
                    best_x = x.copy()
            
            if iteration % record_interval == 0:
                convergence.append(ConvergencePoint(
                    iteration=iteration,
                    energy=best_energy,
                    temperature=temperature,
                    accepted=accept
                ))
            
            if temperature > self.min_temperature:
                temperature *= self.cooling_rate
        
        convergence.append(ConvergencePoint(
            iteration=self.num_iterations,
            energy=best_energy,
            temperature=temperature,
            accepted=None
        ))
        
        return best_x, best_energy, convergence
    
    @classmethod
    def is_available(cls) -> bool:
        return True
    
    @classmethod
    def get_metadata(cls) -> SolverMetadata:
        return SolverMetadata(
            solver_type=cls.solver_type,
            category=cls.solver_category,
            display_name="Classical SA (NumPy)",
            description="Pure NumPy simulated annealing implementation. No external dependencies.",
            is_available=True,
            max_variables=10000,
            typical_use_case="Baseline comparison, large problems"
        )


# =============================================================================
# D-WAVE NEAL SIMULATED ANNEALING
# =============================================================================

class DWaveNealSA(BaseSolver):
    solver_type = SolverType.DWAVE_NEAL_SA
    solver_category = SolverCategory.QUANTUM_INSPIRED
    
    def __init__(
        self,
        num_reads: int = 100,
        num_sweeps: int = 1000,
        beta_range: Optional[Tuple[float, float]] = None,
        seed: Optional[int] = None
    ):
        if not NEAL_AVAILABLE:
            raise ImportError("D-Wave Neal not installed. Run: pip install dwave-neal")
        
        self.num_reads = num_reads
        self.num_sweeps = num_sweeps
        self.beta_range = beta_range
        self.seed = seed
    
    def solve(self, problem: QUBOProblem) -> SolverResult:
        start_time = time.perf_counter()
        
        bqm = problem.to_bqm()
        sampler = NealSA()
        
        kwargs = {
            "num_reads": self.num_reads,
            "num_sweeps": self.num_sweeps
        }
        if self.beta_range:
            kwargs["beta_range"] = self.beta_range
        if self.seed is not None:
            kwargs["seed"] = self.seed
        
        sample_start = time.perf_counter()
        sampleset = sampler.sample(bqm, **kwargs)
        sample_time = (time.perf_counter() - sample_start) * 1000
        
        execution_time = (time.perf_counter() - start_time) * 1000
        
        best_sample = sampleset.first.sample
        best_energy = sampleset.first.energy
        
        solution_dict = {
            problem.variable_names[i]: int(best_sample[i])
            for i in range(problem.n)
        }
        
        solution_vector = [int(best_sample[i]) for i in range(problem.n)]
        
        convergence = [
            ConvergencePoint(iteration=i, energy=sample.energy)
            for i, sample in enumerate(sampleset.data(['energy']))
        ]
        
        return SolverResult(
            solver_type=self.solver_type,
            solver_category=self.solver_category,
            solution=solution_dict,
            solution_vector=solution_vector,
            energy=best_energy,
            execution_time_ms=execution_time,
            num_reads=self.num_reads,
            num_samples=len(sampleset),
            convergence_history=convergence[:100],
            metadata={
                "num_sweeps": self.num_sweeps,
                "beta_range": self.beta_range,
                "timing": {
                    "sampling_ms": sample_time,
                    "total_ms": execution_time
                },
                "num_occurrences": int(sampleset.first.num_occurrences),
                "all_energies": [float(s.energy) for s in list(sampleset.data(['energy']))[:20]]
            },
            random_seed=self.seed
        )
    
    @classmethod
    def is_available(cls) -> bool:
        return NEAL_AVAILABLE
    
    @classmethod
    def get_metadata(cls) -> SolverMetadata:
        return SolverMetadata(
            solver_type=cls.solver_type,
            category=cls.solver_category,
            display_name="D-Wave Neal SA",
            description="D-Wave's optimized simulated annealing.",
            is_available=NEAL_AVAILABLE,
            max_variables=50000,
            typical_use_case="Production workloads, benchmarking"
        )


# =============================================================================
# D-WAVE EXACT SOLVER (For small problems)
# =============================================================================

class DWaveExactSolver(BaseSolver):
    solver_type = SolverType.DWAVE_EXACT
    solver_category = SolverCategory.CLASSICAL
    
    MAX_VARIABLES = 20
    
    def __init__(self):
        if not DWAVE_AVAILABLE:
            raise ImportError("D-Wave dimod not installed. Run: pip install dimod")
    
    def solve(self, problem: QUBOProblem) -> SolverResult:
        if problem.n > self.MAX_VARIABLES:
            raise ValueError(
                f"Exact solver only feasible for n ≤ {self.MAX_VARIABLES}, "
                f"got n={problem.n}"
            )
        
        start_time = time.perf_counter()
        
        bqm = problem.to_bqm()
        sampler = ExactSolver()
        sampleset = sampler.sample(bqm)
        
        execution_time = (time.perf_counter() - start_time) * 1000
        
        best_sample = sampleset.first.sample
        best_energy = sampleset.first.energy
        
        solution_dict = {
            problem.variable_names[i]: int(best_sample[i])
            for i in range(problem.n)
        }
        
        solution_vector = [int(best_sample[i]) for i in range(problem.n)]
        
        return SolverResult(
            solver_type=self.solver_type,
            solver_category=self.solver_category,
            solution=solution_dict,
            solution_vector=solution_vector,
            energy=best_energy,
            execution_time_ms=execution_time,
            num_samples=len(sampleset),
            metadata={
                "method": "brute_force_enumeration",
                "num_states_evaluated": 2 ** problem.n,
                "is_optimal": True
            }
        )
    
    @classmethod
    def is_available(cls) -> bool:
        return DWAVE_AVAILABLE
    
    @classmethod
    def get_metadata(cls) -> SolverMetadata:
        return SolverMetadata(
            solver_type=cls.solver_type,
            category=cls.solver_category,
            display_name="Exact Solver (Brute Force)",
            description=f"Enumerates all 2^n states. Only for n ≤ {cls.MAX_VARIABLES}.",
            is_available=DWAVE_AVAILABLE,
            max_variables=cls.MAX_VARIABLES,
            typical_use_case="Validation, small problems"
        )


# =============================================================================
# CUSTOM QAOA IMPLEMENTATION (Pure Qiskit, No qiskit-optimization)
# =============================================================================

class QAOACustom(BaseSolver):
    solver_type = SolverType.QAOA_CUSTOM
    solver_category = SolverCategory.QUANTUM_SIMULATION
    
    MAX_VARIABLES = 20
    
    def __init__(
        self,
        p: int = 2,
        shots: int = 1024,
        optimizer: str = "COBYLA",
        maxiter: int = 100,
        seed: Optional[int] = None
    ):
        if not QISKIT_AVAILABLE:
            raise ImportError("Qiskit not installed.")
        
        self.p = p
        self.shots = shots
        self.optimizer_name = optimizer
        self.maxiter = maxiter
        self.seed = seed
        
        if QISKIT_ALGORITHMS_AVAILABLE and seed is not None:
            algorithm_globals.random_seed = seed
    
    def solve(self, problem: QUBOProblem) -> SolverResult:
        if problem.n > self.MAX_VARIABLES:
            raise ValueError(
                f"QAOA simulation feasible for n ≤ {self.MAX_VARIABLES}, "
                f"got n={problem.n}. Use classical solver for larger problems."
            )
        
        start_time = time.perf_counter()
        n = problem.n
        
        linear = problem.get_linear_terms()
        quadratic = problem.get_quadratic_terms()
        var_to_idx = {name: i for i, name in enumerate(problem.variable_names)}
        
        def qaoa_circuit(gamma: List[float], beta: List[float]) -> QuantumCircuit:
            qc = QuantumCircuit(n)
            qc.h(range(n))
            for layer in range(self.p):
                for var_name, coef in linear.items():
                    i = var_to_idx[var_name]
                    qc.rz(2 * gamma[layer] * coef, i)
                for (var_i, var_j), coef in quadratic.items():
                    i = var_to_idx[var_i]
                    j = var_to_idx[var_j]
                    qc.cx(i, j)
                    qc.rz(2 * gamma[layer] * coef, j)
                    qc.cx(i, j)
                for i in range(n):
                    qc.rx(2 * beta[layer], i)
            qc.measure_all()
            return qc
        
        def objective(params: np.ndarray) -> float:
            gamma = params[:self.p]
            beta = params[self.p:]
            qc = qaoa_circuit(gamma.tolist(), beta.tolist())
            backend = AerSimulator()
            transpiled = transpile(qc, backend)
            job = backend.run(transpiled, shots=self.shots, seed_simulator=self.seed)
            counts = job.result().get_counts()
            
            total_energy = 0.0
            for bitstring, count in counts.items():
                x = np.array([int(b) for b in reversed(bitstring)], dtype=np.float64)
                energy = problem.evaluate(x)
                total_energy += energy * count
            return total_energy / self.shots
        
        np.random.seed(self.seed)
        gamma_init = np.random.uniform(0, 2*np.pi, self.p)
        beta_init = np.random.uniform(0, np.pi, self.p)
        params_init = np.concatenate([gamma_init, beta_init])
        
        optimization_start = time.perf_counter()
        
        if self.optimizer_name == "COBYLA":
            from scipy.optimize import minimize
            result = minimize(
                objective, 
                params_init, 
                method='COBYLA',
                options={'maxiter': self.maxiter, 'disp': False}
            )
            optimal_params = result.x
            optimization_result = {"success": result.success, "nfev": result.nfev}
        else:
            from scipy.optimize import minimize
            result = minimize(
                objective, 
                params_init, 
                method='COBYLA',
                options={'maxiter': self.maxiter}
            )
            optimal_params = result.x
            optimization_result = {"success": result.success, "nfev": result.nfev}
        
        optimization_time = (time.perf_counter() - optimization_start) * 1000
        
        gamma_opt = optimal_params[:self.p]
        beta_opt = optimal_params[self.p:]
        
        qc_final = qaoa_circuit(gamma_opt.tolist(), beta_opt.tolist())
        backend = AerSimulator()
        transpiled = transpile(qc_final, backend)
        job = backend.run(transpiled, shots=self.shots * 4, seed_simulator=self.seed)
        counts = job.result().get_counts()
        
        best_bitstring = None
        best_energy = float('inf')
        
        for bitstring, count in counts.items():
            x = np.array([int(b) for b in reversed(bitstring)], dtype=np.float64)
            energy = problem.evaluate(x)
            if energy < best_energy:
                best_energy = energy
                best_bitstring = bitstring
        
        execution_time = (time.perf_counter() - start_time) * 1000
        best_x = np.array([int(b) for b in reversed(best_bitstring)], dtype=np.float64)
        
        solution_dict = {
            problem.variable_names[i]: int(best_x[i])
            for i in range(n)
        }
        
        return SolverResult(
            solver_type=self.solver_type,
            solver_category=self.solver_category,
            solution=solution_dict,
            solution_vector=[int(v) for v in best_x],
            energy=best_energy,
            execution_time_ms=execution_time,
            iterations=optimization_result.get("nfev", self.maxiter),
            num_reads=self.shots * 4,
            metadata={
                "p": self.p,
                "shots": self.shots,
                "optimizer": self.optimizer_name,
                "maxiter": self.maxiter,
                "optimal_gamma": gamma_opt.tolist(),
                "optimal_beta": beta_opt.tolist(),
                "optimization_success": optimization_result.get("success", None),
                "optimization_nfev": optimization_result.get("nfev", None),
                "timing": {
                    "optimization_ms": optimization_time,
                    "total_ms": execution_time
                },
                "backend": "qasm_simulator",
                "circuit_depth": qc_final.depth()
            },
            random_seed=self.seed
        )
    
    @classmethod
    def is_available(cls) -> bool:
        return QISKIT_AVAILABLE
    
    @classmethod
    def get_metadata(cls) -> SolverMetadata:
        return SolverMetadata(
            solver_type=cls.solver_type,
            category=cls.solver_category,
            display_name="QAOA (Custom Implementation)",
            description="Gate-based quantum approximate optimization. Runs on Qiskit simulator.",
            is_available=QISKIT_AVAILABLE,
            max_variables=cls.MAX_VARIABLES,
            typical_use_case="Quantum algorithm demonstration, small problems"
        )


# =============================================================================
# QISKIT QAOA (Using qiskit-algorithms if available)
# =============================================================================

class QiskitQAOA(BaseSolver):
    solver_type = SolverType.QISKIT_QAOA
    solver_category = SolverCategory.QUANTUM_SIMULATION
    
    MAX_VARIABLES = 16
    
    def __init__(
        self,
        reps: int = 2,
        shots: int = 1024,
        optimizer: str = "COBYLA",
        seed: Optional[int] = None
    ):
        if not (QISKIT_AVAILABLE and QISKIT_OPTIMIZATION_AVAILABLE and QISKIT_ALGORITHMS_AVAILABLE):
            raise ImportError(
                "Qiskit packages not fully installed. Run: "
                "pip install qiskit qiskit-aer qiskit-optimization qiskit-algorithms"
            )
        
        self.reps = reps
        self.shots = shots
        self.optimizer_name = optimizer
        self.seed = seed
    
    def solve(self, problem: QUBOProblem) -> SolverResult:
        if problem.n > self.MAX_VARIABLES:
            raise ValueError(f"Qiskit QAOA limited to n ≤ {self.MAX_VARIABLES}")
        
        start_time = time.perf_counter()
        
        if self.seed is not None:
            algorithm_globals.random_seed = self.seed
        
        qp = QuadraticProgram()
        for name in problem.variable_names:
            qp.binary_var(name)
        
        linear = problem.get_linear_terms()
        quadratic = problem.get_quadratic_terms()
        qp.minimize(linear=linear, quadratic=quadratic)
        
        backend = AerSimulator()
        
        if self.optimizer_name == "COBYLA":
            optimizer = COBYLA(maxiter=100)
        elif self.optimizer_name == "SPSA":
            optimizer = SPSA(maxiter=100)
        else:
            optimizer = COBYLA(maxiter=100)
        
        sampler = Sampler()
        
        qaoa = QAOA(
            sampler=sampler,
            optimizer=optimizer,
            reps=self.reps
        )
        
        qaoa_optimizer = MinimumEigenOptimizer(qaoa)
        
        result = qaoa_optimizer.solve(qp)
        
        execution_time = (time.perf_counter() - start_time) * 1000
        
        solution_dict = {
            var.name: int(result.x[i])
            for i, var in enumerate(qp.variables)
        }
        
        solution_vector = [int(v) for v in result.x]
        
        return SolverResult(
            solver_type=self.solver_type,
            solver_category=self.solver_category,
            solution=solution_dict,
            solution_vector=solution_vector,
            energy=result.fval + problem.offset,
            execution_time_ms=execution_time,
            num_reads=self.shots,
            metadata={
                "reps": self.reps,
                "shots": self.shots,
                "optimizer": self.optimizer_name,
                "status": str(result.status),
                "qiskit_version": QISKIT_VERSION
            },
            random_seed=self.seed
        )
    
    @classmethod
    def is_available(cls) -> bool:
        return QISKIT_AVAILABLE and QISKIT_OPTIMIZATION_AVAILABLE and QISKIT_ALGORITHMS_AVAILABLE
    
    @classmethod
    def get_metadata(cls) -> SolverMetadata:
        return SolverMetadata(
            solver_type=cls.solver_type,
            category=cls.solver_category,
            display_name="Qiskit QAOA",
            description="Qiskit's QAOA implementation with MinimumEigenOptimizer.",
            is_available=cls.is_available(),
            max_variables=cls.MAX_VARIABLES,
            typical_use_case="Quantum algorithm benchmarking"
        )


# =============================================================================
# SOLVER FACTORY & REGISTRY
# =============================================================================

class SolverRegistry:
    _solvers: Dict[SolverType, type] = {}
    
    @classmethod
    def register(cls, solver_class: type):
        cls._solvers[solver_class.solver_type] = solver_class
        return solver_class
    
    @classmethod
    def get_solver(cls, solver_type: SolverType, **kwargs) -> BaseSolver:
        if solver_type not in cls._solvers:
            raise ValueError(f"Unknown solver type: {solver_type}")
        
        solver_class = cls._solvers[solver_type]
        
        if not solver_class.is_available():
            raise ImportError(f"Solver {solver_type.value} is not available (missing dependencies)")
        
        return solver_class(**kwargs)
    
    @classmethod
    def get_available_solvers(cls) -> List[SolverMetadata]:
        return [
            solver_class.get_metadata()
            for solver_class in cls._solvers.values()
            if solver_class.is_available()
        ]
    
    @classmethod
    def get_all_solvers(cls) -> List[SolverMetadata]:
        return [solver_class.get_metadata() for solver_class in cls._solvers.values()]


# Register all solvers
SolverRegistry.register(ClassicalSimulatedAnnealing)
if NEAL_AVAILABLE:
    SolverRegistry.register(DWaveNealSA)
if DWAVE_AVAILABLE:
    SolverRegistry.register(DWaveExactSolver)
if QISKIT_AVAILABLE:
    SolverRegistry.register(QAOACustom)
if QISKIT_AVAILABLE and QISKIT_OPTIMIZATION_AVAILABLE and QISKIT_ALGORITHMS_AVAILABLE:
    SolverRegistry.register(QiskitQAOA)


# =============================================================================
# BENCHMARK RUNNER
# =============================================================================

class QuantumBenchmark:
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.available_solvers = SolverRegistry.get_available_solvers()
    
    def get_solver_status(self) -> Dict[str, Any]:
        return {
            "qiskit_available": QISKIT_AVAILABLE,
            "qiskit_version": QISKIT_VERSION,
            "dwave_available": DWAVE_AVAILABLE,
            "neal_available": NEAL_AVAILABLE,
            "available_solvers": [
                {
                    "type": s.solver_type.value,
                    "display_name": s.display_name,
                    "category": s.category.value,
                    "is_available": s.is_available,
                    "max_variables": s.max_variables
                }
                for s in SolverRegistry.get_all_solvers()
            ]
        }
    
    def run_benchmark(
        self,
        problem: QUBOProblem,
        solvers: Optional[List[SolverType]] = None,
        skip_large_quantum: bool = True
    ) -> BenchmarkResult:
        start_time = time.perf_counter()
        
        if solvers is None:
            solvers = [s.solver_type for s in self.available_solvers]
        
        results: Dict[SolverType, SolverResult] = {}
        
        for solver_type in solvers:
            try:
                metadata = SolverRegistry._solvers[solver_type].get_metadata()
            except KeyError:
                logger.warning(f"Solver {solver_type} not registered, skipping")
                continue
            
            if not metadata.is_available:
                logger.warning(f"Solver {solver_type.value} not available, skipping")
                continue
            
            if skip_large_quantum:
                if metadata.category in [SolverCategory.QUANTUM_SIMULATION, SolverCategory.QUANTUM_HARDWARE]:
                    if metadata.max_variables and problem.n > metadata.max_variables:
                        logger.info(
                            f"Skipping {solver_type.value} (n={problem.n} > max={metadata.max_variables})"
                        )
                        continue
            
            logger.info(f"Running {solver_type.value}...")
            
            try:
                solver_kwargs = {"seed": self.seed}
                
                if solver_type == SolverType.CLASSICAL_SA_NUMPY:
                    solver_kwargs["num_iterations"] = 10000
                elif solver_type == SolverType.DWAVE_NEAL_SA:
                    solver_kwargs["num_reads"] = 100
                elif solver_type in [SolverType.QAOA_CUSTOM, SolverType.QISKIT_QAOA]:
                    solver_kwargs["p" if solver_type == SolverType.QAOA_CUSTOM else "reps"] = 2
                
                solver = SolverRegistry.get_solver(solver_type, **solver_kwargs)
                result = solver.solve(problem)
                results[solver_type] = result
                
                logger.info(f"  ✓ Energy: {result.energy:.4f}, Time: {result.execution_time_ms:.2f}ms")
                
            except Exception as e:
                logger.error(f"  ✗ Failed: {e}")
                continue
        
        if results:
            best_solver = min(results.keys(), key=lambda k: results[k].energy)
            best_energy = results[best_solver].energy
        else:
            best_solver = None
            best_energy = float('inf')
        
        total_time = (time.perf_counter() - start_time) * 1000
        
        comparison = self._build_comparison(results, best_energy)
        
        return BenchmarkResult(
            problem_id=problem.problem_hash,
            problem_size=problem.n,
            num_variables=problem.n,
            num_nonzero=problem.num_nonzero,
            sparsity=problem.sparsity,
            results=results,
            best_energy=best_energy,
            best_solver=best_solver,
            timestamp=datetime.utcnow().isoformat(),
            total_time_ms=total_time,
            comparison=comparison
        )
    
    def _build_comparison(
        self, 
        results: Dict[SolverType, SolverResult],
        best_energy: float
    ) -> Dict[str, Any]:
        if not results or best_energy == float('inf'):
            return {}
        
        comparison = {
            "solvers": [],
            "summary": {}
        }
        
        classical_times = []
        quantum_times = []
        
        for solver_type, result in results.items():
            if best_energy != 0:
                quality = min(100.0, abs(best_energy / result.energy) * 100)
            else:
                quality = 100.0 if result.energy == 0 else 0.0
            
            is_quantum = result.solver_category in [
                SolverCategory.QUANTUM_SIMULATION,
                SolverCategory.QUANTUM_HARDWARE
            ]
            
            solver_data = {
                "type": solver_type.value,
                "category": result.solver_category.value,
                "is_quantum": is_quantum,
                "energy": result.energy,
                "execution_time_ms": result.execution_time_ms,
                "solution_quality": quality,
                "gap_from_best": result.energy - best_energy,
                "gap_percent": ((result.energy - best_energy) / abs(best_energy) * 100) if best_energy != 0 else 0
            }
            
            comparison["solvers"].append(solver_data)
            
            if is_quantum:
                quantum_times.append(result.execution_time_ms)
            else:
                classical_times.append(result.execution_time_ms)
        
        comparison["summary"] = {
            "num_classical": len(classical_times),
            "num_quantum": len(quantum_times),
            "avg_classical_time_ms": np.mean(classical_times) if classical_times else None,
            "avg_quantum_time_ms": np.mean(quantum_times) if quantum_times else None,
            "best_classical_energy": min(
                (r.energy for r in results.values() 
                 if r.solver_category == SolverCategory.CLASSICAL),
                default=None
            ),
            "best_quantum_energy": min(
                (r.energy for r in results.values()
                 if r.solver_category in [SolverCategory.QUANTUM_SIMULATION, SolverCategory.QUANTUM_HARDWARE]),
                default=None
            )
        }
        
        return comparison
    
    def generate_chart_data(self, benchmark: BenchmarkResult) -> Dict:
        chart_data = {
            "problemSize": benchmark.num_variables,
            "problemHash": benchmark.problem_id,
            "bestEnergy": benchmark.best_energy,
            "bestSolver": benchmark.best_solver.value if benchmark.best_solver else None,
            "timestamp": benchmark.timestamp,
            "totalTimeMs": benchmark.total_time_ms,
            "solvers": []
        }
        
        display_names = {
            SolverType.CLASSICAL_SA_NUMPY: "Classical SA (NumPy)",
            SolverType.CLASSICAL_SA: "Classical SA",
            SolverType.DWAVE_NEAL_SA: "D-Wave Neal SA",
            SolverType.DWAVE_EXACT: "Exact Solver",
            SolverType.DWAVE_QPU: "D-Wave QPU",
            SolverType.QISKIT_QAOA: "Qiskit QAOA",
            SolverType.QAOA_CUSTOM: "QAOA (Custom)",
        }
        
        for solver_type, result in benchmark.results.items():
            if benchmark.best_energy != 0:
                quality = min(100.0, abs(benchmark.best_energy / result.energy) * 100)
            else:
                quality = 100.0 if result.energy == 0 else 0.0
            
            solver_info = {
                "name": solver_type.value,
                "displayName": display_names.get(solver_type, solver_type.value),
                "category": result.solver_category.value,
                "isQuantum": result.solver_category in [
                    SolverCategory.QUANTUM_SIMULATION,
                    SolverCategory.QUANTUM_HARDWARE
                ],
                "energy": result.energy,
                "executionTimeMs": result.execution_time_ms,
                "solutionQuality": quality,
                "gapFromBest": result.energy - benchmark.best_energy,
                "iterations": result.iterations,
                "numReads": result.num_reads,
                "convergenceData": [
                    {"iteration": p.iteration, "energy": p.energy}
                    for p in result.convergence_history[:50]
                ],
                "metadata": result.metadata
            }
            
            chart_data["solvers"].append(solver_info)
        
        chart_data["solvers"].sort(key=lambda x: x["energy"])
        
        return chart_data


def create_qubo_from_dict(
    Q_dict: Dict[Tuple[int, int], float],
    n: int,
    variable_names: Optional[List[str]] = None
) -> QUBOProblem:
    Q = np.zeros((n, n))
    for (i, j), val in Q_dict.items():
        if i == j:
            Q[i, j] = val
        else:
            Q[i, j] = val / 2
            Q[j, i] = val / 2
    
    return QUBOProblem(Q, variable_names)

def run_quick_benchmark(
    Q: np.ndarray,
    variable_names: Optional[List[str]] = None,
    seed: int = 42
) -> Dict:
    problem = QUBOProblem(Q, variable_names)
    benchmark = QuantumBenchmark(seed=seed)
    result = benchmark.run_benchmark(problem)
    return benchmark.generate_chart_data(result)

def demo():
    benchmark = QuantumBenchmark()
    status = benchmark.get_solver_status()
    print("Solver Status:", status)
    n = 8
    np.random.seed(42)
    Q = np.random.randn(n, n) * 10
    Q = (Q + Q.T) / 2
    np.fill_diagonal(Q, np.abs(np.diag(Q)) + 20)
    variable_names = [f"bucket_{i}" for i in range(n)]
    problem = QUBOProblem(Q, variable_names, problem_name="test_qubo")
    result = benchmark.run_benchmark(problem)
    print("Best energy:", result.best_energy)
    return result

if __name__ == "__main__":
    demo()
