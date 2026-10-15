"""Numerical checks on the connected finance engine: convergence and multiple equilibria."""
import numpy as np
import engine as E


def run(seed: int, n: int = 3000) -> dict:
    rows = {}
    for i, sc in enumerate(E.SEVERITY):
        base = E.simulate_finance(sc, n, seed + i)
        long = E.simulate_finance(sc, n, seed + i, iters=60)
        lo = E.simulate_finance(sc, n, seed + i, iters=60, l0=0.0)
        hi = E.simulate_finance(sc, n, seed + i, iters=60, l0=1.0)
        d_iter = np.abs(base["liq"] - long["liq"]); d_start = np.abs(lo["liq"] - hi["liq"])
        rows[sc] = {"residualAfter8": float(base["resid"].max()), "residualAfter60": float(long["resid"].max()),
                    "meanAbsLiquidityGap8vs60": float(d_iter.mean()), "p99AbsLiquidityGap8vs60": float(np.percentile(d_iter, 99)),
                    "pathsWithDifferentEquilibrium": float((d_start.max(axis=1) > .02).mean()), "maxStartGap": float(d_start.max()),
                    "medianEquityTroughShift": float(np.median(long["equity"].min(axis=1)) - np.median(base["equity"].min(axis=1)))}
    return {"method": "Same shocks; iteration cap 8 vs 60; fixed-point start from liquidity 0 vs 1", "scenarios": rows,
            "worstResidualAfter8": max(r["residualAfter8"] for r in rows.values()),
            "worstMultiEquilibriumShare": max(r["pathsWithDifferentEquilibrium"] for r in rows.values()),
            "timeResolution": "Annual state updates. Within-year dynamics (margin calls in days, funding in weeks) are collapsed into one fixed point per year; see methodology limitations."}
