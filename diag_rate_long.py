"""diag_rate_long.py -- settle the real sieve rate at lim 100M/150M.

Two incompatible numbers exist for the same lim, polynomial and q band:

  23,088 rel/s  direct measurement (180 s, host wall clock, full GLAS_* env)
  29,614 rel/s  HANDOFF section 13 table, provenance unclear

The pipeline's `relq` is n/w where w is the BAND WIDTH IN q
(factor_c175.sh:1561), i.e. relations per q unit, not per second.  If the
29,614 was derived from relq, it is wrong by construction.

This runs 900 s of sieving on q starting at 2.2M with the full pipeline env
(GLAS_ADJUST=3, GLAS_ADJUST_SQUEEZE=3, all other GLAS_* as exported by
factor_c175.sh), and samples the relation count every 30 s with host-side
timestamps.  It reports the cumulative rate and the per-window rate, so the
steady-state value is separable from any warm-up.

Expected: ~20.8M relations if the rate is 23,088; ~26.6M if it is 29,614.

  env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy \
      -u ALL_PROXY -u all_proxy \
  python -m modal run ./diag_rate_long.py
"""

import os
import subprocess
import time
from pathlib import Path

import modal

SOLVER_DIR = Path(r"C:\Users\maxen\enigma_rsa\rsa580_solver")
POLY_FILE = Path(r"C:\Users\maxen\AppData\Local\Temp\poly_P.txt")

RLIM, ALIM = 100_000_000, 150_000_000
LPB0, LPB1 = 32, 33
MFB0, MFB1 = 64, 66
LAMBDA0, LAMBDA1 = 2.0352, 2.0379
SIEVE_A = 29
Q0, Q1 = 2_200_000, 4_000_000
SECS = 900
POLL = 30

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
    "GLAS_ADJUST": "3",
    "GLAS_ADJUST_SQUEEZE": "3",
}

app = modal.App("rsa580-diagrate")

image = (
    modal.Image.from_dockerfile(SOLVER_DIR / "Dockerfile", context_dir=SOLVER_DIR)
    .dockerfile_commands("RUN ln -sf /usr/bin/python3 /usr/local/bin/python")
    .entrypoint([])
)


class LineCounter:
    """Count complete lines incrementally: only new bytes are read each poll."""

    def __init__(self, path):
        self.path = Path(path)
        self.off = 0
        self.n = 0
        self.partial = 0

    def poll(self):
        if not self.path.exists():
            return self.n
        with open(self.path, "rb") as fh:
            fh.seek(self.off)
            chunk = fh.read()
        if not chunk:
            return self.n
        self.off += len(chunk)
        self.n += chunk.count(b"\n")
        return self.n


@app.function(image=image, gpu="RTX-PRO-6000", cpu=24, memory=32768, timeout=2400)
def measure(poly_text: str) -> dict:
    poly = "/tmp/poly.cado"
    Path(poly).write_text(poly_text)

    r = subprocess.run(
        ["/app/cado-filter/makefb", "-poly", poly, "-side", "1",
         "-lim", str(ALIM), "-maxbits", str((SIEVE_A + 1) // 2),
         "-t", "24", "-out", "/tmp/fb1"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return {"err": r.stderr[-1500:]}

    rel = "/tmp/rel_long.txt"
    log = "/tmp/glas_long.log"
    env = os.environ.copy()
    env.update(PIPELINE_GLAS_ENV)

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

    counter = LineCounter(rel)
    samples = []
    t0 = time.monotonic()
    with open(log, "wb") as fh:
        proc = subprocess.Popen(cmd, env=env, stdout=fh, stderr=subprocess.STDOUT)
        try:
            while time.monotonic() - t0 < SECS:
                time.sleep(POLL)
                el = time.monotonic() - t0
                samples.append((round(el, 1), counter.poll()))
                if proc.poll() is not None:
                    break
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    proc.kill()

    el = time.monotonic() - t0
    n = counter.poll()
    logtail = Path(log).read_text(errors="replace")[-1500:] if Path(log).exists() else ""
    return {
        "elapsed": round(el, 1),
        "relations": n,
        "samples": samples,
        "log_tail": logtail,
    }


@app.local_entrypoint()
def main() -> None:
    res = measure.remote(POLY_FILE.read_text())
    if "err" in res:
        print("makefb FAILED:", res["err"], flush=True)
        return

    el = res["elapsed"]
    n = res["relations"]
    samples = res["samples"]

    print("=== LONG RATE MEASUREMENT (lim 100M/150M, poly P, ADJUST=3 SQUEEZE=3) ===", flush=True)
    print(f"wall {el:.1f} s   relations {n:,}   mean {n/el:,.1f} rel/s\n", flush=True)

    print(f"{'t (s)':>7} {'cum rel':>12} {'window rel/s':>13} {'cum rel/s':>10}", flush=True)
    prev_t, prev_n = 0.0, 0
    for t, c in samples:
        dt = t - prev_t
        dn = c - prev_n
        wr = dn / dt if dt > 0 else 0
        print(f"{t:>7.0f} {c:>12,} {wr:>13,.0f} {c/t:>10,.0f}", flush=True)
        prev_t, prev_n = t, c

    # steady state: second half of the run
    half = len(samples) // 2
    if len(samples) >= 4:
        t1, c1 = samples[half]
        t2, c2 = samples[-1]
        if t2 > t1:
            print(f"\nsteady-state (last {t2-t1:.0f} s): {(c2-c1)/(t2-t1):,.1f} rel/s", flush=True)
    print(f"whole run: {n/el:,.1f} rel/s", flush=True)
    print("\nreferences: 23,088 (direct 180 s) vs 29,614 (HANDOFF 13 table)", flush=True)
    print("expected relations at 900 s: 20.8M (23,088) / 26.6M (29,614)", flush=True)
