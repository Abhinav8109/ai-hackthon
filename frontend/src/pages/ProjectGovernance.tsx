import React, { useState, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import {
  FolderKanban,
  CheckCircle2,
  Clock,
  AlertTriangle,
  User,
  Calendar,
  Layers,
  ArrowRight
} from 'lucide-react';
import { api } from '../api/client';
import { ProjectItem, MilestoneItem } from '../types';

export const ProjectGovernance: React.FC = () => {
  const { reportingPeriod } = useOutletContext<{ reportingPeriod: string }>();
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [milestones, setMilestones] = useState<MilestoneItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([api.getProjects(reportingPeriod), api.getMilestones()]).then(([p, m]) => {
      setProjects(p);
      setMilestones(m);
      setLoading(false);
    }).catch(console.error);
  }, [reportingPeriod]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1 rounded bg-blue-100 dark:bg-blue-950 text-blue-600 dark:text-blue-400">
              <FolderKanban size={18} />
            </span>
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
              Project & Program Governance
            </h2>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Portfolio delivery health, milestone tracking, schedule recovery plans, and customer dependency bottlenecks.
          </p>
        </div>
      </div>

      {/* Projects Portfolio Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {projects.map((proj) => (
          <div
            key={proj.id}
            className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-3"
          >
            <div className="flex items-start justify-between">
              <div>
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  {proj.program}
                </span>
                <h3 className="font-bold text-base text-slate-900 dark:text-white mt-0.5">
                  {proj.name}
                </h3>
              </div>
              <span className={`px-2.5 py-0.5 rounded text-xs font-bold uppercase ${
                proj.health === 'green' ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-400' :
                proj.health === 'amber' ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-400' :
                'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-400'
              }`}>
                {proj.health}
              </span>
            </div>

            <div className="grid grid-cols-3 gap-2 text-xs pt-1">
              <div>
                <span className="text-slate-400 text-[10px]">Delivery Confidence</span>
                <p className="font-bold text-slate-900 dark:text-white mt-0.5">{proj.delivery_confidence}%</p>
              </div>
              <div>
                <span className="text-slate-400 text-[10px]">Spend vs Budget</span>
                <p className="font-bold text-slate-900 dark:text-white mt-0.5">
                  ${(proj.actual_spend / 1000).toFixed(0)}k / ${(proj.approved_budget / 1000).toFixed(0)}k
                </p>
              </div>
              <div>
                <span className="text-slate-400 text-[10px]">Owner / Sponsor</span>
                <p className="font-bold text-slate-900 dark:text-white mt-0.5 truncate">{proj.owner}</p>
              </div>
            </div>

            <p className="text-xs text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-800/60 p-2.5 rounded-lg border border-slate-100 dark:border-slate-800">
              <strong>Update:</strong> {proj.key_updates}
            </p>
          </div>
        ))}
      </div>

      {/* Milestones Register & Timeline */}
      <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white">
            Delivery Milestones & Schedule Health
          </h3>
          <span className="text-xs text-slate-400 font-medium">
            {milestones.length} Strategic Milestones Tracked
          </span>
        </div>

        <div className="space-y-3">
          {milestones.map((m) => (
            <div
              key={m.id}
              className="p-4 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-850 space-y-2"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                    m.status === 'completed' ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-400' :
                    m.status === 'delayed' ? 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-400' :
                    'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-400'
                  }`}>
                    {m.status.replace('_', ' ')}
                  </span>
                  <h4 className="font-bold text-sm text-slate-900 dark:text-white">
                    {m.title}
                  </h4>
                  {m.customer_dependency && (
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-400">
                      Customer Dependency
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-3 text-xs text-slate-500">
                  <span>Planned: <strong>{m.planned_date}</strong></span>
                  <span>Target: <strong>{m.actual_or_forecast_date}</strong></span>
                  <span>Owner: <strong>{m.owner}</strong></span>
                </div>
              </div>

              {/* Progress Bar */}
              <div className="w-full bg-slate-200 dark:bg-slate-700 h-2 rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ${
                    m.status === 'completed' ? 'bg-emerald-500' :
                    m.status === 'delayed' ? 'bg-rose-500' : 'bg-blue-500'
                  }`}
                  style={{ width: `${m.completion_pct}%` }}
                />
              </div>

              {m.recovery_plan && (
                <p className="text-xs text-rose-700 dark:text-rose-400 font-medium">
                  <strong>Recovery Action:</strong> {m.recovery_plan}
                </p>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
