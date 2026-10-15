"""Connected stress engine: one shared financial state, then macro paths with hysteresis.

Stage 1 (finance) iterates AI revenue expectations, cash-flow coverage, funding costs,
equity losses, margin calls, forced sales, dollar liquidity, China capital outflow,
LGFV refinancing and Treasury-sale pressure to a fixed point inside every simulated year.
Stage 2 (macro) turns that state into output gaps, permanent output scars (hysteresis),
unemployment and growth for the US, China, Europe and Switzerland.

Window: year 0 = 2026 (baseline year, no shock). Years 1-4 = 2027-2030. Every probability
and every path in the release refers to this same window, ending 31 December 2030.
"""
from __future__ import annotations
import numpy as np

YEARS = [2026, 2027, 2028, 2029, 2030]
SEVERITY = {"continued_boom": 0, "no_burst_sideways": .14, "mild_adjustment": .30, "moderate_burst": .48,
            "deep_drawdown_no_vacuum": .66, "severe_burst": .82, "severe_burst_with_financial_crisis": 1.0}
SHAPE = np.array([0, .95, .82, .58, .38])
CH0, OUT0, SALE0 = .22, .135, .065          # China baseline stress levels (calm state)
US_G0, EU_G0, CH_G0 = 2.4, 1.5, 1.4          # baseline growth, %
UNEMP0 = {"US": 4.3, "EU": 6.3, "Switzerland": 4.4, "China": 5.1}
UNC = .40   # lognormal sd of the macro-damage multipliers
BETA = {"China": .82, "EU": .68, "Switzerland": .48}   # equity / spread beta to the US state


def logistic(x): return 1 / (1 + np.exp(-x))


def simulate_finance(sc: str, n: int, seed: int, iters: int = 40, l0=None) -> dict:
    sev = SEVERITY[sc]; rng = np.random.default_rng(seed)
    exp = np.ones((n, 5)); equity = np.full((n, 5), 100.); liq = np.zeros((n, 5)); marg = np.zeros((n, 5))
    cov = np.full((n, 5), 1.65); tech = np.full((n, 5), 5.0); sale_a = np.zeros((n, 5)); out_a = np.full((n, 5), OUT0)
    lgfv = np.full((n, 5), 4.5); ch_a = np.full((n, 5), CH0); sale_a[:] = SALE0
    resid = np.zeros(5)
    eps = {k: rng.normal(0, s, (n, 5)) for k, s in (("us", .30), ("cn", .32), ("eu", .25))}
    # Parameter uncertainty: how hard and how lasting the macro damage is for a given financial state.
    mult = {k: np.exp(rng.normal(0, UNC, n)) for k in ("phi_us", "kap_us", "phi_cn", "kap_cn")}
    for t in range(1, 5):
        common = rng.normal(0, .07, n)
        exp[:, t] = np.clip(1 - sev * SHAPE[t] + common, .03, 1.12)
        prev_eq, prev_liq, prev_ch = equity[:, t - 1], liq[:, t - 1], ch_a[:, t - 1]
        l = prev_liq * .52 if l0 is None else np.full(n, float(l0)); e = prev_eq.copy(); ch = prev_ch.copy()
        eq_noise = rng.normal(0, 1.45, n)   # drawn once per year, so the fixed point is deterministic given the shocks
        for it in range(iters):
            l_prev_it = l
            revenue = np.clip(.70 + .40 * exp[:, t] - .15 * l, .12, 1.15)
            commitment = 1 + .48 * sev * np.exp(-.18 * (t - 1))
            c = 1.82 * revenue / commitment
            draw = np.maximum(0, 1 - e / 100); prev_draw = np.maximum(0, 1 - prev_eq / 100)
            m = .36 * marg[:, t - 1] + np.maximum(0, draw - prev_draw - .025) * (1.18 + .72 * sev)
            o = np.clip(.08 + .50 * l + .34 * (1 - exp[:, t]) + .25 * ch, 0, 1)
            s = np.clip(.025 + .40 * np.maximum(0, o - .30) + .18 * ch, 0, .72)
            policy = .075 * max(0, t - 1) * sev * (1 - .55 * m)
            l = np.clip(.44 * prev_liq + .76 * np.maximum(0, 1 - c) + 1.12 * m + .34 * s - policy, 0, 1)
            if sc == "deep_drawdown_no_vacuum": l = np.minimum(l, .58)
            target = 100 * (1 - .52 * sev * SHAPE[t] - .20 * l - .10 * m)
            e = np.clip(.54 * e + .46 * target + eq_noise, 10, 150)
            ch = np.clip(.58 * prev_ch + .35 * o + .24 * l + .11 * sev, 0, 1)
        resid[t] = float(np.max(np.abs(l - l_prev_it)))
        exp[:, t] = np.clip(exp[:, t] - .09 * l, 0, 1.12)
        equity[:, t] = e; liq[:, t] = l; marg[:, t] = m; cov[:, t] = c; sale_a[:, t] = s; out_a[:, t] = o; ch_a[:, t] = ch
        tech[:, t] = 4.8 + 5.2 * l + 1.3 * np.maximum(0, 1 - c)
        lgfv[:, t] = 4.5 + 5.1 * o + 1.35 * s
    return {"exp": exp, "equity": equity, "liq": liq, "marg": marg, "cov": cov, "tech": tech, "sale": sale_a,
            "out": out_a, "lgfv": lgfv, "ch": ch_a, "eps": eps, "mult": mult, "sev": sev, "resid": resid}


