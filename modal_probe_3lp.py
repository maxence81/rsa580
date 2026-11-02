"""Modal runner for the cuda-sieve 3LP probe on the c175 polynomial.

Local inputs (env vars, defaults below):
  CS_LOCAL    dir with `bench` and `fbgen_gpu` (extracted from the 530 solution zip)
  POLY_LOCAL  CADO-format c175 polynomial (poly_P.txt)

Run from the repo root, proxy vars removed, in the background:
  CS_LOCAL='C:\\Users\\maxen\\sol_enum\\badf0faf\\cuda-sieve' \
  POLY_LOCAL='C:\\Users\\maxen\\AppData\\Local\\Temp\\poly_P.txt' \
  env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy \
    python -m modal run ./modal_probe_3lp.py
"""
import os
import pathlib
import time

import modal

HERE = pathlib.Path(__file__).resolve().parent
CS_LOCAL = os.environ.get("CS_LOCAL", r"C:\Users\maxen\sol_enum\badf0faf\cuda-sieve")
POLY_LOCAL = os.environ.get("POLY_LOCAL", r"C:\Users\maxen\AppData\Local\Temp\poly_P.txt")
POLYSEL = os.environ.get(
    "POLYSEL_LOCAL", str(HERE / "rsa580_solver" / "pipeline_c169" / "polysel160.py")
)

# Ubuntu 24.04 userland: the 530 binaries were built in
# nvidia/cuda:13.0.1-devel-ubuntu24.04 (glibc 2.39).
image = (
    modal.Image.from_registry("nvidia/cuda:13.0.1-runtime-ubuntu24.04", add_python="3.11")
    .apt_install("bash", "coreutils", "grep", "gawk", "time")
    .add_local_file(os.path.join(CS_LOCAL, "bench"), "/opt/cuda-sieve/bench")
    .add_local_file(os.path.join(CS_LOCAL, "fbgen_gpu"), "/opt/cuda-sieve/fbgen_gpu")
    .add_local_file(POLYSEL, "/opt/pipeline/polysel160.py")
    .add_local_file(str(HERE / "probe_3lp.sh"), "/opt/pipeline/probe_3lp.sh")
    .add_local_file(str(HERE / "probe_3lp_analyze.py"), "/opt/pipeline/probe_3lp_analyze.py")
    .add_local_file(POLY_LOCAL, "/opt/poly_P.txt")
)

app = modal.App("rsa580-probe-3lp")


@app.function(image=image, gpu="RTX-PRO-6000", cpu=8, memory=32768, timeout=5400)
def run(env: dict) -> dict:
    import subprocess

    e = dict(os.environ)
    e.update({k: v for k, v in env.items() if v})
    p = subprocess.run(
        ["bash", "/opt/pipeline/probe_3lp.sh"], env=e, capture_output=True, text=True
    )
    out = {"stdout": p.stdout, "stderr": p.stderr[-6000:], "rc": p.returncode, "files": {}}
    for f in sorted(pathlib.Path(e.get("OUT", "/tmp/probe_out")).glob("*")):
        if f.suffix in (".txt", ".tsv", ".log") and f.stat().st_size < 400_000:
            out["files"][f.name] = f.read_text(errors="replace")[-20000:]
    return out


@app.local_entrypoint()
def main(regimes: str = "", bands: str = "", analyze_args: str = ""):
    res = run.remote({"REGIMES": regimes, "BANDS": bands, "ANALYZE_ARGS": analyze_args})
    print(res["stdout"])
    print("rc:", res["rc"])
    if res["stderr"].strip():
        print("stderr tail:\n", res["stderr"])
    d = HERE / f"probe_3lp_result_{time.strftime('%Y%m%d_%H%M%S')}"
    d.mkdir(exist_ok=True)
    for n, t in res["files"].items():
        (d / n).write_text(t, encoding="utf-8")
    print("saved:", d)
