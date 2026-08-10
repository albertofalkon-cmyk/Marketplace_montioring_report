#!/usr/bin/env python3
# Reusable polished Auto weekly report generator (Hex-style). Import helpers + call page().
import html, csv
def esc(s): return html.escape(str(s))

INK="#1b2330"; INK2="#4c5666"; MUT="#8a94a4"
UP="#1f9d55"; DOWN="#d64545"; FLAT="#9aa3b0"
LINE="#e8ebf1"; LINE2="#f1f3f8"; PANEL="#f7f9fc"; ACCENT="#2f6df6"; ACCSOFT="#dbe6fb"
C_STACK=["#e7a6c4","#a6dcc6","#4d6e71","#52a06e","#6f9cc9","#5cb85c","#e5808a","#e0975c","#e6c34c","#a97e5c","#8f80b5"]
C_VISIT="#9b8bb3"; C_FSR="#e0a92e"; C_FQ="#d9605f"; C_ADS="#d76b72"; C_QUOTES="#3f7d80"
NS='http://www.w3.org/2000/svg'

def heat(pct):
    p=max(-18,min(18,pct)); t=abs(p)/18.0
    if abs(pct)<0.3: return "#f5f7fa","#3a3f47"
    if p<0:
        r=int(255-(255-214)*t); g=int(255-(255-69)*t); b=int(255-(255-69)*t); fg="#ffffff" if t>0.5 else "#8a1f1f"
    else:
        r=int(255-(255-31)*t); g=int(255-(255-157)*t); b=int(255-(255-85)*t); fg="#ffffff" if t>0.5 else "#0f5a2f"
    return f"rgb({r},{g},{b})",fg

def load_daily(path):
    rows=list(csv.reader(open(path)))
    days=sorted(set(r[0] for r in rows)); srcs=sorted(set(r[1] for r in rows))
    tbl={s:{d:0.0 for d in days} for s in srcs}
    for dt,s,c in rows: tbl[s][dt]=float(c)
    order=sorted(srcs,key=lambda s:-sum(tbl[s].values()))
    series=[(s,[tbl[s][d] for d in days]) for s in order]
    daylab=[f"{int(d[5:7])}/{int(d[8:10])}" for d in days]
    return daylab,series

def kpi_grid(KPI):
    d={r[0]:r for r in KPI}
    def tile(m,big=False):
        _,val,pct=d[m]
        col=UP if pct>0.3 else (DOWN if pct<-0.3 else FLAT); arr='▲' if pct>0.3 else ('▼' if pct<-0.3 else '▬'); sign='+' if pct>0 else ''
        vsz='31px' if big else '21px'
        return f'<div class="tile"><div class="tlab">{esc(m)}</div><div class="tval" style="font-size:{vsz}">{esc(val)}</div><div class="tdelta" style="color:{col}">{arr} {sign}{pct:.1f}%</div></div>'
    return (f'<div class="kpi"><div class="krow r1">{tile("Total Revenue",True)}</div>'
      f'<div class="krow r2">{tile("Ad Revenue")}{tile("Sale Revenue")}</div>'
      f'<div class="krow r2">{tile("Visits")}{tile("Flow Starts")}</div>'
      f'<div class="krow r3">{tile("RPV")}{tile("AdRPV")}{tile("Sale RPV")}</div>'
      f'<div class="krow r4">{tile("Ad Clicks Per Visit")}{tile("Ad Clicks")}{tile("AdRPC")}{tile("ALeads")}</div></div>')

def adv_heatmap(ADV):
    body=[]
    for name,prev,cur,pct in ADV:
        bg,fg=heat(pct); sign='+' if pct>0 else ''
        body.append(f'<tr><td class="hn">{esc(name)}</td><td class="hp">${prev:.2f}</td>'
          f'<td class="hc" style="background:{bg};color:{fg}">${cur:.2f}</td>'
          f'<td class="hd" style="background:{bg};color:{fg}">{sign}{pct:.1f}%</td></tr>')
    return ('<table class="heat"><thead><tr><th>Advertiser</th><th>Prev avg bid</th>'
      f'<th>Current avg bid</th><th>WoW</th></tr></thead><tbody>{"".join(body)}</tbody></table>')

