/* Global Economic Futures, 2026–2030: explorer front end.
 * Vanilla JavaScript, no dependencies, no network calls beyond same-origin data/*.json.
 * Charts are SVG drawn from precomputed outputs. Every chart has a generated caption
 * (figcaption and SVG <desc>) and a table alternative. The only computation in the
 * browser is display filtering and the sensitivity re-display of stored sweep values.
 */
(function () {
  "use strict";

  var NS = "http://www.w3.org/2000/svg";
  var DATA = {};
  var METRIC_LABELS = {
    real_consumption_index_2026_100: "Real consumption index (2026 = 100)",
    fixed_nominal_debt_real_burden_index_2026_100: "Real debt-burden index (2026 = 100)",
    domestic_residual_funding_stress_fraction_assumed_pool: "Domestic residual funding stress (fraction, assumed pool)",
    external_residual_funding_stress_fraction_assumed_maturity: "External residual funding stress (fraction, assumed maturity)"
  };
  var CN_LINES = [
    ["property_value_index_2026_100", "Property value index"],
    ["real_consumption_index_2026_100", "Real consumption index"],
    ["working_age_proxy_index_2026_100", "Working-age proxy index"]
  ];

  // ------------------------------------------------------------ helpers

  function $(id) { return document.getElementById(id); }

  function esc(s) {
    return String(s === null || s === undefined ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[c];
    });
  }

  function uniq(a) {
    var seen = {}, out = [];
    a.forEach(function (x) { if (!seen[x]) { seen[x] = true; out.push(x); } });
    return out;
  }

  function sign(v) { return v < 0 ? "−" : ""; }

  // fraction -> percent string, e.g. -0.0068 -> "−0.68%"
  function pctFrac(x, d) {
    if (x === null || x === undefined || isNaN(x)) return "n/a";
    return sign(x) + Math.abs(x * 100).toFixed(d === undefined ? 2 : d) + "%";
  }

  // value already in percent units, e.g. 0.6 -> "0.6%"
  function pctUnit(x, d) {
    if (x === null || x === undefined || isNaN(x)) return "n/a";
    return sign(x) + Math.abs(x).toFixed(d === undefined ? 1 : d) + "%";
  }

  function num(x, d) {
    if (x === null || x === undefined || isNaN(x)) return "n/a";
    return sign(x) + Math.abs(x).toFixed(d === undefined ? 1 : d);
  }

  function getJSON(path) {
    return fetch(path, { cache: "no-store" }).then(function (r) {
      if (!r.ok) { throw new Error(path + " returned HTTP " + r.status); }
      return r.json();
    });
  }

  function labelOf(list, id) {
    for (var i = 0; i < (list || []).length; i++) { if (list[i].id === id) { return list[i].label; } }
    return id;
  }

  function fillSelect(sel, items) {
    if (!sel) { return; }
    sel.innerHTML = "";
    items.forEach(function (it) {
      var o = document.createElement("option");
      o.value = it.value;
      o.textContent = it.label;
      sel.appendChild(o);
    });
  }

  function tableHTML(caption, headers, rows) {
    var head = "<thead><tr>" + headers.map(function (h, i) {
      return "<th scope=\"col\"" + (i > 0 ? " class=\"num\"" : "") + ">" + esc(h) + "</th>";
    }).join("") + "</tr></thead>";
    var body = "<tbody>" + rows.map(function (r) {
      return "<tr>" + r.map(function (c, i) {
        return i === 0 ? "<th scope=\"row\">" + esc(c) + "</th>" : "<td class=\"num\">" + esc(c) + "</td>";
      }).join("") + "</tr>";
    }).join("") + "</tbody>";
    return "<div class=\"table-wrap\"><table class=\"data\"><caption>" + esc(caption) + "</caption>" + head + body + "</table></div>";
  }

  function setText(id, text) { var n = $(id); if (n) { n.textContent = text; } }

  function setTable(id, html) { var n = $(id); if (n) { n.innerHTML = html; } }

  function noData(container, message) {
    container.innerHTML = "<p class=\"chart-empty\">" + esc(message) + "</p>";
  }

  // ------------------------------------------------------------ SVG primitives

  function svgEl(name, attrs, parent) {
    var n = document.createElementNS(NS, name);
    Object.keys(attrs || {}).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    if (parent) { parent.appendChild(n); }
    return n;
  }

  function textEl(attrs, parent, text) {
    var t = svgEl("text", attrs, parent);
    t.textContent = text;
    return t;
  }

  function startSvg(container, title, desc, W, H) {
    container.innerHTML = "";
    var base = container.id || "chart";
    var s = svgEl("svg", {
      viewBox: "0 0 " + W + " " + H, role: "img", class: "plot", focusable: "false",
      "aria-labelledby": base + "-title " + base + "-desc"
    }, container);
    var t = svgEl("title", { id: base + "-title" }, s);
    t.textContent = title;
    var d = svgEl("desc", { id: base + "-desc" }, s);
    d.textContent = desc;
    return s;
  }

  function legendInto(container, items) {
    var box = document.createElement("ul");
    box.className = "legend-inline";
    box.setAttribute("aria-hidden", "false");
    items.forEach(function (it) {
      var li = document.createElement("li");
      li.innerHTML = "<span class=\"swatch " + esc(it.cls) + "\" aria-hidden=\"true\"></span>" + esc(it.name);
      box.appendChild(li);
    });
    container.appendChild(box);
  }

  // Nice tick values across [lo, hi].
  function niceTicks(lo, hi, n) {
    var span = hi - lo;
    if (!(span > 0)) { return [lo]; }
    var raw = span / n;
    var p = Math.pow(10, Math.floor(Math.log(raw) / Math.LN10));
    var step = p;
    [1, 2, 2.5, 5, 10].some(function (m) { if (m * p >= raw) { step = m * p; return true; } return false; });
    var out = [], v = Math.ceil(lo / step) * step;
    for (var k = 0; v <= hi + step * 1e-9 && k < 100; k++, v += step) { out.push(Number(v.toFixed(10))); }
    return out;
  }

  function domain(values, includeZero) {
    var lo = Infinity, hi = -Infinity;
    values.forEach(function (v) {
      if (v === null || v === undefined || isNaN(v)) { return; }
      if (v < lo) { lo = v; }
      if (v > hi) { hi = v; }
    });
    if (includeZero) { lo = Math.min(lo, 0); hi = Math.max(hi, 0); }
    if (!isFinite(lo) || !isFinite(hi)) { lo = 0; hi = 1; }
    if (lo === hi) { lo -= 1; hi += 1; }
    var pad = (hi - lo) * 0.08;
    return [lo - pad, hi + pad];
  }

  // Frame: grid, axes and tick labels. Returns coordinate functions.
  function frame(s, o) {
    var W = o.W, H = o.H, m = { l: 66, r: 16, t: 14, b: 40 };
    var x = function (v) { return m.l + (v - o.x0) * (W - m.l - m.r) / ((o.x1 - o.x0) || 1); };
    var y = function (v) { return H - m.b - (v - o.y0) * (H - m.t - m.b) / ((o.y1 - o.y0) || 1); };
    o.yTicks.forEach(function (v) {
      svgEl("line", { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), class: "grid" }, s);
      textEl({ x: m.l - 8, y: y(v) + 4, "text-anchor": "end", class: "tick" }, s, o.yFmt(v));
    });
    o.xTicks.forEach(function (v) {
      textEl({ x: x(v), y: H - m.b + 18, "text-anchor": "middle", class: "tick" }, s, o.xFmt(v));
    });
    if (o.y0 < 0 && o.y1 > 0) { svgEl("line", { x1: m.l, x2: W - m.r, y1: y(0), y2: y(0), class: "zero" }, s); }
    if (o.ref !== undefined) { svgEl("line", { x1: m.l, x2: W - m.r, y1: y(o.ref), y2: y(o.ref), class: "ref" }, s); }
    svgEl("line", { x1: m.l, x2: W - m.r, y1: H - m.b, y2: H - m.b, class: "axis" }, s);
    svgEl("line", { x1: m.l, x2: m.l, y1: m.t, y2: H - m.b, class: "axis" }, s);
    return { x: x, y: y, m: m };
  }

  // ------------------------------------------------------------ chart types

  // spec: {id, title, desc, W, H, series:[{name,cls,pts:[[x,y]],dash}], bands:[{name,cls,pts:[[x,lo,hi]]}],
  //        xTicks, xFmt, yFmt, zero, ref}
  function drawLines(container, spec) {
    var W = spec.W || 640, H = spec.H || 340;
    var xs = [], ys = [];
    (spec.series || []).forEach(function (sr) { sr.pts.forEach(function (p) { xs.push(p[0]); ys.push(p[1]); }); });
    (spec.bands || []).forEach(function (b) { b.pts.forEach(function (p) { xs.push(p[0]); ys.push(p[1]); ys.push(p[2]); }); });
    if (spec.ref !== undefined) { ys.push(spec.ref); }
    if (!xs.length || !ys.length) { noData(container, "No values available for this selection."); return; }
    var yd = domain(ys, !!spec.zero);
    var xd = [Math.min.apply(null, xs), Math.max.apply(null, xs)];
    if (xd[0] === xd[1]) { xd = [xd[0] - 0.5, xd[1] + 0.5]; }
    var s = startSvg(container, spec.title, spec.desc, W, H);
    var f = frame(s, {
      W: W, H: H, x0: xd[0], x1: xd[1], y0: yd[0], y1: yd[1],
      xTicks: spec.xTicks || uniq(xs), xFmt: spec.xFmt || function (v) { return String(v); },
      yTicks: niceTicks(yd[0], yd[1], 5), yFmt: spec.yFmt || function (v) { return String(v); },
      ref: spec.ref
    });
    (spec.bands || []).forEach(function (b) {
      var up = b.pts.map(function (p) { return f.x(p[0]) + "," + f.y(p[2]); });
      var dn = b.pts.slice().reverse().map(function (p) { return f.x(p[0]) + "," + f.y(p[1]); });
      svgEl("polygon", { points: up.concat(dn).join(" "), class: "band " + b.cls }, s);
    });
    (spec.series || []).forEach(function (sr) {
      var d = sr.pts.map(function (p, i) { return (i ? "L" : "M") + f.x(p[0]).toFixed(1) + "," + f.y(p[1]).toFixed(1); }).join(" ");
      svgEl("path", { d: d, class: "line " + sr.cls + (sr.dash ? " dash" : ""), fill: "none" }, s);
      sr.pts.forEach(function (p) {
        var c = svgEl("circle", { cx: f.x(p[0]), cy: f.y(p[1]), r: 3.2, class: "dot " + sr.cls }, s);
        var t = svgEl("title", {}, c);
        t.textContent = sr.name + ", " + (spec.xFmt ? spec.xFmt(p[0]) : p[0]) + ": " + spec.yFmt(p[1]);
      });
    });
    var items = (spec.series || []).map(function (sr) { return { name: sr.name, cls: "sw-" + sr.cls }; });
    (spec.bands || []).forEach(function (b) { items.push({ name: b.name, cls: "sw-band " + b.cls }); });
    legendInto(container, items);
  }

  // spec: {id,title,desc,W,H,cats:[label], groups:[{name,cls,vals:[v]}], yFmt}
  function drawBars(container, spec) {
    var W = spec.W || 640, H = spec.H || 380;
    var all = [];
    spec.groups.forEach(function (g) { g.vals.forEach(function (v) { all.push(v); }); });
    if (!all.length) { noData(container, "No values for this selection."); return; }
    var yd = domain(all, true);
    var s = startSvg(container, spec.title, spec.desc, W, H);
    var f = frame(s, {
      W: W, H: H, x0: 0, x1: spec.cats.length, y0: yd[0], y1: yd[1],
      xTicks: [], xFmt: function () { return ""; },
      yTicks: niceTicks(yd[0], yd[1], 5), yFmt: spec.yFmt
    });
    var band = (W - f.m.l - f.m.r) / spec.cats.length;
    var gw = band * 0.8, bw = gw / spec.groups.length;
    spec.cats.forEach(function (cat, ci) {
      var x0 = f.m.l + ci * band + (band - gw) / 2;
      spec.groups.forEach(function (g, gi) {
        var v = g.vals[ci];
        if (v === null || v === undefined || isNaN(v)) { return; }
        var y0 = f.y(0), y1 = f.y(v);
        var r = svgEl("rect", {
          x: (x0 + gi * bw + 1).toFixed(1), y: Math.min(y0, y1).toFixed(1),
          width: Math.max(bw - 2, 1).toFixed(1), height: Math.max(Math.abs(y1 - y0), 0.5).toFixed(1),
          class: "bar " + g.cls
        }, s);
        var t = svgEl("title", {}, r);
        t.textContent = g.name + " · " + cat.label + ": " + spec.yFmt(v);
      });
      var cx = f.m.l + ci * band + band / 2;
      var lines = wrapLabel(cat.label, 16);
      var tx = textEl({ x: cx, y: H - f.m.b + 16, "text-anchor": "middle", class: "tick" }, s, lines[0]);
      lines.slice(1).forEach(function (ln, k) {
        var ts = svgEl("tspan", { x: cx, dy: 12 }, tx);
        ts.textContent = ln;
      });
    });
    legendInto(container, spec.groups.map(function (g) { return { name: g.name, cls: "sw-" + g.cls }; }));
  }

  function wrapLabel(text, max) {
    var words = String(text).split(" "), lines = [""];
    words.forEach(function (w) {
      var last = lines.length - 1;
      if ((lines[last] + " " + w).trim().length > max && lines[last]) { lines.push(w); } else { lines[last] = (lines[last] + " " + w).trim(); }
    });
    return lines.slice(0, 3);
  }

  // spec: {title,desc,W,H,items:[{x,label,lo,mid,hi}], yFmt, zero}
  function drawRanges(container, spec) {
    var W = spec.W || 640, H = spec.H || 340;
    var ys = [];
    spec.items.forEach(function (it) { ys.push(it.lo, it.hi); if (it.mid !== null && it.mid !== undefined) { ys.push(it.mid); } });
    if (!ys.length) { noData(container, "No values for this selection."); return; }
    var yd = domain(ys, !!spec.zero);
    var s = startSvg(container, spec.title, spec.desc, W, H);
    var n = spec.items.length;
    var f = frame(s, {
      W: W, H: H, x0: -0.5, x1: n - 0.5, y0: yd[0], y1: yd[1],
      xTicks: spec.items.map(function (it, i) { return i; }),
      xFmt: function (i) { return spec.items[i] ? spec.items[i].label : ""; },
      yTicks: niceTicks(yd[0], yd[1], 5), yFmt: spec.yFmt
    });
    spec.items.forEach(function (it, i) {
      var cx = f.x(i);
      var r = svgEl("rect", {
        x: (cx - 9).toFixed(1), y: f.y(it.hi).toFixed(1), width: 18,
        height: Math.max(f.y(it.lo) - f.y(it.hi), 1).toFixed(1), class: "range"
      }, s);
      svgEl("title", {}, r).textContent = it.label + ": " + spec.yFmt(it.lo) + " to " + spec.yFmt(it.hi);
      if (it.mid !== null && it.mid !== undefined) {
        var m = svgEl("line", { x1: cx - 9, x2: cx + 9, y1: f.y(it.mid), y2: f.y(it.mid), class: "mid" }, s);
        svgEl("title", {}, m).textContent = it.label + " median: " + spec.yFmt(it.mid);
      }
    });
    legendInto(container, [{ name: spec.rangeName || "Percentile range", cls: "sw-band range" }].concat(
      spec.midName ? [{ name: spec.midName, cls: "sw-mid" }] : []));
  }

  // ------------------------------------------------------------ global explorer

  function gRows(kind, scen, region) {
    return DATA.global[kind].filter(function (r) { return r.scenario === scen || r.scenarioId === scen; })
      .filter(function (r) { return !region || r.region === region; });
  }

  function drawFan() {
    var G = DATA.global;
    var scen = $("fan-scenario").value, region = $("fan-region").value;
    var lbl = labelOf(G.scenarios, scen);
    var mc = G.mc.filter(function (r) { return r.scenarioId === scen && r.region === region; })
      .sort(function (a, b) { return a.year - b.year; });
    var det = G.deterministic.filter(function (r) { return r.scenario === scen && r.region === region; })
      .sort(function (a, b) { return a.year - b.year; });
    if (!mc.length) { noData($("fan-chart"), "No conditional draws for this selection."); setText("fan-caption", ""); setTable("fan-table", ""); return; }
    var yfmt = function (v) { return pctFrac(v, 1); };
    var series = [
      { name: "Conditional median (p50)", cls: "s-main", pts: mc.map(function (r) { return [r.year, r.p50]; }) },
      { name: "Deterministic path", cls: "s-det", dash: true, pts: det.map(function (r) { return [r.year, r.close_level_deviation_fraction]; }) }
    ];
    var bands = [
      { name: "p05–p95 range", cls: "b-inner", pts: mc.map(function (r) { return [r.year, r.p05, r.p95]; }) },
      { name: "p01–p99 range", cls: "b-outer", pts: mc.map(function (r) { return [r.year, r.p01, r.p99]; }) }
    ];
    drawLines($("fan-chart"), {
      id: "fan-chart", title: "Fan chart: " + lbl + ", " + region,
      desc: "Normalized demand-index deviation from 2026 = 100, 2027 to 2030. Bands show conditional design percentiles; the solid line is the median and the dashed line the deterministic path.",
      series: series, bands: bands, zero: true, yFmt: yfmt,
      xTicks: mc.map(function (r) { return r.year; }), xFmt: function (v) { return String(v); }
    });
    var last = mc[mc.length - 1];
    var dl = det[det.length - 1];
    setText("fan-caption",
      lbl + ", " + region + ". In " + last.year + ", the conditional median is " + pctFrac(last.p50) +
      " (p05 to p95: " + pctFrac(last.p05) + " to " + pctFrac(last.p95) + "); the deterministic path is " +
      (dl ? pctFrac(dl.close_level_deviation_fraction) : "n/a") + ". Values are deviations of a 2026 = 100 index, and the bands are not calibrated probabilities.");
    setTable("fan-table", tableHTML(
      "Fan chart values, " + lbl + ", " + region + " (fractions shown as percent)",
      ["Year", "p01", "p05", "Median p50", "p95", "p99", "Deterministic"],
      mc.map(function (r) {
        var d = det.filter(function (x) { return x.year === r.year; })[0];
        return [String(r.year), pctFrac(r.p01), pctFrac(r.p05), pctFrac(r.p50), pctFrac(r.p95), pctFrac(r.p99),
          d ? pctFrac(d.close_level_deviation_fraction) : "n/a"];
      })));
  }

  function drawBarsGlobal() {
    var G = DATA.global;
    var year = Number($("bar-year").value), measure = $("bar-measure").value;
    var cats = G.scenarios.map(function (s) { return { id: s.id, label: s.label }; });
    var groups = G.regions.map(function (rg, i) {
      return {
        name: rg, cls: "s" + (i % 8),
        vals: cats.map(function (c) {
          var r = measure === "p50"
            ? G.mc.filter(function (x) { return x.scenarioId === c.id && x.region === rg && x.year === year; })[0]
            : G.deterministic.filter(function (x) { return x.scenario === c.id && x.region === rg && x.year === year; })[0];
          if (!r) { return null; }
          return measure === "p50" ? r.p50 : r.close_level_deviation_fraction;
        })
      };
    });
    var yfmt = function (v) { return pctFrac(v, 2); };
    var what = measure === "p50" ? "conditional median" : "deterministic path";
    drawBars($("bar-chart"), {
      id: "bar-chart", title: "Demand-index deviation by scenario and region, " + year,
      desc: "Grouped bars: " + what + " of the normalized demand-index deviation in " + year + " for each scenario, with one bar per region. Values are deviations of a 2026 = 100 index.",
      cats: cats, groups: groups, yFmt: yfmt
    });
    var best = null;
    groups.forEach(function (g) {
      g.vals.forEach(function (v, ci) {
        if (v !== null && (best === null || Math.abs(v) > Math.abs(best.v))) { best = { v: v, rg: g.name, sc: cats[ci].label }; }
      });
    });
    setText("bar-caption", "Showing the " + what + " in " + year + ". Largest magnitude: " + (best ? best.rg + " under " + best.sc + " at " + pctFrac(best.v) : "n/a") + ". Labels are scenario conditions to test, not likelihoods.");
    setTable("bar-table", tableHTML(
      "Scenario by region, " + what + ", " + year,
      ["Scenario"].concat(G.regions),
      cats.map(function (c, ci) { return [c.label].concat(groups.map(function (g) { return pctFrac(g.vals[ci]); })); })));
  }

  function drawCompanyChart() {
    var C = DATA.company;
    if (!C || !C.companies || !$("co-chart")) { return; }
    var cos = C.companies;
    var cats = cos.map(function (c) { return { label: c.company }; });
    var groups = [
      { name: "Liquid resources, cash and marketable securities (USD bn)", cls: "s0", vals: cos.map(function (c) { return c.liquidResourcesTotal; }) },
      { name: "Debt, face principal (USD bn)", cls: "s1", vals: cos.map(function (c) { return c.debtFacePrincipal; }) }
    ];
    drawBars($("co-chart"), {
      id: "co-chart", title: "Observed liquid resources and debt principal, top-five cohort",
      desc: "Grouped bars in USD billion, observed as reported in issuer filings. One pair of bars per company. The two measures are side by side and are not summed or netted.",
      W: 720, H: 380, cats: cats, groups: groups, yFmt: function (v) { return num(v, 1); }
    });
    setText("co-caption", "Observed as reported. Liquid resources are at each firm's latest balance date. Debt is face principal at the date shown in the table; Oracle's debt uses its 31 May 2026 schedule, earlier than its liquidity date. Bars are not a bridge and are not netted: simulated company paths are withheld.");
    setTable("co-table", tableHTML(
      "Observed issuer liquidity and debt principal, USD bn, with balance dates",
      ["Company", "Liquid resources", "Liquidity date", "Debt face principal", "Debt date and basis"],
      cos.map(function (c) {
        return [c.company, num(c.liquidResourcesTotal, 3), c.liquidDate || "n/a", num(c.debtFacePrincipal, 3), (c.debtDate || "n/a") + "; " + (c.debtBasis || "")];
      })));
  }

  function drawSens() {
    var G = DATA.global;
    var param = $("sens-param").value, region = $("sens-region").value;
    var rows = G.sensitivity.filter(function (r) { return r.parameter === param && r.region === region; });
    if (!rows.length) {
      noData($("sens-chart"), "This parameter has no sweep rows for the selected region. The sweep covers only the rows listed in the download.");
      setText("sens-caption", "No rows for this parameter and region.");
      setTable("sens-table", "");
      return;
    }
    var values = uniq(rows.map(function (r) { return String(r.value); }));
    var allNumeric = values.every(function (v) { return v !== "" && !isNaN(Number(v)); });
    if (allNumeric) { values.sort(function (a, b) { return Number(a) - Number(b); }); }
    var idx = {};
    values.forEach(function (v, i) { idx[v] = i; });
    var scens = uniq(rows.map(function (r) { return r.scenarioId; }));
    var series = scens.map(function (sc, i) {
      return {
        name: labelOf(G.scenarios, sc), cls: "s" + (i % 8),
        pts: rows.filter(function (r) { return r.scenarioId === sc; })
          .map(function (r) { return [idx[String(r.value)], r.close2030]; })
          .sort(function (a, b) { return a[0] - b[0]; })
      };
    });
    drawLines($("sens-chart"), {
      id: "sens-chart", title: "2030 sensitivity: " + param + ", " + region,
      desc: "2030 demand-index deviation for each swept value of " + param + " in " + region + ", one line per stress scenario. Values are deviations of a 2026 = 100 index.",
      series: series, zero: true, yFmt: function (v) { return pctFrac(v, 2); },
      xTicks: values.map(function (v, i) { return i; }),
      xFmt: function (i) { return values[i] !== undefined ? values[i] : ""; }
    });
    setText("sens-caption", "2030 deviation for " + param + " in " + region + " across " + values.length + " swept value(s): " +
      values.map(function (v) { return v; }).join(", ") + ". The sweep is a robustness check, not an estimated effect.");
    setTable("sens-table", tableHTML(
      "Sensitivity values, 2030, " + param + ", " + region,
      ["Value"].concat(scens.map(function (sc) { return labelOf(G.scenarios, sc); })),
      values.map(function (v) {
        return [v].concat(scens.map(function (sc) {
          var r = rows.filter(function (x) { return x.scenarioId === sc && String(x.value) === v; })[0];
          return r ? pctFrac(r.close2030, 2) : "n/a";
        }));
      })));
  }

  // ------------------------------------------------------------ China

  function drawChina() {
    var C = DATA.china, scen = $("cn-scenario").value;
    var rows = C.deterministic.filter(function (r) { return r.scenario_id === scen; }).sort(function (a, b) { return a.year - b.year; });
    if (!rows.length) { noData($("cn-chart"), "No deterministic path for this scenario."); return; }
    var palette = ["s0", "s1", "s2"];
    var series = CN_LINES.map(function (ln, i) {
      return { name: ln[1], cls: palette[i], pts: rows.map(function (r) { return [r.year, r[ln[0]]]; }) };
    });
    drawLines($("cn-chart"), {
      id: "cn-chart", title: "China deterministic paths: " + labelOf(C.scenarios, scen),
      desc: "Property value, real consumption and working-age proxy indices, 2027 to 2030, on a 2026 = 100 base. The reference line is 100. Transmission is an assumption-based mapping, not a causal estimate.",
      series: series, ref: 100, yFmt: function (v) { return num(v, 1); },
      xTicks: rows.map(function (r) { return r.year; }), xFmt: function (v) { return String(v); }
    });
    var last = rows[rows.length - 1];
    setText("cn-caption", labelOf(C.scenarios, scen) + " in " + last.year + ": property value index " + num(last.property_value_index_2026_100, 1) +
      ", real consumption index " + num(last.real_consumption_index_2026_100, 1) + ", working-age proxy " + num(last.working_age_proxy_index_2026_100, 1) +
      " (2026 = 100). CPI deviation " + num(last.cpi_deviation_pp_vs_zero_reference, 1) + " pp versus the zero reference.");
    setTable("cn-table", tableHTML(
      "China deterministic indices, " + labelOf(C.scenarios, scen),
      ["Year", "Property value", "Real consumption", "Working-age proxy", "CPI deviation (pp)"],
      rows.map(function (r) {
        return [String(r.year), num(r.property_value_index_2026_100, 1), num(r.real_consumption_index_2026_100, 1),
          num(r.working_age_proxy_index_2026_100, 1), num(r.cpi_deviation_pp_vs_zero_reference, 1)];
      })));
  }

  function drawChinaMC() {
    var C = DATA.china, scen = $("cn-mc-scenario").value, metric = $("cn-metric").value;
    var block = C.mc.scenarios[scen] || {};
    var years = Object.keys(block).sort();
    var isFrac = /fraction/.test(metric);
    var yfmt = isFrac ? function (v) { return pctFrac(v, 1); } : function (v) { return num(v, 1); };
    var items = years.map(function (y) {
      var m = (block[y] || {})[metric];
      return m ? { x: Number(y), label: y, lo: m.p05, mid: m.p50, hi: m.p95 } : null;
    }).filter(function (x) { return x; });
    drawRanges($("cn-mc"), {
      id: "cn-mc", title: "Parameter-design percentiles: " + (METRIC_LABELS[metric] || metric) + ", " + labelOf(C.scenarios, scen),
      desc: "For each year, the bar spans the 5th to 95th percentile of 2,000 parameter-design draws and the tick marks the median. Draws are independent uniform samples over stated assumption bounds, not probability-calibrated.",
      items: items, yFmt: yfmt, zero: isFrac, rangeName: "p05–p95 range", midName: "Median (p50)"
    });
    var last = items[items.length - 1];
    setText("cn-mc-caption", (METRIC_LABELS[metric] || metric) + ", " + labelOf(C.scenarios, scen) + ", " + (last ? last.label : "") +
      ": median " + (last ? yfmt(last.mid) : "n/a") + ", 5th to 95th percentile " + (last ? yfmt(last.lo) + " to " + yfmt(last.hi) : "n/a") +
      ". These are design sensitivities, not forecast probabilities.");
    setTable("cn-mc-table", tableHTML(
      "Percentiles, " + (METRIC_LABELS[metric] || metric),
      ["Year", "p05", "Median", "p95"],
      items.map(function (it) { return [it.label, yfmt(it.lo), yfmt(it.mid), yfmt(it.hi)]; })));
  }

  // ------------------------------------------------------------ EU

  function drawEU() {
    var E = DATA.eu;
    var items = E.share.map(function (r) {
      return { x: r.year, label: String(r.year), lo: r.low, hi: r.high, mid: null };
    });
    drawRanges($("eu-chart"), {
      id: "eu-chart", title: "EU NdFeB secondary supply as share of demand, source-model range",
      desc: "Range bars give the source-model low and high share of selected-application NdFeB demand met by secondary (recycled) supply, by year. These are feasibility bounds under stated assumptions, not observed outcomes.",
      items: items, yFmt: function (v) { return num(v, 0) + "%"; }, zero: true,
      rangeName: "Source-model low to high"
    });
    var y30 = E.share.filter(function (r) { return r.year === 2030; })[0];
    setText("eu-caption", "2030: secondary supply " + (y30 ? num(y30.low, 0) + "–" + num(y30.high, 0) + "%" : "n/a") +
      " of selected-application demand (2.88–6.84 kt of 36 kt modeled demand; source RIZOS_MAGNET_CESEPS_2022). The ~30% recycling-sufficiency claim lies above this source-model range, so it is not supported by this model envelope.");
    setTable("eu-table", tableHTML(
      "Secondary supply share by year (source-model range, percent)",
      ["Year", "Low", "High"],
      items.map(function (it) { return [it.label, num(it.lo, 0) + "%", num(it.hi, 0) + "%"]; })));
  }

  // ------------------------------------------------------------ Switzerland

  function drawSwiss() {
    var S = DATA.swiss;
    var years = uniq(S.deterministic.map(function (r) { return r.year; })).sort();
    var series = S.scenarios.map(function (sc, i) {
      return {
        name: sc.label, cls: "s" + (i % 8),
        pts: S.deterministic.filter(function (r) { return r.scenario === sc.id; })
          .sort(function (a, b) { return a.year - b.year; })
          .map(function (r) { return [r.year, r.cpi_annual_average_pct]; })
      };
    }).filter(function (s) { return s.pts.length; });
    drawLines($("ch-chart"), {
      id: "ch-chart", title: "Swiss CPI annual average by branch, 2027 to 2030",
      desc: "CPI annual average inflation in percent, by Swiss branch. Branches are design conditions: the signed package is conditional on entry into force, and status-quo erosion is an assumed path. The severe branch has no CPI pass-through in the deterministic model.",
      series: series, zero: true, yFmt: function (v) { return pctUnit(v, 1); },
      xTicks: years, xFmt: function (v) { return String(v); }
    });
    var lastYear = years[years.length - 1];
    var parts = series.map(function (s) {
      var p = s.pts.filter(function (q) { return q[0] === lastYear; })[0];
      return s.name + " " + (p ? pctUnit(p[1], 1) : "n/a");
    });
    setText("ch-caption", "CPI annual average in " + lastYear + ": " + parts.join("; ") + ". For reference, observed Swiss CPI for 2026-09 was +1.0% y/y (source CH_CPI_202609); this is an observation, not a branch output.");
    setTable("ch-table", tableHTML(
      "Swiss CPI annual average by branch (percent)",
      ["Branch"].concat(years.map(String)),
      series.map(function (s) {
        return [s.name].concat(years.map(function (y) {
          var p = s.pts.filter(function (q) { return q[0] === y; })[0];
          return p ? pctUnit(p[1], 1) : "n/a";
        }));
      })));
  }

  // ------------------------------------------------------------ search

  function resultHTML(x) {
    var status = x.status ? "<span class=\"pill status-" + esc(x.status) + "\">" + esc(String(x.status).replace(/_/g, " ")) + "</span>" : "";
    var sources = (x.sources || []).length
      ? "<p class=\"sources\">Sources: " + x.sources.map(function (s) { return "<code>" + esc(s) + "</code>"; }).join(" ") + "</p>"
      : "";
    return "<li class=\"result\"><div class=\"result-head\"><span class=\"pill\">" + esc(x.type) + "</span>" +
      "<span class=\"pill\">" + esc(x.region) + "</span>" + status + "</div>" +
      "<p class=\"result-title\"><strong>" + esc(x.title) + "</strong> <span class=\"muted\">" + esc(x.id) + "</span></p>" +
      "<p>" + esc(x.text) + "</p>" + sources + "</li>";
  }

  function runSearch() {
    if (!DATA.search) { return; }
    var q = ($("q").value || "").trim().toLowerCase();
    var t = $("f-type").value, r = $("f-region").value, s = $("f-status").value;
    var words = q ? q.split(/\s+/) : [];
    var hits = DATA.search.filter(function (x) {
      if (t && x.type !== t) { return false; }
      if (r && x.region !== r) { return false; }
      if (s && x.status !== s) { return false; }
      if (!words.length) { return true; }
      var hay = (String(x.id) + " " + x.title + " " + x.text + " " + (x.sources || []).join(" ")).toLowerCase();
      return words.every(function (w) { return hay.indexOf(w) !== -1; });
    });
    var shown = hits.slice(0, 80);
    setText("search-status", hits.length + " matching record" + (hits.length === 1 ? "" : "s") +
      (hits.length > shown.length ? "; showing the first " + shown.length + ". Refine the search to see more." : "."));
    $("search-results").innerHTML = shown.map(resultHTML).join("");
  }

  // ------------------------------------------------------------ wiring

  function bind(id, ev, fn) { var n = $(id); if (n) { n.addEventListener(ev, fn); } }

  function setup() {
    var G = DATA.global, C = DATA.china;
    var regions = G.regions.map(function (r) { return { value: r, label: r }; });
    fillSelect($("fan-scenario"), G.scenarios.map(function (s) { return { value: s.id, label: s.label }; }));
    fillSelect($("fan-region"), regions);
    fillSelect($("bar-year"), [2027, 2028, 2029, 2030].map(function (y) { return { value: String(y), label: String(y) }; }));
    fillSelect($("sens-region"), regions);
    fillSelect($("sens-param"), uniq(G.sensitivity.map(function (r) { return r.parameter; })).map(function (p) { return { value: p, label: p }; }));
    fillSelect($("cn-scenario"), C.scenarios.map(function (s) { return { value: s.id, label: s.label }; }));
    var mcIds = Object.keys(C.mc.scenarios);
    fillSelect($("cn-mc-scenario"), mcIds.map(function (id) { return { value: id, label: labelOf(C.scenarios, id) }; }));
    var firstYear = Object.keys(C.mc.scenarios[mcIds[0]])[0];
    var metrics = Object.keys(C.mc.scenarios[mcIds[0]][firstYear]);
    fillSelect($("cn-metric"), metrics.map(function (m) { return { value: m, label: METRIC_LABELS[m] || m }; }));

    ["fan-scenario", "fan-region"].forEach(function (id) { bind(id, "change", drawFan); });
    ["bar-year", "bar-measure"].forEach(function (id) { bind(id, "change", drawBarsGlobal); });
    ["sens-param", "sens-region"].forEach(function (id) { bind(id, "change", drawSens); });
    bind("cn-scenario", "change", drawChina);
    ["cn-mc-scenario", "cn-metric"].forEach(function (id) { bind(id, "change", drawChinaMC); });

    drawFan();
    drawBarsGlobal();
    drawSens();
    drawChina();
    drawChinaMC();
    drawEU();
    drawSwiss();
  }

  function showError(err) {
    var msg = "The interactive parts could not load (" + (err && err.message ? err.message : err) +
      "). The narrative, the tables in each section and the downloads still work. Serve the site over HTTP rather than opening the file directly.";
    setText("search-status", msg);
    document.querySelectorAll(".chart").forEach(function (c) { c.innerHTML = "<p class=\"chart-empty\">Chart unavailable.</p>"; });
  }

  function init() {
    if (!document.getElementById("fan-chart")) { return; }
    bind("search-form", "submit", function (e) { e.preventDefault(); });
    bind("q", "input", runSearch);
    ["f-type", "f-region", "f-status"].forEach(function (id) { bind(id, "change", runSearch); });
    Promise.all([getJSON("data/global.json"), getJSON("data/china.json"), getJSON("data/eu.json"), getJSON("data/swiss.json")])
      .then(function (r) {
        DATA.global = r[0]; DATA.china = r[1]; DATA.eu = r[2]; DATA.swiss = r[3];
        setup();
      })
      .catch(showError);
    getJSON("data/company_chart.json").then(function (c) {
      DATA.company = c;
      drawCompanyChart();
    }).catch(showError);
    getJSON("data/search.json").then(function (s) {
      DATA.search = s;
      runSearch();
    }).catch(showError);
  }

  if (document.readyState === "loading") { document.addEventListener("DOMContentLoaded", init); } else { init(); }
})();
