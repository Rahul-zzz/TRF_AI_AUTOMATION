# TR AI Operations Platform — Version 0.1 (Local Tracking MVP)

**Intelligent Logistics Operations & Daily Review System**
Built for: TR Finished Vehicles Logistics Solutions Limited

## 1. What this is

A local, modular internal operations platform. This version (0.1) fully
implements the **Tracking** module only. POD, Accounts and HR are visible
in navigation but display "Coming Soon" — no fake data or fake metrics
are shown anywhere in the app.

This app runs **alongside** the existing Digital ASPL ERP, not in place
of it, and requires no hosting — everything runs on your machine against
a local SQLite database.

## 2. Business objective

Automate the manual review the Tracking team currently does on branch
Excel reports: consolidating ~7-8 branch files, spotting accidents,
delays, GPS failures, stationary vehicles, and unloading/transit issues,
and producing a structured daily review — without an LLM guessing at
what counts as "critical." All alert logic is explicit, rule-based, and
configurable.

## 3. Architecture

```
Presentation      pages/*.py (Streamlit) + app.py (Home dashboard)
        |
Module layer      modules/tracking/*  — pure Python, no Streamlit imports,
                   fully unit-testable (column mapping, validation,
                   processing, alert rules, analytics, reports, synthetic data)
        |
Service layer     services/*  — daily_review, file_manager,
                   ai_service (stub), gmail_service (stub)
        |
Database layer     database/*  — SQLAlchemy models + operations, SQLite
```

POD/Accounts/HR each get a `modules/<name>/placeholder.py` and a
one-line "Coming Soon" page. When one of those departments is scoped for
real, give it the same shape as `modules/tracking/` and it plugs into
the same platform without touching Tracking.

## 4. Technology

Python 3.x · Streamlit · pandas · openpyxl · SQLite via SQLAlchemy ·
Plotly (charts) · ReportLab (PDF export) · pytest.

## 5. Folder structure

```
tr-ai-operations/
├── app.py                     Home dashboard entry point
├── requirements.txt
├── README.md
├── .gitignore
├── .env.example
├── config/settings.py         PROTOTYPE alert thresholds (env-overridable)
├── database/                  models.py, database.py, operations.py
├── modules/
│   ├── tracking/               column_mapping, validation, processor,
│   │                            alerts, alert_runner, analytics, reports,
│   │                            synthetic_data
│   ├── pod/placeholder.py
│   ├── accounts/placeholder.py
│   └── hr/placeholder.py
├── services/                  ai_service, gmail_service, daily_review, file_manager
├── pages/                     1_Tracking, 2_POD, 3_Accounts, 4_HR,
│                                5_Daily_Review, 6_Settings
├── data/{demo,uploads,processed,exports}
├── tests/                     pytest suite (22 tests)
└── utils/                     constants.py, helpers.py
```

## 6. Installation

```bash
cd tr-ai-operations
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
```

(Optional) copy `.env.example` to `.env` and adjust thresholds/database
path — the app works fine with the defaults if you skip this.

## 7. Running locally

```bash
streamlit run app.py
```

