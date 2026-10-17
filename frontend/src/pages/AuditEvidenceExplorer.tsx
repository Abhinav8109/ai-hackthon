import React, { useState, useEffect } from 'react';
import {
  SearchCheck,
  Search,
  Database,
  FileSpreadsheet,
  ShieldCheck,
  ExternalLink,
  Layers
} from 'lucide-react';
import { api } from '../api/client';

export const AuditEvidenceExplorer: React.FC = () => {
  const [auditData, setAuditData] = useState<any | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.getAudit().then((data) => {
      setAuditData(data);
      setLoading(false);
    }).catch(console.error);
  }, []);

  const records = auditData?.kpi_lineage_records || [];
  const filtered = records.filter((r: any) =>
    r.metric_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    r.source_file.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1 rounded bg-blue-100 dark:bg-blue-950 text-blue-600 dark:text-blue-400">
              <SearchCheck size={18} />
            </span>
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
              Audit & Evidence Lineage Explorer
            </h2>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            End-to-end evidence lineage: source spreadsheet → row & cell location → canonical KPI → calculation → QBR claim.
          </p>
        </div>
      </div>

      {/* Search & Audit Table */}
      <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Database size={16} className="text-blue-500" />
            <span>Traceable KPI Records ({filtered.length})</span>
          </h3>

          <div className="relative">
            <Search size={14} className="absolute left-2.5 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search file or metric..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-8 pr-3 py-1.5 text-xs rounded-md border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-400 font-semibold">
                <th className="pb-2.5 pl-2">Record ID</th>
                <th className="pb-2.5">Metric Name</th>
                <th className="pb-2.5">Actual Value</th>
                <th className="pb-2.5">Target Value</th>
                <th className="pb-2.5">Source File</th>
                <th className="pb-2.5">Row / Cell Lineage</th>
                <th className="pb-2.5 pr-2">Ingestion Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 font-mono">
              {filtered.map((r: any) => (
                <tr key={r.record_id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40 text-[11px]">
                  <td className="py-2.5 pl-2 text-slate-500">
                    {r.record_id}
                  </td>
                  <td className="py-2.5 font-bold font-sans text-slate-900 dark:text-white">
                    {r.metric_name}
                  </td>
                  <td className="py-2.5 text-slate-800 dark:text-slate-200">
                    {r.actual_value}
                  </td>
                  <td className="py-2.5 text-slate-500">
                    {r.target_value}
                  </td>
                  <td className="py-2.5 text-blue-600 dark:text-blue-400">
                    {r.source_file}
                  </td>
                  <td className="py-2.5 text-emerald-600 dark:text-emerald-400 font-bold">
                    Row {r.source_row} ({r.source_cell})
                  </td>
                  <td className="py-2.5 pr-2 text-slate-400">
                    {new Date(r.timestamp).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
