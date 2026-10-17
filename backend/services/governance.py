import json
import uuid
from typing import List, Dict, Any, Optional
from datetime import date, datetime

from backend.database import get_db_connection
from backend.models.schemas import (
    Project,
    Milestone,
    RAIDItem,
    ActionItem,
    DecisionItem
)

# --- Project Management ---
def list_projects(reporting_period: Optional[str] = None) -> List[Project]:
    conn = get_db_connection()
    if reporting_period:
        rows = conn.execute("SELECT * FROM projects WHERE reporting_period = ?", (reporting_period,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM projects").fetchall()
    conn.close()
    return [Project(**dict(r)) for r in rows]

def save_project(proj: Project) -> Project:
    conn = get_db_connection()
    conn.execute("""
    INSERT OR REPLACE INTO projects (
        id, name, program, sponsor, owner, health,
        delivery_confidence, approved_budget, actual_spend,
        reporting_period, key_updates
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        proj.id, proj.name, proj.program, proj.sponsor, proj.owner, proj.health,
        proj.delivery_confidence, proj.approved_budget, proj.actual_spend,
        proj.reporting_period, proj.key_updates
    ))
    conn.commit()
    conn.close()
    return proj

# --- Milestone Management ---
def list_milestones(project_id: Optional[str] = None) -> List[Milestone]:
    conn = get_db_connection()
    if project_id:
        rows = conn.execute("SELECT * FROM milestones WHERE project_id = ?", (project_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM milestones").fetchall()
    conn.close()
    
    milestones = []
    for r in rows:
        d = dict(r)
        d["dependencies"] = json.loads(d.get("dependencies_json", "[]"))
        d["customer_dependency"] = bool(d.get("customer_dependency", 0))
        del d["dependencies_json"]
        milestones.append(Milestone(**d))
    return milestones

def save_milestone(m: Milestone) -> Milestone:
    conn = get_db_connection()
    conn.execute("""
    INSERT OR REPLACE INTO milestones (
        id, project_id, project_name, title, planned_date,
        actual_or_forecast_date, completion_pct, status, owner,
        criticality, dependencies_json, recovery_plan, customer_dependency, escalation_status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        m.id, m.project_id, m.project_name, m.title, m.planned_date,
        m.actual_or_forecast_date, m.completion_pct, m.status, m.owner,
        m.criticality, json.dumps(m.dependencies), m.recovery_plan,
        1 if m.customer_dependency else 0, m.escalation_status
    ))
    conn.commit()
    conn.close()
    return m

# --- RAID Management ---
def list_raid_items(raid_type: Optional[str] = None, severity: Optional[str] = None) -> List[RAIDItem]:
    conn = get_db_connection()
    query = "SELECT * FROM raid_items WHERE 1=1"
    params = []
    if raid_type:
        query += " AND type = ?"
        params.append(raid_type)
    if severity:
        query += " AND severity = ?"
        params.append(severity)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [RAIDItem(**dict(r)) for r in rows]

def save_raid_item(item: RAIDItem) -> RAIDItem:
    # Deterministic risk scoring: impact * likelihood
    item.score = item.impact * item.likelihood
    if item.score >= 16:
        item.severity = "critical"
    elif item.score >= 10:
        item.severity = "high"
    elif item.score >= 5:
        item.severity = "medium"
    else:
        item.severity = "low"

    conn = get_db_connection()
    conn.execute("""
    INSERT OR REPLACE INTO raid_items (
        id, type, title, description, category, impact, likelihood,
        score, severity, owner, due_date, status, mitigation, contingency,
        project_id, related_milestone_id, source_reference
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        item.id, item.type, item.title, item.description, item.category,
        item.impact, item.likelihood, item.score, item.severity,
        item.owner, item.due_date, item.status, item.mitigation,
        item.contingency, item.project_id, item.related_milestone_id,
        item.source_reference
    ))
    conn.commit()
    conn.close()
    return item

# --- Action Items Management ---
def list_action_items(status: Optional[str] = None, priority: Optional[str] = None) -> List[ActionItem]:
    conn = get_db_connection()
    query = "SELECT * FROM action_items WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if priority:
        query += " AND priority = ?"
        params.append(priority)
    rows = conn.execute(query, params).fetchall()
    conn.close()

    actions = []
    for r in rows:
        d = dict(r)
        d["dependencies"] = json.loads(d.get("dependencies_json", "[]"))
        d["is_proposal"] = bool(d.get("is_proposal", 0))
        del d["dependencies_json"]
        actions.append(ActionItem(**d))
    return actions

def save_action_item(action: ActionItem) -> ActionItem:
    conn = get_db_connection()
    conn.execute("""
    INSERT OR REPLACE INTO action_items (
        id, title, description, owner, priority, due_date, status,
        related_qbr, linked_risk_id, dependencies_json, acceptance_criteria,
        closure_evidence, closure_date, is_proposal
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        action.id, action.title, action.description, action.owner,
        action.priority, action.due_date, action.status, action.related_qbr,
        action.linked_risk_id, json.dumps(action.dependencies),
        action.acceptance_criteria, action.closure_evidence,
        action.closure_date, 1 if action.is_proposal else 0
    ))
    conn.commit()
    conn.close()
    return action

# --- Decision Items Management ---
def list_decision_items(status: Optional[str] = None) -> List[DecisionItem]:
    conn = get_db_connection()
    query = "SELECT * FROM decision_items WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    rows = conn.execute(query, params).fetchall()
    conn.close()

    decisions = []
    for r in rows:
        d = dict(r)
        d["options_considered"] = json.loads(d.get("options_considered_json", "[]"))
        d["dependencies"] = json.loads(d.get("dependencies_json", "[]"))
        d["follow_up_actions"] = json.loads(d.get("follow_up_actions_json", "[]"))
        d["customer_ask"] = bool(d.get("customer_ask", 0))
        del d["options_considered_json"]
        del d["dependencies_json"]
        del d["follow_up_actions_json"]
        decisions.append(DecisionItem(**d))
    return decisions

def save_decision_item(decision: DecisionItem) -> DecisionItem:
    conn = get_db_connection()
    conn.execute("""
    INSERT OR REPLACE INTO decision_items (
        id, title, options_considered_json, selected_decision,
        rationale, decision_owner, decision_date, status,
        dependencies_json, follow_up_actions_json, customer_ask
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        decision.id, decision.title, json.dumps(decision.options_considered),
        decision.selected_decision, decision.rationale, decision.decision_owner,
        decision.decision_date, decision.status, json.dumps(decision.dependencies),
        json.dumps(decision.follow_up_actions), 1 if decision.customer_ask else 0
    ))
    conn.commit()
    conn.close()
    return decision

def calculate_program_health_summary() -> Dict[str, Any]:
    """
    Computes explainable program health indicators from verified project, RAID, and action records.
    """
    projects = list_projects()
    milestones = list_milestones()
    raid = list_raid_items()
    actions = list_action_items()
    decisions = list_decision_items()

    total_projects = len(projects)
    red_projects = sum(1 for p in projects if p.health == "red")
    amber_projects = sum(1 for p in projects if p.health == "amber")
    green_projects = sum(1 for p in projects if p.health == "green")
    
    avg_delivery_confidence = round(sum(p.delivery_confidence for p in projects) / total_projects, 1) if total_projects > 0 else 0.0

    at_risk_milestones = [m for m in milestones if m.status in ["at_risk", "delayed", "blocked"]]
    critical_risks = [r for r in raid if r.type == "risk" and r.severity in ["critical", "high"] and r.status in ["open", "in_progress"]]
    open_issues = [i for i in raid if i.type == "issue" and i.status in ["open", "in_progress"]]
    
    # Overdue action detection
    today_str = date.today().isoformat()
    overdue_actions = [a for a in actions if a.due_date < today_str and a.status != "completed"]
    pending_customer_decisions = [d for d in decisions if d.customer_ask and d.status in ["proposed", "deferred"]]

    # Overall health score calculation
    health_score = 100.0
    health_score -= (red_projects * 15.0)
    health_score -= (amber_projects * 5.0)
    health_score -= (len(critical_risks) * 6.0)
    health_score -= (len(at_risk_milestones) * 5.0)
    health_score -= (len(overdue_actions) * 3.0)
    health_score = max(10.0, min(100.0, round(health_score, 1)))

    overall_status = "green"
    if health_score < 60 or red_projects > 0 or len(critical_risks) >= 3:
        overall_status = "red"
    elif health_score < 80 or amber_projects > 0 or len(critical_risks) > 0:
        overall_status = "amber"

    return {
        "overall_status": overall_status,
        "health_score": health_score,
        "total_projects": total_projects,
        "green_projects": green_projects,
        "amber_projects": amber_projects,
        "red_projects": red_projects,
        "avg_delivery_confidence": avg_delivery_confidence,
        "total_milestones": len(milestones),
        "at_risk_milestones_count": len(at_risk_milestones),
        "critical_risks_count": len(critical_risks),
        "open_issues_count": len(open_issues),
        "overdue_actions_count": len(overdue_actions),
        "pending_customer_decisions_count": len(pending_customer_decisions),
        "drivers": [
            f"{red_projects} projects in Red status" if red_projects > 0 else "All core projects in Green/Amber",
            f"{len(critical_risks)} active high/critical risks in register",
            f"{len(at_risk_milestones)} milestones requiring schedule mitigation",
            f"{len(pending_customer_decisions)} customer decisions pending QBR ratification"
        ]
    }