Open the URL Streamlit prints (typically http://localhost:8501).

## 8. Testing with data — no real file needed yet

1. Go to **Tracking → 🧬 Synthetic Demo Data**.
2. Choose **Single file** (one branch, quick test) or **Multi-branch**
   (one `.xlsx` per branch, zipped — tests real consolidation).
3. Click **Generate**, then download the file(s). Every synthetic file
   is watermarked `SYNTHETIC DEMO DATA — NOT REAL COMPANY DATA` and its
   upload batch is flagged `is_synthetic=True` in the database — it is
   never treated as, or mixed with, real company data.
4. Go to **Tracking → 📤 Upload & Process**, upload the file(s) (leave
   "synthetic/demo data" checked), and click **Process Files**.
5. Check **📊 Dashboard**, **🚨 Alerts**, **🔍 Vehicle Search**,
   **🏢 Branch Analytics**, **🧪 Data Quality**.
6. Go to **Daily Review**, pick today's date, click **Generate Daily
   Review**, and export it as PDF or JSON.

When a real branch Excel file is available, upload it the same way —
the pipeline doesn't distinguish between the two except for the
`is_synthetic` flag you can uncheck.

## 9. Excel format

The Tracking Excel must contain (at minimum) **Carrier Number**,
**Vehicle Category**, and **Vehicle Status**; the other 23 columns from
the original spec are recognized when present. Minor header variations
are handled by `modules/tracking/column_mapping.py` (e.g. "Carrier No.",
"carrier_number", "Carrier  Number" all map to the same field). Columns
that can't be matched are **kept, not discarded**, and reported as
"unmapped" so the mapping table can be extended rather than silently
losing data.

## 10. Alert rules — PROTOTYPE, not official policy

Every threshold in `config/settings.py` (`AlertThresholds`) is a
prototype assumption and is labeled as such throughout the UI
(Settings page, alert messages). Categories implemented:

Accident (keyword match on Remarks/Status — always flagged for human
verification, never auto-confirmed) · GPS Issue · Unloading Delay ·
Excessive Days at Location · Transit Delay · Tracking Inactivity ·
Stationary Vehicle · Route Issue (incomplete route info) · Data Quality.

**Fuel Inefficiency** is architected (see `AlertCategory.FUEL_INEFFICIENCY`)
but intentionally not calculated — the current Excel format doesn't
carry sufficient fuel data.

Thresholds can be changed without touching code via environment
variables (see `.env.example`) or by editing `config/settings.py`.

## 11. Database

SQLite (default path `data/tr_operations.db`), created automatically on
first run. `tracking_records` is **append-only** — a new upload never
deletes or overwrites a previous day's records, so historical trend
analysis stays possible. Possible duplicate uploads (same carrier
number + load date + branch, within a configurable window) are flagged
in the validation results but still inserted — nothing is silently
dropped.

## 12. Future Gmail integration (not implemented)

`services/gmail_service.py` documents the intended flow (OAuth →
identify branch report emails → download attachment → validate →
process → store) and currently raises `NotImplementedError` on every
call. No Gmail password is ever requested or stored — future auth will
use OAuth only.

## 13. Future AI integration (not implemented)

`services/ai_service.py` defines the interface a real assistant will
eventually implement (`ask_question`, `summarize_tracking`,
`explain_alert`, `generate_daily_review`, etc.). Every method currently
returns a plain "AI Assistant — Integration Pending" string — nothing
here fabricates an AI answer.

## 14. Future departments (not implemented)

POD, Accounts, HR each have a `modules/<name>/placeholder.py` returning
`{"implemented": False, "status": "Coming Soon..."}` and a page that
displays exactly that. The 4 PM company-wide Daily Review architecture
(`services/daily_review.py`) already reserves sections for these three
departments and marks them "Coming Soon" rather than inventing figures.

## 15. Known limitations

- Single-user, no authentication — the `users` table exists in the
  schema for future attribution but isn't enforced yet.
- Branch detection uses the mode of "Entered By Branch" per **file**
  (i.e. it assumes one file = one branch, which matches how branch
  exports actually work) — a single file mixing several branches will
  need manual per-row handling, which isn't built yet.
- Route Issue detection only checks for missing/incomplete route
  fields — it cannot detect actual GPS route deviation, since the
  current dataset has no continuous GPS telemetry.
- Fuel Inefficiency detection is not calculated (see §10).
- Gmail and real AI integration are architected but not implemented.
- Settings page is read-only in this version (thresholds are changed
  via `.env` / environment variables, not a database-backed UI yet).
- Accident detection is keyword-based on free text and will have false
  positives/negatives — every hit is explicitly labeled "Human
  Verification Required," never auto-confirmed.

## 16. Testing

```bash
pytest tests/ -v
```

22 tests cover column mapping/normalization, row-level validation
(including duplicate/negative/invalid-date detection), every alert
rule and its priority classification, database insertion and
historical-record retention (including duplicate-upload handling), and
daily review generation (including the "Data not available." path when
no data exists).

## 17. Suggested next development step

With Tracking validated against a **real** branch file, the most
valuable next steps are: (a) scope and build POD following the same
module shape, since POD status commonly gates delivery confirmation
close behind Tracking; (b) turn the Settings page from read-only into a
database-backed threshold editor so operations staff can tune alert
rules themselves; (c) once thresholds are validated by staff, revisit
whether Fuel Inefficiency and Gmail integration have enough real data
and access to implement.
