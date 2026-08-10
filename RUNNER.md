# Weekly Marketplace Monitoring — Monday Runner

Runs every Monday afternoon. Produces **two** situation reports for **last week (window ending the most recent Sunday)** — one for **Auto** and one for **Home** — posts both under a single weekly entry in the Notion draft page, then sends a Slack DM to Alberto. Draft-first: it appends to the private page below; do not switch to a shared/auto-publish target until Steve/Alberto signs off. Run steps 1–2 once per vertical (independently), then post both together (step 3) and notify (step 4).

**Durable locations**
- Pipeline: `tools/marketplace-monitoring/weekly_report.py` (+ `report_gen.py`); work dir `tools/marketplace-monitoring/work/`.
- Interpretation spec: `output/plans/report-interpretation-framework.md` (Annie owns it).
- Hex token: `~/.hex_token` (read, never print).
- Chrome for PDF: `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`.
- Python: `/Users/albertofalkon/.pyenv/versions/3.10.11/envs/dbt_venv/bin/python`.
- Notion draft page id: `3b8a8367-d4b2-8157-8a4a-e706bc22e9e3` ("Marketplace Monitoring — Weekly Reports (Draft)").

## Steps

**0. Compute the window end date** = most recent Sunday relative to today (a Monday → yesterday). Format `YYYY-MM-DD`. Call it `END`.

**1. Capture + first build** (recompute is ~3–5 min):
```
<python> tools/marketplace-monitoring/weekly_report.py --vertical auto --end END --lookback 7
```
This drives the public dashboard link, sets inputs, clicks Run, screenshots each tab to `work/cap_*.png`, scrapes the KPI tiles, writes `work/capture_report.json`, and builds a first PDF. Sanity-check `capture_report.json` shows `recomputed: true` and a plausible Total Revenue (Auto ≈ millions). If `recomputed:false`, re-run before continuing.

**2. Interpretation (Annie)** — spawn the Annie agent with the week's data from `work/capture_report.json` (the 12 scraped tiles + WoW%) and the cropped charts, and have her produce `work/analysis_auto_END.json` following `output/plans/report-interpretation-framework.md`. Schema:
```json
{ "exec_html": "<p>…numbers + light interpretation, GUIDE don't conclude…</p>",
  "sections": [ {"key":"overview","category":"","title":"Key Metrics Overview","what":"","why":""},
                {"key":"mix|flow|adv","category":"…","title":"…","what":"…","why":"…"} ],
  "kpi_highlights": [
    {"name":"Outcome — where revenue landed","color":"#185FA5","metrics":["Total Revenue","Ad Revenue","Sale Revenue"]},
    {"name":"Volume — <week-specific role>","color":"#BA7517","metrics":["Visits","Flow Starts","Ad Clicks"]},
    {"name":"Per-visit monetization — <week-specific role>","color":"#0F6E56","metrics":["RPV","Ad RPV","Ad RPC"]} ] }
```
Run Annie SEPARATELY per vertical — Auto and Home get fully independent selections (different lead chart, count, order, and greyed tiles are all expected). Never copy one vertical's sections onto the other; each is chosen only from its own numbers.

`kpi_highlights` color-groups ONLY the tiles that drive THIS week's story on the page-1 Key Metrics Overview (tiles not listed stay grey). Keep the 3 fixed colors (blue outcome / amber volume / teal monetization) but WRITE THE GROUP NAME to fit the week (e.g. monetization "— what cushioned it" when it rose, "— also softened" when it fell). Include only the groups that matter; you may list fewer metrics if only some are relevant.
Order the diagnostic sections by relevance to THIS week (drop flat/immaterial ones). Then rebuild from the same captures:
```
<python> tools/marketplace-monitoring/weekly_report.py --vertical auto --end END --lookback 7 --build-only
```
Output: `work/Marketplace_Monitoring_Auto_END_real.pdf`. (QL auto-skips if its dashboard cell errors; that's expected.)

**3. Post to Notion** (uses the Notion connector — no separate token). Upload BOTH PDFs, then append ONE weekly entry with an Auto and a Home subsection:
1. For each vertical: `notion-create-file-upload` with filename `Marketplace_Monitoring_<Vtitle>_END.pdf` → returns `upload_url`, `upload_headers.authorization`, `file_upload_id`.
2. For each: `curl -s -X POST "<upload_url>" -H "authorization: <auth>" -F "file=@work/Marketplace_Monitoring_<Vtitle>_END_real.pdf;type=application/pdf"` → confirm `"status":"uploaded"`.
3. `update-page` (command `insert_content`, position end) on page `3b8a8367-d4b2-8157-8a4a-e706bc22e9e3`, appending ONE new collapsible **toggle heading** for the week (big bold title, both verticals nested inside). The child lines MUST each be indented with a single tab so they nest inside the toggle:
   ```
   ## Week ending END {toggle="true"}
   →### Auto
   →<one-line Auto headline>
   →<pdf src="file-upload://<auto file_upload_id>"></pdf>
   →### Home
   →<one-line Home headline>
   →<pdf src="file-upload://<home file_upload_id>"></pdf>
   ```
   (Each `→` above is a literal TAB — required, or the children won't be contained in the dropdown.)

**4. Notify (Slack)** — `slack_send_message` with `channel_id` `U0BF11GFCQG` (Alberto's DM, draft phase — do NOT post to a shared channel yet). Short message: "✅ Marketplace Monitoring — week ending END is live", the Notion link `https://app.notion.com/p/3b8a8367d4b281578a4ae706bc22e9e3`, and a one-line headline for Auto and for Home. If any step failed, do NOT send — report the problem instead.

## Notes / gotchas
- Uses the **shareable link** (Testing copy) — anonymous recompute, no login, never edits the shared dashboard.
- Locked format (do not change): page 1 = Exec Summary + Key metric moves + Key Metrics Overview; then relevance-ordered diagnostic sections with what/why captions; shrink graphs so sections pack (no big mid-page gaps); no data-source names in the report text.
- Exec tone: numbers + light interpretation, **guide don't conclude**.
- Auto and Home are curated INDEPENDENTLY (see the framework's per-vertical independence rule) — different graphs/order/greyed tiles per vertical, never mirrored.
- Home: revenue ≈ ad revenue (sale side negligible → grey it); QL cell errors → skipped.
- Slack notify goes ONLY to Alberto's DM (U0BF11GFCQG) during the draft phase; switch to a stakeholder channel only after sign-off.
