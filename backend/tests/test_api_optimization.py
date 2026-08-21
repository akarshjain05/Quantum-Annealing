def test_health_endpoint(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_login_rejects_bad_password(client):
    resp = client.post("/api/auth/login", json={"email": "treasury@demo-bank.com", "password": "wrong"})
    assert resp.status_code == 401


def test_dashboard_requires_auth(client):
    resp = client.get("/api/dashboard")
    assert resp.status_code == 401


def test_dashboard_returns_seeded_data(client, auth_headers):
    resp = client.get("/api/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["num_corridors"] >= 10
    assert data["total_nostro_liquidity_musd"] > 0
    assert "Synthetic" in data["synthetic_data_notice"]


def test_optimization_run_end_to_end(client, auth_headers):
    resp = client.post("/api/optimization/run", headers=auth_headers, json={
        "confidence_level": 0.95, "iterations": 3000,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("COMPLETED", "INVALID")
    assert data["qubo_variables"] > 0
    assert data["final_energy"] <= data["initial_energy"]
    assert len(data["corridor_results"]) >= 10
    assert data["onehot_clean"] is True


def test_qubo_inspector_returns_bounded_matrix(client, auth_headers):
    run_resp = client.post("/api/optimization/run", headers=auth_headers, json={"iterations": 2000})
    run_id = run_resp.json()["run_id"]
    resp = client.get(f"/api/qubo/{run_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["matrix_dimension"] == [data["num_variables"], data["num_variables"]]
    assert data["num_variables"] < 500  # bounded/manageable per spec §7


def test_agent_ask_general_snapshot(client, auth_headers):
    resp = client.post("/api/agent/ask", headers=auth_headers, json={"question": "hello"})
    assert resp.status_code == 200
    data = resp.json()
    assert "Total nostro liquidity" in data["answer"]
    assert data["intent_detected"] == "general_snapshot"


def test_agent_ask_regulation_never_claims_real_regulation(client, auth_headers):
    resp = client.post("/api/agent/ask", headers=auth_headers, json={"question": "which recommendation is based on a regulatory rule?"})
    assert resp.status_code == 200
    answer = resp.json()["answer"]
    assert "could not verify" in answer or "SYNTHETIC" in answer


def test_audit_chain_valid_after_runs(client, auth_headers):
    client.post("/api/optimization/run", headers=auth_headers, json={"iterations": 1500})
    resp = client.get("/api/audit/verify", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["valid"] is True


def test_stress_tests_run(client, auth_headers):
    resp = client.post("/api/stress-tests/run", headers=auth_headers, json={})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["scenarios"]) == 8
    for s in data["scenarios"]:
        assert s["settlement_coverage"] > 0
