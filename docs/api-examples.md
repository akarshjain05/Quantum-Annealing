# NostroQ Quantum API Examples

## Check Quantum Status

```bash
curl -X GET http://localhost:8000/api/quantum/status
```

Response:
```json
{
  "qiskit_available": true,
  "qiskit_version": "1.0.0",
  "dwave_available": true,
  "neal_available": true,
  "quantum_ready": true,
  "available_solvers": [
    {"type": "classical_sa_numpy", "display_name": "Classical SA (NumPy)", "is_available": true},
    {"type": "dwave_neal_sa", "display_name": "D-Wave Neal SA", "is_available": true},
    {"type": "qaoa_custom", "display_name": "QAOA (Custom)", "is_available": true}
  ],
  "message": "System is quantum-ready. QAOA and/or quantum annealing simulation available."
}
```

## Run Optimization with Benchmark

```bash
curl -X POST http://localhost:8000/api/quantum/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "risk_config": {
      "risk_appetite": "conservative",
      "confidence_level": 0.95
    },
    "solver_config": {
      "run_classical": true,
      "run_quantum": true,
      "seed": 42
    },
    "run_benchmark": true
  }'
```

Response:
```json
{
  "run_id": "run_20240821_153245_a3f8c2",
  "timestamp": "2024-08-21T15:32:45Z",
  "status": "completed",
  "problem_size": 88,
  "num_corridors": 11,
  "total_liquidity": 378500000,
  "capital_released": 68500000,
  "capital_release_percent": 18.1,
  "annual_savings_opportunity": 3425000,
  "benchmark": {
    "problem_size": 88,
    "best_energy": -6946.0,
    "best_solver": "classical_sa_numpy",
    "solvers": [
      {
        "solver_type": "classical_sa_numpy",
        "display_name": "Classical SA (NumPy)",
        "is_quantum": false,
        "energy": -6946.0,
        "execution_time_ms": 847.23,
        "solution_quality": 100.0
      },
      {
        "solver_type": "dwave_neal_sa",
        "display_name": "D-Wave Neal SA",
        "is_quantum": false,
        "energy": -6944.2,
        "execution_time_ms": 1234.56,
        "solution_quality": 99.97
      }
    ]
  }
}
```

## Run Quick Benchmark (Test)

```bash
curl -X POST "http://localhost:8000/api/quantum/benchmark/quick?num_variables=16&seed=42&run_quantum=true"
```

## Get Benchmark History

```bash
curl -X GET "http://localhost:8000/api/quantum/benchmark/history?limit=10"
```

## Validate Custom QUBO Matrix

```bash
curl -X POST http://localhost:8000/api/quantum/validate-qubo \
  -H "Content-Type: application/json" \
  -d '{
    "matrix": [
      [1.0, -0.5, 0.0],
      [-0.5, 2.0, -0.3],
      [0.0, -0.3, 1.5]
    ],
    "variable_names": ["x0", "x1", "x2"]
  }'
```

## Health Check

```bash
curl -X GET http://localhost:8000/api/quantum/health
```

## Export Results

```bash
# JSON format
curl -X GET "http://localhost:8000/api/quantum/export/run_20240821_153245_a3f8c2?format=json"

# CSV format
curl -X GET "http://localhost:8000/api/quantum/export/run_20240821_153245_a3f8c2?format=csv"
```

---

## Running the API

### 1. Start the Server

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. View API Documentation

Open in browser:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 3. Run Tests

```bash
cd backend
python -m pytest test_api_quantum.py -v
```
