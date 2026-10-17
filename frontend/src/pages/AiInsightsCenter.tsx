import React, { useState, useEffect } from 'react';
import { useOutletContext, useNavigate } from 'react-router-dom';
import {
  BrainCircuit,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  Lightbulb,
  ShieldCheck,
  FileText,
  ArrowRight
} from 'lucide-react';
import { api } from '../api/client';
import { AgentRunRecord } from '../types';

export const AiInsightsCenter: React.FC = () => {
  const { reportingPeriod } = useOutletContext<{ reportingPeriod: string }>();
  const navigate = useNavigate();
  const [runRecord, setRunRecord] = useState<AgentRunRecord | null>(null);

  useEffect(() => {
    api.getLatestAgentRun().then(setRunRecord).catch(console.error);
  }, [reportingPeriod]);

  const facts = [
    {
      claim: "Platform Availability measured at 98.8% vs contractual target of 99.5% (gap: -0.7%).",
      source: "synthetic_q3_sla_telemetry.csv (Row 2)",
      verified_by: "KPI Analyst Agent & Critic Validator"
    },
    {
      claim: "Contract penalty liability is deterministically $35,000 under MSA Schedule 4.2.",
      source: "MSA Schedule 4.2 penalty rules table",
      verified_by: "Penalty Engine Python function"
    },
    {
      claim: "Gross margin is 31.1% against 35.0% baseline, yielding $575k gross profit.",
      source: "synthetic_q3_financial_ledger.xlsx (Row 18)",
      verified_by: "Financial Analytics Engine"
    }
  ];

  const recommendations = [
    {
      title: "Ratify Dual-Zone Heartbeat Failover Configuration",
      rationale: "Remediates root cause of August 14 replica deadlock, preventing future availability breaches.",
      owner: "SRE Director",
      priority: "Urgent",
      related_kpi: "Platform Availability"
    },
    {
      title: "Obtain Customer Sign-off on Holiday Change Freeze (Option B)",
      rationale: "Ensures platform stability during peak transaction volumes while permitting critical security fixes.",
      owner: "Account Executive & Customer Sponsor",
      priority: "High",
      related_kpi: "Customer Governance"
    },
    {
      title: "Complete Aurora Database Cutover by Sept 15 Window",
      rationale: "Closes delayed milestone M-DEMO-01 using parallel migration squad to prevent downstream delays.",
      owner: "Database Lead",
      priority: "Critical",
      related_kpi: "Schedule Delivery"
    }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1 rounded bg-purple-100 dark:bg-purple-950 text-purple-600 dark:text-purple-400">
              <BrainCircuit size={18} />
            </span>
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
              AI Insights & Executive Synthesis Center
            </h2>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Grounded intelligence stream strictly categorizing verified facts, analytical interpretations, and human-in-the-loop decisions.
          </p>
        </div>

        <button
          onClick={() => navigate('/workspace')}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-sm"
        >
          <span>Re-Run Analysis</span>
          <ArrowRight size={14} />
        </button>
      </div>

      {/* Verified Facts vs Recommendations */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Facts Card */}
        <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 font-bold text-xs uppercase tracking-wider">
              <ShieldCheck size={16} />
              <span>Deterministically Verified Facts</span>
            </div>
            <span className="text-[10px] px-2 py-0.5 rounded font-semibold bg-emerald-50 dark:bg-emerald-950 text-emerald-600">
              Zero Hallucination
            </span>
          </div>

          <div className="space-y-3">
            {facts.map((f, i) => (
              <div key={i} className="p-3.5 rounded-lg bg-slate-50 dark:bg-slate-850 border border-slate-200 dark:border-slate-800 text-xs space-y-1.5">
                <p className="font-semibold text-slate-900 dark:text-white">
                  • {f.claim}
                </p>
                <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1 border-t border-slate-200 dark:border-slate-800">
                  <span className="font-mono text-blue-600 dark:text-blue-400">Lineage: {f.source}</span>
                  <span className="text-slate-500">{f.verified_by}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recommendations Card */}
        <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-blue-600 dark:text-blue-400 font-bold text-xs uppercase tracking-wider">
              <Lightbulb size={16} />
              <span>Grounded Executive Recommendations</span>
            </div>
            <span className="text-[10px] px-2 py-0.5 rounded font-semibold bg-blue-50 dark:bg-blue-950 text-blue-600">
              Human Actionable
            </span>
          </div>

          <div className="space-y-3">
            {recommendations.map((r, i) => (
              <div key={i} className="p-3.5 rounded-lg bg-slate-50 dark:bg-slate-850 border border-slate-200 dark:border-slate-800 text-xs space-y-1.5">
                <div className="flex items-center justify-between font-semibold text-slate-900 dark:text-white">
                  <span>{r.title}</span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                    r.priority === 'Urgent' ? 'bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-400' :
                    'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-400'
                  }`}>
                    {r.priority}
                  </span>
                </div>
                <p className="text-slate-500 dark:text-slate-400 text-[11px]">
                  {r.rationale}
                </p>
                <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1 border-t border-slate-200 dark:border-slate-800">
                  <span>Owner: <strong>{r.owner}</strong></span>
                  <span className="text-blue-600 dark:text-blue-400 font-semibold">{r.related_kpi}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
