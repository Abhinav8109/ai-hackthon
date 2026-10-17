import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.database import init_db, get_db_connection
from backend.models.schemas import (
    CanonicalKPIRecord,
    Project,
    Milestone,
    RAIDItem,
    ActionItem,
    DecisionItem,
    CommitmentItem,
    CustomerQAItem,
    PresentationConfig,
    ScenarioInput
)
from backend.services.analytics import (
    calculate_qoq_variance,
    calculate_financial_summary,
    calculate_penalty_exposure,
    generate_linear_forecast,
    run_what_if_scenario
)
from backend.services.data_ingestion import (
    parse_and_validate_file,
    save_canonical_records_to_db
)
from backend.services.governance import (
    list_projects, save_project,
    list_milestones, save_milestone,
    list_raid_items, save_raid_item,
    list_action_items, save_action_item,
    list_decision_items, save_decision_item,
    calculate_program_health_summary
)
from backend.services.historical import (
    ingest_historical_document,
    search_historical_chunks,
    list_commitments,
    save_commitment
)
from backend.services.orchestrator import QbrAgentOrchestrator
from backend.services.presentation import generate_qbr_presentation
from backend.services.demo_data import seed_demo_data

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_demo_data(force_reset=False)
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Agentic AI-Powered QBR, Program Governance, and Financial Intelligence Platform",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------
# System & Health
# -------------------------------------------------------------
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "env": settings.ENV,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# -------------------------------------------------------------
# Dashboard Executive Summary
# -------------------------------------------------------------
@app.get("/api/v1/dashboard/summary")
def get_dashboard_summary(period: str = "2026-Q3"):
    health = calculate_program_health_summary()
    
    # Financial summary calculation
    fin = calculate_financial_summary(
        reporting_period=period,
        approved_budget=1500000.0,
        planned_spend=1200000.0,
        actual_spend=1275000.0,
        forecast_spend=1350000.0,
        revenue=1850000.0,
        cost=1275000.0,
        penalty_exposure=35000.0
    )

    penalty = calculate_penalty_exposure(
        rule_id="RULE-MSA-SLA-01",
        sla_name="Platform Availability",
        target_threshold=99.5,
        actual_measured=98.8,
        penalty_rate_per_unit=5000.0,
        unit_step=0.1,
        cap_amount=50000.0
    )

    # Fetch top KPIs
    conn = get_db_connection()
    kpi_rows = conn.execute("SELECT * FROM canonical_kpis WHERE reporting_period = ?", (period,)).fetchall()
    conn.close()

    kpis = []
    for r in kpi_rows:
        res = calculate_qoq_variance(
            metric_name=r["metric_name"],
            category=r["metric_category"],
            reporting_period=r["reporting_period"],
            actual=r["actual_value"],
            target=r["target_value"],
            unit=r["unit"],
            direction=r["direction_of_improvement"],
            source_lineage=f"{r['source_file']} (Row {r['source_row']})"
        )
        kpis.append(res.model_dump())

    # Executive alerts
    alerts = [
        {
            "id": "ALT-01",
            "severity": "critical",
            "title": "Platform Availability Breached SLA (98.8% vs 99.5%)",
            "impacted_metric": "Availability",
            "workstream": "SRE",
            "penalty_exposure": "$35,000",
            "recommended_action": "Ratify automated failover configuration & issue credit memo.",
            "due_date": "2026-09-12"
        },
        {
            "id": "ALT-02",
            "severity": "high",
            "title": "Database Cutover Milestone Delayed by 16 Days",
            "impacted_metric": "Schedule",
            "workstream": "Cloud Modernization",
            "penalty_exposure": "$0",
            "recommended_action": "Engage weekend migration crew for Sept 15 cutover window.",
            "due_date": "2026-09-15"
        },
        {
            "id": "ALT-03",
            "severity": "medium",
            "title": "Customer Decision Pending: Q4 Change Freeze",
            "impacted_metric": "Governance",
            "workstream": "Steering Committee",
            "penalty_exposure": "$0",
            "recommended_action": "Sponsor approval required on Option B freeze schedule.",
            "due_date": "2026-09-15"
        }
    ]

    return {
        "reporting_period": period,
        "health": health,
        "financials": fin.model_dump(),
        "penalty_summary": penalty.model_dump(),
        "kpis": kpis,
        "alerts": alerts,
        "demo_mode": True
    }

# -------------------------------------------------------------
# Data Studio: Ingestion, Validation & Lineage
# -------------------------------------------------------------
@app.get("/api/v1/datasets")
def list_datasets():
    conn = get_db_connection()
    reports = conn.execute("SELECT * FROM validation_reports ORDER BY created_at DESC").fetchall()
    kpi_count = conn.execute("SELECT COUNT(*) as cnt FROM canonical_kpis").fetchone()["cnt"]
    conn.close()

    items = []
    for r in reports:
        d = dict(r)
        d["warnings"] = json.loads(d.get("warnings_json", "[]"))
        d["errors"] = json.loads(d.get("errors_json", "[]"))
        items.append(d)

    return {
        "datasets": items,
        "total_canonical_records": kpi_count
    }

