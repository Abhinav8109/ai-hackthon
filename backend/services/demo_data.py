import json
from datetime import datetime, timezone
from backend.database import get_db_connection, init_db
from backend.models.schemas import (
    CanonicalKPIRecord,
    Project,
    Milestone,
    RAIDItem,
    ActionItem,
    DecisionItem,
    CommitmentItem,
    CustomerQAItem
)
from backend.services.governance import (
    save_project,
    save_milestone,
    save_raid_item,
    save_action_item,
    save_decision_item
)
from backend.services.historical import (
    ingest_historical_document,
    save_commitment
)

DEMO_KPIS = [
    # SLA Metrics
    {
        "record_id": "kpi_demo_01",
        "reporting_period": "2026-Q3",
        "project": "Cloud Platform",
        "program": "Infrastructure Modernization",
        "workstream": "Reliability & SRE",
        "metric_name": "Platform Availability",
        "metric_category": "SLA",
        "actual_value": 98.8,
        "target_value": 99.5,
        "unit": "%",
        "direction_of_improvement": "higher_is_better",
        "currency": "USD",
        "source_file": "synthetic_q3_sla_telemetry.csv",
        "source_row": 2,
        "source_cell": "R2C4",
        "data_quality_status": "warning",
        "notes": "Breached contractual threshold due to August 14 database maintenance deadlock."
    },
    {
        "record_id": "kpi_demo_02",
        "reporting_period": "2026-Q3",
        "project": "Cloud Platform",
        "program": "Infrastructure Modernization",
        "workstream": "Reliability & SRE",
        "metric_name": "P1 MTTR",
        "metric_category": "SLA",
        "actual_value": 42.0,
        "target_value": 60.0,
        "unit": "mins",
        "direction_of_improvement": "lower_is_better",
        "currency": "USD",
        "source_file": "synthetic_q3_sla_telemetry.csv",
        "source_row": 3,
        "source_cell": "R3C4",
        "data_quality_status": "valid",
        "notes": "18 minutes faster than target threshold."
    },
    # Financial Metrics
    {
        "record_id": "kpi_demo_03",
        "reporting_period": "2026-Q3",
        "project": "Cloud Platform",
        "program": "Infrastructure Modernization",
        "workstream": "Finance & FinOps",
        "metric_name": "Actual Spend",
        "metric_category": "Financial",
        "actual_value": 1275000.0,
        "target_value": 1200000.0,
        "unit": "$",
        "direction_of_improvement": "lower_is_better",
        "currency": "USD",
        "source_file": "synthetic_q3_financial_ledger.xlsx",
        "source_row": 15,
        "source_cell": "R15C3",
        "data_quality_status": "valid",
        "notes": "Spend variance +$75,000 due to upfront disaster recovery compute provisioning."
    },
    {
        "record_id": "kpi_demo_04",
        "reporting_period": "2026-Q3",
        "project": "Cloud Platform",
        "program": "Infrastructure Modernization",
        "workstream": "Finance & FinOps",
        "metric_name": "Gross Margin",
        "metric_category": "Financial",
        "actual_value": 31.1,
        "target_value": 35.0,
        "unit": "%",
        "direction_of_improvement": "higher_is_better",
        "currency": "USD",
        "source_file": "synthetic_q3_financial_ledger.xlsx",
        "source_row": 18,
        "source_cell": "R18C3",
        "data_quality_status": "warning",
        "notes": "Gross margin down 3.9% due to hardware inflation and accelerated cloud migration."
    },
    # Quality / CSAT Metrics
    {
        "record_id": "kpi_demo_05",
        "reporting_period": "2026-Q3",
        "project": "Core Apps",
        "program": "Digital Customer Experience",
        "workstream": "Product & Engineering",
        "metric_name": "Customer Satisfaction (CSAT)",
        "metric_category": "Customer",
        "actual_value": 4.7,
        "target_value": 4.5,
        "unit": "score",
        "direction_of_improvement": "higher_is_better",
        "currency": "USD",
        "source_file": "synthetic_q3_csat_surveys.csv",
        "source_row": 8,
        "source_cell": "R8C2",
        "data_quality_status": "valid",
        "notes": "Strong positive sentiment following checkout redesign."
    },
    {
        "record_id": "kpi_demo_06",
        "reporting_period": "2026-Q3",
        "project": "Core Apps",
        "program": "Digital Customer Experience",
        "workstream": "Engineering",
        "metric_name": "Sprint Velocity",
        "metric_category": "Delivery",
        "actual_value": 88.0,
        "target_value": 85.0,
        "unit": "pts",
        "direction_of_improvement": "higher_is_better",
        "currency": "USD",
        "source_file": "synthetic_jira_velocity.csv",
        "source_row": 12,
        "source_cell": "R12C3",
        "data_quality_status": "valid",
        "notes": "Engineering velocity outperforming targets."
    }
]

