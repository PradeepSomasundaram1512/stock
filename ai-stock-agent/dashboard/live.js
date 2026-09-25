/* Live features for the dashboard: market clock and countdowns, scan-landed toasts, watchlist, heatmap, ticker chart.
   Loaded before the page's own script; relies on its globals ($, el, get, usd, pct, spct, num, pill, tickLink, kpi, dataTable, fail, showTab, loaded)
   which are only used at call time. Text from the server is always inserted with textContent. */

let paperData = null, livePx = {}, pulseData = null, clockSkew = 0, prevScanAt = null, prevQuotes = {}, hm = null, hmMode = "c", redrawChart = null;
const nowMs = () => Date.now() + clockSkew;
const fmtDur = ms => { if (ms <= 0) return "now"; const s = Math.floor(ms / 1000), h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), sec = s % 60;
  return h ? `${h}h ${String(m).padStart(2, "0")}m` : m ? `${m}m ${String(sec).padStart(2, "0")}s` : `${sec}s`; };
const utcMs = s => Date.parse(String(s).replace(" ", "T") + (/[zZ]|[+-]\d\d:?\d\d$/.test(s) ? "" : "Z"));
const clampN = (x, a, b) => Math.max(a, Math.min(b, x));
/* Market times are shown in New York time and labelled, whatever time zone the viewer is in. */
const fmtET = ms => new Date(ms).toLocaleString("en-US", {timeZone: "America/New_York", weekday: "short", hour: "numeric", minute: "2-digit"}) + " ET";

/* ---------- toasts and notifications ---------- */
function toast(msg, ms = 7000) {
  const box = $("#toasts"), t = el("div", {className: "toast", textContent: msg, role: "status"});
  t.onclick = () => t.remove(); box.append(t); setTimeout(() => t.remove(), ms);
}
function notifyScan(msg) {
  try { if ("Notification" in window && Notification.permission === "granted" && document.hidden) new Notification("Scanner", {body: msg}); } catch (e) { /* unsupported (e.g. Safari outside a Home Screen app) */ }
}

/* ---------- paper account (re-rendered on every price tick) ---------- */
function renderPaper() {
  const p = paperData; if (!p) return;
  const mkx = {...(p.marks || {}), ...livePx}, acct = $("#paperacct"); acct.replaceChildren();
  const ps = p.paper_summary;
  if (ps) {
    const market = Object.entries(p.paper.positions).reduce((s, [t, v]) => s + v.shares * (mkx[t] || v.avg_price), 0), equity = ps.cash + market, pnl = equity - ps.starting, cls = pnl >= 0 ? "ok" : "bad";
    acct.append(el("div", {className: "kpi"}, el("div", {className: "v " + cls, textContent: usd(equity)}),
      el("div", {className: "l", textContent: `Equity, ${(pnl >= 0 ? "+" : "") + usd(pnl)} (${(pnl / ps.starting * 100).toFixed(2)}%) vs ${usd(ps.starting)} start · cash ${usd(ps.cash)} · marked to the latest price`})));
  }
  const pos = p.paper ? Object.entries(p.paper.positions).map(([t, v]) => ({t, ...v, last: mkx[t]})) : [];
  dataTable($("#positions"), [{label: "Ticker", cell: x => tickLink(x.t)}, {label: "Shares", r: 1, cell: x => x.shares}, {label: "Avg", r: 1, cell: x => usd(x.avg_price)}, {label: "Last", r: 1, cell: x => usd(x.last)},
    {label: "P/L", r: 1, cell: x => x.last ? spct(x.last / x.avg_price - 1, 1) : "–"}], pos, {empty: "No open paper positions."});
  const sw = p.swing ? [...Object.values(p.swing.open_trades).map(x => ({...x, st: "open", last: mkx[x.ticker]})), ...p.swing.closed_trades.map(x => ({...x, st: "closed"}))] : [];
  const out = x => x.exit_price || x.last;
  dataTable($("#swing"), [{label: "Ticker", cell: x => tickLink(x.ticker)}, {label: "Status", cell: x => x.st}, {label: "Entry", cell: x => x.entry_date}, {label: "In", r: 1, cell: x => usd(x.entry_price)},
    {label: "Out / last", r: 1, cell: x => usd(out(x))}, {label: "P/L", r: 1, cell: x => out(x) ? spct(out(x) / x.entry_price - 1, 1) : "–"}], sw, {empty: "No swing trades yet."});
}

