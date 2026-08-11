# Marketplace Monitoring — Weekly Report

Automated weekly report for Insurify's ad marketplace, produced separately for each vertical (**Auto** and **Home**). Each Tuesday it recomputes last week's numbers from the Marketplace Monitoring dashboard in Hex, an analyst step interprets them and selects the charts that best explain that week, and a polished PDF is generated and posted to Notion + Slack.

## What's in here
| File | Purpose |
|---|---|
| `weekly_report.py` | The pipeline: drives the dashboard in a headless browser, captures the real charts, scrapes the KPI tiles, and builds the PDF. |
| `report_gen.py` | Report layout helpers (color-grouped KPI grid, moves bar, page assembly). |
| `RUNNER.md` | The weekly runbook: the exact steps the Monday automation follows (capture → interpret → build → post to Notion → Slack). |
| `report-interpretation-framework.md` | How the analysis is done: revenue decomposition, chart-selection rules, exec-summary tone, and the color-grouping scheme. |
| `requirements.txt` | Python dependencies. |
| `work/` | Generated outputs (screenshots, PDFs, per-week analysis JSON). |

## Workflow
**1. The pipeline**: Captures the real dashboard charts and builds the PDF. Runs on its own (no Claude, no connectors needed).

**2. The full automated loop.** Adds the analyst interpretation (which charts + the written narrative), posting to Notion, the Slack notification, and the Monday schedule. This part runs inside **Claude Code** with the Notion/Slack connectors and a scheduled task; `RUNNER.md` documents it end-to-end.

## Prerequisites
- The Marketplace Monitoring dashboard **shareable link** (set as `URL` in `weekly_report.py`, no login/token is required for the capture).

## Setup
```bash
cd marketplace_monitoring_report
python -m venv .venv && source .venv/bin/activate    
pip install -r requirements.txt
python -m playwright install chromium                  # capture browser
```

## Run the pipeline
```bash
python weekly_report.py --vertical auto --end 2026-05-18 --lookback 7
```
- `--vertical` = `auto` or `home`; `--end` = window end date (a Sunday) as `YYYY-MM-DD`; `--lookback` = window length in days (7).
- Output → `work/Marketplace_Monitoring_Auto_2026-05-18_real.pdf` plus the chart screenshots in `work/`.
- The recompute takes ~3–5 min (the script sets the inputs, clicks **Run**, and verifies the numbers actually refreshed, retrying if needed).
- Add `--build-only` to rebuild the PDF from the most recent capture without re-running the dashboard.

### Interpretive vs. templated output
If `work/analysis_<vertical>_<end>.json` exists, the report uses that week's **curated** narrative, chart selection, and KPI color-groups (see `report-interpretation-framework.md`). Without it, the pipeline still produces a real report with the real charts but a **templated** summary. In the full loop, Claude Code writes that JSON each week per the framework.


## Notes for Alberto and Next Steps
- The dashboard link is the **Testing copy** (anonymous recompute, no login). Don't forget to change to the original one. 
- `RUNNER.md` references the **Alberto's** Notion page id and Slack recipient — replace those with your own targets when you run it.
- Reports are **draft-first** to a private Notion page during validation, before sharing more widely.
- Change the **Hex's API Key** to an non-expiring one. 