@app.post("/api/v1/datasets/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    reporting_period: str = Form("2026-Q3")
):
    contents = await file.read()
    report, records = parse_and_validate_file(
        file_bytes=contents,
        filename=file.filename,
        reporting_period=reporting_period
    )

    if records:
        save_canonical_records_to_db(records, report)

    return {
        "report": report.model_dump(),
        "records_ingested": len(records),
        "status": report.resolution_status
    }

@app.get("/api/v1/kpis")
def get_canonical_kpis(period: Optional[str] = None):
    conn = get_db_connection()
    if period:
        rows = conn.execute("SELECT * FROM canonical_kpis WHERE reporting_period = ?", (period,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM canonical_kpis").fetchall()
    conn.close()
    return [dict(r) for r in rows]

# -------------------------------------------------------------
# Program Governance: Projects, Milestones, RAID, Actions, Decisions
# -------------------------------------------------------------
@app.get("/api/v1/projects")
def get_projects(period: Optional[str] = None):
    return [p.model_dump() for p in list_projects(period)]

@app.post("/api/v1/projects")
def create_project(proj: Project):
    return save_project(proj).model_dump()

@app.get("/api/v1/milestones")
def get_milestones(project_id: Optional[str] = None):
    return [m.model_dump() for m in list_milestones(project_id)]

@app.post("/api/v1/milestones")
def create_milestone(m: Milestone):
    return save_milestone(m).model_dump()

@app.get("/api/v1/raid")
def get_raid(type: Optional[str] = None, severity: Optional[str] = None):
    return [r.model_dump() for r in list_raid_items(type, severity)]

@app.post("/api/v1/raid")
def create_raid(item: RAIDItem):
    return save_raid_item(item).model_dump()

@app.get("/api/v1/actions")
def get_actions(status: Optional[str] = None, priority: Optional[str] = None):
    return [a.model_dump() for a in list_action_items(status, priority)]

@app.post("/api/v1/actions")
def create_action(action: ActionItem):
    return save_action_item(action).model_dump()

@app.patch("/api/v1/actions/{action_id}")
def update_action_status(action_id: str, status: str = Query(...)):
    conn = get_db_connection()
    conn.execute("UPDATE action_items SET status = ? WHERE id = ?", (status, action_id))
    conn.commit()
    conn.close()
    return {"status": "updated", "action_id": action_id, "new_status": status}

@app.get("/api/v1/decisions")
def get_decisions(status: Optional[str] = None):
    return [d.model_dump() for d in list_decision_items(status)]

@app.post("/api/v1/decisions")
def create_decision(decision: DecisionItem):
    return save_decision_item(decision).model_dump()

# -------------------------------------------------------------
# Historical Intelligence & Document Ingestion
# -------------------------------------------------------------
@app.post("/api/v1/history/upload")
async def upload_history_doc(file: UploadFile = File(...)):
    contents = await file.read()
    doc, chunks = ingest_historical_document(contents, file.filename)
    return {
        "document": doc.model_dump(),
        "chunks_indexed": len(chunks)
    }

@app.post("/api/v1/history/search")
def search_history(query: str = Query(..., min_length=2)):
    results = search_historical_chunks(query, limit=5)
    return {"query": query, "results": results}

@app.get("/api/v1/commitments")
def get_commitments(status: Optional[str] = None):
    return [c.model_dump() for c in list_commitments(status)]

@app.post("/api/v1/commitments")
def create_commitment(item: CommitmentItem):
    return save_commitment(item).model_dump()

@app.patch("/api/v1/commitments/{commitment_id}")
def update_commitment_status(commitment_id: str, status: str = Query(...)):
    conn = get_db_connection()
    conn.execute("UPDATE commitments SET current_status = ? WHERE id = ?", (status, commitment_id))
    conn.commit()
    conn.close()
    return {"status": "updated", "commitment_id": commitment_id, "new_status": status}

# -------------------------------------------------------------
# Customer Q&A War Room
# -------------------------------------------------------------
@app.get("/api/v1/qa")
def get_qa_items():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM qa_items").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/v1/qa/generate")
def generate_qa_items(reporting_period: str = "2026-Q3"):
    orchestrator = QbrAgentOrchestrator(reporting_period=reporting_period)
    items = orchestrator._generate_qa_items()
    return {"items": [i.model_dump() for i in items], "count": len(items)}

@app.post("/api/v1/qa/{qa_id}/approve")
def approve_qa_talking_point(qa_id: str, edited_answer: Optional[str] = Form(None)):
    conn = get_db_connection()
    if edited_answer:
        conn.execute("UPDATE qa_items SET approved = 1, user_edited_answer = ? WHERE id = ?", (edited_answer, qa_id))
    else:
        conn.execute("UPDATE qa_items SET approved = 1 WHERE id = ?", (qa_id,))
    conn.commit()
    conn.close()
    return {"status": "approved", "qa_id": qa_id}

# -------------------------------------------------------------
# Scenario & Forecasting Lab
# -------------------------------------------------------------
@app.post("/api/v1/scenarios/run")
def evaluate_scenario(inputs: ScenarioInput):
    baseline = {
        "sla_achievement_pct": 98.8,
        "actual_spend": 1275000.0,
        "penalty_exposure": 35000.0,
        "gross_margin_pct": 31.1
    }
    result = run_what_if_scenario(baseline, inputs)
    return result.model_dump()

@app.post("/api/v1/forecast")
def get_forecast(metric: str = "availability"):
    history = [99.2, 99.4, 98.8]
    forecast = generate_linear_forecast(history, forecast_steps=2)
    return {
        "metric": metric,
        "historical_points": history,
        "forecast": forecast
    }

# -------------------------------------------------------------
# Agent Operations Center
# -------------------------------------------------------------
@app.post("/api/v1/agents/run")
def start_agent_run(reporting_period: str = Form("2026-Q3")):
    orchestrator = QbrAgentOrchestrator(reporting_period=reporting_period)
    record = orchestrator.execute_workflow()
    return record.model_dump()

@app.get("/api/v1/agents/runs/{run_id}")
def get_agent_run(run_id: str):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM agent_runs WHERE run_id = ?", (run_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Agent run record not found")
    
    d = dict(row)
    d["stages"] = json.loads(d.get("stages_json", "[]"))
    d["tool_calls"] = json.loads(d.get("tool_calls_json", "[]"))
    d["executive_narrative"] = json.loads(d.get("executive_narrative_json", "{}"))
    d["critic_notes"] = json.loads(d.get("critic_notes_json", "[]"))
    return d

