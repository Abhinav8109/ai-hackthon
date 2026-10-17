import {
  DashboardData,
  ProjectItem,
  MilestoneItem,
  RAIDItemType,
  ActionItemType,
  DecisionItemType,
  CommitmentItemType,
  QAItemType,
  AgentRunRecord,
  ReportItem
} from '../types';

const API_BASE = '/api/v1';

export const api = {
  // Dashboard
  getDashboardSummary: async (period = '2026-Q3'): Promise<DashboardData> => {
    const res = await fetch(`${API_BASE}/dashboard/summary?period=${period}`);
    if (!res.ok) throw new Error('Failed to fetch dashboard summary');
    return res.json();
  },

  // Governance
  getProjects: async (period?: string): Promise<ProjectItem[]> => {
    const url = period ? `${API_BASE}/projects?period=${period}` : `${API_BASE}/projects`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch projects');
    return res.json();
  },

  getMilestones: async (projectId?: string): Promise<MilestoneItem[]> => {
    const url = projectId ? `${API_BASE}/milestones?project_id=${projectId}` : `${API_BASE}/milestones`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch milestones');
    return res.json();
  },

  getRaid: async (type?: string, severity?: string): Promise<RAIDItemType[]> => {
    let url = `${API_BASE}/raid?`;
    if (type) url += `type=${type}&`;
    if (severity) url += `severity=${severity}&`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch RAID items');
    return res.json();
  },

  createRaid: async (item: Partial<RAIDItemType>): Promise<RAIDItemType> => {
    const res = await fetch(`${API_BASE}/raid`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(item),
    });
    if (!res.ok) throw new Error('Failed to create RAID item');
    return res.json();
  },

  getActions: async (status?: string): Promise<ActionItemType[]> => {
    const url = status ? `${API_BASE}/actions?status=${status}` : `${API_BASE}/actions`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch actions');
    return res.json();
  },

  updateActionStatus: async (actionId: string, status: string): Promise<any> => {
    const res = await fetch(`${API_BASE}/actions/${actionId}?status=${status}`, {
      method: 'PATCH',
    });
    if (!res.ok) throw new Error('Failed to update action status');
    return res.json();
  },

  getDecisions: async (): Promise<DecisionItemType[]> => {
    const res = await fetch(`${API_BASE}/decisions`);
    if (!res.ok) throw new Error('Failed to fetch decisions');
    return res.json();
  },

  // Historical & Commitments
  getCommitments: async (status?: string): Promise<CommitmentItemType[]> => {
    const url = status ? `${API_BASE}/commitments?status=${status}` : `${API_BASE}/commitments`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch commitments');
    return res.json();
  },

  searchHistorical: async (query: string): Promise<{ query: string; results: any[] }> => {
    const res = await fetch(`${API_BASE}/history/search?query=${encodeURIComponent(query)}`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Historical search failed');
    return res.json();
  },

  // Customer Q&A
  getQAItems: async (): Promise<QAItemType[]> => {
    const res = await fetch(`${API_BASE}/qa`);
    if (!res.ok) throw new Error('Failed to fetch QA items');
    return res.json();
  },

  generateQA: async (period = '2026-Q3'): Promise<{ items: QAItemType[]; count: number }> => {
    const res = await fetch(`${API_BASE}/qa/generate?reporting_period=${period}`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to generate QA');
    return res.json();
  },

  approveQA: async (qaId: string, editedAnswer?: string): Promise<any> => {
    const formData = new FormData();
    if (editedAnswer) formData.append('edited_answer', editedAnswer);
    const res = await fetch(`${API_BASE}/qa/${qaId}/approve`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) throw new Error('Failed to approve QA talking point');
    return res.json();
  },

  // Scenarios & Forecasting
  runScenario: async (inputs: {
    scenario_name: string;
    sla_recovery_delta_pct: number;
    cost_reduction_delta: number;
    milestone_acceleration_days: number;
    utilization_target_pct: number;
    penalty_relief_pct: number;
  }): Promise<any> => {
    const res = await fetch(`${API_BASE}/scenarios/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(inputs),
    });
    if (!res.ok) throw new Error('Failed to run scenario');
    return res.json();
  },

  // Agent Operations
  getLatestAgentRun: async (): Promise<AgentRunRecord> => {
    const res = await fetch(`${API_BASE}/agents/latest`);
    if (!res.ok) throw new Error('Failed to fetch latest agent run');
    return res.json();
  },

  startAgentRun: async (period = '2026-Q3'): Promise<AgentRunRecord> => {
    const formData = new FormData();
    formData.append('reporting_period', period);
    const res = await fetch(`${API_BASE}/agents/run`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) throw new Error('Failed to start agent run');
    return res.json();
  },

  // Presentation & Reports
  generatePresentation: async (config: {
    reporting_period: string;
    program_name: string;
    customer_name: string;
    presentation_length: string;
    executive_tone: string;
  }): Promise<any> => {
    const res = await fetch(`${API_BASE}/reports/pptx`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
    if (!res.ok) throw new Error('Failed to generate presentation');
    return res.json();
  },

  getReports: async (): Promise<ReportItem[]> => {
    const res = await fetch(`${API_BASE}/reports`);
    if (!res.ok) throw new Error('Failed to fetch reports');
    return res.json();
  },

  // Datasets
  getDatasets: async (): Promise<any> => {
    const res = await fetch(`${API_BASE}/datasets`);
    if (!res.ok) throw new Error('Failed to fetch datasets');
    return res.json();
  },

  uploadDataset: async (file: File, period: string): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('reporting_period', period);
    const res = await fetch(`${API_BASE}/datasets/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) throw new Error('Failed to upload dataset');
    return res.json();
  },

  // Audit
  getAudit: async (): Promise<any> => {
    const res = await fetch(`${API_BASE}/audit`);
    if (!res.ok) throw new Error('Failed to fetch audit data');
    return res.json();
  },

  // Demo Reset
  resetDemo: async (): Promise<any> => {
    const res = await fetch(`${API_BASE}/demo/reset`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to reset demo');
    return res.json();
  },
};