/* ---------- live bar ---------- */
function renderLive() {
  if (!pulseData) return;
  const s = pulseData.session, nx = pulseData.next[0], la = pulseData.last_scan_at;
  $("#sdot").className = "dot " + s.state; $("#slabel").textContent = s.label;
  $("#scount").textContent = s.next_change_at ? `${s.next_change_label.toLowerCase()} in ${fmtDur(Date.parse(s.next_change_at) - nowMs())}` : "";
  $("#nextscan").textContent = nx ? `Next: ${nx.name} in ${fmtDur(Date.parse(nx.at) - nowMs())}` : "";
  $("#lastscan").textContent = la ? `Last scan ${fmtDur(nowMs() - utcMs(la))} ago` : "";
}
function chip(id, label, m, invert) {
  const e = $(id); if (!e) return; if (!m) { e.textContent = ""; return; }
  const chg = m.prev ? m.price / m.prev - 1 : null, good = chg == null ? "" : ((chg >= 0) !== !!invert ? "ok" : "bad");
  e.replaceChildren(el("span", {className: "mute", textContent: label + " "}), el("b", {textContent: num(m.price)}), el("span", {className: good, textContent: chg == null ? "" : " " + spct(chg)}));
}
async function pollPulse() {
  if (document.hidden) return;
  const d = await get("/api/pulse"); clockSkew = Date.parse(d.now) - Date.now(); pulseData = d;
  livePx = {}; for (const [t, m] of Object.entries(d.marks)) if (m) livePx[t] = m.price;
  chip("#spy", "SPY", d.marks["SPY"]); chip("#vix", "VIX", d.marks["^VIX"], true);
  if (prevScanAt && d.last_scan_at && d.last_scan_at !== prevScanAt) {
    const msg = `New scan landed (${d.scans_today} today)`; toast(msg); notifyScan(msg);
    Object.keys(loaded).forEach(k => delete loaded[k]); loadContext().catch(fail); showTab(location.hash.slice(1) || "overview", true);
  }
  prevScanAt = d.last_scan_at || prevScanAt;
  renderPaper(); renderLive();
}
function startLive() {
  pollPulse().catch(() => {});
  setInterval(() => pollPulse().catch(() => {}), 30000);
  setInterval(renderLive, 1000);
  setInterval(() => { if (!document.hidden && location.hash === "#markets") pollQuotes().catch(() => {}); }, 20000);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) { pollPulse().catch(() => {}); if (location.hash === "#markets") pollQuotes().catch(() => {}); } });
  let rt; window.addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(() => { if (redrawChart) redrawChart(); if (hm && $("#tab-markets").classList.contains("on")) renderHeatmap(); }, 200); });
  const b = $("#alerts"); if (b) { if (!("Notification" in window) || Notification.permission !== "default") b.hidden = true;
    b.onclick = async () => { try { const r = await Notification.requestPermission(); b.hidden = true; toast(r === "granted" ? "Alerts on while this tab is in the background." : "Alerts stay off."); } catch (e) { b.hidden = true; } }; }
}

