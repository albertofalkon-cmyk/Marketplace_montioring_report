#!/usr/bin/env python3
"""
Marketplace Monitoring — weekly report pipeline (shareable-link / no-login path).

One re-runnable script for the Monday scheduler:
  1) open the public Hex app, set inputs (vertical, end_date, lookback), click Run,
     wait for a real recompute, and sanity-check the Total Revenue tile changed;
  2) scrape the Overview KPI tiles (value + signed WoW%) — drives the moves bar + exec headline;
  3) navigate each dashboard tab robustly (scroll + force-click + marker-verify + retries)
     and screenshot it to a real PNG; detect errored/empty cells;
  4) crop the Hex chrome + agent popup + any errored cells, and assemble a PDF
     (page 1 = overall metrics + exec summary + moves bar; then a chart per diagnostic section).

Usage:
  python weekly_report.py --vertical auto --end 2026-06-08 --lookback 7
  python weekly_report.py --build-only          # reuse existing cap_*.png + capture_report.json
"""
import sys, os, time, json, re, argparse, subprocess
_HERE=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,_HERE)
from report_gen import *
from PIL import Image, ImageDraw, ImageChops

# durable work dir next to this script (captures, analysis JSON, and output PDFs land here)
B=os.path.join(_HERE,"work")+"/"
os.makedirs(B, exist_ok=True)
URL="https://app.hex.tech/insurify/app/Marketplace-Monitoring---Testing-03434raQUqSKPMdyL648oV/latest"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# tab key -> (visible tab label, a distinctive marker that only appears once that tab is active)
TABS=[
 ("overview","Overview","Total Revenue"),
 ("flow","Flow Metrics","Revisit Rate Over Time"),
 ("adv","Bid Changes","Advertiser Bids XoX Pivot"),
 ("mix","Mix Shift","Traffic Source Mix Shift Indicator"),
 ("ql","QL Changes","Average Ads and Quotes Displayed Per QL"),
]
# fixed top->bottom, left->right order of the Overview KPI tiles
TILE_ORDER=['Total Revenue','Ad Revenue','Sale Revenue','Visits','Flow Starts',
            'RPV','Sale RPV','Ad RPV','Ad CPV','Ad Clicks','Ad RPC','Aleads']
# metrics shown on the "key metric moves" bar (subset of tiles), lower-is-worse ordering handled at sort time
MOVES_KEYS=['Flow Starts','Ad Clicks','Visits','Total Revenue','Ad CPV','Ad RPV','Ad RPC','RPV','Sale RPV']

# ---------- capture ----------
def rc(pg):
    try: return pg.get_by_text("Running...").count()
    except Exception: return 0
def wait_until(cond, tot, every=3):
    t=0
    while t<tot:
        if cond(): return True
        time.sleep(every); t+=every
    return False

def click_tab(pg, label, marker, tries=4):
    """Robustly switch tab: scroll into view, force-click, verify the marker rendered."""
    for _ in range(tries):
        try:
            el=pg.get_by_text(label, exact=True).first
            el.scroll_into_view_if_needed(timeout=4000)
            el.click(force=True, timeout=4000)
        except Exception: pass
        time.sleep(6)
        try:
            if pg.get_by_text(marker, exact=False).first.count()>0: return True
        except Exception: pass
        time.sleep(3)
    return False

def scrape_tiles(pg):
    """Read the Overview KPI tiles into {label: {'value':str,'pct':float}} using tile order."""
    txt=pg.evaluate("()=>document.body.innerText")
    pcts=re.findall(r'([↑↓]?)\s*(-?\d+(?:\.\d+)?)\s*%', txt)   # arrows ↑/↓ optional
    out={}
    for i,label in enumerate(TILE_ORDER):
        if i<len(pcts):
            arrow,num=pcts[i]; v=float(num)
            if arrow=='↓': v=-abs(v)
            elif arrow=='↑': v=abs(v)
            out[label]={'pct':v}
    for label in TILE_ORDER:   # grab each tile's big number (label appears above its value)
        m=re.search(re.escape(label)+r'\s*\n\s*(\$?[\d,\.]+[MK]?)', txt)
        if m and label in out: out[label]['value']=m.group(1)
    return out

