from datetime import datetime, date, timezone
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field

# --- Canonical KPI Schema ---
class CanonicalKPIRecord(BaseModel):
    record_id: str
    reporting_period: str # e.g. "2026-Q3"
    project: str
    program: str
    workstream: str
    metric_name: str
    metric_category: str # "SLA", "Financial", "Delivery", "Quality", "Customer"
    actual_value: float
    target_value: float
    unit: str # "%", "$", "days", "count", "hrs"
    direction_of_improvement: Literal["higher_is_better", "lower_is_better"] = "higher_is_better"
    currency: Optional[str] = "USD"
    source_file: str
    worksheet_or_table: Optional[str] = "Sheet1"
    source_row: Optional[int] = None
    source_cell: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data_quality_status: Literal["valid", "warning", "error"] = "valid"
    notes: Optional[str] = None

class ValidationIssue(BaseModel):
    row_index: Optional[int] = None
    column: Optional[str] = None
    issue_type: str # "missing_value", "invalid_type", "negative_prohibited", "impossible_percentage", etc.
    message: str
    severity: Literal["error", "warning"]

class ValidationReport(BaseModel):
    dataset_id: str
    filename: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    warnings: List[ValidationIssue] = []
    errors: List[ValidationIssue] = []
    resolution_status: Literal["passed", "warnings_pending", "failed"]

# --- Deterministic Analytics Models ---
class KPIVarianceResult(BaseModel):
    metric_name: str
    category: str
    reporting_period: str
    actual: float
    target: float
    previous_period_value: Optional[float] = None
    absolute_change: Optional[float] = None
    pct_change: Optional[float] = None # handled carefully for 0 denominator
    variance_vs_target: float
    unit: str
    direction_of_improvement: Literal["higher_is_better", "lower_is_better"]
    breached: bool
    materiality_flag: bool # e.g. variance > 5%
    trend: Literal["improving", "deteriorating", "stable"]
    formula_explanation: str
    source_lineage: str

class SLAIntelligenceItem(BaseModel):
    sla_name: str
    workstream: str
    target_pct: float
    actual_pct: float
    gap_pct: float
    breach_count: int
    breach_duration_hours: float
    penalty_exposure: float
    severity: Literal["critical", "high", "medium", "low"]
    trend: Literal["improving", "deteriorating", "stable"]
    explanation: str
    corrective_action: str

class PenaltyCalculationDetail(BaseModel):
    rule_id: str
    sla_name: str
    target_threshold: float
    actual_measured: float
    breach_interval: str # e.g. "per 0.1% breach"
    penalty_basis: str # "fixed", "percentage_of_mrr", "tiered"
    penalty_rate: float
    calculated_exposure: float
    grace_period_applied: bool
    cap_amount: float
    effective_exposure: float
    currency: str = "USD"
    rule_source: str
    assumptions: str
    validation_status: Literal["verified_contract", "estimate_missing_terms", "capped"]

class FinancialIntelligenceSummary(BaseModel):
    reporting_period: str
    approved_budget: float
    planned_spend: float
    actual_spend: float
    forecast_spend: float
    budget_variance: float # actual - planned
    budget_utilization_pct: float # actual / approved * 100
    revenue: Optional[float] = None
    cost: Optional[float] = None
    gross_profit: Optional[float] = None
    gross_margin_pct: Optional[float] = None
    margin_variance_pct: Optional[float] = None
    total_penalty_exposure: float
    currency: str = "USD"
    formulas: Dict[str, str]

# --- Program Governance Models ---
class Project(BaseModel):
    id: str
    name: str
    program: str
    sponsor: str
    owner: str
    health: Literal["green", "amber", "red"]
    delivery_confidence: float # 0 to 100%
    approved_budget: float
    actual_spend: float
    reporting_period: str
    key_updates: str

class Milestone(BaseModel):
    id: str
    project_id: str
    project_name: str
    title: str
    planned_date: str
    actual_or_forecast_date: str
    completion_pct: float
    status: Literal["completed", "on_track", "at_risk", "delayed", "blocked"]
    owner: str
    criticality: Literal["critical", "high", "medium", "low"]
    dependencies: List[str] = []
    recovery_plan: Optional[str] = None
    customer_dependency: bool = False
    escalation_status: Optional[str] = None

class RAIDItem(BaseModel):
    id: str
    type: Literal["risk", "assumption", "issue", "dependency"]
    title: str
    description: str
    category: str # "Technical", "Commercial", "Schedule", "Resource", "Governance"
    impact: int = Field(ge=1, le=5)
    likelihood: int = Field(ge=1, le=5) # For risks
    score: int # impact * likelihood
    severity: Literal["low", "medium", "high", "critical"]
    owner: str
    due_date: str
    status: Literal["open", "in_progress", "mitigated", "closed", "accepted"]
    mitigation: str
    contingency: Optional[str] = None
    project_id: str
    related_milestone_id: Optional[str] = None
    source_reference: Optional[str] = None