/* ---------- watchlist (kept in this browser only) ---------- */
const WL_KEY = "scanner.watchlist";
const getWL = () => { try { const v = JSON.parse(localStorage.getItem(WL_KEY)); return Array.isArray(v) ? v : ["SPY", "QQQ"]; } catch (e) { return ["SPY", "QQQ"]; } };
const setWL = l => { try { localStorage.setItem(WL_KEY, JSON.stringify(l)); } catch (e) { /* private mode */ } };
function addWatch(t) { t = (t || "").trim().toUpperCase(); if (!/^[A-Z0-9.\-^]{1,10}$/.test(t)) return toast("That does not look like a ticker."); const l = getWL(); if (!l.includes(t)) { l.push(t); setWL(l.slice(0, 40)); } pollQuotes().catch(fail); }
async function pollQuotes() {
  const wl = getWL(); if (!wl.length) { renderWatch({}); return; }
  const d = await get("/api/quotes?t=" + encodeURIComponent(wl.join(","))); renderWatch(d.quotes);
}
function renderWatch(q) {
  const rows = getWL().map(t => ({t, m: q[t]}));
  const tbl = $("#wtable"); tbl.replaceChildren();
  if (!rows.length) { tbl.append(el("tbody", {}, el("tr", {}, el("td", {className: "mute", textContent: "Add a ticker above."})))); return; }
  const body = el("tbody");
  rows.forEach(({t, m}) => {
    const chg = m && m.prev ? m.price / m.prev - 1 : null, was = prevQuotes[t], flash = m && was != null && m.price !== was ? (m.price > was ? "flash-up" : "flash-down") : "";
    if (m) prevQuotes[t] = m.price;
    body.append(el("tr", {}, el("td", {}, tickLink(t)), el("td", {className: "r " + flash, textContent: m ? usd(m.price) : "–"}), el("td", {className: "r " + (chg == null ? "" : chg >= 0 ? "ok" : "bad"), textContent: chg == null ? "–" : spct(chg)}),
      el("td", {className: "r"}, el("button", {className: "x", textContent: "✕", title: "Remove " + t, onclick: () => { setWL(getWL().filter(x => x !== t)); pollQuotes().catch(fail); }}))));
  });
  tbl.append(body);
}