# --- rendered KPI grid (replaces the overview screenshot so tiles can be color-grouped) ---
KPI_ROWS=[['Total Revenue'],['Ad Revenue','Sale Revenue'],['Visits','Flow Starts'],
          ['RPV','Sale RPV','Ad RPV'],['Ad CPV','Ad Clicks','Ad RPC','Aleads']]
def render_kpi_grid(tiles, highlights):
    cmap={}
    for g in (highlights or []):
        for m in g.get('metrics',[]): cmap[m]=g['color']
    leg=''
    if highlights:
        items=''.join(f'<span style="display:inline-flex;align-items:center;gap:6px;margin-right:16px"><i style="width:13px;height:13px;border-radius:3px;background:{g["color"]};display:inline-block"></i>{g["name"]}</span>' for g in highlights)
        items+='<span style="display:inline-flex;align-items:center;gap:6px"><i style="width:13px;height:13px;border-radius:3px;background:#d7dce4;display:inline-block"></i>Not central this week</span>'
        leg=f'<div style="font-size:11px;color:#6b7686;margin:1px 0 7px">{items}</div>'
    def tile(label):
        t=tiles.get(label,{}); val=t.get('value') or '&mdash;'; pct=t.get('pct'); color=cmap.get(label)
        border=f'3px solid {color}' if color else '1px solid #e3e7ee'
        dot=f'<span style="width:9px;height:9px;border-radius:50%;background:{color};display:inline-block;margin-right:6px;flex:none"></span>' if color else ''
        delta=''
        if pct is not None:
            up=pct>=0; dcol='#1f9d6b' if up else '#d64545'; ar='&#9650;' if up else '&#9660;'
            delta=f'<div style="font-size:11px;color:{dcol};margin-top:3px">{ar} {abs(pct):.2f}%</div>'
        return (f'<div style="background:#fff;border:{border};border-radius:9px;padding:5px 10px;min-height:30px">'
                f'<div style="display:flex;align-items:center;font-size:9.5px;color:#6b7686;margin-bottom:2px">{dot}{label}</div>'
                f'<div style="font-size:15px;font-weight:700;color:#12203a;line-height:1.05">{val}</div>{delta}</div>')
    rows=''
    for r in KPI_ROWS:
        rows+=f'<div style="display:grid;grid-template-columns:repeat({len(r)},1fr);gap:6px;margin-bottom:6px">'+''.join(tile(m) for m in r)+'</div>'
    return leg+rows

