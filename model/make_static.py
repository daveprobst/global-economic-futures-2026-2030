"""Static, script-free copies of the main results: tables.html and CSV downloads."""
import csv, html, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; D = ROOT / "site/data"
L = lambda n: json.loads((D / f"{n}.json").read_text())
PLAIN = {"continued_boom": "The boom keeps going", "no_burst_sideways": "A quiet pause", "mild_adjustment": "A modest pullback", "moderate_burst": "A sizeable fall",
         "deep_drawdown_no_vacuum": "A deep fall, markets keep working", "severe_burst": "A deep fall and a funding freeze", "severe_burst_with_financial_crisis": "A deep fall, a freeze and a banking crisis"}


def write_csv(name, header, rows):
    with open(D / name, "w", newline="") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)


def table(header, rows):
    e = html.escape
    return "<div class=\"table-wrap\"><table><thead><tr>" + "".join(f"<th>{e(str(h))}</th>" for h in header) + "</tr></thead><tbody>" + "".join("<tr>" + "".join(f"<td>{e(str(c))}</td>" for c in r) + "</tr>" for r in rows) + "</tbody></table></div>"


def main(df):
    t, h, ck, m, tic, cit, val = L("scenario_tree"), L("hysteresis"), L("historical_checks"), L("methodology"), L("treasury"), L("citations"), L("validation")
    prob = [[PLAIN[s["id"]], s["name"], round(s["probability"] * 100, 1), round(s["interval80"][0] * 100, 1), round(s["interval80"][1] * 100, 1), s["description"]] for s in t["scenarios"]]
    write_csv("scenario_probabilities.csv", ["outcome", "technical_name", "chance_in_100", "p10_in_100", "p90_in_100", "definition"], prob)
    cons = [[PLAIN[k], round(v["probability"] * 100, 1), round(v["us"]["outputVsTrend2030"][1], 2), round(v["us"]["outputVsTrend2036NoNewShock"], 2), round(v["us"]["peakUnemployment"], 2),
             round(v["china"]["outputVsTrend2030"][1], 2), round(v["eu"]["outputVsTrend2030"][1], 2)] for k, v in h["scenarios"].items()]
    cc = ["outcome", "chance_in_100", "us_output_vs_trend_2030_pct", "us_output_vs_trend_2036_no_new_shock_pct", "us_peak_unemployment_pct", "china_output_vs_trend_2030_pct", "eu_output_vs_trend_2030_pct"]
    write_csv("scenario_consequences.csv", cc, cons)
    write_csv("historical_episodes.csv", ["country", "origin_year", "source", "runup3_real", "return1_real", "worst_peak_to_trough", "real_return_4y", "outcome"],
              [[r.country, r.originYear, r.source, round(r.runup3, 4), round(r.return1, 4), round(r.drawdown, 4), round(r.cumReturn, 4), r.outcome] for r in df.itertuples()])
    params = [[s["title"], tb["title"], r["name"], r["value"], r["status"], r["how"], ",".join(r["cite"]), r.get("src") or ""] for s in m["sections"] for tb in s.get("tables", []) for r in tb["rows"]]
    write_csv("methodology_parameters.csv", ["section", "table", "parameter", "value", "status", "how_it_was_set", "citation_keys", "code_pointer"], params)
    write_csv("references.csv", ["key", "kind", "authors", "year", "title", "venue", "doi", "url", "used_for"], [[i["key"], i["kind"], "; ".join(i["authors"] or []), i["year"], i["title"], i["venue"], i["doi"], i["url"], i["use"]] for i in cit["items"]])
    write_csv("treasury_holdings.csv", ["month", "japan_usd_bn", "china_mainland_usd_bn"], [[a["month"], a["value"], b["value"]] for a, b in zip(tic["holders"][0]["series"], tic["holders"][1]["series"])])
    vs = val["validation"]["schemes"]["Leave one global wave out"]
    write_csv("validation_models.csv", ["forecast", "brier_waves_out", "log_loss_waves_out", "auc_waves_out"], [[k, round(v["brier"], 4), round(v["logLoss"], 4), v["auc"]] for k, v in vs.items()])
    write_csv("sensitivity.csv", ["variant", "fall_20pct_in_100", "boom_in_100", "episodes", "observed_fall_in_100"], [[r["variant"], round(r["fall20"] * 100, 1), round(r["boom"] * 100, 1), r["episodes"], round(r["observedFall"] * 100, 1)] for r in val["sensitivity"]])
    files = ["scenario_probabilities.csv", "scenario_consequences.csv", "historical_episodes.csv", "methodology_parameters.csv", "references.csv", "treasury_holdings.csv", "validation_models.csv", "sensitivity.csv"]
    jsons = ["scenario_tree.json", "scenario_paths.json", "connected_system.json", "hysteresis.json", "historical_checks.json", "validation.json", "methodology.json", "citations.json", "treasury.json", "joint_crisis.json"]
    body = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Static tables — Fault Lines</title><link rel="stylesheet" href="styles.css"><style>body{{padding:0 5vw 4rem}}table{{min-width:0;margin:1rem 0 2.5rem}}h2{{font-size:1.8rem;margin-top:3rem}}</style></head><body class="detailed"><p><a href="index.html">← Back to the interactive page</a></p>
