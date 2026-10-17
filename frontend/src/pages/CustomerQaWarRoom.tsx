import React, { useState, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import {
  MessageSquareWarning,
  CheckCircle2,
  AlertCircle,
  Edit3,
  Save,
  RotateCcw,
  Sparkles,
  ShieldCheck,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { api } from '../api/client';
import { QAItemType } from '../types';

export const CustomerQaWarRoom: React.FC = () => {
  const { reportingPeriod, showToast } = useOutletContext<{
    reportingPeriod: string;
    showToast: (msg: string) => void;
  }>();

  const [qaItems, setQaItems] = useState<QAItemType[]>([]);
  const [selectedItem, setSelectedItem] = useState<QAItemType | null>(null);
  const [editedAnswer, setEditedAnswer] = useState('');
  const [rehearsalNotes, setRehearsalNotes] = useState('');
  const [regenerating, setRegenerating] = useState(false);

  const loadQA = () => {
    api.getQAItems().then((items) => {
      setQaItems(items);
      if (items.length > 0 && !selectedItem) {
        setSelectedItem(items[0]);
        setEditedAnswer(items[0].user_edited_answer || items[0].recommended_answer);
      }
    }).catch(console.error);
  };

  useEffect(() => {
    loadQA();
  }, [reportingPeriod]);

  const handleSelect = (item: QAItemType) => {
    setSelectedItem(item);
    setEditedAnswer(item.user_edited_answer || item.recommended_answer);
  };

  const handleApprove = async () => {
    if (!selectedItem) return;
    try {
      await api.approveQA(selectedItem.id, editedAnswer);
      showToast(`Talking point approved for ${selectedItem.id}`);
      loadQA();
    } catch (e) {
      showToast('Failed to approve talking point.');
    }
  };

  const handleRegenerate = async () => {
    setRegenerating(true);
    showToast('Re-generating challenging customer questions from active data...');
    try {
      await api.generateQA(reportingPeriod);
      loadQA();
      showToast('Generated fresh questions backed by active telemetry.');
    } catch (e) {
      showToast('Generation failed.');
    } finally {
      setRegenerating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1 rounded bg-amber-100 dark:bg-amber-950 text-amber-600 dark:text-amber-400">
              <MessageSquareWarning size={18} />
            </span>
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
              Customer Q&A War Room
            </h2>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Simulate and rehearse challenging executive stakeholder inquiries backed by deterministic figures and diplomatic responses.
          </p>
        </div>

        <button
          onClick={handleRegenerate}
          disabled={regenerating}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 text-xs font-semibold shadow-sm"
        >
          <RotateCcw size={14} className={regenerating ? 'animate-spin' : ''} />
          <span>{regenerating ? 'Regenerating...' : 'Regenerate Questions'}</span>
        </button>
      </div>

      {/* Main Workspace Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Question List (5 cols) */}
        <div className="lg:col-span-5 space-y-3">
          <div className="flex items-center justify-between text-xs font-bold text-slate-400 uppercase tracking-wider px-1">
            <span>Anticipated Questions ({qaItems.length})</span>
            <span>Evidence Coverage</span>
          </div>

          <div className="space-y-2.5">
            {qaItems.map((q) => {
              const isSelected = selectedItem?.id === q.id;
              return (
                <div
                  key={q.id}
                  onClick={() => handleSelect(q)}
                  className={`p-3.5 rounded-xl border text-xs cursor-pointer transition-all ${
                    isSelected
                      ? 'border-blue-600 bg-blue-50/50 dark:bg-blue-950/40 shadow-sm'
                      : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-slate-300'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-bold text-[10px] text-blue-600 dark:text-blue-400 uppercase">
                      {q.category} • {q.id}
                    </span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                      q.evidence_coverage === 'complete'
                        ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-400'
                        : 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-400'
                    }`}>
                      {q.evidence_coverage}
                    </span>
                  </div>

                  <p className="font-semibold text-slate-900 dark:text-white line-clamp-2">
                    {q.question}
                  </p>

                  <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400">
                    <span className="truncate max-w-[200px]">Why: {q.why_asked}</span>
                    {q.approved ? (
                      <span className="text-emerald-600 dark:text-emerald-400 font-bold flex items-center gap-1">
                        <CheckCircle2 size={12} /> Approved
                      </span>
                    ) : (
                      <span className="text-slate-400">Needs Review</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Selected Question Drilldown & Rehearsal (7 cols) */}
        {selectedItem && (
          <div className="lg:col-span-7 p-6 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-5">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="px-2 py-0.5 rounded text-xs font-bold uppercase bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-400">
                  {selectedItem.severity} Severity
                </span>
                <span className="text-xs text-slate-400">
                  ID: {selectedItem.id}
                </span>
              </div>
              <h3 className="text-base font-bold text-slate-900 dark:text-white">
                {selectedItem.question}
              </h3>
            </div>

            {/* Backing Evidence Box */}
            <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-xs space-y-1">
              <span className="font-bold text-slate-500 dark:text-slate-400 uppercase text-[10px]">
                Supporting KPI / Document Evidence
              </span>
              <p className="font-mono text-slate-800 dark:text-slate-200">
                {selectedItem.supporting_kpi_evidence}
              </p>
              {selectedItem.linked_commitment && (
                <p className="text-[11px] text-blue-600 dark:text-blue-400 font-semibold pt-1">
                  Linked Historical Commitment: {selectedItem.linked_commitment}
                </p>
              )}
            </div>

            {/* Diplomatic Phrasing */}
            <div className="p-3.5 rounded-lg bg-teal-50/50 dark:bg-teal-950/30 border border-teal-200 dark:border-teal-900/60 text-xs space-y-1">
              <span className="font-bold text-teal-700 dark:text-teal-400 uppercase text-[10px]">
                Diplomatic Framing Recommendation
              </span>
              <p className="text-slate-800 dark:text-slate-200 italic">
                "{selectedItem.diplomatic_phrasing}"
              </p>
            </div>

            {/* Editable Talking Point */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <label className="font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                  <Edit3 size={14} />
                  <span>Approved Executive Talking Point</span>
                </label>
                <span className="text-[11px] text-slate-400">Edit before ratification</span>
              </div>
              <textarea
                rows={4}
                value={editedAnswer}
                onChange={(e) => setEditedAnswer(e.target.value)}
                className="w-full p-3 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-blue-500 font-sans"
              />
            </div>

            {/* Actions */}
            <div className="flex items-center justify-between pt-3 border-t border-slate-100 dark:border-slate-800">
              <span className="text-xs text-slate-400">
                Evidence Coverage: <strong>{selectedItem.evidence_coverage.toUpperCase()}</strong>
              </span>
              <button
                onClick={handleApprove}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-sm transition-all"
              >
                <Save size={14} />
                <span>Approve Talking Point</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
