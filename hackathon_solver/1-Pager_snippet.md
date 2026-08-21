### 4. Architecture Snapshot
*   **QUBO Formulation**: Maps corridor cost (opportunity, FX, risk) onto diagonal terms and enforces constraints with quadratic penalty terms.
*   **SA Solver (Production)**: Uses classical Simulated Annealing for scalable, high-performance optimization across the full network.
*   **QAOA Benchmark**: Provides a small-scale correctness and feasibility check by running on Qiskit's simulator.
*   **Feasibility Filter**: Post-processes bit assignments to ensure no allocations strictly violate the base volume requirements.

### 7. What's Fake vs Real
*   The **QAOA benchmark** uses a reduced toy instance (2 corridors, small bit-width), not the full corridor set. This is strictly due to simulator qubit and runtime limits. 
*   **No real quantum advantage** is claimed at this scale; the QAOA implementation is an honest proof-of-correctness and architectural validation.
*   The production results on synthetic datasets use entirely classical SA.
