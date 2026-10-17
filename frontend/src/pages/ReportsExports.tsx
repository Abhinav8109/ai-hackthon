import React, { useState, useEffect } from 'react';
import { useOutletContext, useNavigate } from 'react-router-dom';
import {
  FileDown,
  Download,
  FileCheck,
  Calendar,
  Layers,
  ArrowRight
} from 'lucide-react';
import { api } from '../api/client';
import { ReportItem } from '../types';

export const ReportsExports: React.FC = () => {
  const { reportingPeriod } = useOutletContext<{ reportingPeriod: string }>();
  const navigate = useNavigate();
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.getReports().then((data) => {
      setReports(data);
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
              <FileDown size={18} />
            </span>
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
              Executive Reports & Export Archive
            </h2>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Download center for generated PowerPoint decks, PDF summaries, and contractual audit packages.
          </p>
        </div>

        <button
          onClick={() => navigate('/presentation-studio')}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-sm"
        >
          <span>Generate New Deck</span>
          <ArrowRight size={14} />
        </button>
      </div>

      {/* Reports List */}
      <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-4">
        <h3 className="text-sm font-bold text-slate-900 dark:text-white">
          Generated Presentation Decks & Artifacts
        </h3>

        {reports.length === 0 ? (
          <div className="text-center py-12 text-slate-400 text-xs">
            No exported reports found for this period. Click 'Generate New Deck' above.
          </div>
        ) : (
          <div className="divide-y divide-slate-100 dark:divide-slate-800">
            {reports.map((r) => (
              <div
                key={r.report_id}
                className="py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
              >
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-blue-50 dark:bg-blue-950 text-blue-600 flex items-center justify-center font-bold text-xs shrink-0 mt-0.5">
                    PPTX
                  </div>
                  <div>
                    <h4 className="font-bold text-slate-900 dark:text-white">
                      {r.title}
                    </h4>
                    <p className="text-slate-400 text-[11px] mt-0.5">
                      Period: {r.reporting_period} • {r.metadata.slide_count} Verified Slides • Created: {new Date(r.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-400">
                    VERIFIED .PPTX
                  </span>
                  <a
                    href={`/api/v1/reports/${r.report_id}/download`}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 font-semibold"
                  >
                    <Download size={13} />
                    <span>Download</span>
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
