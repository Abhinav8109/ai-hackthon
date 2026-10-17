import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Sparkles,
  Database,
  BarChart3,
  DollarSign,
  FolderKanban,
  History,
  ShieldAlert,
  BrainCircuit,
  MessageSquareWarning,
  Sliders,
  Presentation,
  FileDown,
  CheckSquare,
  Bot,
  SearchCheck,
  Settings,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

const navSections = [
  {
    title: 'Executive Command',
    items: [
      { name: 'Executive Overview', path: '/', icon: LayoutDashboard },
      { name: 'QBR Workspace', path: '/workspace', icon: Sparkles },
      { name: 'AI Insights Center', path: '/insights', icon: BrainCircuit },
    ]
  },
  {
    title: 'Data & Analytics',
    items: [
      { name: 'Data Studio', path: '/data-studio', icon: Database },
      { name: 'KPI & SLA Intelligence', path: '/kpi-sla', icon: BarChart3 },
      { name: 'Financial Intelligence', path: '/financials', icon: DollarSign },
      { name: 'Scenario & Forecast Lab', path: '/scenarios', icon: Sliders },
    ]
  },
  {
    title: 'Program Governance',
    items: [
      { name: 'Project Governance', path: '/projects', icon: FolderKanban },
      { name: 'Historical Commitments', path: '/commitments', icon: History },
      { name: 'RAID & Risk Register', path: '/raid', icon: ShieldAlert },
      { name: 'Actions & Decisions', path: '/actions-decisions', icon: CheckSquare },
    ]
  },
  {
    title: 'Executive Rehearsal & Decks',
    items: [
      { name: 'Customer Q&A War Room', path: '/qa-war-room', icon: MessageSquareWarning },
      { name: 'Presentation Studio', path: '/presentation-studio', icon: Presentation },
      { name: 'Reports & Exports', path: '/reports', icon: FileDown },
    ]
  },
  {
    title: 'Platform & Operations',
    items: [
      { name: 'Agent Operations Center', path: '/agent-ops', icon: Bot },
      { name: 'Audit & Evidence Explorer', path: '/audit', icon: SearchCheck },
      { name: 'Settings & Integrations', path: '/settings', icon: Settings },
    ]
  }
];

export const Sidebar: React.FC<SidebarProps> = ({ collapsed, onToggle }) => {
  return (
    <aside
      className={`relative flex flex-col border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 transition-all duration-300 ease-in-out z-30 ${
        collapsed ? 'w-20' : 'w-64'
      }`}
    >
      {/* Brand Header */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-slate-200 dark:border-slate-800">
        {!collapsed && (
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold text-sm shadow-sm">
              360
            </div>
            <div>
              <h1 className="font-bold text-sm tracking-tight text-slate-900 dark:text-white leading-tight">
                QBR Intelligence
              </h1>
              <p className="text-[10px] text-blue-600 dark:text-blue-400 font-semibold tracking-wider uppercase">
                Enterprise 360
              </p>
            </div>
          </div>
        )}
        {collapsed && (
          <div className="w-8 h-8 mx-auto rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold text-sm">
            360
          </div>
        )}
        <button
          onClick={onToggle}
          className="p-1.5 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
          title={collapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
        >
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>

      {/* Navigation Links */}
      <div className="flex-1 overflow-y-auto py-3 px-3 space-y-6">
        {navSections.map((section, idx) => (
          <div key={idx} className="space-y-1">
            {!collapsed && (
              <h3 className="px-3 text-[11px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                {section.title}
              </h3>
            )}
            {section.items.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                      isActive
                        ? 'bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-400 font-semibold'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-slate-200 dark:hover:bg-slate-800/60'
                    } ${collapsed ? 'justify-center px-0' : ''}`
                  }
                  title={collapsed ? item.name : undefined}
                >
                  <Icon size={18} className="shrink-0" />
                  {!collapsed && <span className="truncate">{item.name}</span>}
                </NavLink>
              );
            })}
          </div>
        ))}
      </div>

      {/* Footer Info */}
      {!collapsed && (
        <div className="p-3 border-t border-slate-200 dark:border-slate-800 text-[11px] text-slate-400">
          <p className="font-semibold text-slate-600 dark:text-slate-300">v1.0.0 Production</p>
          <p className="truncate">Connected: cloudopsworks</p>
        </div>
      )}
    </aside>
  );
};