<h1 style="font-size:2.6rem">Static tables</h1><p class="plain">Every headline number on the page, as plain tables that need no JavaScript. As of 15 Oct 2026; window to 31 Dec 2030. A what-if exercise, not a forecast or investment advice.</p>
<h2>Chance of each outcome (out of 100)</h2>{table(["Outcome", "Technical name", "Chance", "10th pct", "90th pct", "Definition"], prob)}
<h2>What each outcome means for the economy</h2>{table(["Outcome", "Chance in 100", "US output vs old path, 2030 (%)", "US, 2036 if no new shock (%)", "US peak unemployment (%)", "China 2030 (%)", "Euro area 2030 (%)"], cons)}
<h2>History check: share of cases by outcome</h2>{table(["Group", "Boom holds", "Contained", "20%+ fall", "Cases"], [["Seven outcomes (model weights)"] + [f"{ck['modelWeights'][k]*100:.0f}%" for k in ("boom", "sideways", "bust")] + ["—"], ["25 closest past booms"] + [f"{ck['nearestAnalogs'][k]*100:.0f}%" for k in ("boom", "sideways", "bust")] + [25], ["Past booms of 100%+"] + [f"{ck['runupAtLeast100'][k]*100:.0f}%" for k in ("boom", "sideways", "bust")] + [ck['runupAtLeast100']['n']], ["All past booms of 50%+"] + [f"{ck['all'][k]*100:.0f}%" for k in ("boom", "sideways", "bust")] + [ck['all']['n']]])}
<h2>Held-out tests of seven forecasts (global waves out)</h2>{table(["Forecast", "Brier", "Log loss", "AUC"], [[k, f"{v['brier']:.3f}", f"{v['logLoss']:.3f}", v['auc'] if v['auc'] is None else f"{v['auc']:.2f}"] for k, v in vs.items()])}
<h2>Sensitivity of the fall probability</h2>{table(["Variant", "Fall (in 100)", "Boom (in 100)", "Episodes"], [[r["variant"], round(r["fall20"] * 100), round(r["boom"] * 100), r["episodes"]] for r in val["sensitivity"]])}
<h2>US Treasury holdings, USD billion</h2>{table(["Holder", tic["priorMonth"], tic["latestMonth"]], [[x["name"], x["prior"], x["latest"]] for x in tic["holders"]])}
<h2>Parameters and how they were set</h2><p>{len(params)} entries; full list with explanations in <a href="data/methodology_parameters.csv">methodology_parameters.csv</a>.</p>{table(["Parameter", "Value", "Status"], [[p[2], p[3], p[4]] for p in params])}
<h2 id="downloads">Downloads</h2><ul>{"".join(f'<li><a href="data/{f}">{f}</a></li>' for f in files)}</ul><p>Model output files:</p><ul>{"".join(f'<li><a href="data/{f}">{f}</a></li>' for f in jsons)}</ul>
<h2>References ({len(cit['items'])})</h2><ol>{"".join(f"<li>{html.escape(', '.join(i['authors'] or []))} ({i['year']}). <i>{html.escape(i['title'])}</i>. {html.escape(i['venue'] or '')} {('<a href=' + chr(34) + i['url'] + chr(34) + '>link</a>') if i['url'] else ''}</li>" for i in cit['items'])}</ol></body></html>"""
    (ROOT / "site/tables.html").write_text(body)
