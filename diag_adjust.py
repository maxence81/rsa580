"""diag_adjust.py -- how much of the rate comes from the GLAS_* patch stack?

The previous A/B (diag_profile_ab.py) showed -t is irrelevant (ratio 1.000) but
also measured only 15,372 rel/s where the pipeline sees 29,614 at the same lim
and polynomial.  The difference is that the pipeline exports ~10 GLAS_*
variables, and the binary's compiled-in defaults are the UNPATCHED behaviour:

  glas-adjust-strategy.patch:25
    static int const v = getenv("GLAS_ADJUST") ? atoi(getenv("GLAS_ADJUST")) : 0;

This isolates GLAS_ADJUST (0 vs 3) with every other pipeline GLAS_* knob set,
so the difference is attributable to that one variable.

  arm adjust0 -> if ~15.4k, GLAS_ADJUST alone is the whole 1.93x
  arm adjust3 -> should reproduce the pipeline's ~29.6k (validation)

Run in background:

  env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy \
      -u ALL_PROXY -u all_proxy \
  python -m modal run ./diag_adjust.py
"""

import os
import re
import subprocess
from pathlib import Path

import modal

SOLVER_DIR = Path(r"C:\Users\maxen\enigma_rsa\rsa580_solver")
POLY_FILE = Path(r"C:\Users\maxen\AppData\Local\Temp\poly_P.txt")

RLIM, ALIM = 100_000_000, 150_000_000
LPB0, LPB1 = 32, 33
MFB0, MFB1 = 64, 66
LAMBDA0, LAMBDA1 = 2.0352, 2.0379
SIEVE_A = 29
Q0, Q1 = 2_200_000, 2_400_000
SECS = 180

# exactly the exports of factor_c175.sh (lines 173-183), minus GLAS_ADJUST
PIPELINE_GLAS_ENV = {
    "GLAS_RHITS": "0",
    "GLAS_FILL_COPRIME": "3",
    "GLAS_REGION_PREFETCH": "1",
    "GLAS_XFUSE": "1",
    "GLAS_XFUSE_GRID": "752",
    "GLAS_NARROW": "1",
    "GLAS_IDIV": "1",
    "GLAS_P1": "3",
    "GLAS_REGION_HALF": "1",
    "GLAS_REGION_RX": "1",
}

app = modal.App("rsa580-diagadjust")

image = (
    modal.Image.from_dockerfile(SOLVER_DIR / "Dockerfile", context_dir=SOLVER_DIR)
    .dockerfile_commands("RUN ln -sf /usr/bin/python3 /usr/local/bin/python")
    .entrypoint([])
)


def _count_rel(path):
    p = Path(path)
    if not p.exists():
        return 0
    return sum(1 for ln in p.read_text(errors="replace").splitlines()
               if ln and not ln.startswith("#"))


def _adjust_report(path):
    p = Path(path)
    if not p.exists():
        return None
    for ln in p.read_text(errors="replace").splitlines():
        if "GLAS_ADJUST" in ln and "basis changed" in ln:
            return ln.strip()
    return None


@app.function(image=image, gpu="RTX-PRO-6000", cpu=24, memory=32768, timeout=1800)
def run(poly_text: str) -> dict:
    out = {}
    poly = "/tmp/poly.cado"
    Path(poly).write_text(poly_text)

    r = subprocess.run(
        ["/app/cado-filter/makefb", "-poly", poly, "-side", "1",
         "-lim", str(ALIM), "-maxbits", str((SIEVE_A + 1) // 2),
         "-t", "24", "-out", "/tmp/fb1"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        out["err"] = r.stderr[-1500:]
        return out

    for adjust, squeeze in ((3, 1), (3, 3)):
        tag = f"a{adjust}s{squeeze}"
        rel = f"/tmp/rel_{tag}.txt"
        log = f"/tmp/glas_{tag}.log"
        env = os.environ.copy()
        env.update(PIPELINE_GLAS_ENV)
        env["GLAS_ADJUST"] = str(adjust)
        env["GLAS_ADJUST_SQUEEZE"] = str(squeeze)
        env["GLAS_ADJUST_VERBOSE"] = "1"

        cmd = [
            "/app/glas/glas-gpu",
            "-poly", poly, "-fb1", "/tmp/fb1",
            "-lim0", str(RLIM), "-lim1", str(ALIM),
            "-lpb0", str(LPB0), "-lpb1", str(LPB1),
            "-mfb0", str(MFB0), "-mfb1", str(MFB1),
            "-lambda0", str(LAMBDA0), "-lambda1", str(LAMBDA1),
            "-ncurves0", "17", "-ncurves1", "17",
            "-A", str(SIEVE_A), "-q0", str(Q0), "-q1", str(Q1), "-sqside", "1",
            "-t", "16", "-gpu", "-out", rel,
        ]
        with open(log, "wb") as fh:
            subprocess.run(["timeout", str(SECS)] + cmd, env=env,
                           stdout=fh, stderr=subprocess.STDOUT)
        n = _count_rel(rel)
        out[tag] = {
            "relations": n,
            "rel_per_s": round(n / SECS, 1),
            "adjust_report": _adjust_report(log),
        }
    return out


@app.local_entrypoint()
def main() -> None:
    res = run.remote(POLY_FILE.read_text())
    print("=== GLAS_ADJUST_SQUEEZE (ADJUST=3, all other pipeline GLAS_* set, -t 16) ===", flush=True)
    if "err" in res:
        print("makefb FAILED:", res["err"], flush=True)
        return
    for tag in ("a3s1", "a3s3"):
        d = res.get(tag, {})
        print(f"{tag} : {d.get('relations', 0):>9,} rel  {d.get('rel_per_s', 0):>9,} rel/s",
              flush=True)
        if d.get("adjust_report"):
            print(f"        {d['adjust_report']}", flush=True)
    r1 = res.get("a3s1", {}).get("rel_per_s", 0)
    r3 = res.get("a3s3", {}).get("rel_per_s", 0)
    if r1 and r3:
        print(f"\ngain SQUEEZE 3 vs 1 = {r3/r1:.3f}x", flush=True)
    print("references: ADJUST=0 = 15,372 | ADJUST=3,SQUEEZE=1 = 22,037 | pipeline = 29,614", flush=True)