def china_baseline(trend_slope: float, last_growth: float) -> np.ndarray:
    return last_growth + trend_slope * np.arange(5)


def macro(fin: dict, p: dict, cn_base: np.ndarray, cn_deflator: float, extend: int = 6) -> dict:
    """Output gaps, hysteresis scars and growth. `p` holds the calibrated parameters."""
    n = fin["exp"].shape[0]; sev = fin["sev"]; z = lambda: np.zeros((n, 5))
    liq, marg, exp, cov, ch, out, sale, lgfv = (fin[k] for k in ("liq", "marg", "exp", "cov", "ch", "out", "sale", "lgfv"))
    eps = fin["eps"]
    us = {k: z() for k in ("gap", "scar", "flow", "u", "growth", "C", "I", "U")}
    cn = {k: z() for k in ("gap", "scar", "flow", "growth", "D", "B", "F", "gnom")}
    eu = {k: z() for k in ("gap", "scar", "flow", "growth", "u", "C", "U")}
    us["u"][:] = UNEMP0["US"]; eu["u"][:] = UNEMP0["EU"]
    us["growth"][:, 0] = US_G0; eu["growth"][:, 0] = EU_G0; cn["growth"][:, 0] = cn_base[0]
    cn["gnom"][:, 0] = cn_base[0] + cn_deflator
    for t in range(1, 5):
        # ---- United States
        cyc = -p["phi"] * fin["mult"]["phi_us"] * (4.15 * liq[:, t] + 1.85 * (1 - exp[:, t]) + .70 * marg[:, t]) + eps["us"][:, t]
        us["gap"][:, t] = (1 - p["catch_us"]) * us["gap"][:, t - 1] + cyc
        C = np.clip(.6 * liq[:, t] + .4 * marg[:, t], 0, 1)
        I = np.clip((1.65 - cov[:, t]) / 1.65, 0, 1)
        u = UNEMP0["US"] + p["okun"] * np.maximum(0, -(us["gap"][:, t] - us["scar"][:, t - 1]))
        U = np.clip(np.maximum(0, u - 5.0) / 5.0, 0, 1)
        flow = p["kappa_us"] * fin["mult"]["kap_us"] * (.45 * C + .30 * I + .25 * U)
        us["flow"][:, t] = flow; us["scar"][:, t] = (1 - p["rho"]) * us["scar"][:, t - 1] + flow
        us["u"][:, t] = u; us["C"][:, t] = C; us["I"][:, t] = I; us["U"][:, t] = U
        us["growth"][:, t] = US_G0 + (us["gap"][:, t] - us["gap"][:, t - 1]) - flow
        # ---- China
        cyc = -p["phi_cn"] * fin["mult"]["phi_cn"] * (2.85 * np.maximum(0, ch[:, t] - CH0) + 1.85 * np.maximum(0, out[:, t] - OUT0)
                           + .45 * np.maximum(0, sale[:, t] - SALE0)) + eps["cn"][:, t]
        cn["gap"][:, t] = (1 - p["catch_cn"]) * cn["gap"][:, t - 1] + cyc
        defl = cn_deflator - 1.5 * np.maximum(0, ch[:, t] - CH0)
        g_pre = cn_base[t] + (cn["gap"][:, t] - cn["gap"][:, t - 1])
        gnom = g_pre + defl
        D = np.clip((lgfv[:, t] - gnom - 2.0) / 8.0, 0, 1)
        B = np.clip((ch[:, t] - .30) / .5, 0, 1); F = np.clip((out[:, t] - .30) / .5, 0, 1)
        flow = p["kappa_cn"] * fin["mult"]["kap_cn"] * (.40 * D + .35 * B + .25 * F)
        cn["flow"][:, t] = flow; cn["scar"][:, t] = (1 - p["rho"]) * cn["scar"][:, t - 1] + flow
        cn["D"][:, t], cn["B"][:, t], cn["F"][:, t], cn["gnom"][:, t] = D, B, F, gnom - flow
        cn["growth"][:, t] = g_pre - flow
        # ---- Europe: no AI-capex channel; credit and labour channels only
        cyc = -p["phi"] * fin["mult"]["phi_us"] * (1.85 * liq[:, t] + .62 * (1 - exp[:, t])) + .28 * (t >= 3) * sev + eps["eu"][:, t]
        eu["gap"][:, t] = (1 - p["catch_us"]) * eu["gap"][:, t - 1] + cyc
        Ceu = np.clip(.6 * liq[:, t] + .4 * marg[:, t], 0, 1); Ueu = np.clip(np.maximum(0, -eu["gap"][:, t]) / 10.0, 0, 1)
        flow = p["kappa_us"] * fin["mult"]["kap_us"] * .5 * (.6 * Ceu + .4 * Ueu)
        eu["flow"][:, t] = flow; eu["scar"][:, t] = (1 - p["rho"]) * eu["scar"][:, t - 1] + flow
        eu["u"][:, t] = UNEMP0["EU"] + p["okun"] * np.maximum(0, -(eu["gap"][:, t] - eu["scar"][:, t - 1]))
        eu["growth"][:, t] = EU_G0 + (eu["gap"][:, t] - eu["gap"][:, t - 1]) - flow
    # ---- persistence beyond the window: flows decay, no new shock
    def tail(d, last_flow, catch, k=.7):
        gap, scar, f = d["gap"][:, -1].copy(), d["scar"][:, -1].copy(), last_flow.copy()
        for _ in range(extend):
            f = f * k; gap = (1 - catch) * gap; scar = (1 - p["rho"]) * scar + f
        return gap - scar, scar
    us_ext = tail(us, us["flow"][:, -1], p["catch_us"]); cn_ext = tail(cn, cn["flow"][:, -1], p["catch_cn"])
    res = {"US": us, "China": cn, "EU": eu, "ext": {"US": us_ext, "China": cn_ext}}
    for r in (us, cn, eu):
        r["level"] = r["gap"] - r["scar"]
    return res


DEFAULT_PARAMS = {"phi": .6, "phi_cn": .6, "okun": .55, "rho": .03, "kappa_us": .5, "catch_us": .2, "kappa_cn": .5, "catch_cn": .1}
