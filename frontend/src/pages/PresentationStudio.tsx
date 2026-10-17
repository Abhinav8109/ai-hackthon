import React, { useState } from 'react';
import { useOutletContext, useNavigate } from 'react-router-dom';
import {
  Presentation,
  Download,
  CheckCircle2,
  Sliders,
  FileCheck,
  FileText,
  Sparkles,
  ShieldCheck,
  ArrowRight
} from 'lucide-react';
import { api } from '../api/client';

export const PresentationStudio: React.FC = () => {
  const { reportingPeriod, showToast } = useOutletContext<{
    reportingPeriod: string;
    showToast: (msg: string) => void;
  }>();
  const navigate = useNavigate();

  const [programName, setProgramName] = useState('Cloud Infrastructure Modernization');
  const [customerName, setCustomerName] = useState('Enterprise Global Corp');
  const [length, setLength] = useState('standard');
  const [tone, setTone] = useState('objective_transparent');
  const [generating, setGenerating] = useState(false);
  const [lastExport, setLastExport] = useState<any | null>(null);

  const handleGenerate = async () => {
    setGenerating(true);
    showToast('Compiling verified python-pptx presentation...');
    try {
      const res = await api.generatePresentation({
        reporting_period: reportingPeriod,
        program_name: programName,
        customer_name: customerName,
        presentation_length: length,
        executive_tone: tone
      });
      setLastExport(res);
      showToast(`Presentation generated successfully: ${res.slide_count} slides verified.`);
    } catch (e) {
      showToast('Failed to compile PowerPoint deck.');
    } finally {
      setGenerating(false);
    }
  };

  const slidesOutline = [
    { num: 1, title: 'Title & Cover Slide', desc: `${programName} — Executive QBR ${reportingPeriod}` },
    { num: 2, title: 'Executive Overview & Program Health', desc: 'Health score (85/100), delivery confidence, and core operational takeaways' },
    { num: 3, title: 'SLA Performance & Penalty Audit', desc: 'Contractual SLA variance (98.8% vs 99.5%) and deterministic $35,000 penalty breakdown' },
    { num: 4, title: 'Project Delivery, Milestones & RAID', desc: 'Delayed milestone M-DEMO-01 recovery plan and critical payment gateway risks' },
    { num: 5, title: 'Customer Decisions & Q4 Roadmap', desc: 'Sponsor approval asks (change freeze Option B) and next-quarter commitments' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1 rounded bg-blue-100 dark:bg-blue-950 text-blue-600 dark:text-blue-400">
              <Presentation size={18} />
            </span>
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
              QBR Presentation Studio
            </h2>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Generate authentic Microsoft PowerPoint (.pptx) executive decks compiled directly with python-pptx and backed by validated analytical tables.
          </p>
        </div>

        <button
          onClick={handleGenerate}
          disabled={generating}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-sm transition-all disabled:opacity-50"
        >
          <Sparkles size={14} className={generating ? 'animate-spin' : ''} />
          <span>{generating ? 'Compiling Slide Deck...' : 'Generate PowerPoint (.pptx)'}</span>
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Configuration Form (5 cols) */}
        <div className="lg:col-span-5 p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white">
            Deck Configuration & Tone
          </h3>

          <div className="space-y-3 text-xs">
            <div>
              <label className="block font-medium text-slate-700 dark:text-slate-300 mb-1">Program / Transformation Name</label>
              <input
                type="text"
                value={programName}
                onChange={(e) => setProgramName(e.target.value)}
                className="w-full px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
              />
            </div>

            <div>
              <label className="block font-medium text-slate-700 dark:text-slate-300 mb-1">Customer / Sponsor Organization</label>
              <input
                type="text"
                value={customerName}
                onChange={(e) => setCustomerName(e.target.value)}
                className="w-full px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block font-medium text-slate-700 dark:text-slate-300 mb-1">Deck Length</label>
                <select
                  value={length}
                  onChange={(e) => setLength(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800"
                >
                  <option value="executive_brief">Executive Brief (3-4 slides)</option>
                  <option value="standard">Standard QBR (5-7 slides)</option>
                  <option value="deep_dive">Deep Dive Portfolio (10+ slides)</option>
                </select>
              </div>
              <div>
                <label className="block font-medium text-slate-700 dark:text-slate-300 mb-1">Executive Tone</label>
                <select
                  value={tone}
                  onChange={(e) => setTone(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800"
                >
                  <option value="objective_transparent">Objective & Transparent</option>
                  <option value="collaborative">Collaborative & Forward-Looking</option>
                  <option value="assertive_governance">Strict Contract Governance</option>
                </select>
              </div>
            </div>
          </div>

          {/* Export Success Box */}
          {lastExport && (
            <div className="p-4 rounded-xl bg-emerald-50/60 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-xs space-y-2 mt-4">
              <div className="flex items-center justify-between text-emerald-800 dark:text-emerald-300 font-bold">
                <span className="flex items-center gap-1.5">
                  <FileCheck size={16} /> Deck Verified & Ready
                </span>
                <span>{lastExport.slide_count} Slides</span>
              </div>
              <p className="text-[11px] text-slate-600 dark:text-slate-300 font-mono truncate">
                {lastExport.filename}
              </p>
              <a
                href={`/api/v1/reports/${lastExport.report_id}/download`}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs shadow-sm mt-1"
              >
                <Download size={13} />
                <span>Download Generated .pptx File</span>
              </a>
            </div>
          )}
        </div>

        {/* Right: Slide Sequence Outline (7 cols) */}
        <div className="lg:col-span-7 p-6 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">
              Generated Slide Structure & Content Blueprint
            </h3>
            <span className="text-xs text-slate-400">
              Validated 16:9 Widescreen Template
            </span>
          </div>

          <div className="space-y-3">
            {slidesOutline.map((s) => (
              <div
                key={s.num}
                className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-850 flex items-start gap-3 text-xs"
              >
                <div className="w-6 h-6 rounded bg-blue-100 dark:bg-blue-950 text-blue-600 dark:text-blue-400 flex items-center justify-center font-bold text-xs shrink-0 mt-0.5">
                  {s.num}
                </div>
                <div className="flex-1">
                  <h4 className="font-bold text-slate-900 dark:text-white">
                    {s.title}
                  </h4>
                  <p className="text-slate-500 dark:text-slate-400 mt-0.5">
                    {s.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
