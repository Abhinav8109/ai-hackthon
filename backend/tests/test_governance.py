import pytest
from backend.services.governance import (
    save_project, list_projects,
    save_milestone, list_milestones,
    save_raid_item, list_raid_items,
    save_action_item, list_action_items,
    save_decision_item, list_decision_items,
    calculate_program_health_summary
)
from backend.models.schemas import (
    Project, Milestone, RAIDItem, ActionItem, DecisionItem
)
from backend.database import init_db

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_project_crud():
    proj = Project(
        id="proj-101",
        name="Cloud Migration",
        program="Modernization",
        sponsor="VP Tech",
        owner="Alice",
        health="amber",
        delivery_confidence=82.5,
        approved_budget=500000.0,
        actual_spend=420000.0,
        reporting_period="2026-Q3",
        key_updates="Phase 2 compute clusters provisioning in progress."
    )
    save_project(proj)
    projs = list_projects("2026-Q3")
    assert any(p.id == "proj-101" for p in projs)

def test_raid_scoring_and_severity():
    item = RAIDItem(
        id="R-01",
        type="risk",
        title="Third-party API deprecation",
        description="Payment gateway version 1 retiring in Nov.",
        category="Technical",
        impact=4,
        likelihood=5,
        score=0, # will be recalculated to 20
        severity="low", # will be recalculated to critical
        owner="Bob",
        due_date="2026-11-15",
        status="open",
        mitigation="Implement SDK v2 wrapper.",
        project_id="proj-101"
    )
    saved = save_raid_item(item)
    assert saved.score == 20
    assert saved.severity == "critical"

def test_milestone_and_health_rollup():
    m = Milestone(
        id="M-01",
        project_id="proj-101",
        project_name="Cloud Migration",
        title="Database Cutover",
        planned_date="2026-08-30",
        actual_or_forecast_date="2026-09-15",
        completion_pct=75.0,
        status="delayed",
        owner="Carol",
        criticality="critical",
        dependencies=["M-00"],
        recovery_plan="Adding weekend migration crew.",
        customer_dependency=True
    )
    save_milestone(m)
    
    health = calculate_program_health_summary()
    assert health["at_risk_milestones_count"] >= 1
    assert "drivers" in health
