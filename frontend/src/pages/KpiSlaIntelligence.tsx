import React, { useState, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import {
  BarChart3,
  TrendingDown,
  TrendingUp,
  AlertOctagon,
  Scale,
  ShieldAlert,
  Info,
  CheckCircle2
} from 'lucide-react';
import { api } from '../api/client';
import { KPIItem, PenaltyDetail } from '../types';

export const KpiSlaIntelligence: React.FC = () => {
  const { reportingPeriod } = useOutletContext<{ reportingPeriod: string }>();
  const [kpis, setKpis] = useState<KPIItem[]>([]);
  const [penalty, setPenalty] = useState<PenaltyDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [filterBreachOnly, setFilterBreachOnly] = useState(false);

  useEffect(() => {
    setLoading(true);
    api.getDashboardSummary(reportingPeriod).then((res) => {
      setKpis(res.kpis || []);
      setPenalty(res.penalty_summary || null);
      setLoading(false);
    }).catch(console.error);
  }, [reportingPeriod]);

  const displayedKpis = filterBreachOnly ? kpis.filter((k) => k.breached) : kpis;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1 rounded bg-blue-100 dark:bg-blue-950 text-blue-600 dark:text-blue-400">
              <BarChart3 size={18} />
            </span>
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
              KPI & SLA Intelligence Engine
            </h2>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Exact deterministic evaluations, target gap compliance, metric directionality, and transparent contractual penalty audits.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <label className="flex items-center gap-2 text-xs font-medium text-slate-700 dark:text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={filterBreachOnly}
              onChange={(e) => setFilterBreachOnly(e.target.checked)}
              className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
            />
            Show Target Breaches Only
          </label>
        </div>
      </div>

      {/* Contract Penalty Breakdown Card */}
      {penalty && (
        <div className="p-5 rounded-xl border border-rose-200 dark:border-rose-900/60 bg-rose-50/40 dark:bg-rose-950/20 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-rose-700 dark:text-rose-400 font-bold text-sm">
              <ShieldAlert size={18} />
              <span>Contractual SLA Penalty Liability: Platform Availability</span>
            </div>
            <span className="px-2.5 py-0.5 rounded text-xs font-bold bg-rose-600 text-white">
              Effective Liability: ${penalty.effective_exposure.toLocaleString()}
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs pt-2 border-t border-rose-100 dark:border-rose-900/40">
            <div>
              <span className="text-slate-500 dark:text-slate-400">Target Threshold</span>
              <p className="font-bold text-slate-900 dark:text-white mt-0.5">{penalty.target_threshold}%</p>
            </div>
            <div>
              <span className="text-slate-500 dark:text-slate-400">Measured Availability</span>
              <p className="font-bold text-rose-600 dark:text-rose-400 mt-0.5">{penalty.actual_measured}%</p>
            </div>
            <div>
              <span className="text-slate-500 dark:text-slate-400">Penalty Rate</span>
              <p className="font-bold text-slate-900 dark:text-white mt-0.5">${penalty.penalty_rate.toLocaleString()} / 0.1%</p>
            </div>
            <div>
              <span className="text-slate-500 dark:text-slate-400">Contract Cap</span>
              <p className="font-bold text-slate-900 dark:text-white mt-0.5">${penalty.cap_amount.toLocaleString()}</p>
            </div>
          </div>

          <div className="p-2.5 rounded bg-white dark:bg-slate-900 text-[11px] text-slate-600 dark:text-slate-300 font-mono border border-rose-100 dark:border-rose-900/40">
            <strong>Audit Rule Trace:</strong> {penalty.rule_source} | {penalty.assumptions}
          </div>
        </div>
      )}

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {displayedKpis.map((kpi) => (
          <div
            key={kpi.metric_name}
            className={`p-4 rounded-xl border bg-white dark:bg-slate-900 shadow-sm flex flex-col justify-between ${
              kpi.breached
                ? 'border-rose-300 dark:border-rose-800'
                : 'border-slate-200 dark:border-slate-800'
            }`}
          >
            <div>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="font-semibold text-slate-500 dark:text-slate-400">
                  {kpi.category}
                </span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                  kpi.breached
                    ? 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-400'
                    : 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-400'
                }`}>
                  {kpi.breached ? 'BREACHED' : 'COMPLIANT'}
                </span>
              </div>
              <h3 className="font-bold text-sm text-slate-900 dark:text-white">
                {kpi.metric_name}
              </h3>

              <div className="my-3 flex items-baseline gap-2">
                <span className="text-2xl font-extrabold text-slate-900 dark:text-white">
                  {kpi.actual} {kpi.unit}
                </span>
                <span className="text-xs text-slate-400">
                  (Target: {kpi.target} {kpi.unit})
                </span>
              </div>
            </div>

            <div className="pt-2.5 border-t border-slate-100 dark:border-slate-800 text-[11px] space-y-1">
              <div className="flex items-center justify-between text-slate-600 dark:text-slate-300">
                <span>Target Variance:</span>
                <span className={kpi.breached ? 'font-bold text-rose-600' : 'font-semibold text-emerald-600'}>
                  {kpi.variance_vs_target > 0 ? `+${kpi.variance_vs_target}` : kpi.variance_vs_target} {kpi.unit}
                </span>
              </div>
              <div className="text-[10px] text-slate-400 truncate">
                Evidence: {kpi.source_lineage}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
