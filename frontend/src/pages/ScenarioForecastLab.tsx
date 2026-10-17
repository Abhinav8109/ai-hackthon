import React, { useState, useEffect } from 'react';
import {
  Sliders,
  TrendingUp,
  AlertTriangle,
  Play,
  RotateCcw,
  Scale,
  Sparkles,
  ArrowRight
} from 'lucide-react';
import { api } from '../api/client';

export const ScenarioForecastLab: React.FC = () => {
  const [scenarioName, setScenarioName] = useState('Rapid SLA & Cost Recovery Plan');
  const [slaRecovery, setSlaRecovery] = useState(1.0);
  const [costReduction, setCostReduction] = useState(75000);
  const [milestoneAccel, setMilestoneAccel] = useState(14);
  const [penaltyRelief, setPenaltyRelief] = useState(50);
  const [result, setResult] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);

  const runSimulation = async () => {
    setLoading(true);
    try {
      const res = await api.runScenario({
        scenario_name: scenarioName,
        sla_recovery_delta_pct: slaRecovery,
        cost_reduction_delta: costReduction,
        milestone_acceleration_days: milestoneAccel,
        utilization_target_pct: 85.0,
        penalty_relief_pct: penaltyRelief
      });
      setResult(res);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runSimulation();
  }, [slaRecovery, costReduction, milestoneAccel, penaltyRelief]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1 rounded bg-indigo-100 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400">
              <Sliders size={18} />
            </span>
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
              Scenario & What-If Forecasting Lab
            </h2>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Simulate hypothetical operational assumptions and test trade-offs between SLA recovery, cost reduction, and contract exposure.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Sliders Input Panel (5 cols) */}
        <div className="lg:col-span-5 p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-5">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white">
            Hypothetical Operational Levers
          </h3>

          {/* Slider 1: SLA Recovery */}
          <div className="space-y-1.5 text-xs">
            <div className="flex justify-between font-semibold">
              <span className="text-slate-700 dark:text-slate-300">Target SLA Recovery (Δ%)</span>
              <span className="text-blue-600 dark:text-blue-400 font-bold">+{slaRecovery}%</span>
            </div>
            <input
              type="range"
              min="0.0"
              max="2.5"
              step="0.1"
              value={slaRecovery}
              onChange={(e) => setSlaRecovery(parseFloat(e.target.value))}
              className="w-full accent-blue-600 cursor-pointer"
            />
            <span className="text-[10px] text-slate-400">Pushes availability up to {Math.min(100, 98.8 + slaRecovery).toFixed(1)}%</span>
          </div>

          {/* Slider 2: Cost Reduction */}
          <div className="space-y-1.5 text-xs">
            <div className="flex justify-between font-semibold">
              <span className="text-slate-700 dark:text-slate-300">Target Spend Reduction ($)</span>
              <span className="text-teal-600 dark:text-teal-400 font-bold">${costReduction.toLocaleString()}</span>
            </div>
            <input
              type="range"
              min="0"
              max="150000"
              step="5000"
              value={costReduction}
              onChange={(e) => setCostReduction(parseInt(e.target.value))}
              className="w-full accent-teal-600 cursor-pointer"
            />
            <span className="text-[10px] text-slate-400">Cluster rightsizing and license reclamation</span>
          </div>

          {/* Slider 3: Milestone Acceleration */}
          <div className="space-y-1.5 text-xs">
            <div className="flex justify-between font-semibold">
              <span className="text-slate-700 dark:text-slate-300">Schedule Compression (Days)</span>
              <span className="text-indigo-600 dark:text-indigo-400 font-bold">{milestoneAccel} Days</span>
            </div>
            <input
              type="range"
              min="0"
              max="30"
              step="1"
              value={milestoneAccel}
              onChange={(e) => setMilestoneAccel(parseInt(e.target.value))}
              className="w-full accent-indigo-600 cursor-pointer"
            />
            <span className="text-[10px] text-slate-400">Engages parallel sprint delivery squads</span>
          </div>

          {/* Slider 4: Penalty Relief */}
          <div className="space-y-1.5 text-xs">
            <div className="flex justify-between font-semibold">
              <span className="text-slate-700 dark:text-slate-300">SLA Penalty Relief Negotiations (%)</span>
              <span className="text-rose-600 dark:text-rose-400 font-bold">{penaltyRelief}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              step="5"
              value={penaltyRelief}
              onChange={(e) => setPenaltyRelief(parseInt(e.target.value))}
              className="w-full accent-rose-600 cursor-pointer"
            />
            <span className="text-[10px] text-slate-400">Contingent on client change freeze sign-off</span>
          </div>
        </div>

        {/* Results Comparison Panel (7 cols) */}
        {result && (
          <div className="lg:col-span-7 p-6 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-5">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  Scenario Projection
                </span>
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  Baseline vs Projected Comparison
                </h3>
              </div>
              <div className="text-right">
                <span className="text-[10px] text-slate-400 block">Feasibility Score</span>
                <span className="text-lg font-extrabold text-emerald-600 dark:text-emerald-400">
                  {result.feasibility_score}%
                </span>
              </div>
            </div>

            {/* Metrics Comparison Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-xs">
                <span className="text-slate-400 text-[10px]">SLA Achievement</span>
                <p className="font-bold text-slate-900 dark:text-white text-base mt-0.5">
                  {result.projected.sla_achievement_pct}%
                </p>
                <span className="text-[10px] text-emerald-600 font-semibold">
                  +{result.delta.sla_achievement_delta}% vs 98.8%
                </span>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-xs">
                <span className="text-slate-400 text-[10px]">Program Spend</span>
                <p className="font-bold text-slate-900 dark:text-white text-base mt-0.5">
                  ${(result.projected.actual_spend / 1000).toFixed(0)}k
                </p>
                <span className="text-[10px] text-teal-600 font-semibold">
                  -${Math.abs(result.delta.spend_delta / 1000).toFixed(0)}k
                </span>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-xs">
                <span className="text-slate-400 text-[10px]">Gross Margin</span>
                <p className="font-bold text-slate-900 dark:text-white text-base mt-0.5">
                  {result.projected.gross_margin_pct}%
                </p>
                <span className="text-[10px] text-blue-600 font-semibold">
                  +{result.delta.margin_delta}%
                </span>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-xs">
                <span className="text-slate-400 text-[10px]">Penalty Liability</span>
                <p className="font-bold text-rose-600 dark:text-rose-400 text-base mt-0.5">
                  ${result.projected.penalty_exposure.toLocaleString()}
                </p>
                <span className="text-[10px] text-emerald-600 font-semibold">
                  -${Math.abs(result.delta.penalty_delta).toLocaleString()}
                </span>
              </div>
            </div>

            {/* Impact Narrative */}
            <div className="p-3.5 rounded-lg bg-blue-50/50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-900/60 text-xs text-blue-900 dark:text-blue-300">
              <strong>Executive Impact Summary:</strong> {result.impact_summary}
            </div>

            {/* Trade-offs & Risks */}
            <div className="space-y-1.5 pt-2 border-t border-slate-100 dark:border-slate-800 text-xs">
              <span className="font-bold text-slate-500 dark:text-slate-400 uppercase text-[10px]">
                Identified Operational Trade-offs
              </span>
              <ul className="space-y-1 list-disc list-inside text-slate-600 dark:text-slate-300">
                {result.tradeoffs.map((t: string, idx: number) => (
                  <li key={idx}>{t}</li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
