// Shared SVG chart helpers for the dashboard and the public page. Expects the page to define pct().
const NS = "http://www.w3.org/2000/svg";
const mk = (t, a = {}, txt) => { const e = document.createElementNS(NS, t); for (const k in a) e.setAttribute(k, a[k]); if (txt != null) e.textContent = txt; return e; };

/* forest plot: mean and 95% CI per row, zero line */
function forest(target, rows, w = 620) {
  const rh = 26, pad = {l: 230, r: 14, t: 6, b: 22}, h = pad.t + rows.length * rh + pad.b, svg = mk("svg", {viewBox: `0 0 ${w} ${h}`});
  const lo = Math.min(...rows.map(r => r.lo)) * 1.1, hi = Math.max(...rows.map(r => r.hi)) * 1.1, X = v => pad.l + (v - lo) / (hi - lo) * (w - pad.l - pad.r);
  for (let v = Math.ceil(lo * 100); v <= hi * 100; v += 1) if (v % 2 === 0) svg.append(mk("line", {x1: X(v / 100), x2: X(v / 100), y1: pad.t, y2: h - pad.b, stroke: "var(--line)"}), mk("text", {x: X(v / 100), y: h - 8, fill: "var(--mute)", "font-size": 9, "text-anchor": "middle"}, v + "%"));
  svg.append(mk("line", {x1: X(0), x2: X(0), y1: pad.t, y2: h - pad.b, stroke: "var(--mute)", "stroke-dasharray": "3 3"}));
  rows.forEach((r, i) => { const y = pad.t + i * rh + rh / 2, first = i === 0;
    svg.append(mk("text", {x: 6, y: y + 4, fill: first ? "var(--ink)" : "var(--mute)", "font-size": 11, "font-weight": first ? 700 : 400}, r.name),
      mk("line", {x1: X(r.lo), x2: X(r.hi), y1: y, y2: y, stroke: first ? "var(--acc)" : "var(--mute)", "stroke-width": 2}),
      mk("circle", {cx: X(r.mean), cy: y, r: 4, fill: first ? "var(--acc)" : "var(--mute)"})); });
  target.replaceChildren(svg);
}
/* calibration: mean stated confidence (x) vs. share of winning signals (y), diagonal = perfect */
function calibChart(target, bins, w = 420, h = 300) {
  const pad = 34, X = v => pad + v * (w - pad - 10), Y = v => h - pad - v * (h - pad - 10), svg = mk("svg", {viewBox: `0 0 ${w} ${h}`});
  [0, .25, .5, .75, 1].forEach(v => svg.append(mk("line", {x1: X(0), x2: X(1), y1: Y(v), y2: Y(v), stroke: "var(--line)"}), mk("text", {x: 2, y: Y(v) + 3, fill: "var(--mute)", "font-size": 9}, (v * 100) + "%"), mk("text", {x: X(v), y: h - 16, fill: "var(--mute)", "font-size": 9, "text-anchor": "middle"}, (v * 100) + "%")));
  svg.append(mk("line", {x1: X(0), y1: Y(0), x2: X(1), y2: Y(1), stroke: "var(--mute)", "stroke-dasharray": "4 3"}),
    mk("text", {x: X(.5), y: h - 3, fill: "var(--mute)", "font-size": 10, "text-anchor": "middle"}, "stated confidence →"),
    mk("text", {x: X(.62), y: Y(.66), fill: "var(--mute)", "font-size": 9}, "perfect calibration"));
  const pts = bins.map(b => [X(b.conf), Y(b.win)]);
  svg.append(mk("polyline", {points: pts.map(p => p.join(",")).join(" "), fill: "none", stroke: "var(--acc)", "stroke-width": 2}));
  bins.forEach((b, i) => { const c = mk("circle", {cx: pts[i][0], cy: pts[i][1], r: 3 + Math.sqrt(b.n) / 4, fill: "var(--acc)", opacity: .8}); c.append(mk("title", {}, `${b.cbin}: ${b.n} signals, stated ${pct(b.conf)}, won ${pct(b.win)}`)); svg.append(c); });
  target.replaceChildren(svg);
}


