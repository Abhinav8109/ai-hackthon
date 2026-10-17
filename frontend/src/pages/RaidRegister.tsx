import React, { useState, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import {
  ShieldAlert,
  AlertTriangle,
  Plus,
  Filter,
  CheckCircle,
  Clock,
  Layers,
  ArrowRight
} from 'lucide-react';
import { api } from '../api/client';
import { RAIDItemType } from '../types';

export const RaidRegister: React.FC = () => {
  const { showToast } = useOutletContext<{ showToast: (msg: string) => void }>();
  const [items, setItems] = useState<RAIDItemType[]>([]);
  const [typeFilter, setTypeFilter] = useState('all');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [showModal, setShowModal] = useState(false);

  // New item form
  const [newItem, setNewItem] = useState({
    title: '',
    type: 'risk',
    category: 'Technical',
    impact: 4,
    likelihood: 4,
    owner: '',
    due_date: '2026-10-30',
    mitigation: '',
    project_id: 'proj-demo-1',
    description: ''
  });

  const loadRaid = () => {
    const t = typeFilter !== 'all' ? typeFilter : undefined;
    const s = severityFilter !== 'all' ? severityFilter : undefined;
    api.getRaid(t, s).then(setItems).catch(console.error);
  };

  useEffect(() => {
    loadRaid();
  }, [typeFilter, severityFilter]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newItem.title) return;
    try {
      const id = `RAID-${Date.now().toString().slice(-4)}`;
      await api.createRaid({
        ...newItem,
        id,
        score: newItem.impact * newItem.likelihood,
        severity: (newItem.impact * newItem.likelihood >= 16) ? 'critical' : 'high',
        status: 'open'
      } as any);
      showToast('RAID record added to register.');
      setShowModal(false);
      loadRaid();
    } catch (e) {
      showToast('Failed to add RAID item.');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1 rounded bg-rose-100 dark:bg-rose-950 text-rose-600 dark:text-rose-400">
              <ShieldAlert size={18} />
            </span>
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
              RAID & Risk Governance Register
            </h2>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Track Risks, Assumptions, Issues, and Dependencies with deterministic 5x5 impact scoring and verified mitigations.
          </p>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-sm transition-all"
        >
          <Plus size={14} />
          <span>Add RAID Item</span>
        </button>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-3 p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm text-xs">
        <div className="flex items-center gap-2">
          <Filter size={14} className="text-slate-400" />
          <span className="font-semibold text-slate-700 dark:text-slate-300">Filters:</span>
        </div>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="px-2.5 py-1.5 rounded-md border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
        >
          <option value="all">All RAID Types</option>
          <option value="risk">Risks Only</option>
          <option value="issue">Issues Only</option>
          <option value="dependency">Dependencies Only</option>
          <option value="assumption">Assumptions Only</option>
        </select>
        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
          className="px-2.5 py-1.5 rounded-md border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
        >
          <option value="all">All Severities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
      </div>

      {/* RAID Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {items.map((r) => (
          <div
            key={r.id}
            className={`p-4 rounded-xl border bg-white dark:bg-slate-900 shadow-sm flex flex-col justify-between ${
              r.severity === 'critical' ? 'border-rose-300 dark:border-rose-900' :
              r.severity === 'high' ? 'border-amber-300 dark:border-amber-900' :
              'border-slate-200 dark:border-slate-800'
            }`}
          >
            <div>
              <div className="flex items-center justify-between text-xs mb-1.5">
                <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                  {r.type}
                </span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                  r.severity === 'critical' ? 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-400' :
                  r.severity === 'high' ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-400' :
                  'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-400'
                }`}>
                  Score: {r.score} ({r.severity})
                </span>
              </div>

              <h4 className="font-bold text-sm text-slate-900 dark:text-white leading-snug">
                {r.title}
              </h4>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">
                {r.description}
              </p>
            </div>

            <div className="pt-3 border-t border-slate-100 dark:border-slate-800 text-[11px] space-y-1.5 mt-3">
              <div className="flex items-center justify-between text-slate-600 dark:text-slate-300">
                <span>Owner: <strong>{r.owner}</strong></span>
                <span>Due: {r.due_date}</span>
              </div>
              <p className="text-[11px] text-slate-700 dark:text-slate-200 bg-slate-50 dark:bg-slate-800/60 p-2 rounded">
                <strong>Mitigation:</strong> {r.mitigation}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Modal for New RAID Item */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 max-w-md w-full space-y-4 shadow-xl">
            <h3 className="text-base font-bold text-slate-900 dark:text-white">
              Log New RAID Item
            </h3>
            <form onSubmit={handleCreate} className="space-y-3 text-xs">
              <div>
                <label className="block font-medium text-slate-700 dark:text-slate-300 mb-1">Title</label>
                <input
                  type="text"
                  required
                  value={newItem.title}
                  onChange={(e) => setNewItem({ ...newItem, title: e.target.value })}
                  className="w-full px-3 py-1.5 rounded border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block font-medium text-slate-700 dark:text-slate-300 mb-1">Type</label>
                  <select
                    value={newItem.type}
                    onChange={(e) => setNewItem({ ...newItem, type: e.target.value })}
                    className="w-full px-2 py-1.5 rounded border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800"
                  >
                    <option value="risk">Risk</option>
                    <option value="issue">Issue</option>
                    <option value="dependency">Dependency</option>
                    <option value="assumption">Assumption</option>
                  </select>
                </div>
                <div>
                  <label className="block font-medium text-slate-700 dark:text-slate-300 mb-1">Owner</label>
                  <input
                    type="text"
                    required
                    value={newItem.owner}
                    onChange={(e) => setNewItem({ ...newItem, owner: e.target.value })}
                    className="w-full px-3 py-1.5 rounded border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block font-medium text-slate-700 dark:text-slate-300 mb-1">Impact (1-5)</label>
                  <input
                    type="number"
                    min="1"
                    max="5"
                    value={newItem.impact}
                    onChange={(e) => setNewItem({ ...newItem, impact: parseInt(e.target.value) || 1 })}
                    className="w-full px-3 py-1.5 rounded border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800"
                  />
                </div>
                <div>
                  <label className="block font-medium text-slate-700 dark:text-slate-300 mb-1">Likelihood (1-5)</label>
                  <input
                    type="number"
                    min="1"
                    max="5"
                    value={newItem.likelihood}
                    onChange={(e) => setNewItem({ ...newItem, likelihood: parseInt(e.target.value) || 1 })}
                    className="w-full px-3 py-1.5 rounded border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800"
                  />
                </div>
              </div>
              <div>
                <label className="block font-medium text-slate-700 dark:text-slate-300 mb-1">Mitigation Plan</label>
                <textarea
                  rows={2}
                  required
                  value={newItem.mitigation}
                  onChange={(e) => setNewItem({ ...newItem, mitigation: e.target.value })}
                  className="w-full px-3 py-1.5 rounded border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-3 py-1.5 rounded border border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded bg-blue-600 hover:bg-blue-700 text-white font-semibold"
                >
                  Save Record
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