/* ---------- heatmap ---------- */
function tileStyle(x, mode) {
  if (mode === "rsi") { const v = x.rsi == null ? 0 : (x.rsi - 50) / 25, a = clampN(Math.abs(v), 0, 1); return [v >= 0 ? `rgba(245,158,11,${.14 + .76 * a})` : `rgba(59,130,246,${.14 + .76 * a})`, a]; }
  const v = x[mode] / (mode === "c5" ? 0.06 : 0.03), a = clampN(Math.abs(v), 0, 1);
  return [v >= 0 ? `rgba(26,160,90,${.14 + .78 * a})` : `rgba(210,50,50,${.14 + .78 * a})`, a];
}
function renderHeatmap() {
  const box = $("#heatmap"); if (!hm || !hm.stocks.length) { box.textContent = hm && hm.note ? hm.note : "No data yet."; return; }
  box.replaceChildren();
  const W = box.clientWidth || 600, H = Math.round(W < 640 ? W * 1.25 : W * 0.6); box.style.height = H + "px";
  const bySec = {}; hm.stocks.forEach(s => (bySec[s.sector] = bySec[s.sector] || []).push(s));
  const secItems = Object.entries(bySec).map(([name, list]) => ({name, list, value: list.reduce((a, s) => a + Math.sqrt(s.dv || 1), 0)})).sort((a, b) => b.value - a.value);
  squarify(secItems, 0, 0, W, H).forEach(sec => {
    const hdr = sec.w > 46 && sec.h > 40 ? 15 : 0, inner = squarify(sec.list.map(s => ({...s, value: Math.sqrt(s.dv || 1)})).sort((a, b) => b.value - a.value), sec.x + 1, sec.y + hdr + 1, sec.w - 2, sec.h - hdr - 2);
    const wrap = el("div", {className: "hm-sec", style: `left:${sec.x}px;top:${sec.y}px;width:${sec.w}px;height:${sec.h}px`});
    if (hdr) wrap.append(el("div", {className: "hm-label", textContent: sec.name}));
    box.append(wrap);
    inner.forEach(t => {
      const [bg, a] = tileStyle(t, hmMode), big = t.w > 34 && t.h > 20, val = hmMode === "rsi" ? (t.rsi == null ? "" : Math.round(t.rsi)) : spct(t[hmMode], 1).replace(/\.0%$/, "%");
      const d = el("button", {className: "hm-tile" + (t.analysed ? " analysed" : ""), style: `left:${t.x - sec.x}px;top:${t.y - sec.y}px;width:${t.w - 1}px;height:${t.h - 1}px;background:${bg};color:${a > .55 ? "#fff" : "var(--ink)"};font-size:${clampN(Math.sqrt(t.w * t.h) / 4.2, 8, 16)}px`,
        title: `${t.t}: ${spct(t.c)} today, ${spct(t.c5)} over 5 days`}, big ? el("b", {textContent: (t.call === "BUY" ? "★" : "") + t.t}) : "", t.h > 34 && t.w > 34 ? el("span", {textContent: String(val)}) : "");
      d.onclick = () => openSheet(t); wrap.append(d);
    });
  });
  const age = hm.age_min; $("#hmmeta").textContent = `${hm.n} stocks · prices ~15 min delayed · updated ${age < 90 ? age + " min" : Math.round(age / 60) + " h"} ago`;
  $("#hmlegend").textContent = hmMode === "rsi" ? "Blue = low RSI (oversold), orange = high RSI (overbought), grey = neutral. Not a buy or sell signal." : `Color = ${hmMode === "c5" ? "5-day" : "1-day"} change (full color at ${hmMode === "c5" ? "±6%" : "±3%"}). Tile size = trading volume. Outlined = analysed in the latest scan; ★ = model said BUY.`;
}
function renderSectors() {
  const box = $("#sectorbars"); box.replaceChildren(); if (!hm) return;
  const mx = Math.max(0.005, ...hm.sectors.map(s => Math.abs(s[hmMode === "rsi" ? "c" : hmMode])));
  hm.sectors.forEach(s => { const v = s[hmMode === "rsi" ? "c" : hmMode];
    box.append(el("div", {className: "sec-row"}, el("span", {className: "sec-name", textContent: `${s.name} (${s.n})`}), el("span", {className: "sec-bar"}, el("i", {className: v >= 0 ? "pos" : "neg", style: `width:${Math.abs(v) / mx * 100}%`})), el("span", {className: "sec-val " + (v >= 0 ? "ok" : "bad"), textContent: spct(v)}))); });
}
function openSheet(t) {
  const s = $("#sheet"); s.replaceChildren();
  s.append(el("div", {className: "sheet-head"}, el("b", {textContent: t.t}), el("span", {className: "mute", textContent: " " + t.sector}), el("button", {className: "x", textContent: "✕", onclick: () => s.hidden = true, "aria-label": "Close"})),
    el("div", {className: "sheet-grid"}, ...[["Price", usd(t.p)], ["Today", spct(t.c)], ["5 days", spct(t.c5)], ["RSI(14)", t.rsi == null ? "–" : Math.round(t.rsi)], ["Latest model call", t.call || "not analysed"]].map(([k, v]) => el("div", {}, el("div", {className: "mute small", textContent: k}), el("div", {textContent: String(v)})))),
    el("div", {className: "sheet-actions"}, el("button", {textContent: "Open chart", onclick: () => { s.hidden = true; showTab("history"); $("#tickin").value = t.t; lookup().catch(fail); }}), el("button", {textContent: "Add to watchlist", onclick: () => { addWatch(t.t); toast(t.t + " added to your watchlist"); }})));
  s.hidden = false;
}
async function loadMarkets() {
  hm = await get("/api/heatmap"); renderHeatmap(); renderSectors(); pollQuotes().catch(fail);
}
function initMarkets() {
  document.querySelectorAll("#hmmode button").forEach(b => b.onclick = () => { hmMode = b.dataset.m; document.querySelectorAll("#hmmode button").forEach(x => x.classList.toggle("on", x === b)); renderHeatmap(); renderSectors(); });
  $("#wform").onsubmit = e => { e.preventDefault(); addWatch($("#winput").value); $("#winput").value = ""; };
}