def seed_demo_data(force_reset: bool = False):
    """
    Populates SQLite database with rich, fully interconnected demo records.
    """
    init_db()
    conn = get_db_connection()

    if force_reset:
        conn.execute("DELETE FROM canonical_kpis")
        conn.execute("DELETE FROM validation_reports")
        conn.execute("DELETE FROM projects")
        conn.execute("DELETE FROM milestones")
        conn.execute("DELETE FROM raid_items")
        conn.execute("DELETE FROM action_items")
        conn.execute("DELETE FROM decision_items")
        conn.execute("DELETE FROM historical_documents")
        conn.execute("DELETE FROM historical_chunks")
        conn.execute("DELETE FROM commitments")
        conn.execute("DELETE FROM qa_items")
        conn.execute("DELETE FROM agent_runs")
        conn.execute("DELETE FROM reports")
        conn.commit()

    # Check if already seeded
    existing_kpis = conn.execute("SELECT COUNT(*) as cnt FROM canonical_kpis").fetchone()["cnt"]
    if existing_kpis > 0 and not force_reset:
        conn.close()
        return

    conn.close()

    # 1. Seed Canonical KPIs
    conn = get_db_connection()
    for k in DEMO_KPIS:
        conn.execute("""
        INSERT OR REPLACE INTO canonical_kpis (
            record_id, reporting_period, project, program, workstream,
            metric_name, metric_category, actual_value, target_value, unit,
            direction_of_improvement, currency, source_file, worksheet_or_table,
            source_row, source_cell, timestamp, data_quality_status, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?, ?)
        """, (
            k["record_id"], k["reporting_period"], k["project"], k["program"],
            k["workstream"], k["metric_name"], k["metric_category"],
            k["actual_value"], k["target_value"], k["unit"],
            k["direction_of_improvement"], k["currency"], k["source_file"],
            "Sheet1", k["source_row"], k["source_cell"],
            k["data_quality_status"], k["notes"]
        ))
    conn.commit()
    conn.close()

    # 2. Seed Projects
    save_project(Project(
        id="proj-demo-1",
        name="Cloud Migration & Modernization",
        program="Infrastructure Transformation",
        sponsor="EVP Technology",
        owner="Marcus Vance",
        health="amber",
        delivery_confidence=82.0,
        approved_budget=1500000.0,
        actual_spend=1275000.0,
        reporting_period="2026-Q3",
        key_updates="Core cluster migration 90% complete. Database cutover experiencing schedule delay."
    ))
    save_project(Project(
        id="proj-demo-2",
        name="Digital Customer Experience",
        program="Growth Platforms",
        sponsor="Chief Digital Officer",
        owner="Elena Rostova",
        health="green",
        delivery_confidence=94.0,
        approved_budget=800000.0,
        actual_spend=740000.0,
        reporting_period="2026-Q3",
        key_updates="New checkout portal launched ahead of schedule. CSAT tracking at 4.7/5.0."
    ))

    # 3. Seed Milestones
    save_milestone(Milestone(
        id="M-DEMO-01",
        project_id="proj-demo-1",
        project_name="Cloud Migration & Modernization",
        title="Database Cutover (Production)",
        planned_date="2026-08-30",
        actual_or_forecast_date="2026-09-15",
        completion_pct=75.0,
        status="delayed",
        owner="Database Team Lead",
        criticality="critical",
        dependencies=["M-DEMO-00"],
        recovery_plan="Additional rehearsal window scheduled on Sept 6; parallel cutover team engaged.",
        customer_dependency=True,
        escalation_status="Escalated to Program Steering Committee"
    ))
    save_milestone(Milestone(
        id="M-DEMO-02",
        project_id="proj-demo-1",
        project_name="Cloud Migration & Modernization",
        title="Multi-Region Automated Failover",
        planned_date="2026-09-20",
        actual_or_forecast_date="2026-09-22",
        completion_pct=60.0,
        status="on_track",
        owner="SRE Director",
        criticality="high",
        dependencies=["M-DEMO-01"],
        recovery_plan=None,
        customer_dependency=False
    ))
    save_milestone(Milestone(
        id="M-DEMO-03",
        project_id="proj-demo-2",
        project_name="Digital Customer Experience",
        title="Checkout Microservices Rollout",
        planned_date="2026-07-15",
        actual_or_forecast_date="2026-07-12",
        completion_pct=100.0,
        status="completed",
        owner="Lead Architect",
        criticality="high",
        dependencies=[],
        recovery_plan=None,
        customer_dependency=False
    ))

    # 4. Seed RAID
    save_raid_item(RAIDItem(
        id="R-DEMO-01",
        type="risk",
        title="Third-Party Payment Gateway Deprecation",
        description="Legacy API v1 will be turned off in November, potentially impacting checkout reliability.",
        category="Technical",
        impact=4,
        likelihood=4,
        score=16,
        severity="critical",
        owner="Lead Architect",
        due_date="2026-10-15",
        status="open",
        mitigation="Develop v2 adapter in sprint 33; validate against sandbox endpoints.",
        contingency="Maintain failover to secondary merchant processor.",
        project_id="proj-demo-2",
        related_milestone_id="M-DEMO-03"
    ))
    save_raid_item(RAIDItem(
        id="R-DEMO-02",
        type="issue",
        title="Platform Availability SLA Breach",
        description="August 14 database replica synchronization stalled for 42 minutes, reducing Q3 availability to 98.8%.",
        category="Governance",
        impact=4,
        likelihood=5,
        score=20,
        severity="critical",
        owner="SRE Lead",
        due_date="2026-09-10",
        status="in_progress",
        mitigation="Apply $35,000 credit memo per MSA Schedule 4.2; implement automated heartbeat failover.",
        contingency=None,
        project_id="proj-demo-1"
    ))
    save_raid_item(RAIDItem(
        id="R-DEMO-03",
        type="dependency",
        title="Customer Security Approval for SSO Federation",
        description="SSO implementation complete; waiting on customer security architecture sign-off.",
        category="Governance",
        impact=3,
        likelihood=3,
        score=9,
        severity="medium",
        owner="Security Architect",
        due_date="2026-09-05",
        status="open",
        mitigation="Submitted architecture review documentation on August 10.",
        project_id="proj-demo-1"
    ))

    # 5. Seed Actions & Decisions
    save_action_item(ActionItem(
        id="ACT-DEMO-01",
        title="Execute Automated Failover Simulation",
        description="Conduct chaos test on secondary cloud region prior to peak holiday traffic.",
        owner="Sarah Chen (SRE)",
        priority="urgent",
        due_date="2026-09-12",
        status="in_progress",
        related_qbr="2026-Q3",
        linked_risk_id="R-DEMO-02",
        dependencies=["M-DEMO-02"],
        acceptance_criteria="Failover completes within 60 seconds with zero transaction loss."
    ))
    save_action_item(ActionItem(
        id="ACT-DEMO-02",
        title="Submit $35,000 SLA Credit Memo",
        description="Process contractual penalty credit on October billing cycle.",
        owner="Financial Controller",
        priority="high",
        due_date="2026-09-25",
        status="open",
        related_qbr="2026-Q3",
        dependencies=[],
        acceptance_criteria="Credit verified by account executive and client procurement."
    ))

    save_decision_item(DecisionItem(
        id="DEC-DEMO-01",
        title="Approve Change Freeze Calendar for Q4 Peak Season",
        options_considered=[
            "Option A: Strict code freeze from Nov 15 - Jan 05",
            "Option B: Partial freeze allowing priority bugfixes with VP approval",
            "Option C: Business as usual weekly deployments"
        ],
        selected_decision="Option B: Partial freeze with VP approval gateway",
        rationale="Balances operational stability with the flexibility to remediate critical merchant issues.",
        decision_owner="EVP Technology & Customer Sponsor",
        decision_date="2026-09-15",
        status="proposed",
        dependencies=["ACT-DEMO-01"],
        follow_up_actions=["Publish change freeze criteria to engineering squads"],
        customer_ask=True
    ))

    # 6. Seed Historical Document & Commitments
    hist_sample = """MINUTES OF Q2 EXECUTIVE BUSINESS REVIEW (2026-06-15)
Attendees: Marcus Vance, Elena Rostova, Client VP John Doe.

Commitments & Agreed Actions:
1. SRE squad committed to deploy automated multi-region failover by Q3.
2. Architecture squad committed to upgrading the database cluster by August 15.
3. Security squad committed to implement SSO Federation pending customer security sign-off.
4. FinOps agreed to complete cluster rightsizing to reduce compute unit cost by 8%.
"""
    ingest_historical_document(hist_sample.encode("utf-8"), "Q2_Executive_Review_Minutes.txt")

    save_commitment(CommitmentItem(
        id="CMT-DEMO-01",
        original_wording="Architecture squad committed to upgrading the database cluster by August 15.",
        source_document="Q2_Executive_Review_Minutes.txt",
        source_location="Section 2, Bullet 2",
        owner="Database Team Lead",
        due_date="2026-08-15",
        project_id="proj-demo-1",
        expected_outcome="Production database running on Aurora cluster.",
        current_status="at_risk",
        closure_evidence="Cutover delayed to Sept 15 due to data synchronization verification.",
        confidence=0.88,
        review_requirement="Review recovery trajectory at Q3 QBR."
    ))
    save_commitment(CommitmentItem(
        id="CMT-DEMO-02",
        original_wording="Security squad committed to implement SSO Federation pending customer security sign-off.",
        source_document="Q2_Executive_Review_Minutes.txt",
        source_location="Section 2, Bullet 3",
        owner="Security Architect",
        due_date="2026-08-30",
        project_id="proj-demo-1",
        expected_outcome="Single sign-on operational for all client users.",
        current_status="open",
        closure_evidence="Implementation completed in staging; customer sign-off pending.",
        confidence=0.92,
        review_requirement="Requires customer security sponsor approval."
    ))
    save_commitment(CommitmentItem(
        id="CMT-DEMO-03",
        original_wording="FinOps agreed to complete cluster rightsizing to reduce compute unit cost by 8%.",
        source_document="Q2_Executive_Review_Minutes.txt",
        source_location="Section 2, Bullet 4",
        owner="FinOps Lead",
        due_date="2026-07-31",
        project_id="proj-demo-1",
        expected_outcome="8% reduction in EC2/GKE compute bills.",
        current_status="closed_with_evidence",
        closure_evidence="Verified 8.4% compute cost reduction reflected in July and August invoices.",
        confidence=0.98,
        review_requirement="Closed with financial telemetry."
    ))

    print("Demo dataset seeded successfully.")

if __name__ == "__main__":
    seed_demo_data(force_reset=True)
