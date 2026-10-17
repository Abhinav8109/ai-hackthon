import React, { useState, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import {
  CheckSquare,
  CheckCircle2,
  Clock,
  AlertTriangle,
  User,
  Vote,
  ArrowRight,
  Filter
} from 'lucide-react';
import { api } from '../api/client';
import { ActionItemType, DecisionItemType } from '../types';

export const ActionDecisionRegister: React.FC = () => {
  const { showToast } = useOutletContext<{ showToast: (msg: string) => void }>();
  const [actions, setActions] = useState<ActionItemType[]>([]);
  const [decisions, setDecisions] = useState<DecisionItemType[]>([]);
  const [activeTab, setActiveTab] = useState<'actions' | 'decisions'>('actions');

  const loadData = () => {
    Promise.all([api.getActions(), api.getDecisions()]).then(([a, d]) => {
      setActions(a);
      setDecisions(d);
    }).catch(console.error);
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleActionStatus = async (id: string, newStatus: string) => {
    try {
      await api.updateActionStatus(id, newStatus);
      showToast(`Action ${id} marked as ${newStatus}.`);
      loadData();
    } catch (e) {
      showToast('Failed to update action status.');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1 rounded bg-blue-100 dark:bg-blue-950 text-blue-600 dark:text-blue-400">
              <CheckSquare size={18} />
            </span>
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
              Action & Decision Governance Register
            </h2>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Track operational corrective actions, acceptance criteria, closure evidence, and ratified executive decision logs.
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-slate-200 dark:border-slate-800">
        <button
          onClick={() => setActiveTab('actions')}
          className={`px-4 py-2 text-xs font-bold border-b-2 transition-all ${
            activeTab === 'actions'
              ? 'border-blue-600 text-blue-600 dark:text-blue-400'
              : 'border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-slate-300'
          }`}
        >
          Action Items ({actions.length})
        </button>
        <button
          onClick={() => setActiveTab('decisions')}
          className={`px-4 py-2 text-xs font-bold border-b-2 transition-all ${
            activeTab === 'decisions'
              ? 'border-blue-600 text-blue-600 dark:text-blue-400'
              : 'border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-slate-300'
          }`}
        >
          Decision Log ({decisions.length})
        </button>
      </div>

      {/* Action Items List */}
      {activeTab === 'actions' && (
        <div className="space-y-3">
          {actions.map((act) => (
            <div
              key={act.id}
              className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                    act.priority === 'urgent' ? 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-400' :
                    'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-400'
                  }`}>
                    {act.priority}
                  </span>
                  <h4 className="font-bold text-slate-900 dark:text-white">
                    {act.title}
                  </h4>
                </div>
                <p className="text-slate-500 dark:text-slate-400">
                  {act.description}
                </p>
                <div className="flex items-center gap-4 text-[11px] text-slate-400 pt-1">
                  <span>Owner: <strong>{act.owner}</strong></span>
                  <span>Due: {act.due_date}</span>
                  <span>Criteria: {act.acceptance_criteria}</span>
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <select
                  value={act.status}
                  onChange={(e) => handleActionStatus(act.id, e.target.value)}
                  className="px-2.5 py-1.5 rounded-md border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-semibold"
                >
                  <option value="open">Open</option>
                  <option value="in_progress">In Progress</option>
                  <option value="blocked">Blocked</option>
                  <option value="completed">Completed</option>
                </select>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Decision Log List */}
      {activeTab === 'decisions' && (
        <div className="space-y-4">
          {decisions.map((dec) => (
            <div
              key={dec.id}
              className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-3 text-xs"
            >
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-[10px] font-bold text-blue-600 dark:text-blue-400 uppercase tracking-wider">
                    {dec.id} • {dec.status.toUpperCase()}
                  </span>
                  <h4 className="font-bold text-sm text-slate-900 dark:text-white mt-0.5">
                    {dec.title}
                  </h4>
                </div>
                {dec.customer_ask && (
                  <span className="px-2.5 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-400">
                    Customer Sponsor Approval Required
                  </span>
                )}
              </div>

              <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-850 border border-slate-200 dark:border-slate-800 space-y-1.5">
                <span className="font-semibold text-slate-700 dark:text-slate-300">Selected Decision & Rationale:</span>
                <p className="text-slate-800 dark:text-slate-100 font-medium">
                  "{dec.selected_decision}"
                </p>
                <p className="text-[11px] text-slate-500">
                  Rationale: {dec.rationale}
                </p>
              </div>

              <div className="flex flex-wrap items-center justify-between text-[11px] text-slate-400 pt-2 border-t border-slate-100 dark:border-slate-800">
                <span>Decision Owner: <strong>{dec.decision_owner}</strong></span>
                <span>Ratification Date: {dec.decision_date}</span>
                <span>Follow-ups: {dec.follow_up_actions.join(', ')}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
