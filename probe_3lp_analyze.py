#!/usr/bin/env python3
"""Project c175 sieve time from per-band probe data written by probe_3lp.sh.

Model: special-q density is 1/ln q. rel/q and ms/q are interpolated linearly in ln q between
measured bands, and extrapolated beyond the last band (floored at 15% of it, flagged EXTRAP).

CAVEAT: the number of RAW relations a 3LP run needs (NEED) is NOT measured by a short probe.
It is scanned over a range; the output also gives the largest NEED each regime could afford
inside the sieve budget ("break-even"). Only a purge curve from a ~100M-relation run settles it.
"""
import argparse
import csv
import math
import sys
from collections import defaultdict


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def load(path):
    rows = defaultdict(list)
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            q0 = fnum(r.get("q0"))
            if q0 is None:
                continue
            nq = fnum(r.get("nq"))
            rl = fnum(r.get("rel_lines"))
            rq = fnum(r.get("rq_log"))
            ms = fnum(r.get("ms_log"))
            wall = fnum(r.get("wall_s"))
            rpq = rq if rq is not None else (rl / nq if (rl is not None and nq) else None)
            ms_ext = (wall * 1000.0 / nq) if (wall and nq) else None
            rows[r["regime"]].append(
                dict(
                    q=q0,
                    nq=nq,
                    rl=rl,
                    rpq=rpq,
                    ms=ms if ms is not None else ms_ext,
                    ms_ext=ms_ext,
                    wall=wall,
                    rc=r.get("rc"),
                    sk=r.get("skipped"),
                    lpb=(r.get("lpb0"), r.get("lpb1")),
                    mfb=(r.get("mfb0"), r.get("mfb1")),
                )
            )
    return rows


def build_model(bands):
    pts = sorted(
        [b for b in bands if b["rpq"] and b["ms"] and b["rpq"] > 0 and b["ms"] > 0],
        key=lambda b: b["q"],
    )
    if not pts:
        return None
    xs = [math.log(b["q"]) for b in pts]
    rs = [b["rpq"] for b in pts]
    ms = [b["ms"] for b in pts]

    def interp(vs, x):
        if x <= xs[0]:
            return vs[0], False
        for i in range(1, len(xs)):
            if x <= xs[i]:
                t = (x - xs[i - 1]) / (xs[i] - xs[i - 1])
                return vs[i - 1] + t * (vs[i] - vs[i - 1]), False
        if len(xs) >= 2:
            slope = (vs[-1] - vs[-2]) / (xs[-1] - xs[-2])
            return max(vs[-1] + slope * (x - xs[-1]), 0.15 * vs[-1]), True
        return vs[-1], True

    def at(q):
        x = math.log(q)
        r, e = interp(rs, x)
        m = ms[-1] if x > xs[-1] else interp(ms, x)[0]
        return max(r, 0.0), max(m, 1e-6), (x > xs[-1])

    return pts, at


def project(at, q0, need):
    q, rels, t, extrap = q0, 0.0, 0.0, False
    while rels < need and q < 4e9:
        dq = max(10000.0, 0.005 * q)
        r, m, e = at(q + dq / 2)
        nq = dq / math.log(q)
        rels += nq * r
        t += nq * m / 1000.0
        q += dq
        extrap = extrap or e
    return (t, q, extrap) if rels >= need else (float("inf"), q, extrap)