/* ---------- candlestick chart ----------
   candles: [[ts_ms, o, h, l, c, v], ...]; opts: {markers:[{ts,kind,label,detail}], levels:[{price,label,color}], cmp:[[ts,close]...],
   onScrub(candle|null)}. Pointer Events, so it scrubs with a finger on iOS; vertical swipes still scroll the page (touch-action: pan-y). */
function candleChart(target, candles, opts = {}) {
  target.replaceChildren();
  if (!candles || candles.length < 2) { target.append(Object.assign(document.createElement("div"), {className: "mute small", textContent: "No chart data available."})); return; }
  const W = Math.max(300, target.clientWidth || 600), H = Math.round(Math.min(420, Math.max(260, W * 0.55))), pad = {l: 8, r: 46, t: 8, b: 20}, vh = 46;
  const svg = mk("svg", {viewBox: `0 0 ${W} ${H}`, style: "touch-action:pan-y;user-select:none;-webkit-user-select:none;height:" + H + "px"});
  const n = candles.length, cw = (W - pad.l - pad.r) / n, X = i => pad.l + (i + 0.5) * cw;
  const plotH = H - pad.t - pad.b - vh;
  let lo = Math.min(...candles.map(c => c[3])), hi = Math.max(...candles.map(c => c[2]));
  const cmp = opts.cmp && opts.cmp.length > 1 ? opts.cmp : null;
  let cmpPts = null;
  if (cmp) { const base = candles[0][4], c0 = cmp[0][1]; cmpPts = candles.map(c => { let j = 0; while (j + 1 < cmp.length && cmp[j + 1][0] <= c[0]) j++; return base * cmp[j][1] / c0; }); lo = Math.min(lo, ...cmpPts); hi = Math.max(hi, ...cmpPts); }
  (opts.levels || []).forEach(l => { lo = Math.min(lo, l.price); hi = Math.max(hi, l.price); });
  const span = (hi - lo) || 1; lo -= span * 0.04; hi += span * 0.04;
  const Y = v => pad.t + (hi - v) / (hi - lo) * plotH, vmax = Math.max(1, ...candles.map(c => c[5] || 0));
  const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim() || "#888";
  for (let k = 0; k <= 4; k++) { const v = lo + (hi - lo) * k / 4, y = Y(v); svg.append(mk("line", {x1: pad.l, x2: W - pad.r, y1: y, y2: y, stroke: "var(--line)"}), mk("text", {x: W - pad.r + 4, y: y + 3, fill: "var(--mute)", "font-size": 10}, v >= 100 ? v.toFixed(0) : v.toFixed(2))); }
  const intraday = candles[1][0] - candles[0][0] < 86400000 * 0.9, fmt = ts => { const d = new Date(ts); return intraday ? d.toLocaleDateString(undefined, {month: "short", day: "numeric"}) : d.toLocaleDateString(undefined, {month: "short", year: n > 130 ? "2-digit" : undefined, day: n > 130 ? undefined : "numeric"}); };
  [0, Math.floor(n / 3), Math.floor(2 * n / 3), n - 1].forEach((i, k) => svg.append(mk("text", {x: X(i), y: H - 5, fill: "var(--mute)", "font-size": 10, "text-anchor": k === 0 ? "start" : k === 3 ? "end" : "middle"}, fmt(candles[i][0]))));
  const up = css("--buy"), dn = css("--sell");
  candles.forEach((c, i) => {
    const col = c[4] >= c[1] ? up : dn, x = X(i), bw = Math.max(1, cw * 0.7);
    svg.append(mk("line", {x1: x, x2: x, y1: Y(c[2]), y2: Y(c[3]), stroke: col, "stroke-width": 1}),
      mk("rect", {x: x - bw / 2, y: Math.min(Y(c[1]), Y(c[4])), width: bw, height: Math.max(1, Math.abs(Y(c[1]) - Y(c[4]))), fill: col}),
      mk("rect", {x: x - bw / 2, y: H - pad.b - (c[5] || 0) / vmax * vh, width: bw, height: (c[5] || 0) / vmax * vh, fill: col, opacity: .3}));
  });
  if (cmpPts) svg.append(mk("polyline", {points: cmpPts.map((v, i) => `${X(i)},${Y(v)}`).join(" "), fill: "none", stroke: "var(--acc)", "stroke-width": 1.5, opacity: .9}));
  (opts.levels || []).forEach(l => svg.append(mk("line", {x1: pad.l, x2: W - pad.r, y1: Y(l.price), y2: Y(l.price), stroke: l.color, "stroke-dasharray": "5 4", "stroke-width": 1.2}),
    mk("text", {x: pad.l + 3, y: Y(l.price) - 3, fill: l.color, "font-size": 10, "font-weight": 600}, l.label)));
  const idxAt = ts => { let j = -1; for (let i = 0; i < n; i++) if (candles[i][0] <= ts) j = i; else break; return j; };
  (opts.markers || []).forEach(m => { const i = idxAt(m.ts); if (i < 0) return; const buy = /BUY/.test(m.kind), x = X(i), y = buy ? Y(candles[i][3]) + 10 : Y(candles[i][2]) - 10, s = 5;
    const tri = mk("polygon", {points: buy ? `${x},${y - s} ${x - s},${y + s} ${x + s},${y + s}` : `${x},${y + s} ${x - s},${y - s} ${x + s},${y - s}`, fill: buy ? up : dn, stroke: "var(--card)", "stroke-width": 1});
    tri.append(mk("title", {}, m.detail || m.kind)); svg.append(tri); });
  const cross = mk("line", {y1: pad.t, y2: H - pad.b, stroke: "var(--mute)", "stroke-dasharray": "3 3", visibility: "hidden"});
  svg.append(cross);
  const move = ev => { const r = svg.getBoundingClientRect(), x = (ev.clientX - r.left) / r.width * W, i = Math.max(0, Math.min(n - 1, Math.floor((x - pad.l) / cw)));
    cross.setAttribute("x1", X(i)); cross.setAttribute("x2", X(i)); cross.setAttribute("visibility", "visible"); if (opts.onScrub) opts.onScrub(candles[i], i); };
  const leave = () => { cross.setAttribute("visibility", "hidden"); if (opts.onScrub) opts.onScrub(null); };
  svg.addEventListener("pointermove", move); svg.addEventListener("pointerdown", move); svg.addEventListener("pointerleave", leave); svg.addEventListener("pointerup", ev => { if (ev.pointerType !== "mouse") leave(); });
  target.append(svg);
}

