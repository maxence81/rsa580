"""diag_3lp_cofac.py -- one-off diagnostic: what do GLAS's 3LP leftovers look like?

Why
---
A 3LP glas session produces ZERO relations in ~19 min with no error and no
overflow (HANDOFF 15.5).  The source shows the cofactorisation is done on the
HOST by facul (glas.cpp:1276-1310), and that a never-wired hook
GLAS_COFAC_DUMP=path dumps every candidate leftover before facul runs.

This runs makefb + a SHORT glas 3LP session with that hook enabled, then prints
the dump as base64 so it can be analysed locally with
rsa580_solver/tools/cofac_dump_stats.py.

  median leftover <= 65 b  -> facul splits in microseconds; the blocker is the
                              caps / survivor filter, i.e. fixable.
  median leftover >= 85 b  -> facul's ECM cost per candidate is the wall; 3LP
                              needs decoupled cofactorisation.
  0 candidates             -> the rejection is UPSTREAM of cofactorisation, so
                              the ECM hypothesis is wrong.

Run (always detached/background, see HANDOFF 14.4 about SIGTERM):

  env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy \
      -u ALL_PROXY -u all_proxy \
  python -m modal run ./diag_3lp_cofac.py
"""

import base64
import os
import subprocess
from pathlib import Path

import modal

SOLVER_DIR = Path(r"C:\Users\maxen\enigma_rsa\rsa580_solver")
# explicit Windows path: Git Bash /tmp and Python's /tmp are not reliably the same place
POLY_FILE = Path(r"C:\Users\maxen\AppData\Local\Temp\poly_P.txt")

# 3LP regime under test: CADO's own c175 lims, mfb high enough for 3 primes.
RLIM, ALIM = 48_000_000, 67_000_000
LPB0, LPB1 = 32, 33
MFB0, MFB1 = 90, 92
LAMBDA0, LAMBDA1 = 2.81, 2.79
SIEVE_A = 29
Q0, Q1 = 2_200_000, 2_400_000   # the same band the 2LP rate measurements used
SIEVE_SECS = 240                # short: we want the leftover distribution, not relations

app = modal.App("rsa580-diag3lp")

image = (
    modal.Image.from_dockerfile(SOLVER_DIR / "Dockerfile", context_dir=SOLVER_DIR)
    .dockerfile_commands("RUN ln -sf /usr/bin/python3 /usr/local/bin/python")
    .entrypoint([])
)


def _run(cmd, env, log_path):
    with open(log_path, "wb") as fh:
        return subprocess.run(cmd, env=env, stdout=fh, stderr=subprocess.STDOUT)


@app.function(image=image, gpu="RTX-PRO-6000", cpu=24, memory=32768, timeout=1800)
def diag(poly_text: str) -> dict:
    out = {}

    poly = "/tmp/poly.cado"
    Path(poly).write_text(poly_text)
    out["poly_lines"] = len(poly_text.strip().splitlines())

    # side-1 factor base, exactly as the pipeline builds it (factor_c175.sh:820-821)
    rc = _run(
        ["/app/cado-filter/makefb", "-poly", poly, "-side", "1",
         "-lim", str(ALIM), "-maxbits", str((SIEVE_A + 1) // 2),
         "-t", "24", "-out", "/tmp/fb1"],
        os.environ.copy(), "/tmp/makefb.log",
    )
    out["makefb_rc"] = rc.returncode
    out["fb1_bytes"] = os.path.getsize("/tmp/fb1") if os.path.exists("/tmp/fb1") else 0
    if rc.returncode != 0:
        out["makefb_log"] = Path("/tmp/makefb.log").read_text(errors="replace")[-2000:]
        return out

    env = os.environ.copy()
    env["GLAS_COFAC_DUMP"] = "/tmp/cof.bin"

    cmd = [
        "/app/glas/glas-gpu",
        "-poly", poly, "-fb1", "/tmp/fb1",
        "-lim0", str(RLIM), "-lim1", str(ALIM),
        "-lpb0", str(LPB0), "-lpb1", str(LPB1),
        "-mfb0", str(MFB0), "-mfb1", str(MFB1),
        "-lambda0", str(LAMBDA0), "-lambda1", str(LAMBDA1),
        "-ncurves0", "17", "-ncurves1", "17",
        "-A", str(SIEVE_A), "-q0", str(Q0), "-q1", str(Q1), "-sqside", "1",
        "-t", "20", "-gpu", "-out", "/tmp/rel.txt",
    ]
    out["cmd"] = " ".join(cmd)

    # timeout: the dump is fflush()ed after every candidate batch, so a kill
    # still leaves a readable file (glas.cpp:1129).
    rc = _run(["timeout", str(SIEVE_SECS)] + cmd, env, "/tmp/glas.log")
    out["glas_rc"] = rc.returncode

    glog = Path("/tmp/glas.log").read_text(errors="replace")
    out["glas_log_tail"] = glog[-3000:]

    relf = Path("/tmp/rel.txt")
    out["relations"] = 0
    if relf.exists():
        txt = relf.read_text(errors="replace")
        out["relations"] = sum(1 for ln in txt.splitlines() if ln and not ln.startswith("#"))
        out["rel_head"] = txt[:600]

    cof = Path("/tmp/cof.bin")
    if cof.exists() and cof.stat().st_size > 72:
        raw = cof.read_bytes()
        out["cof_bytes"] = len(raw)
        out["cof_candidates"] = (len(raw) - 72) // 32
        out["cof_b64"] = base64.b64encode(raw).decode()
    else:
        out["cof_bytes"] = cof.stat().st_size if cof.exists() else 0
        out["cof_candidates"] = 0
    return out


@app.local_entrypoint()
def main() -> None:
    poly_text = POLY_FILE.read_text()
    res = diag.remote(poly_text)

    print("=== DIAG 3LP COFACTORISATION ===", flush=True)
    for k in ("poly_lines", "makefb_rc", "fb1_bytes", "glas_rc", "relations",
              "cof_bytes", "cof_candidates"):
        print(f"{k:18} {res.get(k)}", flush=True)
    if "makefb_log" in res:
        print("--- makefb log ---", flush=True)
        print(res["makefb_log"], flush=True)
    if res.get("rel_head"):
        print("--- relations head ---", flush=True)
        print(res["rel_head"], flush=True)
    print("--- glas log tail ---", flush=True)
    print(res.get("glas_log_tail", ""), flush=True)

    if res.get("cof_b64"):
        dst = Path(r"C:\Users\maxen\enigma_rsa\cof_3lp.bin")
        dst.write_bytes(base64.b64decode(res["cof_b64"]))
        print(f"DUMP_WRITTEN {dst} ({res['cof_candidates']} candidates)", flush=True)
        print("now: python rsa580_solver/tools/cofac_dump_stats.py cof_3lp.bin", flush=True)
    else:
        print("NO DUMP: zero candidates reached cofactorisation", flush=True)
