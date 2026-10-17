import React, { useState } from 'react';
import {
  Sun,
  Moon,
  RotateCcw,
  ShieldCheck,
  CheckCircle2,
  Calendar,
  CloudUpload
} from 'lucide-react';
import { api } from '../api/client';

interface NavbarProps {
  darkMode: boolean;
  onToggleTheme: () => void;
  reportingPeriod: string;
  onPeriodChange: (p: string) => void;
  onNotification?: (msg: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  darkMode,
  onToggleTheme,
  reportingPeriod,
  onPeriodChange,
  onNotification
}) => {
  const [resetting, setResetting] = useState(false);

  const handleResetDemo = async () => {
    if (!window.confirm('Reset demo environment to the baseline benchmark data?')) return;
    setResetting(true);
    try {
      await api.resetDemo();
      if (onNotification) onNotification('Demo benchmark data reset successfully.');
      window.location.reload();
    } catch (e) {
      alert('Failed to reset demo');
    } finally {
      setResetting(false);
    }
  };

  return (
    <header className="h-16 border-b border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-20">
      {/* Left: Program / Period badge */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-xs font-medium text-slate-500 dark:text-slate-400">
          <Calendar size={15} className="text-slate-400" />
          <span>Reporting Period:</span>
        </div>
        <select
          value={reportingPeriod}
          onChange={(e) => onPeriodChange(e.target.value)}
          className="text-xs font-semibold px-2.5 py-1.5 rounded-md border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="2026-Q3">2026-Q3 (Active Review)</option>
          <option value="2026-Q2">2026-Q2 (Prior Benchmark)</option>
          <option value="2026-Q1">2026-Q1 (Historical)</option>
        </select>

        {/* Demo Mode Badge */}
        <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-50 dark:bg-amber-950/60 border border-amber-200 dark:border-amber-800/80 text-[11px] font-semibold text-amber-700 dark:text-amber-400">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
          Synthetic Demo Benchmark Active
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-3">
        {/* Reset Demo Button */}
        <button
          onClick={handleResetDemo}
          disabled={resetting}
          className="flex items-center gap-1.5 text-xs font-medium px-2.5 py-1.5 rounded-md border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 transition-colors"
          title="Reset synthetic dataset to clean default"
        >
          <RotateCcw size={13} className={resetting ? 'animate-spin' : ''} />
          <span>{resetting ? 'Resetting...' : 'Reset Demo'}</span>
        </button>

        {/* Cloud Status */}
        <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-900/60 text-[11px] font-medium text-emerald-700 dark:text-emerald-400">
          <ShieldCheck size={14} />
          <span>Cloud Run Validated</span>
        </div>

        {/* Theme Toggle */}
        <button
          onClick={onToggleTheme}
          className="p-2 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 transition-colors"
          title={darkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
        >
          {darkMode ? <Sun size={18} /> : <Moon size={18} />}
        </button>
      </div>
    </header>
  );
};