@app.get("/api/v1/agents/latest")
def get_latest_agent_run():
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM agent_runs ORDER BY created_at DESC LIMIT 1").fetchone()
    conn.close()
    if not row:
        # Run workflow on the fly
        orchestrator = QbrAgentOrchestrator("2026-Q3")
        rec = orchestrator.execute_workflow()
        return rec.model_dump()

    d = dict(row)
    d["stages"] = json.loads(d.get("stages_json", "[]"))
    d["tool_calls"] = json.loads(d.get("tool_calls_json", "[]"))
    d["executive_narrative"] = json.loads(d.get("executive_narrative_json", "{}"))
    d["critic_notes"] = json.loads(d.get("critic_notes_json", "[]"))
    return d

# -------------------------------------------------------------
# Presentation Studio & Export
# -------------------------------------------------------------
@app.post("/api/v1/reports/pptx")
def export_pptx(config: PresentationConfig):
    result = generate_qbr_presentation(config)
    return result

@app.get("/api/v1/reports")
def list_reports():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM reports ORDER BY created_at DESC").fetchall()
    conn.close()
    reports = []
    for r in rows:
        d = dict(r)
        d["metadata"] = json.loads(d.get("metadata_json", "{}"))
        reports.append(d)
    return reports

@app.get("/api/v1/reports/{report_id}/download")
def download_report(report_id: str):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM reports WHERE report_id = ?", (report_id,)).fetchone()
    conn.close()
    if not row or not os.path.exists(row["filepath"]):
        raise HTTPException(status_code=404, detail="Report file not found")
    
    meta = json.loads(row["metadata_json"])
    return FileResponse(
        path=row["filepath"],
        filename=meta.get("filename", "QBR_Executive_Deck.pptx"),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )

# -------------------------------------------------------------
# Demo Reset & Audit Explorer
# -------------------------------------------------------------
@app.post("/api/v1/demo/reset")
def reset_demo_environment():
    seed_demo_data(force_reset=True)
    return {"status": "success", "message": "Demo data reset to clean initial benchmark state."}

@app.get("/api/v1/audit")
def get_audit_trail():
    conn = get_db_connection()
    kpi_rows = conn.execute("SELECT record_id, metric_name, actual_value, target_value, source_file, source_row, source_cell, timestamp FROM canonical_kpis").fetchall()
    runs = conn.execute("SELECT run_id, reporting_period, status, created_at FROM agent_runs ORDER BY created_at DESC LIMIT 5").fetchall()
    reports = conn.execute("SELECT report_id, title, format, created_at FROM reports ORDER BY created_at DESC LIMIT 5").fetchall()
    conn.close()

    return {
        "kpi_lineage_records": [dict(r) for r in kpi_rows],
        "agent_run_history": [dict(r) for r in runs],
        "exported_reports": [dict(r) for r in reports]
    }

# -------------------------------------------------------------
# Static files & SPA fallback for production frontend bundle
# -------------------------------------------------------------
dist_path = settings.BASE_DIR / "frontend" / "dist"
if dist_path.exists():
    assets_path = dist_path / "assets"
    if assets_path.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_path)), name="static_assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api") or full_path.startswith("health"):
            raise HTTPException(status_code=404, detail="Not Found")
        file_path = dist_path / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(dist_path / "index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host=settings.HOST, port=settings.PORT, reload=True)
