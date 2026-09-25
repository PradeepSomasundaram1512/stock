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

