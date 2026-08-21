## Solver Engine

The optimization pipeline runs three different solvers depending on the execution context:

*   **`solve_with_neal`**: Production classical Simulated Annealing solver (using D-Wave's `neal` sampler). Highly efficient for very large problems.
*   **`solve_with_custom_sa`**: Hand-rolled bit-flip Simulated Annealing local search with $O(1)$ incremental delta-energy updates per flip. Useful for explainability and as a robust fallback.
*   **`solve_with_qaoa`**: Quantum Approximate Optimization Algorithm via Qiskit. **Note:** QAOA runs only on small toy instances (≤18 variables) due to simulator limits; production-scale results use classical SA. No real quantum advantage is claimed at this scale.
