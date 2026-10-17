import React, { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Navbar } from './Navbar';

export const Layout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [reportingPeriod, setReportingPeriod] = useState('2026-Q3');
  const [notification, setNotification] = useState<string | null>(null);

  // Toggle theme class on document element
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);

  const showToast = (msg: string) => {
    setNotification(msg);
    setTimeout(() => setNotification(null), 4000);
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-50 dark:bg-slate-950 font-sans">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} />
      
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Navbar
          darkMode={darkMode}
          onToggleTheme={() => setDarkMode(!darkMode)}
          reportingPeriod={reportingPeriod}
          onPeriodChange={(p) => setReportingPeriod(p)}
          onNotification={showToast}
        />

        {/* Global Toast */}
        {notification && (
          <div className="fixed bottom-6 right-6 z-50 px-4 py-2.5 rounded-lg bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 text-xs font-semibold shadow-lg transition-all animate-bounce">
            {notification}
          </div>
        )}

        {/* Main Content Area */}
        <main className="flex-1 overflow-y-auto p-6 md:p-8">
          <Outlet context={{ reportingPeriod, showToast }} />
        </main>
      </div>
    </div>
  );
};