class ActionItem(BaseModel):
    id: str
    title: str
    description: str
    owner: str
    priority: Literal["urgent", "high", "medium", "low"]
    due_date: str
    status: Literal["open", "in_progress", "blocked", "completed"]
    related_qbr: str
    linked_risk_id: Optional[str] = None
    dependencies: List[str] = []
    acceptance_criteria: str
    closure_evidence: Optional[str] = None
    closure_date: Optional[str] = None
    is_proposal: bool = False # from AI planner until confirmed

class DecisionItem(BaseModel):
    id: str
    title: str
    options_considered: List[str]
    selected_decision: str
    rationale: str
    decision_owner: str
    decision_date: str
    status: Literal["proposed", "approved", "rejected", "deferred"]
    dependencies: List[str] = []
    follow_up_actions: List[str] = []
    customer_ask: bool = False

# --- Historical & Commitments ---
class HistoricalDocument(BaseModel):
    id: str
    filename: str
    file_type: str
    upload_date: str
    chunk_count: int
    summary: str
    page_or_slide_count: Optional[int] = None

class CommitmentItem(BaseModel):
    id: str
    original_wording: str
    source_document: str
    source_location: str # e.g. "Slide 14, Bullet 2" or "Page 4, Section 2.1"
    owner: str
    due_date: str
    project_id: str
    expected_outcome: str
    current_status: Literal[
        "closed_with_evidence",
        "open",
        "at_risk",
        "overdue",
        "blocked",
        "unverified",
        "requires_human_review"
    ]
    closure_evidence: Optional[str] = None
    confidence: float # 0.0 - 1.0
    review_requirement: str

# --- Customer Q&A War Room ---
class CustomerQAItem(BaseModel):
    id: str
    question: str
    category: str # "SLA", "Financial", "Delivery", "Scope", "Staffing"
    severity: Literal["critical", "high", "medium"]
    why_asked: str
    supporting_kpi_evidence: str
    linked_commitment: Optional[str] = None
    recommended_answer: str
    diplomatic_phrasing: str
    evidence_coverage: Literal["complete", "partial", "unsupported"]
    user_edited_answer: Optional[str] = None
    approved: bool = False
    rehearsal_notes: Optional[str] = None

# --- Scenario & What-If ---
class ScenarioInput(BaseModel):
    scenario_name: str
    sla_recovery_delta_pct: float = 0.0
    cost_reduction_delta: float = 0.0
    milestone_acceleration_days: int = 0
    utilization_target_pct: float = 85.0
    penalty_relief_pct: float = 0.0

class ScenarioComparisonResult(BaseModel):
    scenario_name: str
    baseline: Dict[str, float]
    projected: Dict[str, float]
    delta: Dict[str, float]
    feasibility_score: float # 0 - 100
    impact_summary: str
    tradeoffs: List[str]

# --- Agent Operations ---
class AgentToolCall(BaseModel):
    tool_name: str
    agent_name: str
    input_params: Dict[str, Any]
    output_result: Any
    timestamp: str
    status: Literal["success", "failure"]

class AgentExecutionStage(BaseModel):
    stage_id: str
    stage_name: str
    agent_name: str
    status: Literal["queued", "running", "completed", "failed", "skipped"]
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    findings_count: int = 0
    critic_verdict: Optional[Literal["passed", "rejected", "flagged"]] = None

class AgentRunRecord(BaseModel):
    run_id: str
    reporting_period: str
    status: Literal["queued", "running", "waiting_for_input", "completed", "failed"]
    current_stage: str
    stages: List[AgentExecutionStage]
    tool_calls: List[AgentToolCall] = []
    executive_narrative: Optional[Dict[str, Any]] = None
    critic_notes: List[str] = []
    created_at: str
    updated_at: str

# --- Presentation Studio ---
class PresentationConfig(BaseModel):
    reporting_period: str = "2026-Q3"
    program_name: str = "Cloud Modernization & Operations"
    customer_name: str = "Enterprise Global Corp"
    presentation_length: Literal["executive_brief", "standard", "deep_dive"] = "standard"
    executive_tone: Literal["collaborative", "objective_transparent", "assertive_governance"] = "objective_transparent"
    include_appendix: bool = True
    include_raid: bool = True
    include_qa: bool = True
    include_penalties: bool = True
