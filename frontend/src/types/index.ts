export interface ProgramHealth {
  overall_status: 'green' | 'amber' | 'red';
  health_score: number;
  total_projects: number;
  green_projects: number;
  amber_projects: number;
  red_projects: number;
  avg_delivery_confidence: number;
  total_milestones: number;
  at_risk_milestones_count: number;
  critical_risks_count: number;
  open_issues_count: number;
  overdue_actions_count: number;
  pending_customer_decisions_count: number;
  drivers: string[];
}

export interface FinancialSummary {
  reporting_period: string;
  approved_budget: number;
  planned_spend: number;
  actual_spend: number;
  forecast_spend: number;
  budget_variance: number;
  budget_utilization_pct: number;
  revenue?: number;
  cost?: number;
  gross_profit?: number;
  gross_margin_pct?: number;
  total_penalty_exposure: number;
  currency: string;
  formulas: Record<string, string>;
}

export interface PenaltyDetail {
  rule_id: string;
  sla_name: string;
  target_threshold: number;
  actual_measured: number;
  breach_interval: string;
  penalty_basis: string;
  penalty_rate: number;
  calculated_exposure: number;
  grace_period_applied: boolean;
  cap_amount: number;
  effective_exposure: number;
  currency: string;
  rule_source: string;
  assumptions: string;
  validation_status: string;
}

export interface KPIItem {
  metric_name: string;
  category: string;
  reporting_period: string;
  actual: number;
  target: number;
  previous_period_value?: number;
  absolute_change?: number;
  pct_change?: number;
  variance_vs_target: number;
  unit: string;
  direction_of_improvement: 'higher_is_better' | 'lower_is_better';
  breached: boolean;
  materiality_flag: boolean;
  trend: 'improving' | 'deteriorating' | 'stable';
  formula_explanation: string;
  source_lineage: string;
}

export interface ExecutiveAlert {
  id: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  title: string;
  impacted_metric: string;
  workstream: string;
  penalty_exposure: string;
  recommended_action: string;
  due_date: string;
}

export interface DashboardData {
  reporting_period: string;
  health: ProgramHealth;
  financials: FinancialSummary;
  penalty_summary: PenaltyDetail;
  kpis: KPIItem[];
  alerts: ExecutiveAlert[];
  demo_mode: boolean;
}

export interface ProjectItem {
  id: string;
  name: string;
  program: string;
  sponsor: string;
  owner: string;
  health: 'green' | 'amber' | 'red';
  delivery_confidence: number;
  approved_budget: number;
  actual_spend: number;
  reporting_period: string;
  key_updates: string;
}

export interface MilestoneItem {
  id: string;
  project_id: string;
  project_name: string;
  title: string;
  planned_date: string;
  actual_or_forecast_date: string;
  completion_pct: number;
  status: 'completed' | 'on_track' | 'at_risk' | 'delayed' | 'blocked';
  owner: string;
  criticality: 'critical' | 'high' | 'medium' | 'low';
  dependencies: string[];
  recovery_plan?: string;
  customer_dependency: boolean;
  escalation_status?: string;
}

export interface RAIDItemType {
  id: string;
  type: 'risk' | 'assumption' | 'issue' | 'dependency';
  title: string;
  description: string;
  category: string;
  impact: number;
  likelihood: number;
  score: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  owner: string;
  due_date: string;
  status: 'open' | 'in_progress' | 'mitigated' | 'closed' | 'accepted';
  mitigation: string;
  contingency?: string;
  project_id: string;
  related_milestone_id?: string;
  source_reference?: string;
}

export interface ActionItemType {
  id: string;
  title: string;
  description: string;
  owner: string;
  priority: 'urgent' | 'high' | 'medium' | 'low';
  due_date: string;
  status: 'open' | 'in_progress' | 'blocked' | 'completed';
  related_qbr: string;
  linked_risk_id?: string;
  dependencies: string[];
  acceptance_criteria: string;
  closure_evidence?: string;
  closure_date?: string;
  is_proposal?: boolean;
}

export interface DecisionItemType {
  id: string;
  title: string;
  options_considered: string[];
  selected_decision: string;
  rationale: string;
  decision_owner: string;
  decision_date: string;
  status: 'proposed' | 'approved' | 'rejected' | 'deferred';
  dependencies: string[];
  follow_up_actions: string[];
  customer_ask: boolean;
}

export interface CommitmentItemType {
  id: string;
  original_wording: string;
  source_document: string;
  source_location: string;
  owner: string;
  due_date: string;
  project_id: string;
  expected_outcome: string;
  current_status: 'closed_with_evidence' | 'open' | 'at_risk' | 'overdue' | 'blocked' | 'unverified' | 'requires_human_review';
  closure_evidence?: string;
  confidence: number;
  review_requirement: string;
}

export interface QAItemType {
  id: string;
  question: string;
  category: string;
  severity: 'critical' | 'high' | 'medium';
  why_asked: string;
  supporting_kpi_evidence: string;
  linked_commitment?: string;
  recommended_answer: string;
  diplomatic_phrasing: string;
  evidence_coverage: 'complete' | 'partial' | 'unsupported';
  user_edited_answer?: string;
  approved: boolean | number;
  rehearsal_notes?: string;
}

export interface AgentStage {
  stage_id: string;
  stage_name: string;
  agent_name: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'skipped';
  started_at?: string;
  completed_at?: string;
  findings_count: number;
  critic_verdict?: 'passed' | 'rejected' | 'flagged';
}

export interface AgentToolCall {
  tool_name: string;
  agent_name: string;
  input_params: Record<string, any>;
  output_result: any;
  timestamp: string;
  status: 'success' | 'failure';
}

export interface AgentRunRecord {
  run_id: string;
  reporting_period: string;
  status: 'queued' | 'running' | 'waiting_for_input' | 'completed' | 'failed';
  current_stage: string;
  stages: AgentStage[];
  tool_calls: AgentToolCall[];
  executive_narrative?: {
    executive_summary?: string;
    key_wins?: string[];
    critical_risks?: string[];
    customer_asks?: string[];
  };
  critic_notes: string[];
  created_at: string;
  updated_at: string;
}

export interface ReportItem {
  report_id: string;
  title: string;
  reporting_period: string;
  format: string;
  filepath: string;
  created_at: string;
  metadata: {
    slide_count: number;
    verified: boolean;
    filename: string;
    filesize_bytes?: number;
  };
}