def capture(vertical, end_date, lookback):
    from playwright.sync_api import sync_playwright
    report={'params':{'vertical':vertical,'end':end_date,'lookback':lookback},'tabs':{}}
    with sync_playwright() as p:
        b=p.chromium.launch(headless=True)
        ctx=b.new_context(viewport={"width":1500,"height":2300}, device_scale_factor=2)
        pg=ctx.new_page(); pg.goto(URL, wait_until="domcontentloaded", timeout=60000)
        time.sleep(6); wait_until(lambda: rc(pg)==0, 90); time.sleep(2)
        tr0=pg.evaluate("()=>{const l=[...document.querySelectorAll('*')].find(e=>e.textContent&&e.textContent.trim()==='Total Revenue');let m=l&&l.parentElement?(l.parentElement.innerText||'').match(/\\$[0-9,]+/):null;return m?m[0]:'?';}")
        def read_tr():
            return pg.evaluate("()=>{const l=[...document.querySelectorAll('*')].find(e=>e.textContent&&e.textContent.trim()==='Total Revenue');let m=l&&l.parentElement?(l.parentElement.innerText||'').match(/\\$[0-9,]+/):null;return m?m[0]:'?';}")
        def click_run():
            try: pg.get_by_role("button",name="Run").first.click(timeout=5000); return
            except Exception:
                try: pg.get_by_text("Run",exact=True).first.click(timeout=5000)
                except Exception as e: print("run err",e,flush=True)
        def set_vertical():
            # open the Vertical dropdown regardless of its current value, then pick the target option
            opened=False
            for name in ("auto","home","renters","life","pet","travel","commercial"):
                try: pg.get_by_text(name,exact=True).first.click(timeout=1200); opened=True; break
                except Exception: continue
            if not opened:  # coordinate fallback: click the control just under the 'Vertical' label
                try:
                    box=pg.evaluate("()=>{const lab=[...document.querySelectorAll('*')].find(e=>e.textContent&&e.textContent.trim()==='Vertical'&&e.children.length===0);if(!lab)return null;const r=lab.getBoundingClientRect();return {x:r.x+40,y:r.y+34};}")
                    if box: pg.mouse.click(box['x'],box['y'])
                except Exception as e: print("vert open fallback err",e,flush=True)
            time.sleep(0.7)
            try: pg.get_by_text(vertical,exact=True).last.click(timeout=2500)   # .last = the option in the open list, not the label
            except Exception as e: print("vert pick err",e,flush=True)
            time.sleep(0.8)
        # set inputs + Run, and VERIFY the tile actually changed; retry the whole thing up to 3x (recompute is flaky)
        tr1=tr0
        for attempt in range(3):
            try: pg.locator("input[value*='2026-']").first.fill(end_date); pg.keyboard.press("Enter"); time.sleep(1)
            except Exception as e: print("date err",e,flush=True)
            set_vertical()
            click_run(); time.sleep(3)
            wait_until(lambda: rc(pg)>0, 25)                 # running started
            wait_until(lambda: rc(pg)==0, 300); time.sleep(6)  # running finished
            tr1=read_tr()
            if tr1 and tr1!='?' and tr1!=tr0:
                print(f"attempt {attempt+1}: recomputed {tr0} -> {tr1}",flush=True); break
            print(f"attempt {attempt+1}: still {tr1} (stale) — retrying inputs+Run",flush=True)
        report['total_revenue_before']=tr0; report['total_revenue_after']=tr1
        report['recomputed']=(tr1!=tr0 and tr1!='?')
        print(f"Total Revenue {tr0} -> {tr1}  recomputed={report['recomputed']}",flush=True)
        # per tab
        for key,label,marker in TABS:
            ok=True
            if key!='overview': ok=click_tab(pg,label,marker)
            try: pg.evaluate("()=>{window.scrollTo(0,0);document.querySelectorAll('*').forEach(e=>{try{if(e.scrollTop>0)e.scrollTop=0;}catch(_){}});}")
            except Exception: pass
            time.sleep(1.5)
            errs=0; loading=0
            try: errs=pg.get_by_text("Something went wrong",exact=False).count()
            except Exception: pass
            try: loading=pg.get_by_text("Loading chart",exact=False).count()
            except Exception: pass
            pg.screenshot(path=B+f"cap_{key}.png")
            report['tabs'][key]={'clicked':ok,'errored_cells':errs,'loading_cells':loading}
            print(f"captured {key} clicked={ok} errs={errs} loading={loading}",flush=True)
            if key=='overview':
                try: report['tiles']=scrape_tiles(pg)
                except Exception as e: print("scrape err",e,flush=True); report['tiles']={}
        b.close()
    json.dump(report, open(B+"capture_report.json","w"), indent=2)
    print("CAPTURE DONE",flush=True)
    return report