def breakeven(at, q0, budget):
    lo, hi = 1e7, 2e9
    if project(at, q0, lo)[0] > budget:
        return 0.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if project(at, q0, mid)[0] <= budget:
            lo = mid
        else:
            hi = mid
    return lo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("summary")
    ap.add_argument("--needs", default="200,250,300", help="raw relations needed, millions")
    ap.add_argument(
        "--overhead",
        type=float,
        default=2400.0,
        help="non-sieve seconds: polyselect + filter + LA + sqrt (ASSUMED, unmeasured)",
    )
    ap.add_argument("--limit", type=float, default=14400.0)
    a = ap.parse_args()

    needs = [float(x) * 1e6 for x in a.needs.split(",")]
    budget = a.limit - a.overhead
    data = load(a.summary)
    if not data:
        print("no data rows")
        return 1

    print(
        f"\nAssumed non-sieve overhead {a.overhead:.0f}s -> sieve budget {budget:.0f}s "
        f"of {a.limit:.0f}s.  NEED values are ASSUMPTIONS, not measurements.\n"
    )

    for name, bands in data.items():
        b0 = sorted(bands, key=lambda b: b["q"])[0]
        print(f"=== regime {name}  lpb {b0['lpb'][0]}/{b0['lpb'][1]}  mfb {b0['mfb'][0]}/{b0['mfb'][1]}")
        print(
            f"{'q0':>11} {'nq':>6} {'rel':>8} {'rel/q':>8} {'ms/q':>8} {'ms/q(ext)':>10} "
            f"{'rel/s':>8} {'rc':>4} {'skip':>5}"
        )
        for b in sorted(bands, key=lambda b: b["q"]):
            rps = (b["rpq"] * 1000.0 / b["ms"]) if (b["rpq"] and b["ms"]) else None

            def s(v, w, p=1):
                return f"{v:{w}.{p}f}" if v is not None else " " * (w - 1) + "?"

            print(
                f"{b['q']:>11.0f} {s(b['nq'],6,0)} {s(b['rl'],8,0)} {s(b['rpq'],8)} "
                f"{s(b['ms'],8)} {s(b['ms_ext'],10)} {s(rps,8,0)} {b['rc']:>4} {b['sk']:>5}"
            )

        m = build_model(bands)
        if m is None:
            print("  !! no usable band (no relations and/or no timing). Read the *.tail.txt files.\n")
            continue
        pts, at = m
        q0 = pts[0]["q"]
        if len(pts) >= 2 and pts[0]["rpq"]:
            print(
                f"  yield decay: rel/q {pts[0]['rpq']:.1f} @q={pts[0]['q']:.3g} -> "
                f"{pts[-1]['rpq']:.1f} @q={pts[-1]['q']:.3g} "
                f"({pts[-1]['rpq'] / pts[0]['rpq']:.2f}x)"
            )
        print(
            f"  {'NEED(M)':>8} {'sieve s':>9} {'rel/s':>8} {'q_end':>9} {'total s':>9}  verdict"
        )
        for need in needs:
            t, qe, ex = project(at, q0, need)
            tot = t + a.overhead
            if t == float("inf"):
                v = "never (extrapolation floor)"
            else:
                v = "FITS" if t <= budget else "over by %.0f%%" % (100 * (tot / a.limit - 1))
            print(
                f"  {need / 1e6:>8.0f} {t:>9.0f} {(need / t if t not in (0, float('inf')) else 0):>8.0f} "
                f"{qe:>9.3g} {tot:>9.0f}  {v}{'  [EXTRAP]' if ex else ''}"
            )
        be = breakeven(at, q0, budget)
        print(f"  break-even: this regime can afford at most ~{be / 1e6:.0f}M raw relations\n")

    # ---- controlled comparison: regimes that differ only in mfb1 (2LP vs 3LP) ----
    names = list(data.keys())
    for i in range(len(names)):
        for j in range(len(names)):
            if i == j:
                continue
            A, B = data[names[i]], data[names[j]]
            a0 = sorted(A, key=lambda b: b["q"])[0]
            b0 = sorted(B, key=lambda b: b["q"])[0]
            if a0["lpb"] != b0["lpb"] or a0["mfb"][0] != b0["mfb"][0]:
                continue
            # only report the direction that actually adds large primes (2LP -> 3LP)
            if not (fnum(b0["mfb"][1]) or 0) > (fnum(a0["mfb"][1]) or 0):
                continue
            print(f"=== 3LP effect: {names[j]} (mfb1 {b0['mfb'][1]}) vs {names[i]} (mfb1 {a0['mfb'][1]})")
            byq = {round(b["q"]): b for b in A}
            print(f"{'q0':>11} {'rel/q A':>9} {'rel/q B':>9} {'x':>6} {'ms/q A':>8} {'ms/q B':>8} {'x':>6} {'rel/s x':>8}")
            for b in sorted(B, key=lambda b: b["q"]):
                aa = byq.get(round(b["q"]))
                if not aa or not aa["rpq"] or not aa["ms"] or not b["rpq"] or not b["ms"]:
                    continue
                rx = b["rpq"] / aa["rpq"]
                mx = b["ms"] / aa["ms"]
                sx = (b["rpq"] / b["ms"]) / (aa["rpq"] / aa["ms"])
                print(f"{b['q']:>11.0f} {aa['rpq']:>9.1f} {b['rpq']:>9.1f} {rx:>6.2f} "
                      f"{aa['ms']:>8.2f} {b['ms']:>8.2f} {mx:>6.2f} {sx:>8.2f}")
            print()

    print("Decision rule, fixed BEFORE measuring:")
    print("  FITS at NEED=250M            -> worth a ~100M-relation run to read the real purge curve")
    print("  FITS only at NEED=200M       -> marginal, needs a second lever")
    print("  does not fit at NEED=200M    -> the 3LP route is closed for this siever")
    print("Reminder: bottom-of-range bands over-state yield; the extrapolated tail is the weak part.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
