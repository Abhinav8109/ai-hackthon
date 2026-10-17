# QBR Intelligence 360
> **From Operational Data to Executive Decisions.**
> Agentic AI-Powered Quarterly Business Review, Program Governance, Financial Intelligence, and Executive Decision Platform.

[![Build & Tests](https://img.shields.io/badge/Tests-24%2F24%20Passed-emerald)](backend/tests)
[![Frontend](https://img.shields.io/badge/Frontend-React%2018%20%2B%20TypeScript%20%2B%20Tailwind-blue)](frontend)
[![Backend](https://img.shields.io/badge/Backend-FastAPI%20%2B%20Pydantic%20v2-teal)](backend)
[![Export](https://img.shields.io/badge/Export-Verified%20python--pptx-indigo)](backend/services/presentation.py)
[![Cloud](https://img.shields.io/badge/Cloud-Google%20Cloud%20Run-blue)](Dockerfile)

---

## 1. Product Overview

Preparing a Quarterly Business Review (QBR) conventionally takes days of manual spreadsheet consolidation, KPI reconciliation, SLA breach calculations, financial exposure audits, commitment tracking, slide formatting, and anticipating adversarial customer inquiries.

**QBR Intelligence 360** transforms this fragmented process into an autonomous, evidence-backed workflow:
- **Python Deterministic Math Engine:** Calculations (QoQ variances, budget variances, gross margins, penalty step schedules) are computed deterministically by verified Python functions—never fabricated by LLM arithmetic.
- **Genuine Multi-Agent Orchestration:** Coordinates 9 specialist agents (Data Quality, KPI Analyst, Governance, Historical, Narrative, Customer Q&A Coach, Chart Insight, Critic/Evidence Validator, Presentation Agent) executing typed tool calls with full input/output transparency.
- **Strict Evidence Lineage:** Preserves row-level citations (`source_file → worksheet → row/cell → canonical record → calculation → executive claim`).
- **Verifiable PowerPoint Studio:** Generates authentic `.pptx` presentation decks compiled via `python-pptx`, validated on disk, and ready for instant executive download.
- **Customer Q&A War Room:** Prepares leaders for 8–10 tough stakeholder questions, diplomatic framing recommendations, and talking point ratification.
- **Scenario & What-If Lab:** Real-time simulation of operational trade-offs (SLA recovery, cost reduction, milestone acceleration, penalty relief).

---

## 2. Technology Architecture

### Frontend
- **Framework:** React 18 with TypeScript and Vite
- **Styling & UI:** Tailwind CSS, Lucide icons, Dark/Light theme switching
- **Data Visualizations:** Recharts (Line, Bar, Area charts)
- **Navigation:** React Router v6 (17 integrated views)
- **State & Data Fetching:** Typed REST client with auto-proxying

### Backend
- **Framework:** FastAPI & Uvicorn (Python 3.12/3.14)
- **Validation:** Pydantic v2 schemas (`CanonicalKPIRecord`, `ValidationReport`, `Project`, `Milestone`, `RAIDItem`, etc.)
- **Tabular Data & Document Parsing:** Pandas, OpenPyXL, PyPDF, python-docx, python-pptx
- **Persistence:** SQLite repository abstraction with full relational schemas
- **Testing:** Automated test suite with `pytest` (24 verified unit and integration tests)

---

## 3. Product Modules (17 Implemented Views)

| # | Module | Key Capabilities |
|---|---|---|
| 1 | **Executive Overview** | Program health gauge (85/100), SLA trends, budget variance, milestone status, executive alerts feed |
| 2 | **QBR Workspace** | End-to-end 7-stage multi-agent orchestration pipeline with live execution states & narrative synthesis |
| 3 | **Data Studio** | File upload (.csv, .xlsx, .json), auto-column mapping, validation report, and canonical lineage table |
| 4 | **KPI & SLA Intelligence** | QoQ variances, metric directionality (higher vs lower is better), penalty rules engine & contract audit |
| 5 | **Financial Intelligence** | Approved budget, planned vs actual spend, gross margin %, budget utilization %, formula breakdown |
| 6 | **Project Governance** | Portfolio delivery confidence, project cards, milestone timeline progress bars, recovery plans |
| 7 | **Historical Commitments** | Document text extraction per page/slide, deterministic chunk search, prior commitment register |
| 8 | **RAID Register** | 5x5 impact × likelihood risk scoring, critical/high/medium classification, new RAID item modal |
| 9 | **AI Insights Center** | Categorization of verified facts vs analytical interpretations vs human recommendations |
| 10 | **Customer Q&A War Room** | 5–10 adversarial stakeholder questions, evidence coverage indicator, editable talking points |
| 11 | **Scenario & Forecast Lab** | Interactive sliders for SLA recovery, cost reduction, schedule compression, and penalty relief |
| 12 | **Presentation Studio** | Deck length & executive tone selector, slide outline preview, direct python-pptx generator |
| 13 | **Reports & Exports** | Download center for verified `.pptx` decks and audit packages |
| 14 | **Actions & Decisions** | Operational corrective actions (status toggling) and ratified customer decision logs |
| 15 | **Agent Operations Center** | Live tool call execution graph, typed input/output inspector, and Critic audit notes |
| 16 | **Audit Evidence Explorer** | Searchable row & cell lineage table tracking executive claims to source spreadsheet origins |
| 17 | **Settings & Integrations** | Google Cloud Run status, Gemini API configuration, database health, and 1-click Demo Reset |

---

## 4. Five-Minute Live Demonstration Script

### Minute 1 — Executive Overview
- Launch application at `http://localhost:8000`.
- Highlight **Overall Program Health (85/100)**, **Availability SLA Breach (98.8% vs 99.5%)**, and **Spend Variance (+$75,000)**.
- Note the **"Synthetic Demo Benchmark Active"** indicator and clean dark/light theme toggle.

### Minute 2 — Deterministic Evidence & Financial Penalties
- Navigate to **KPI & SLA Intelligence**.
- Show the **Contractual SLA Penalty Breakdown** card:
  - Breach: 98.8% vs 99.5% target (-0.7% gap = 7 steps of 0.1% @ $5,000/step).
  - Effective Liability: **$35,000** capped under MSA Schedule 4.2.
  - Drill into the exact Python formula breakdown and source lineage citation (`synthetic_q3_sla_telemetry.csv`, Row 2).

### Minute 3 — Multi-Agent Orchestration & Critic Verification
- Navigate to **QBR Workspace** and click **"Execute Full QBR Workflow"**.
- Watch the 7 specialist agent stages execute in sequence:
  `Data Quality → Deterministic Analytics → Governance → Historical Retrieval → Narrative Synthesis → Q&A Coach → Critic Audit`.
- Inspect the **Critic & Evidence Validator** tab to confirm 100% of claims are mathematically grounded.

### Minute 4 — Customer Q&A War Room
- Open **Customer Q&A War Room**.
- Select Question 1: *"Why did platform availability drop to 98.8% against the 99.5% contractual SLA?"*.
- Review the **Complete Evidence Coverage**, recommended diplomatic phrasing, and click **"Approve Talking Point"**.

### Minute 5 — Presentation Studio & PowerPoint Download
- Navigate to **Presentation Studio**.
- Select tone *"Objective & Transparent"* and click **"Generate PowerPoint (.pptx)"**.
- Download and open the resulting `.pptx` file in Microsoft PowerPoint to verify real enterprise slides, formatted tables, and validated charts.

---

## 5. Verification & Test Suite

All 24 automated backend unit and integration tests pass cleanly:

```bash
python -m pytest backend/tests
```

```text
backend\tests\test_analytics.py ........                                 [ 33%]
backend\tests\test_api.py ......                                         [ 58%]
backend\tests\test_data_ingestion.py ...                                 [ 70%]
backend\tests\test_governance.py ...                                     [ 83%]
backend\tests\test_historical.py ..                                      [ 91%]
backend\tests\test_orchestrator.py .                                     [ 95%]
backend\tests\test_presentation.py .                                     [100%]

============================= 24 passed in 2.84s ==============================
```

Frontend production bundle verification:

```bash
cd frontend && npm run build
```

```text
✓ built in 8.92s
dist/index.html                   0.77 kB
dist/assets/index-WX8iXKvK.css   31.39 kB
dist/assets/index-DmPqSnjU.js   694.48 kB
```

---

## 6. Local Quickstart

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm

### 1. Run Unified Application
```bash
# From workspace root
python -m backend.app
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser. The backend automatically serves the compiled frontend and all REST endpoints.

---

## 7. Google Cloud Run Deployment

Google Cloud deployment is configured for project **`cloudopsworks-511015`**:

```bash
# Using PowerShell
./deploy_gcloud.ps1 -ProjectId "cloudopsworks-511015" -Region "us-central1"

# Or using Bash
./deploy_gcloud.sh "cloudopsworks-511015" "us-central1"
```

Cloud Build automatically builds the multi-stage Docker container and deploys it to Cloud Run with zero downtime.
