import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { ExecutiveOverview } from './pages/ExecutiveOverview';
import { QbrWorkspace } from './pages/QbrWorkspace';
import { DataStudio } from './pages/DataStudio';
import { KpiSlaIntelligence } from './pages/KpiSlaIntelligence';
import { FinancialIntelligence } from './pages/FinancialIntelligence';
import { ProjectGovernance } from './pages/ProjectGovernance';
import { HistoricalCommitments } from './pages/HistoricalCommitments';
import { RaidRegister } from './pages/RaidRegister';
import { AiInsightsCenter } from './pages/AiInsightsCenter';
import { CustomerQaWarRoom } from './pages/CustomerQaWarRoom';
import { ScenarioForecastLab } from './pages/ScenarioForecastLab';
import { PresentationStudio } from './pages/PresentationStudio';
import { ReportsExports } from './pages/ReportsExports';
import { ActionDecisionRegister } from './pages/ActionDecisionRegister';
import { AgentOperationsCenter } from './pages/AgentOperationsCenter';
import { AuditEvidenceExplorer } from './pages/AuditEvidenceExplorer';
import { SettingsIntegrations } from './pages/SettingsIntegrations';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<ExecutiveOverview />} />
          <Route path="workspace" element={<QbrWorkspace />} />
          <Route path="data-studio" element={<DataStudio />} />
          <Route path="kpi-sla" element={<KpiSlaIntelligence />} />
          <Route path="financials" element={<FinancialIntelligence />} />
          <Route path="projects" element={<ProjectGovernance />} />
          <Route path="commitments" element={<HistoricalCommitments />} />
          <Route path="raid" element={<RaidRegister />} />
          <Route path="insights" element={<AiInsightsCenter />} />
          <Route path="qa-war-room" element={<CustomerQaWarRoom />} />
          <Route path="scenarios" element={<ScenarioForecastLab />} />
          <Route path="presentation-studio" element={<PresentationStudio />} />
          <Route path="reports" element={<ReportsExports />} />
          <Route path="actions-decisions" element={<ActionDecisionRegister />} />
          <Route path="agent-ops" element={<AgentOperationsCenter />} />
          <Route path="audit" element={<AuditEvidenceExplorer />} />
          <Route path="settings" element={<SettingsIntegrations />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;