# ---------- crop ----------
BOTTOM={'mix':1690}   # exclude the errored Advertiser sub-cells under the traffic-source table
def crop(key):
    im=Image.open(B+f"cap_{key}.png").convert("RGB"); w,h=im.size
    top=660 if key=='overview' else 440
    work=im.copy(); d=ImageDraw.Draw(work)
    d.rectangle([0,0,w,top],fill="white")
    if key in BOTTOM: d.rectangle([0,BOTTOM[key],w,h],fill="white")
    d.rectangle([int(w*0.70),int(h*0.78),w,h],fill="white")   # agent popup
    diff=ImageChops.difference(work.convert("L"),Image.new("L",(w,h),255)); bbox=diff.getbbox() or (0,top,w,h)
    x0,y0,x1,y1=bbox; pad=16
    out=B+f"cap_{key}_crop.png"; work.crop((max(0,x0-pad),max(0,y0-pad),min(w,x1+pad),min(h,y1+pad))).save(out)
    return out

# ---------- build ----------
def fmt(p): return ("+%.1f%%"%p) if p>=0 else ("%.1f%%"%p)
def build(report):
    tiles=report.get('tiles',{}) or {}
    def pct(k): return tiles.get(k,{}).get('pct')
    def val(k): return tiles.get(k,{}).get('value','')
    prm=report['params']; end=prm['end']

    # moves bar from scraped tiles (skip any that didn't scrape); sorted worst->best
    moves=[(k,pct(k)) for k in MOVES_KEYS if pct(k) is not None]
    moves.sort(key=lambda x:x[1])

    tabinfo=report.get('tabs',{})
    def s(k):
        v=pct(k); return f"{fmt(v)}" if v is not None else "n/a"

    # ---- ANALYSIS OVERRIDE ----
    # If an analyst produced a per-week narrative+selection, it drives the report.
    # Schema: {"exec_html": "...", "note": "...", "sections":[{key,category,title,what,why}, ...]}
    import os
    ana_path=B+f"analysis_{prm['vertical']}_{end}.json"
    ANA=json.load(open(ana_path)) if os.path.exists(ana_path) else None

    if ANA:
        EXEC=ANA['exec_html']
        SEC_LIST=[(x['key'],x.get('category',''),x['title'],x.get('what',''),x.get('why','')) for x in ANA['sections']]
        drop_note=ANA.get('note')
    else:
        # fallback: templated headline + fixed diagnostic order (no per-week judgment)
        tr=val('Total Revenue') or '—'
        EXEC=(f"<p>Week ending {end} &middot; vertical <b>{prm['vertical']}</b>. On volume, "
              f"<b>visits {s('Visits')}, ad clicks {s('Ad Clicks')}</b> (flow-starts {s('Flow Starts')}); "
              f"total revenue <b>{tr} ({s('Total Revenue')})</b>.</p>"
              f"<p>Per-visit monetization: RPV {s('RPV')}, Ad RPV {s('Ad RPV')}, Ad RPC {s('Ad RPC')}; "
              f"sale side Sale RPV {s('Sale RPV')}, sale revenue {s('Sale Revenue')}.</p>")
        SEC_LIST=[
         ('overview','Overall metrics','Overall metrics','Every headline KPI with its week-over-week move.',''),
         ('flow','Funnel','Funnel &mdash; visits &amp; rates by prefill','Visits, flow-start rate, and flow-start&rarr;quote-list, split by prefill.',''),
         ('adv','Demand &amp; Bids','Advertiser bids, week over week','Each advertiser’s average bid, prior vs current, with % change.',''),
         ('mix','Traffic Mix','Traffic-source mix shift','Mix-shift indicator, stacked share of ad clicks, and the source table.',''),
        ]
        ql=tabinfo.get('ql',{})
        if ql.get('clicked') and ql.get('errored_cells',0)==0 and ql.get('loading_cells',0)==0:
            SEC_LIST.append(('ql','Funnel','QL changes','Ads and quotes displayed per QL, prev vs current.',''))
        drop_note=None

    def available(k):
        # a stuck "Loading" or several errored cells means the tab's primary chart failed (e.g. QL);
        # a single errored cell (mix's advertiser sub-cells) is cropped out, so the tab is still usable.
        if k=='overview': return True
        t=tabinfo.get(k,{})
        return bool(t.get('clicked')) and t.get('loading_cells',0)==0 and t.get('errored_cells',0)<=1

    # per-section image height caps (inches) so sections PACK instead of jumping a page and leaving a blank band.
    # tuned so short sections pair up on a page; the tallest (adv) fills its own page.
    MAXH={'mix':3.8,'flow':3.8,'adv':6.8}
    STYLE=("<style>.imgsec{margin-top:16px;} .imgsec.first{margin-top:4px} .imgsec .secttitle{break-after:avoid;page-break-after:avoid;margin-bottom:6px}"
     " .cat{font-size:10px;letter-spacing:.09em;text-transform:uppercase;color:#8a94a6;font-weight:700;margin-bottom:2px;break-after:avoid;page-break-after:avoid}"
     " .imgwrap{border:1px solid #e8ebf1;border-radius:12px;padding:6px;background:#fff;box-shadow:0 1px 2px rgba(20,30,50,.035)}"
     " .imgwrap img{width:100%;display:block;border-radius:8px}"
     " .imgwrap img.fit{width:auto;max-width:100%;margin:0 auto}"              # cap tall graphs so they shrink to fit
     " .imgwrap.kpi img{width:auto;max-height:3.05in;margin:0 auto}"          # shrink KPI grid so it shares page 1
     " .movesbar img{max-height:1.28in;width:auto;margin:0 auto}"
     " .cap{font-size:12px;color:#3a4351;line-height:1.55;margin-top:9px} .cap .lbl{font-weight:700;color:#1a2230}</style>")
    body=STYLE+execbox(EXEC)
    if moves: body+=sect(secttitle("Key metric moves &mdash; week over week", hint="worst to best"),
                         card('<div class="movesbar">'+moves_bar(moves)+'</div>'))
    skipped=[]
    for key,category,title,what,why in SEC_LIST:
        cat=f'<div class="cat">{category}</div>' if category else ''
        if key=='overview':   # rendered, color-grouped tile grid (not a screenshot)
            body+=f'<div class="imgsec first">'+cat+secttitle(title)+render_kpi_grid(tiles,(ANA or {}).get('kpi_highlights'))+'</div>'
            continue
        if not available(key): skipped.append(key); continue
        path=crop(key)
        img=f'<img class="fit" style="max-height:{MAXH.get(key,4.2)}in" src="file://{path}"/>'
        blk=f'<div class="imgsec diag">'+cat+secttitle(title)+f'<div class="imgwrap">{img}</div>'
        if what or why:
            blk+=('<div class="cap">'
                  + (f'<span class="lbl">What this shows:</span> {what}<br>' if what else '')
                  + (f'<span class="lbl">Why it matters this week:</span> {why}' if why else '')
                  + '</div>')
        body+=blk+'</div>'

    foot=f"{prm['vertical'].title()} &middot; {prm['lookback']}-day window ending {end}"
    out=B+f"Marketplace_Monitoring_{prm['vertical'].title()}_{end}_real.pdf"
    html=B+"mm_weekly.html"
    page("Marketplace Monitoring &mdash; "+prm['vertical'].title(),
         "Week-over-week performance and the drivers behind it",
         f"{prm['lookback']}-day window ending <b>{end}</b><br>vertical: {prm['vertical']}",
         "", body, foot, html)
    subprocess.run([CHROME,"--headless=new","--disable-gpu","--no-pdf-header-footer",
                    f"--print-to-pdf={out}", f"file://{html}"], capture_output=True)
    print("PDF:",out,"| skipped:",skipped, flush=True)
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--vertical",default="auto"); ap.add_argument("--end",default="2026-06-08")
    ap.add_argument("--lookback",default="7"); ap.add_argument("--build-only",action="store_true")
    a=ap.parse_args()
    if a.build_only:
        report=json.load(open(B+"capture_report.json"))
    else:
        report=capture(a.vertical,a.end,a.lookback)
    build(report)

if __name__=="__main__": main()