/* ---------- ticker chart card ---------- */
function chartCard(t) {
  const RANGES = [["5d", "5D"], ["1mo", "1M"], ["3mo", "3M"], ["6mo", "6M"], ["1y", "1Y"]];
  let rng = "6mo", cmp = false, data = null, showPast = false;
  const readout = el("div", {className: "small mute chart-read", textContent: "Touch or hover the chart to read prices."}), box = el("div", {className: "chartbox"});
  const seg = el("div", {className: "seg"}), cmpBtn = el("button", {textContent: "vs SPY", className: "cmp", "aria-pressed": "false"});
  RANGES.forEach(([v, l]) => seg.append(el("button", {textContent: l, className: v === rng ? "on" : "", onclick: e => { rng = v; [...seg.children].forEach(x => x.classList.toggle("on", x === e.target)); load(); }})));
  cmpBtn.onclick = () => { cmp = !cmp; cmpBtn.classList.toggle("on", cmp); cmpBtn.setAttribute("aria-pressed", String(cmp)); load(); };
  const pastBtn = el("button", {textContent: "Past calls", className: "cmp", "aria-pressed": "false", onclick: () => { showPast = !showPast; pastBtn.classList.toggle("on", showPast); pastBtn.setAttribute("aria-pressed", String(showPast)); draw(); }});
  const card = el("div", {className: "card", style: "margin-bottom:12px"}, el("div", {className: "toolbar"}, el("b", {textContent: t}), seg, cmpBtn, pastBtn), readout, box,
    el("div", {className: "mute small", textContent: "Triangle: the model's latest call (turn on \"Past calls\" for earlier ones). Dashed lines: target and stop of that call. Prices ~15 min delayed."}));
  const fmtTs = ts => new Date(ts).toLocaleString(undefined, {month: "short", day: "numeric", hour: RANGES.slice(0, 2).some(r => r[0] === rng) ? "numeric" : undefined, minute: RANGES.slice(0, 2).some(r => r[0] === rng) ? "2-digit" : undefined});
  const draw = () => {
    if (!data) return;
    const decisions = data.decisions || [], newest = decisions.slice(-1)[0];
    // Default: only the model's LATEST call. "Past calls" adds the earlier recommendations and decisions.
    const calls = showPast ? [...(data.recommendations || []).map(r => ({at: r.at, kind: r.decision, conf: r.confidence})), ...decisions.map(r => ({at: r.at, kind: r.decision, conf: r.confidence}))]
                           : (newest ? [{at: newest.at, kind: newest.decision, conf: newest.confidence}] : []);
    const seen = new Set(), markers = [];
    calls.filter(m => m.kind && m.kind !== "HOLD").forEach(m => { const ts = utcMs(m.at), key = new Date(ts).toISOString().slice(0, 10) + m.kind; if (seen.has(key)) return; seen.add(key);
      markers.push({ts, kind: m.kind, detail: `${m.kind}${m.conf != null ? " at " + pct(m.conf) + " confidence" : ""} · ${new Date(ts).toLocaleDateString()}`}); });
    const levels = [];
    if (newest && /BUY/.test(newest.decision || "") && newest.price_target && newest.stop_loss)
      levels.push({price: newest.price_target, label: "Target " + usd(newest.price_target), color: "var(--buy)"}, {price: newest.stop_loss, label: "Stop " + usd(newest.stop_loss), color: "var(--sell)"});
    candleChart(box, data.candles, {markers, levels, cmp: data.spy && data.spy.map(c => [c[0], c[4]]),
      onScrub: c => { readout.textContent = c ? `${fmtTs(c[0])}   O ${num(c[1])}  H ${num(c[2])}  L ${num(c[3])}  C ${num(c[4])}   Vol ${(c[5] / 1e6).toFixed(2)}M   ${spct(c[4] / c[1] - 1)}` : "Touch or hover the chart to read prices."; }});
  };
  const load = async () => { box.textContent = "Loading chart…"; try { data = await get(`/api/chart?t=${encodeURIComponent(t)}&range=${rng}${cmp ? "&cmp=1" : ""}`); if (data.error) { box.textContent = data.error; return; } draw(); } catch (e) { box.textContent = "Could not load the chart."; } };
  redrawChart = draw; load();
  return card;
}

