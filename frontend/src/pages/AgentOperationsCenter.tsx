import React, { useState, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import {
  Bot,
  Terminal,
  ShieldCheck,
  CheckCircle2,
  Clock,
  Play,
  RotateCcw,
  Cpu,
  Layers
} from 'lucide-react';
import { api } from '../api/client';
import { AgentRunRecord, AgentToolCall } from '../types';

export const AgentOperationsCenter: React.FC = () => {
  const { reportingPeriod, showToast } = useOutletContext<{
    reportingPeriod: string;
    showToast: (msg: string) => void;
  }>();

  const [runRecord, setRunRecord] = useState<AgentRunRecord | null>(null);
  const [selectedToolCall, setSelectedToolCall] = useState<AgentToolCall | null>(null);

  const loadData = () => {
    api.getLatestAgentRun().then((data) => {
      setRunRecord(data);
      if (data.tool_calls.length > 0 && !selectedToolCall) {
        setSelectedToolCall(data.tool_calls[0]);
      }
    }).catch(console.error);
  };

  useEffect(() => {
    loadData();
  }, [reportingPeriod]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1 rounded bg-blue-100 dark:bg-blue-950 text-blue-600 dark:text-blue-400">
              <Bot size={18} />
            </span>
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
              Agent Operations & Traceability Center
            </h2>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Real-time multi-agent execution telemetry, typed tool parameters, observable handoffs, and verification verdicts.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Tool Invocations List (5 cols) */}
        <div className="lg:col-span-5 p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
              <Terminal size={15} />
              <span>Tool Call Traces ({runRecord?.tool_calls.length || 0})</span>
            </h3>
            <span className="text-[10px] font-semibold text-emerald-600 bg-emerald-50 dark:bg-emerald-950 px-2 py-0.5 rounded">
              Verified Sandboxed
            </span>
          </div>

          <div className="space-y-2">
            {runRecord?.tool_calls.map((call, idx) => {
              const isSelected = selectedToolCall?.tool_name === call.tool_name && selectedToolCall?.timestamp === call.timestamp;
              return (
                <div
                  key={idx}
                  onClick={() => setSelectedToolCall(call)}
                  className={`p-3 rounded-lg border text-xs cursor-pointer transition-all ${
                    isSelected
                      ? 'border-blue-600 bg-blue-50/60 dark:bg-blue-950/40 shadow-sm'
                      : 'border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-850 hover:border-slate-300'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-mono font-bold text-blue-600 dark:text-blue-400">
                      {call.tool_name}()
                    </span>
                    <span className="text-[10px] font-bold text-emerald-600 uppercase">
                      {call.status}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-slate-400">
                    <span>{call.agent_name}</span>
                    <span>{new Date(call.timestamp).toLocaleTimeString()}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Tool Call Inspector (7 cols) */}
        {selectedToolCall && (
          <div className="lg:col-span-7 p-6 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                  Tool Call Execution Detail
                </span>
                <h4 className="text-base font-bold font-mono text-slate-900 dark:text-white mt-0.5">
                  {selectedToolCall.tool_name}
                </h4>
              </div>
              <span className="text-xs text-slate-400">
                Agent: <strong>{selectedToolCall.agent_name}</strong>
              </span>
            </div>

            {/* Parameters */}
            <div className="space-y-1.5">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                Input Parameters
              </span>
              <pre className="p-3 rounded-lg bg-slate-900 text-slate-200 text-xs font-mono overflow-x-auto max-h-40">
                {JSON.stringify(selectedToolCall.input_params, null, 2)}
              </pre>
            </div>

            {/* Output Result */}
            <div className="space-y-1.5">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                Tool Output Result (Verified Ground Truth)
              </span>
              <pre className="p-3 rounded-lg bg-slate-900 text-emerald-400 text-xs font-mono overflow-x-auto max-h-56">
                {JSON.stringify(selectedToolCall.output_result, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
