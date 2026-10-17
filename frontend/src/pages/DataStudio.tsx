import React, { useState, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import {
  UploadCloud,
  FileCheck2,
  AlertTriangle,
  FileSpreadsheet,
  CheckCircle,
  Database,
  ArrowUpDown,
  Search,
  Filter
} from 'lucide-react';
import { api } from '../api/client';

export const DataStudio: React.FC = () => {
  const { reportingPeriod, showToast } = useOutletContext<{
    reportingPeriod: string;
    showToast: (msg: string) => void;
  }>();

  const [datasets, setDatasets] = useState<any[]>([]);
  const [canonicalRecords, setCanonicalRecords] = useState<any[]>([]);
  const [uploading, setUploading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');

  const loadData = () => {
    api.getDatasets().then((res) => {
      setDatasets(res.datasets || []);
    }).catch(console.error);

    fetch(`/api/v1/kpis?period=${reportingPeriod}`)
      .then((res) => res.json())
      .then((data) => setCanonicalRecords(data))
      .catch(console.error);
  };

  useEffect(() => {
    loadData();
  }, [reportingPeriod]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    showToast(`Uploading and validating ${file.name}...`);
    try {
      const res = await api.uploadDataset(file, reportingPeriod);
      showToast(`Dataset validated: ${res.report.valid_rows} valid records ingested.`);
      loadData();
    } catch (err) {
      showToast('Upload failed or validation error occurred.');
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const filteredRecords = canonicalRecords.filter((r) => {
    const matchesSearch = r.metric_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.workstream.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCat = categoryFilter === 'all' || r.metric_category === categoryFilter;
    return matchesSearch && matchesCat;
  });

  return (
    <div className="space-y-6">
      {/* Page Title */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
            Data Studio & Ingestion Engine
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Ingest, auto-map columns, validate schema rules, and preserve row-level evidence lineage into Canonical KPI records.
          </p>
        </div>
      </div>

      {/* Upload Zone & Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload Box */}
        <div className="lg:col-span-2 p-6 rounded-xl border-2 border-dashed border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 flex flex-col items-center justify-center text-center">
          <UploadCloud size={36} className="text-blue-500 mb-2" />
          <h3 className="text-sm font-bold text-slate-900 dark:text-white">
            Upload Performance & Operational Files
          </h3>
          <p className="text-xs text-slate-400 max-w-sm mt-1 mb-4">
            Supports .CSV, .XLSX, and .JSON. Automatically detects metric headers, validates value ranges, and generates data lineage tags.
          </p>
          <label className="cursor-pointer px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-sm transition-all">
            {uploading ? 'Validating Dataset...' : 'Choose File to Ingest'}
            <input
              type="file"
              accept=".csv,.xlsx,.xls,.json"
              onChange={handleFileUpload}
              disabled={uploading}
              className="hidden"
            />
          </label>
        </div>

        {/* Ingestion Summary Card */}
        <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm flex flex-col justify-between">
          <div>
            <h4 className="text-xs font-bold text-slate-400 uppercase">
              Canonical Ingestion Summary
            </h4>
            <div className="my-3">
              <span className="text-3xl font-extrabold text-slate-900 dark:text-white">
                {canonicalRecords.length}
              </span>
              <span className="text-xs text-slate-400 ml-1.5">Active KPI Records</span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Validated against contractual SLAs and financial ledgers for <strong>{reportingPeriod}</strong>.
            </p>
          </div>
          <div className="pt-3 border-t border-slate-100 dark:border-slate-800 text-[11px] text-emerald-600 dark:text-emerald-400 font-semibold flex items-center gap-1.5">
            <CheckCircle size={14} /> 100% Data Lineage Maintained
          </div>
        </div>
      </div>

      {/* Canonical Records Table */}
      <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Database size={16} className="text-blue-500" />
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">
              Canonical KPI Records & Evidence Lineage
            </h3>
          </div>

          <div className="flex items-center gap-2">
            <div className="relative">
              <Search size={14} className="absolute left-2.5 top-2.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search KPI or stream..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-8 pr-3 py-1.5 text-xs rounded-md border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none"
              />
            </div>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="text-xs px-2.5 py-1.5 rounded-md border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none"
            >
              <option value="all">All Categories</option>
              <option value="SLA">SLA</option>
              <option value="Financial">Financial</option>
              <option value="Customer">Customer</option>
              <option value="Delivery">Delivery</option>
            </select>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-400 font-semibold">
                <th className="pb-2.5 pl-2">Metric Name</th>
                <th className="pb-2.5">Category</th>
                <th className="pb-2.5">Actual Value</th>
                <th className="pb-2.5">Target Value</th>
                <th className="pb-2.5">Workstream</th>
                <th className="pb-2.5">Source Evidence Lineage</th>
                <th className="pb-2.5 pr-2">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
              {filteredRecords.map((r) => (
                <tr key={r.record_id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                  <td className="py-2.5 pl-2 font-semibold text-slate-800 dark:text-slate-100">
                    {r.metric_name}
                  </td>
                  <td className="py-2.5">
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                      {r.metric_category}
                    </span>
                  </td>
                  <td className="py-2.5 font-bold text-slate-900 dark:text-white">
                    {r.actual_value} {r.unit}
                  </td>
                  <td className="py-2.5 text-slate-500">
                    {r.target_value} {r.unit}
                  </td>
                  <td className="py-2.5 text-slate-600 dark:text-slate-300">
                    {r.workstream}
                  </td>
                  <td className="py-2.5 text-[11px] text-blue-600 dark:text-blue-400 font-mono">
                    {r.source_file} (Row {r.source_row}, {r.source_cell})
                  </td>
                  <td className="py-2.5 pr-2">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                      r.data_quality_status === 'valid'
                        ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-400'
                        : 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-400'
                    }`}>
                      {r.data_quality_status}
                    </span>
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