/* ---------- latest call for a ticker ---------- */
function latestCallBanner(t, d) {
  const c = d.latest_call, box = el("div", {className: "card", style: "margin-bottom:12px"});
  if (!c) { box.append(el("div", {className: "mute", textContent: `${t} has not been analysed by the scanner yet.`})); return box; }
  const when = fmtET(utcMs(c.at));
  box.append(el("div", {className: "toolbar", style: "margin:0"}, el("b", {textContent: "Latest call"}), pill(c.decision), el("span", {textContent: c.confidence != null ? pct(c.confidence) + " confidence" : ""}),
    c.final ? pill(c.final) : "", el("span", {className: "mute small", textContent: when + (c.in_latest_scan ? " · from the latest scan" : " · not analysed in the latest scan, this is its most recent call")})));
  if (c.reasoning) box.append(el("div", {className: "small mute", style: "margin-top:6px", textContent: c.reasoning}));
  box.append(similarBlock(t));
  return box;
}

/* How did past calls like this one turn out? (from the logged history; honest about uncertainty and small samples) */
function similarBlock(t) {
  const box = el("div", {className: "similar small", style: "margin-top:10px;padding-top:8px;border-top:1px solid var(--line)"});
  box.append(el("div", {className: "mute", textContent: "Checking how similar past calls did…"}));
  get("/api/similar?t=" + encodeURIComponent(t)).then(d => {
    box.replaceChildren(el("b", {textContent: "How similar past calls did"}));
    if (!d.available) { box.append(el("div", {className: "mute", textContent: "No history to compare with yet."})); return; }
    const rate = c => `${pct(c.win_rate)} won (95% interval ${pct(c.lo)} to ${pct(c.hi)}, ${c.n} calls)`, ok = c => c && c.n >= d.min_n, line = txt => box.append(el("div", {textContent: txt}));
    const s = d.similar;
    if (ok(s)) line(`Past ${d.decision} calls in a similar setup (RSI ${s.rsi_range[0]} to ${s.rsi_range[1]}${s.trend ? ", " + s.trend + " trend" : ""}): ${rate(s)}${s.avg_pl != null ? "; average result " + num(s.avg_pl, 2) + "%" : ""}.`);
    else line(`Too few similar past ${d.decision} calls to say anything (${s ? s.n : 0}; at least ${d.min_n} needed).`);
    if (ok(d.all_same_decision)) line(`All past ${d.decision} calls: ${rate(d.all_same_decision)}.`);
    if (ok(d.same_confidence)) line(`At about the same confidence (${pct(d.same_confidence.range[0])} to ${pct(d.same_confidence.range[1])}): ${rate(d.same_confidence)}.`);
    if (d.confidence_informative === false) line("In this history, higher stated confidence has not gone with better outcomes, so do not read it as a probability.");
    box.append(el("div", {className: "mute", textContent: "Results are the labels from the live stop/target/time exit rules on closed calls. This describes the past; it is not a forecast."}));
  }).catch(() => { box.replaceChildren(); });
  return box;
}
