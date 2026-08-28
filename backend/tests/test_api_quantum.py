import pytest
from fastapi.testclient import TestClient
import sys
import os

from app.main import app

client = TestClient(app)

class TestQuantumStatusEndpoint:
    def test_get_status(self):
        response = client.get("/api/quantum/status")
        assert response.status_code == 200
        data = response.json()
        assert "qiskit_available" in data
        assert "dwave_available" in data
        assert "available_solvers" in data
        assert "quantum_ready" in data
        assert "message" in data

    def test_status_has_classical_solver(self):
        response = client.get("/api/quantum/status")
        data = response.json()
        solver_types = [s["type"] for s in data["available_solvers"]]
        assert "classical_sa_numpy" in solver_types

class TestSolversEndpoint:
    def test_list_solvers(self):
        response = client.get("/api/quantum/solvers")
        assert response.status_code == 200
        data = response.json()
        assert "solvers" in data
        assert "total" in data
        assert "available" in data
        assert len(data["solvers"]) > 0

    def test_solver_has_required_fields(self):
        response = client.get("/api/quantum/solvers")
        data = response.json()
        for solver in data["solvers"]:
            assert "type" in solver
            assert "category" in solver
            assert "display_name" in solver
            assert "is_available" in solver
            assert "is_quantum" in solver

class TestQuickBenchmarkEndpoint:
    def test_quick_benchmark(self):
        response = client.post(
            "/api/quantum/benchmark/quick",
            params={"num_variables": 8, "seed": 42}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "benchmark" in data
        assert data["problem"]["num_variables"] == 8

class TestValidateQuboEndpoint:
    def test_validate_simple_qubo(self):
        response = client.post(
            "/api/quantum/validate-qubo",
            json={
                "matrix": [[1, -0.5], [-0.5, 2]],
                "variable_names": ["x0", "x1"]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] == True
        assert data["num_variables"] == 2
        assert data["is_symmetric"] == True

class TestHealthEndpoint:
    def test_health_check(self):
        response = client.get("/api/quantum/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

