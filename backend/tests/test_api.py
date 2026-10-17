import pytest
from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "QBR Intelligence" in data["app"]

def test_dashboard_summary_endpoint():
    response = client.get("/api/v1/dashboard/summary?period=2026-Q3")
    assert response.status_code == 200
    data = response.json()
    assert "health" in data
    assert "financials" in data
    assert "kpis" in data
    assert len(data["kpis"]) >= 3
    assert data["financials"]["approved_budget"] > 0

def test_projects_and_governance():
    response = client.get("/api/v1/projects")
    assert response.status_code == 200
    projects = response.json()
    assert len(projects) >= 1
    assert "delivery_confidence" in projects[0]

def test_scenario_run():
    payload = {
        "scenario_name": "API Test Scenario",
        "sla_recovery_delta_pct": 1.0,
        "cost_reduction_delta": 25000.0,
        "milestone_acceleration_days": 10,
        "utilization_target_pct": 85.0,
        "penalty_relief_pct": 25.0
    }
    response = client.post("/api/v1/scenarios/run", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["scenario_name"] == "API Test Scenario"
    assert "projected" in data
    assert data["projected"]["sla_achievement_pct"] > 0

def test_agent_run_execution():
    response = client.post("/api/v1/agents/run", data={"reporting_period": "2026-Q3"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert len(data["stages"]) == 7
    assert len(data["tool_calls"]) >= 4

def test_pptx_export_endpoint():
    config = {
        "reporting_period": "2026-Q3",
        "program_name": "API Test Program",
        "customer_name": "Enterprise Client Inc",
        "presentation_length": "standard",
        "executive_tone": "objective_transparent"
    }
    response = client.post("/api/v1/reports/pptx", json=config)
    assert response.status_code == 200
    data = response.json()
    assert data["verified"] is True
    assert data["slide_count"] >= 5

    # Test download endpoint
    report_id = data["report_id"]
    dl_response = client.get(f"/api/v1/reports/{report_id}/download")
    assert dl_response.status_code == 200
    assert len(dl_response.content) > 1000
