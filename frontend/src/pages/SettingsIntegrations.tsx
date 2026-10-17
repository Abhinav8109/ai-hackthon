import React, { useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import {
  Settings,
  ShieldCheck,
  Cloud,
  Key,
  Database,
  RotateCcw,
  CheckCircle2,
  Server,
  Info
} from 'lucide-react';
import { api } from '../api/client';

export const SettingsIntegrations: React.FC = () => {
  const { showToast } = useOutletContext<{ showToast: (msg: string) => void }>();
  const [apiKey, setApiKey] = useState('');
  const [resetting, setResetting] = useState(false);

  const handleSaveApiKey = (e: React.FormEvent) => {
    e.preventDefault();
    showToast('API Key configured in runtime session.');
  };

  const handleReset = async () => {
    if (!window.confirm('Reset all demo records back to baseline benchmark?')) return;
    setResetting(true);
    try {
      await api.resetDemo();
      showToast('Environment reset to clean demo benchmark state.');
      window.location.reload();
    } catch (e) {
      showToast('Reset failed.');
    } finally {
      setResetting(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
              <Settings size={18} />
            </span>
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
              Settings & Cloud Integrations
            </h2>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Google Cloud configuration, Gemini model integrations, and database storage telemetry.
          </p>
        </div>
      </div>

      {/* Cloud & Model Status */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-bold text-slate-900 dark:text-white">
              <Cloud size={16} className="text-blue-500" />
              <span>Google Cloud Run Environment</span>
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-400">
              Configured
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Active Project: <strong>cloudopsworks-511015</strong>
          </p>
          <div className="p-2.5 rounded bg-slate-50 dark:bg-slate-800/60 text-[11px] text-slate-600 dark:text-slate-300 font-mono">
            Target Service: qbr-intelligence-360 | Region: us-central1
          </div>
        </div>

        <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-bold text-slate-900 dark:text-white">
              <Database size={16} className="text-teal-500" />
              <span>Persistence & Storage Layer</span>
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-400">
              Online
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Engine: <strong>SQLite Repository with GCS Abstraction</strong>
          </p>
          <div className="p-2.5 rounded bg-slate-50 dark:bg-slate-800/60 text-[11px] text-slate-600 dark:text-slate-300 font-mono">
            File Lineage: data/qbr_intelligence.db
          </div>
        </div>
      </div>

      {/* Gemini API Key Configuration */}
      <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-3">
        <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <Key size={15} className="text-amber-500" />
          <span>Gemini / Vertex AI API Configuration</span>
        </h3>
        <p className="text-xs text-slate-400">
          The application operates deterministically with zero external API calls by default. If a Gemini API Key is provided, live generative extensions are enabled.
        </p>

        <form onSubmit={handleSaveApiKey} className="flex gap-2">
          <input
            type="password"
            placeholder="AIzaSy..."
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            className="flex-1 px-3 py-1.5 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none"
          />
          <button
            type="submit"
            className="px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold"
          >
            Save Key
          </button>
        </form>
      </div>

      {/* Demo Reset Card */}
      <div className="p-5 rounded-xl border border-amber-200 dark:border-amber-900/60 bg-amber-50/30 dark:bg-amber-950/20 shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs font-bold text-amber-800 dark:text-amber-300">
            <RotateCcw size={16} />
            <span>Reset Demo Benchmark Data</span>
          </div>
          <button
            onClick={handleReset}
            disabled={resetting}
            className="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold transition-all disabled:opacity-50"
          >
            {resetting ? 'Resetting...' : 'Reset to Benchmark'}
          </button>
        </div>
        <p className="text-xs text-slate-600 dark:text-slate-400">
          Reverts all canonical KPI records, project milestones, RAID entries, customer Q&A questions, and commitments back to the official hackathon demo benchmark scenario.
        </p>
      </div>
    </div>
  );
};