def mix_tiles(MIX):
    ind,pct=MIX; s1='+' if ind>=0 else '-'; s2='+' if pct>=0 else ''; col=UP if pct>=0 else DOWN
    return (f'<div class="mixtiles"><div class="mt"><div class="mtlab">Mix Shift Indicator</div>'
      f'<div class="mtval" style="color:{col}">{s1}${abs(ind):.2f}<span>/visit</span></div></div>'
      f'<div class="mt"><div class="mtlab">Mix Shift Percentage</div>'
      f'<div class="mtval" style="color:{col}">{s2}{pct:.1f}%</div></div></div>')

def src_heatmap(SRC_WEEKLY):
    body=[]
    for name,prev,cur in SRC_WEEKLY:
        pct=(cur-prev)/prev*100 if prev else 0; bg,fg=heat(pct)
        body.append(f'<tr><td class="hn">{esc(name)}</td><td class="hp">{prev:,}</td>'
          f'<td class="hc" style="background:{bg};color:{fg}">{cur:,}</td></tr>')
    return ('<table class="heat src"><thead><tr><th>Traffic source</th><th>Prev</th>'
      f'<th>Current</th></tr></thead><tbody>{"".join(body)}</tbody></table>')

def stacked_area(days,series):
    W=720; H=250; pl=8; pr=118; pt=10; pb=24; iw=W-pl-pr; ih=H-pt-pb; n=len(days)
    tot=[sum(sv[i] for _,sv in series) or 1 for i in range(n)]; X=lambda i: pl+iw*i/(n-1)
    p=[f'<svg viewBox="0 0 {W} {H}" width="100%" xmlns="{NS}" font-family="-apple-system,Helvetica,Arial,sans-serif">']
    cum=[0.0]*n
    for si,(name,vals) in enumerate(series):
        top=[cum[i]+vals[i]/tot[i] for i in range(n)]
        pts=[f"{X(i):.1f} {pt+ih*(1-top[i]):.1f}" for i in range(n)]+[f"{X(i):.1f} {pt+ih*(1-cum[i]):.1f}" for i in range(n-1,-1,-1)]
        p.append(f'<polygon points="{" ".join(pts)}" fill="{C_STACK[si%len(C_STACK)]}" stroke="#fff" stroke-width="0.5"/>'); cum=top
    for si,(name,_) in enumerate(series):
        yy=pt+10+si*15
        p.append(f'<rect x="{W-pr+10}" y="{yy-8}" width="9" height="9" rx="2" fill="{C_STACK[si%len(C_STACK)]}"/>')
        p.append(f'<text x="{W-pr+23}" y="{yy}" font-size="9.5" fill="{INK2}">{esc(name)}</text>')
    for i in (0,n//2,n-1):
        p.append(f'<text x="{X(i):.1f}" y="{H-7}" text-anchor="middle" font-size="9" fill="{MUT}">{esc(days[i])}</text>')
    return "".join(p)+'</svg>'

def funnel_combo(FUNNEL):
    f=FUNNEL; W=720; H=250; facets=[('false','Non-prefill'),('true','Prefill')]; fw=(W-40)/2
    p=[f'<svg viewBox="0 0 {W} {H}" width="100%" xmlns="{NS}" font-family="-apple-system,Helvetica,Arial,sans-serif">']
    maxv=max(f[k][d][0] for k in f for d in ('prev','cur'))*1.15
    for fi,(key,title) in enumerate(facets):
        ox=20+fi*fw; pl=ox+30; iw=fw-60; pt=28; ih=H-pt-30
        p.append(f'<text x="{ox+fw/2:.0f}" y="16" text-anchor="middle" font-size="11" font-weight="700" fill="{INK}">{title}</text>')
        for di,dk in enumerate(('prev','cur')):
            visits=f[key][dk][0]; bx=pl+iw*(0.16+di*0.42); bw=iw*0.26; bh=ih*visits/maxv
            p.append(f'<rect x="{bx:.1f}" y="{pt+ih-bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" fill="{C_VISIT}" rx="2"/>')
            p.append(f'<text x="{bx+bw/2:.1f}" y="{H-14}" text-anchor="middle" font-size="9" fill="{MUT}">{"prev" if dk=="prev" else "cur"}</text>')
        def ry(pct): return pt+ih*(1-pct/100.0)
        for series,col in (((f[key]['prev'][1],f[key]['cur'][1]),C_FSR),((f[key]['prev'][2],f[key]['cur'][2]),C_FQ)):
            xs=[pl+iw*0.29,pl+iw*0.71]
            p.append(f'<path d="M{xs[0]:.1f} {ry(series[0]):.1f} L{xs[1]:.1f} {ry(series[1]):.1f}" stroke="{col}" stroke-width="2.4" fill="none"/>')
            for xi,val in zip(xs,series):
                p.append(f'<circle cx="{xi:.1f}" cy="{ry(val):.1f}" r="3.5" fill="{col}"/>')
                p.append(f'<text x="{xi:.1f}" y="{ry(val)-6:.1f}" text-anchor="middle" font-size="9" font-weight="700" fill="{INK}">{val:.0f}%</text>')
    return "".join(p)+'</svg>'

def ql_grouped(QL):
    q=QL; W=720; H=230; pl=50; pr=14; pt=16; pb=28; iw=W-pl-pr; ih=H-pt-pb
    mx=max(q['ads'][0],q['ads'][1],q['quotes'][0],q['quotes'][1])*1.2
    p=[f'<svg viewBox="0 0 {W} {H}" width="100%" xmlns="{NS}" font-family="-apple-system,Helvetica,Arial,sans-serif">']
    for gi,(glab,ix) in enumerate([('1 - previous',0),('2 - current',1)]):
        gx=pl+gi*(iw/2); gw=iw/2
        for bi,(col,arr) in enumerate(((C_ADS,q['ads']),(C_QUOTES,q['quotes']))):
            val=arr[ix]; bw=gw*0.28; bx=gx+gw*(0.18+bi*0.34); bh=ih*val/mx
            p.append(f'<rect x="{bx:.1f}" y="{pt+ih-bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" fill="{col}" rx="2"/>')
            p.append(f'<text x="{bx+bw/2:.1f}" y="{pt+ih-bh-5:.1f}" text-anchor="middle" font-size="10" font-weight="700" fill="{INK}">{val:.3f}</text>')
        p.append(f'<text x="{gx+gw/2:.1f}" y="{H-9}" text-anchor="middle" font-size="10" fill="{MUT}">{glab}</text>')
    return "".join(p)+'</svg>'

def legend_row(items):
    out=['<div class="legend">']
    for lab,col,kind in items:
        if kind=='bar': i=f'<i style="background:{col};border:none;height:9px;width:11px;border-radius:2px"></i>'
        else: i=f'<i style="border-top:2px {"dashed" if kind=="dash" else "solid"} {col}"></i>'
        out.append(f'<span>{i}{esc(lab)}</span>')
    return "".join(out)+'</div>'

def moves_bar(items, W=720):
    rowH=18; pl=138; pr=52; pt=5; H=pt*2+len(items)*rowH
    mx=max(abs(v) for _,v in items)*1.18 or 1
    mid=pl+(W-pl-pr)/2; half=(W-pl-pr)/2
    p=[f'<svg viewBox="0 0 {W} {H}" width="100%" xmlns="{NS}" font-family="-apple-system,Helvetica,Arial,sans-serif">']
    p.append(f'<line x1="{mid}" y1="{pt}" x2="{mid}" y2="{H-pt}" stroke="{LINE}" stroke-width="1"/>')
    for i,(name,v) in enumerate(items):
        y=pt+i*rowH; w=abs(v)/mx*half; pos=v>=0; col=UP if pos else DOWN
        x=mid if pos else mid-w
        p.append(f'<rect x="{x:.1f}" y="{y+4}" width="{max(w,1):.1f}" height="{rowH-9}" rx="3" fill="{col}" fill-opacity="0.9"/>')
        p.append(f'<text x="{pl-10}" y="{y+rowH/2+3:.1f}" text-anchor="end" font-size="11" fill="{INK}">{esc(name)}</text>')
        lx=mid+w+6 if pos else mid-w-6; anc="start" if pos else "end"
        p.append(f'<text x="{lx:.1f}" y="{y+rowH/2+3:.1f}" text-anchor="{anc}" font-size="10.5" font-weight="700" fill="{col}">{"+" if pos else ""}{v:.1f}%</text>')
    return "".join(p)+'</svg>'

# ---- layout helpers ----
def secttitle(text, chip=None, hint=None, tone='driver'):
    tc = '' if tone=='driver' else ' '+tone
    right = f'<span class="chip{tc}">{chip}</span>' if chip else (f'<span class="hint">{hint}</span>' if hint else '')
    return f'<div class="secttitle"><span class="dot"></span><h3>{text}</h3>{right}</div>'
def card(inner): return f'<div class="card">{inner}</div>'
def note(text): return f'<div class="note">{text}</div>'
def takeaway(text, tone='neu'): return f'<div class="tk {tone}">{text}</div>'
def sect(title_html, body_html): return f'<div class="sect">{title_html}{body_html}</div>'
def execbox(inner): return f'<div class="exec"><div class="h">Executive summary</div>{inner}</div>'
def ruledbox(inner): return f'<div class="ruled"><div class="h">Reviewed &amp; ruled out this week</div><p>{inner}</p></div>'
def mix_section(MIX, SRC_WEEKLY, days, series, note_html):
    return card(mix_tiles(MIX)+f'<div class="mixgrid"><div class="chartbox">{stacked_area(days,series)}</div><div>{src_heatmap(SRC_WEEKLY)}</div></div>'+note(note_html))

def page(title, sub, period_html, status_label, body_html, footer_r, out_path, status_tone='watch'):
    _sc = '' if status_tone=='watch' else status_tone
    HTML=f'''<!doctype html><html><head><meta charset="utf-8"><style>
@page {{ size: Letter; margin: 13mm 14mm; }}
*{{box-sizing:border-box}}
html,body{{margin:0;color:{INK};font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;-webkit-print-color-adjust:exact;print-color-adjust:exact}}
body{{font-size:12px;line-height:1.5;background:#fff}}
.mast{{position:relative;display:flex;justify-content:space-between;align-items:flex-end;padding-bottom:8px;margin-bottom:4px;border-bottom:1px solid {LINE}}}
.mast::after{{content:"";position:absolute;left:0;bottom:-1px;width:60px;height:3px;background:{ACCENT};border-radius:3px}}
.eyebrow{{font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:{ACCENT};font-weight:700;margin:0 0 5px}}
h1{{font-size:23px;margin:0;letter-spacing:-.015em;font-weight:700}}
.sub{{color:{MUT};font-size:12px;margin-top:4px}}
.period{{text-align:right;font-size:11px;color:{MUT};line-height:1.7}} .period b{{color:{INK};font-weight:600}}
.status{{display:inline-block;font-size:10px;font-weight:700;letter-spacing:.03em;padding:2px 9px;border-radius:20px;background:#fdf3df;color:#9a6a12;margin-top:6px}}
.status.good{{background:#e7f6ee;color:#1f7d4a}} .status.bad{{background:#fbeaea;color:#c0392b}}
.secttitle{{display:flex;align-items:center;gap:9px;margin:10px 0 6px}}
.secttitle h3{{font-size:13.5px;font-weight:600;margin:0;color:{INK};letter-spacing:.005em}}
.dot{{width:7px;height:7px;border-radius:50%;background:{ACCENT};flex:none}}
.hint{{margin-left:auto;font-size:10px;color:{MUT}}}
.chip{{margin-left:auto;font-size:9.5px;font-weight:700;color:#1f7d4a;background:#e7f6ee;padding:3px 10px;border-radius:20px;letter-spacing:.01em}}
.chip.neutral{{color:#6b7688;background:#eef1f6}}
.card{{border:1px solid {LINE};border-radius:12px;background:#fff;box-shadow:0 1px 2px rgba(20,30,50,.035);padding:12px 14px;break-inside:avoid}}
.note{{margin:8px 2px 2px;font-size:11px;line-height:1.6;color:{INK2};padding-left:11px;border-left:2px solid {ACCSOFT}}} .note b{{color:{INK}}}
.tk{{font-size:11.5px;font-weight:600;margin:10px 2px 0}} .tk.pos{{color:#1f7d4a}} .tk.neg{{color:#c0392b}} .tk.neu{{color:#5a6373}}
.exec{{border:1px solid {LINE};border-left:4px solid {ACCENT};border-radius:12px;background:{PANEL};padding:8px 16px;margin-top:6px;box-shadow:0 1px 2px rgba(20,30,50,.035)}}
.exec .h{{font-size:10.5px;text-transform:uppercase;letter-spacing:.12em;color:{ACCENT};font-weight:700;margin-bottom:3px}}
.exec p{{margin:0 0 5px;font-size:11px;line-height:1.42;color:#2f3846}} .exec p:last-child{{margin-bottom:0}}
.ruled{{border:1px dashed #cfd6e2;border-radius:12px;background:#fbfcfe;padding:13px 16px;margin-top:9px}}
.ruled .h{{font-size:10.5px;text-transform:uppercase;letter-spacing:.1em;color:{MUT};font-weight:700;margin-bottom:6px}}
.ruled p{{margin:0;font-size:11.5px;line-height:1.62;color:#5a6373}} .ruled b{{color:{INK}}}
.kpi{{border:1px solid {LINE};border-radius:12px;overflow:hidden;box-shadow:0 1px 2px rgba(20,30,50,.035)}}
.krow{{display:grid;border-top:1px solid {LINE2}}} .krow:first-child{{border-top:none}}
.r1{{grid-template-columns:1fr}} .r2{{grid-template-columns:1fr 1fr}} .r3{{grid-template-columns:1fr 1fr 1fr}} .r4{{grid-template-columns:1fr 1fr 1fr 1fr}}
.tile{{padding:7px 10px;text-align:center;border-left:1px solid {LINE2}}} .tile:first-child{{border-left:none}}
.r1 .tile{{background:{PANEL};padding:9px 10px}}
.tlab{{font-size:10px;color:{MUT};text-transform:uppercase;letter-spacing:.05em;font-weight:600}}
.tval{{font-weight:700;color:{INK};letter-spacing:-.015em;line-height:1.1;margin:2px 0}}
.tdelta{{font-size:11px;font-weight:700}}
table.heat{{width:100%;border-collapse:separate;border-spacing:0;font-size:11px}}
table.heat th{{text-align:right;font-size:9.5px;letter-spacing:.04em;text-transform:uppercase;color:{MUT};font-weight:700;padding:4px 9px 7px}}
table.heat th:first-child{{text-align:left}}
table.heat td{{padding:6px 9px;border-top:1px solid {LINE2};text-align:right;font-variant-numeric:tabular-nums}}
table.heat tbody tr:first-child td{{border-top:none}}
table.heat td.hn{{text-align:left;font-weight:600;color:{INK}}} table.heat td.hp{{color:{MUT}}}
table.heat td.hc,table.heat td.hd{{font-weight:700}} table.heat.src{{font-size:10.5px}}
.mixtiles{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px}}
.mt{{border:1px solid {LINE};border-radius:10px;padding:12px 14px;text-align:center;background:{PANEL}}}
.mtlab{{font-size:10px;color:{MUT};text-transform:uppercase;letter-spacing:.05em;font-weight:600}}
.mtval{{font-size:28px;font-weight:700;margin-top:3px}} .mtval span{{font-size:12px;color:{MUT};font-weight:600;margin-left:2px}}
.mixgrid{{display:grid;grid-template-columns:1.4fr 1fr;gap:14px;align-items:start}}
.chartbox{{border:1px solid {LINE};border-radius:10px;padding:6px 8px;background:#fff}}
.legend{{display:flex;gap:16px;font-size:10.5px;color:{MUT};margin:2px 0 7px;flex-wrap:wrap}} .legend span{{display:flex;align-items:center;gap:5px}} .legend i{{width:15px;height:0;display:inline-block}}
footer{{margin-top:16px;padding-top:9px;border-top:1px solid {LINE};color:{MUT};font-size:9.5px;display:flex;justify-content:space-between}}
.card,.kpi,.exec,.ruled,.mt,.chartbox,table.heat{{break-inside:avoid}}
.sect{{break-inside:avoid;page-break-inside:avoid}} .sect .secttitle{{margin-top:14px}} .sect:first-child .secttitle{{margin-top:6px}}
</style></head><body>
<div class="mast"><div>
  <div class="eyebrow">Ad Marketplace &middot; Weekly Situation Report</div>
  <h1>{title}</h1><div class="sub">{sub}</div>
</div><div class="period">{period_html}</div></div>
{body_html}
<footer><span>Source: Insurify Marketplace analytics &middot; Marketplace Monitoring.</span><span>{footer_r}</span></footer>
</body></html>'''
    open(out_path,'w').write(HTML); return out_path
