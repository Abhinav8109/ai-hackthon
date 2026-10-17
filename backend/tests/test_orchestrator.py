import pytest
from backend.services.orchestrator import QbrAgentOrchestrator
from backend.database import init_db, get_db_connection

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_agent_orchestration_workflow():
    orchestrator = QbrAgentOrchestrator(reporting_period="2026-Q3")
    run_record = orchestrator.execute_workflow()

    assert run_record.status == "completed"
    assert len(run_record.stages) == 7
    assert len(run_record.tool_calls) >= 5
    assert run_record.executive_narrative is not None
    assert len(run_record.critic_notes) >= 3

    # Check stage names
    stage_names = [s.stage_name for s in run_record.stages]
    assert any("Data Quality" in s for s in stage_names)
    assert any("Deterministic KPI" in s for s in stage_names)
    assert any("Customer Q&A" in s for s in stage_names)
    assert any("Evidence Traceability" in s for s in stage_names)

    # Verify run record in DB
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM agent_runs WHERE run_id = ?", (run_record.run_id,)).fetchone()
    assert row is not None
    assert row["status"] == "completed"
    conn.close()
