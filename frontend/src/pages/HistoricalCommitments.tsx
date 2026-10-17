import React, { useState, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import {
  History,
  Search,
  Upload,
  CheckCircle2,
  AlertTriangle,
  Clock,
  FileText,
  ShieldCheck,
  ExternalLink
} from 'lucide-react';
import { api } from '../api/client';
import { CommitmentItemType } from '../types';

export const HistoricalCommitments: React.FC = () => {
  const { showToast } = useOutletContext<{ showToast: (msg: string) => void }>();
  const [commitments, setCommitments] = useState<CommitmentItemType[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);
  const [uploading, setUploading] = useState(false);

  const loadCommitments = () => {
    api.getCommitments().then(setCommitments).catch(console.error);
  };

  useEffect(() => {
    loadCommitments();
  }, []);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const res = await api.searchHistorical(searchQuery);
      setSearchResults(res.results || []);
    } catch (err) {
      showToast('Search failed.');
    } finally {
      setSearching(false);
    }
  };

  const handleDocUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    showToast(`Ingesting and indexing ${file.name}...`);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch('/api/v1/history/upload', { method: 'POST', body: formData });
      const data = await res.json();
      showToast(`Document ingested: ${data.chunks_indexed} sections indexed.`);
      loadCommitments();
    } catch (e) {
      showToast('Document ingestion failed.');
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const handleStatusChange = async (id: string, newStatus: string) => {
    try {
      await api.updateActionStatus(id, newStatus);
      showToast('Commitment status updated.');
      loadCommitments();
    } catch (e) {
      showToast('Failed to update status.');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1 rounded bg-blue-100 dark:bg-blue-950 text-blue-600 dark:text-blue-400">
              <History size={18} />
            </span>
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
              Historical QBR & Commitment Intelligence
            </h2>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Ground-truth commitment tracking: prior quarter agreements vs verifiable closure evidence with full document citations.
          </p>
        </div>

        <div>
          <label className="cursor-pointer flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-xs font-semibold text-slate-700 dark:text-slate-200 transition-all">
            <Upload size={14} />
            <span>{uploading ? 'Ingesting...' : 'Ingest Past Minutes / Deck'}</span>
            <input
              type="file"
              accept=".txt,.pdf,.docx,.pptx"
              onChange={handleDocUpload}
              disabled={uploading}
              className="hidden"
            />
          </label>
        </div>
      </div>

      {/* Historical Retrieval Search Box */}
      <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-3">
        <h3 className="text-sm font-bold text-slate-900 dark:text-white">
          Deterministic Historical Chunk Search
        </h3>
        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="relative flex-1">
            <Search size={15} className="absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search past QBR minutes (e.g. 'failover', 'database', 'SSO', 'cost reduction')..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none"
            />
          </div>
          <button
            type="submit"
            disabled={searching}
            className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shrink-0"
          >
            {searching ? 'Searching...' : 'Search Evidence'}
          </button>
        </form>

        {/* Search Results Display */}
        {searchResults.length > 0 && (
          <div className="pt-3 border-t border-slate-100 dark:border-slate-800 space-y-2">
            <span className="text-[11px] font-bold text-slate-400 uppercase">
              Top Ranked Evidence Citations
            </span>
            {searchResults.map((r, i) => (
              <div
                key={i}
                className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 text-xs space-y-1"
              >
                <div className="flex items-center justify-between font-semibold text-blue-600 dark:text-blue-400">
                  <span>{r.document_name} ({r.location})</span>
                  <span className="text-[10px] bg-blue-50 dark:bg-blue-950 px-2 py-0.5 rounded">
                    Score: {r.score}
                  </span>
                </div>
                <p className="text-slate-700 dark:text-slate-200 italic">
                  "{r.text_content}"
                </p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Commitments Tracking Table */}
      <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white">
            Historical Commitments Register
          </h3>
          <span className="text-xs text-slate-400">
            {commitments.length} Tracked Commitments
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-400 font-semibold">
                <th className="pb-2.5 pl-2">Original Commitment Wording</th>
                <th className="pb-2.5">Source Document & Location</th>
                <th className="pb-2.5">Owner</th>
                <th className="pb-2.5">Due Date</th>
                <th className="pb-2.5">Current Status</th>
                <th className="pb-2.5 pr-2">Closure Evidence</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
              {commitments.map((c) => (
                <tr key={c.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                  <td className="py-3 pl-2 font-medium text-slate-900 dark:text-slate-100 max-w-xs">
                    {c.original_wording}
                  </td>
                  <td className="py-3 text-[11px] font-mono text-blue-600 dark:text-blue-400">
                    {c.source_document} ({c.source_location})
                  </td>
                  <td className="py-3 text-slate-600 dark:text-slate-300">
                    {c.owner}
                  </td>
                  <td className="py-3 text-slate-500">
                    {c.due_date}
                  </td>
                  <td className="py-3">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                      c.current_status === 'closed_with_evidence' ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-400' :
                      c.current_status === 'at_risk' ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-400' :
                      'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-400'
                    }`}>
                      {c.current_status.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td className="py-3 pr-2 text-slate-500 text-[11px] max-w-xs">
                    {c.closure_evidence || 'No technical closure evidence provided yet.'}
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
