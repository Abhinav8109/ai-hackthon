import React, { useState, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import {
  DollarSign,
  TrendingDown,
  TrendingUp,
  CreditCard,
  PieChart as PieIcon,
  Calculator,
  ArrowRight
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid
} from 'recharts';
import { api } from '../api/client';
import { FinancialSummary } from '../types';

export const FinancialIntelligence: React.FC = () => {
  const { reportingPeriod } = useOutletContext<{ reportingPeriod: string }>();
  const [fin, setFin] = useState<FinancialSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.getDashboardSummary(reportingPeriod).then((res) => {
      setFin(res.financials || null);
      setLoading(false);
    }).catch(console.error);
  }, [reportingPeriod]);

  if (loading || !fin) {
    return <div className="p-8 text-center text-slate-400">Loading Financial Intelligence...</div>;
  }

  const breakdownData = [
    { category: 'Compute & Cloud (AWS/GCP)', planned: 550, actual: 610 },
    { category: 'Database & Storage', planned: 250, actual: 275 },
    { category: 'SRE & Support Engineering', planned: 280, actual: 270 },
    { category: 'Security & Compliance', planned: 120, actual: 120 },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1 rounded bg-teal-100 dark:bg-teal-950 text-teal-600 dark:text-teal-400">
              <DollarSign size={18} />
            </span>
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
              Financial Intelligence & Budget Governance
            </h2>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Exact Python arithmetic for budget consumption, gross margin variances, and contractual exposure.
          </p>
        </div>
      </div>

      {/* Financial Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
          <span className="text-xs font-semibold text-slate-400">Approved Budget</span>
          <div className="my-2 text-2xl font-extrabold text-slate-900 dark:text-white">
            ${(fin.approved_budget / 1000).toFixed(0)}k
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400">
            Authorized Q3 expenditure ceiling
          </p>
        </div>

        <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
          <span className="text-xs font-semibold text-slate-400">Actual Spend</span>
          <div className="my-2 text-2xl font-extrabold text-teal-600 dark:text-teal-400">
            ${(fin.actual_spend / 1000).toFixed(0)}k
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 flex items-center justify-between">
            <span>Utilization: <strong>{fin.budget_utilization_pct}%</strong></span>
            <span className="text-amber-500 font-semibold">+${(fin.budget_variance / 1000).toFixed(0)}k vs Plan</span>
          </p>
        </div>

        <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
          <span className="text-xs font-semibold text-slate-400">Gross Margin %</span>
          <div className="my-2 text-2xl font-extrabold text-slate-900 dark:text-white">
            {fin.gross_margin_pct}%
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400">
            Gross Profit: <strong>${((fin.gross_profit || 0) / 1000).toFixed(0)}k</strong>
          </p>
        </div>

        <div className="p-4 rounded-xl border border-rose-200 dark:border-rose-900/60 bg-rose-50/30 dark:bg-rose-950/20 shadow-sm">
          <span className="text-xs font-semibold text-rose-600 dark:text-rose-400">Total Penalty Exposure</span>
          <div className="my-2 text-2xl font-extrabold text-rose-600 dark:text-rose-400">
            ${fin.total_penalty_exposure.toLocaleString()}
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400">
            SLA Schedule 4.2 Liability
          </p>
        </div>
      </div>

      {/* Spend Breakdown Chart & Mathematical Formulas */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-3">
            Spend Allocation by Infrastructure Category ($k)
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={breakdownData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                <XAxis type="number" fontSize={11} unit="k" />
                <YAxis dataKey="category" type="category" fontSize={11} width={130} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderRadius: '8px', color: '#fff', fontSize: '12px' }} />
                <Legend />
                <Bar dataKey="planned" fill="#94a3b8" name="Planned ($k)" radius={[0, 4, 4, 0]} />
                <Bar dataKey="actual" fill="#0d9488" name="Actual ($k)" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Formulas Transparency Box */}
        <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-3">
          <div className="flex items-center gap-2 text-xs font-bold text-blue-600 dark:text-blue-400 uppercase">
            <Calculator size={15} />
            <span>Deterministic Formulas</span>
          </div>
          <p className="text-xs text-slate-400">
            Calculations strictly computed by Python analytics without LLM estimation.
          </p>
          <div className="space-y-2 text-xs font-mono">
            <div className="p-2 rounded bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
              <span className="text-slate-400 block text-[10px]">Budget Variance</span>
              actual_spend - planned_spend
            </div>
            <div className="p-2 rounded bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
              <span className="text-slate-400 block text-[10px]">Budget Utilization</span>
              (actual_spend / approved_budget) * 100
            </div>
            <div className="p-2 rounded bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
              <span className="text-slate-400 block text-[10px]">Gross Margin %</span>
              ((revenue - cost) / revenue) * 100
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
