import React, { useEffect, useState } from 'react';
import { useOutletContext, useNavigate } from 'react-router-dom';
import {
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ArrowRight,
  ShieldAlert,
  Activity,
  Layers,
  FileSpreadsheet
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  LineChart,
  Line
} from 'recharts';
import { api } from '../api/client';
import { DashboardData } from '../types';

export const ExecutiveOverview: React.FC = () => {
  const { reportingPeriod } = useOutletContext<{ reportingPeriod: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    api.getDashboardSummary(reportingPeriod)
      .then((res) => {
        if (isMounted) {
          setData(res);
          setLoading(false);
        }
      })
      .catch((err) => {
        console.error(err);
        if (isMounted) setLoading(false);
      });
    return () => { isMounted = false; };
  }, [reportingPeriod]);

  if (loading || !data) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400 text-sm">
        <Activity className="animate-spin mr-2" size={20} />
        Loading Executive Dashboard...
      </div>
    );
  }

  // Chart dataset for SLA trends
  const slaTrendData = [
    { period: '2026-Q1', actual: 99.2, target: 99.5 },
    { period: '2026-Q2', actual: 99.4, target: 99.5 },
    { period: '2026-Q3', actual: 98.8, target: 99.5 },
    { period: '2026-Q4 (F)', actual: 99.6, target: 99.5 },
  ];

  // Chart dataset for Spend vs Planned
  const spendData = [
    { name: 'Q1', planned: 950, actual: 920 },
    { name: 'Q2', planned: 1100, actual: 1080 },
    { name: 'Q3 (Active)', planned: 1200, actual: 1275 },
    { name: 'Q4 (Forecast)', planned: 1300, actual: 1350 },
  ];

  return (
    <div className="space-y-6">
      {/* Top Banner / Welcome */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
            Executive Command Center
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Real-time program governance, deterministic KPI variances, and active contractual risk telemetry.
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <button
            onClick={() => navigate('/workspace')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-sm transition-all"
          >
            Launch QBR Orchestrator
            <ArrowRight size={14} />
          </button>
        </div>
      </div>

      {/* Top KPI Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Program Health */}
        <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500 dark:text-slate-400">
            <span>Overall Program Health</span>
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
              data.health.overall_status === 'green' ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-400' :
              data.health.overall_status === 'amber' ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-400' :
              'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-400'
            }`}>
              {data.health.overall_status}
            </span>
          </div>
          <div className="my-2 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-slate-900 dark:text-white">
              {data.health.health_score}
            </span>
            <span className="text-xs text-slate-400">/ 100</span>
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 flex items-center justify-between border-t border-slate-100 dark:border-slate-800/60 pt-2 mt-1">
            <span>Delivery Confidence: <strong>{data.health.avg_delivery_confidence}%</strong></span>
            <span>{data.health.total_projects} Projects</span>
          </p>
        </div>

        {/* Card 2: Platform Availability SLA */}
        <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500 dark:text-slate-400">
            <span>Platform Availability (SLA)</span>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-700 dark:bg-rose-950/70 dark:text-rose-400">
              Breached Target
            </span>
          </div>
          <div className="my-2 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-slate-900 dark:text-white">
              98.8%
            </span>
            <span className="text-xs text-rose-500 font-semibold flex items-center">
              <TrendingDown size={14} className="mr-0.5" /> -0.7% vs 99.5%
            </span>
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 flex items-center justify-between border-t border-slate-100 dark:border-slate-800/60 pt-2 mt-1">
            <span>Breach Duration: 4.2h</span>
            <span className="text-rose-600 font-medium">Penalty: $35,000</span>
          </p>
        </div>

        {/* Card 3: Financial Spend vs Plan */}
        <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500 dark:text-slate-400">
            <span>Actual Spend (Q3)</span>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-700 dark:bg-amber-950/70 dark:text-amber-400">
              +$75k Variance
            </span>
          </div>
          <div className="my-2 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-slate-900 dark:text-white">
              ${(data.financials.actual_spend / 1000).toFixed(0)}k
            </span>
            <span className="text-xs text-slate-400">of ${(data.financials.approved_budget / 1000).toFixed(0)}k Budget</span>
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 flex items-center justify-between border-t border-slate-100 dark:border-slate-800/60 pt-2 mt-1">
            <span>Utilization: <strong>{data.financials.budget_utilization_pct}%</strong></span>
            <span>Margin: <strong>{data.financials.gross_margin_pct}%</strong></span>
          </p>
        </div>

        {/* Card 4: Milestones & Critical Risks */}
        <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500 dark:text-slate-400">
            <span>Milestones & RAID Status</span>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-700 dark:bg-blue-950/70 dark:text-blue-400">
              Active
            </span>
          </div>
          <div className="my-2 flex items-baseline gap-3">
            <div>
              <span className="text-3xl font-extrabold text-rose-600">
                {data.health.at_risk_milestones_count}
              </span>
              <span className="text-[11px] text-slate-400 ml-1">Delayed</span>
            </div>
            <span className="text-slate-300 dark:text-slate-700">|</span>
            <div>
              <span className="text-3xl font-extrabold text-amber-600">
                {data.health.critical_risks_count}
              </span>
              <span className="text-[11px] text-slate-400 ml-1">Critical Risks</span>
            </div>
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 flex items-center justify-between border-t border-slate-100 dark:border-slate-800/60 pt-2 mt-1">
            <span>{data.health.pending_customer_decisions_count} Pending Dec.</span>
            <span>{data.health.overdue_actions_count} Overdue Act.</span>
          </p>
        </div>
      </div>

      {/* Interactive Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Chart 1: SLA Availability */}
        <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                Platform Availability SLA vs Target (%)
              </h3>
              <p className="text-[11px] text-slate-400">
                Historical actuals vs contractual target (99.5%) with deterministic breach alert in Q3.
              </p>
            </div>
            <span className="text-xs font-semibold px-2 py-1 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
              QoQ Trend
            </span>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={slaTrendData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#94a3b8" opacity={0.2} />
                <XAxis dataKey="period" stroke="#94a3b8" fontSize={11} />
                <YAxis domain={[98.0, 100.0]} stroke="#94a3b8" fontSize={11} unit="%" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', color: '#fff', fontSize: '12px' }}
                />
                <Legend />
                <Line type="monotone" dataKey="actual" stroke="#2563eb" strokeWidth={3} name="Measured Availability" />
                <Line type="monotone" dataKey="target" stroke="#ef4444" strokeDasharray="5 5" strokeWidth={2} name="SLA Target (99.5%)" />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-3 p-2.5 rounded-lg bg-blue-50/60 dark:bg-blue-950/40 text-[11px] text-blue-800 dark:text-blue-300 border border-blue-100 dark:border-blue-900/60 flex items-center justify-between">
            <span>
              <strong>Insight:</strong> Q3 drop to 98.8% resolved through automated dual-zone replica synchronization.
            </span>
            <button onClick={() => navigate('/kpi-sla')} className="text-blue-600 dark:text-blue-400 font-bold hover:underline shrink-0 ml-2">
              View SLA Details →
            </button>
          </div>
        </div>

        {/* Chart 2: Planned vs Actual Spend */}
        <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                Program Spend: Planned vs Actual ($000s)
              </h3>
              <p className="text-[11px] text-slate-400">
                Budget variance tracked across quarters. Upfront DR hardware accounts for Q3 variance.
              </p>
            </div>
            <span className="text-xs font-semibold px-2 py-1 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
              Finance
            </span>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={spendData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#94a3b8" opacity={0.2} />
                <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} />
                <YAxis stroke="#94a3b8" fontSize={11} unit="k" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', color: '#fff', fontSize: '12px' }}
                />
                <Legend />
                <Bar dataKey="planned" fill="#94a3b8" name="Planned Spend ($k)" radius={[4, 4, 0, 0]} />
                <Bar dataKey="actual" fill="#0d9488" name="Actual Spend ($k)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-3 p-2.5 rounded-lg bg-teal-50/60 dark:bg-teal-950/40 text-[11px] text-teal-800 dark:text-teal-300 border border-teal-100 dark:border-teal-900/60 flex items-center justify-between">
            <span>
              <strong>Insight:</strong> Q3 spend is 6.2% above baseline due to forward-investing in high-availability clusters.
            </span>
            <button onClick={() => navigate('/financials')} className="text-teal-600 dark:text-teal-400 font-bold hover:underline shrink-0 ml-2">
              Financial Analysis →
            </button>
          </div>
        </div>
      </div>

      {/* Executive Alerts Feed */}
      <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <ShieldAlert size={18} className="text-rose-500" />
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">
              Actionable Executive Alerts & Decision Gateways
            </h3>
          </div>
          <span className="text-xs text-slate-400 font-medium">
            {data.alerts.length} Active Items
          </span>
        </div>
        <div className="divide-y divide-slate-100 dark:divide-slate-800/80">
          {data.alerts.map((alt) => (
            <div key={alt.id} className="py-3 flex flex-col md:flex-row md:items-center justify-between gap-3">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                    alt.severity === 'critical' ? 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-400' :
                    alt.severity === 'high' ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-400' :
                    'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-400'
                  }`}>
                    {alt.severity}
                  </span>
                  <span className="text-xs font-semibold text-slate-800 dark:text-slate-100">
                    {alt.title}
                  </span>
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Workstream: <strong>{alt.workstream}</strong> | Recommended Action: {alt.recommended_action}
                </p>
              </div>
              <div className="flex items-center gap-3 shrink-0 text-xs">
                {alt.penalty_exposure !== '$0' && (
                  <span className="font-bold text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/60 px-2 py-1 rounded">
                    Liability: {alt.penalty_exposure}
                  </span>
                )}
                <span className="text-slate-400 text-[11px] flex items-center gap-1">
                  <Clock size={12} /> Due: {alt.due_date}
                </span>
                <button
                  onClick={() => navigate('/qa-war-room')}
                  className="px-2.5 py-1 rounded border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 font-medium text-slate-700 dark:text-slate-200"
                >
                  Rehearse Q&A
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