/* ---------- squarified treemap ----------
   items: [{value, ...}] sorted by value desc; returns items with x,y,w,h filling the rectangle (Bruls et al.). */
function squarify(items, x, y, w, h) {
  const total = items.reduce((s, i) => s + i.value, 0), out = [];
  if (!items.length || total <= 0 || w <= 0 || h <= 0) return out;
  const scale = w * h / total, nodes = items.map(i => ({...i, area: i.value * scale}));
  let rest = nodes.slice(), rx = x, ry = y, rw = w, rh = h;
  const worst = (row, side) => { const s = row.reduce((a, b) => a + b.area, 0), mx = Math.max(...row.map(r => r.area)), mn = Math.min(...row.map(r => r.area)); return Math.max(side * side * mx / (s * s), s * s / (side * side * mn)); };
  while (rest.length) {
    const side = Math.min(rw, rh); let row = [rest[0]], i = 1;
    while (i < rest.length && worst([...row, rest[i]], side) <= worst(row, side)) row.push(rest[i++]);
    rest = rest.slice(row.length);
    const s = row.reduce((a, b) => a + b.area, 0);
    if (rw >= rh) { const cwid = s / rh; let cy = ry; row.forEach(r => { const hh = r.area / cwid; out.push({...r, x: rx, y: cy, w: cwid, h: hh}); cy += hh; }); rx += cwid; rw -= cwid; }
    else { const chei = s / rw; let cx = rx; row.forEach(r => { const ww = r.area / chei; out.push({...r, x: cx, y: ry, w: ww, h: chei}); cx += ww; }); ry += chei; rh -= chei; }
  }
  return out;
}
