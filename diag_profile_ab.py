"""diag_profile_ab.py -- is the ~1.35x rate gap the production thread profile?

Context
-------
The 560 production note (rsa560_solver/pipeline_c169/factor_c169.sh:73) records
"blind GCP key 31 at 32/33: 14,774 s wall, 485M raw, N 16.8M", which implies
~40k rel/s.  Our own 580 measurement at the same lim is 29,614 rel/s
(JOURNAL_TENTATIVES.md, run R).  Two pipelines are near-identical (1687 vs 1689
lines), so the gap is profile or polynomial, not code.

The profile difference that could matter is the siever thread count: production
runs CONTAINER=1 -> NCPU=20, SIEVE_T=16; every 580 run so far went through
modal_rsa580.py with CONTAINER unset -> NCPU=24, SIEVE_T=20.

This runs the SAME q band twice, changing only -t, so the difference is
attributable.  If the two rates match, the profile is not the explanation and
the polynomial (ropt/sopt, never exercised here) is the remaining candidate.

Run (background, see HANDOFF 14.4 about SIGTERM):

  env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy \
      -u ALL_PROXY -u all_proxy \
  python -m modal run ./diag_profile_ab.py
"""

import os
import re
import subprocess
from pathlib import Path

import modal

SOLVER_DIR = Path(r"C:\Users\maxen\enigma_rsa\rsa580_solver")
POLY_FILE = Path(r"C:\Users\maxen\AppData\Local\Temp\poly_P.txt")

# 560 production set: lpb 32/33, mfb 64/66, lim 100M/150M (README.md:28)
RLIM, ALIM = 100_000_000, 150_000_000
LPB0, LPB1 = 32, 33
MFB0, MFB1 = 64, 66
LAMBDA0, LAMBDA1 = 2.0352, 2.0379
SIEVE_A = 29
Q0, Q1 = 2_200_000, 2_400_000   # same band as every previous 580 measurement
SECS = 180                      # per arm
ARMS = [16, 20]                 # SIEVE_T: production vs what we have been using

app = modal.App("rsa580-diagprofile")

image = (
    modal.Image.from_dockerfile(SOLVER_DIR / "Dockerfile", context_dir=SOLVER_DIR)
    .dockerfile_commands("RUN ln -sf /usr/bin/python3 /usr/local/bin/python")
    .entrypoint([])
)


def _count_rel(path):
    p = Path(path)
    if not p.exists():
        return 0
    n = 0
    for ln in p.read_text(errors="replace").splitlines():
        if ln and not ln.startswith("#"):
            n += 1
    return n


def _last_surv(path):
    p = Path(path)
    if not p.exists():
        return None
    last = None
    for ln in p.read_text(errors="replace").splitlines():
        m = re.search(r"q=(\d+);.*?(\d+) survivors", ln)
        if m:
            last = (int(m.group(1)), int(m.group(2)))
    return last


@app.function(image=image, gpu="RTX-PRO-6000", cpu=24, memory=32768, timeout=1800)
def ab(poly_text: str) -> dict:
    out = {}
    poly = "/tmp/poly.cado"
    Path(poly).write_text(poly_text)

    r = subprocess.run(
        ["/app/cado-filter/makefb", "-poly", poly, "-side", "1",
         "-lim", str(ALIM), "-maxbits", str((SIEVE_A + 1) // 2),
         "-t", "24", "-out", "/tmp/fb1"],
        capture_output=True, text=True,
    )
    out["makefb_rc"] = r.returncode
    if r.returncode != 0:
        out["makefb_err"] = r.stderr[-1500:]
        return out

    for t in ARMS:
        rel = f"/tmp/rel_t{t}.txt"
        log = f"/tmp/glas_t{t}.log"
        cmd = [
            "/app/glas/glas-gpu",
            "-poly", poly, "-fb1", "/tmp/fb1",
            "-lim0", str(RLIM), "-lim1", str(ALIM),
            "-lpb0", str(LPB0), "-lpb1", str(LPB1),
            "-mfb0", str(MFB0), "-mfb1", str(MFB1),
            "-lambda0", str(LAMBDA0), "-lambda1", str(LAMBDA1),
            "-ncurves0", "17", "-ncurves1", "17",
            "-A", str(SIEVE_A), "-q0", str(Q0), "-q1", str(Q1), "-sqside", "1",
            "-t", str(t), "-gpu", "-out", rel,
        ]
        with open(log, "wb") as fh:
            subprocess.run(["timeout", str(SECS)] + cmd, stdout=fh, stderr=subprocess.STDOUT)
        n = _count_rel(rel)
        out[f"t{t}"] = {
            "relations": n,
            "rel_per_s": round(n / SECS, 1),
            "last_q_survivors": _last_surv(log),
        }
    return out


@app.local_entrypoint()
def main() -> None:
    res = ab.remote(POLY_FILE.read_text())
    print("=== PROFILE A/B (lim 100M/150M, poly P, q 2.2M-2.4M) ===", flush=True)
    if "makefb_err" in res:
        print("makefb FAILED:", res["makefb_err"], flush=True)
        return
    for t in ARMS:
        d = res.get(f"t{t}", {})
        print(f"-t {t:>2} : {d.get('relations', 0):>8,} rel  "
              f"{d.get('rel_per_s', 0):>9,} rel/s   last_q/surv {d.get('last_q_survivors')}",
              flush=True)
    a = res.get(f"t{ARMS[0]}", {}).get("rel_per_s", 0)
    b = res.get(f"t{ARMS[1]}", {}).get("rel_per_s", 0)
    if a and b:
        print(f"\nratio -t{ARMS[0]} / -t{ARMS[1]} = {a/b:.3f}", flush=True)
        print("reference: run R measured 29,614 rel/s at this lim (CONTAINER=0, -t 20)", flush=True)
        print("target to close the gap: ~38,000-40,000 rel/s", flush=True)
