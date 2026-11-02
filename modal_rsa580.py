import base64
import os
import subprocess
import sys
from pathlib import Path

import modal


SOLVER_DIR = Path(r"C:\Users\maxen\enigma_rsa\rsa580_solver")
ENIGMA_DIR = Path(r"C:\Users\maxen\enigma")

# Regime A/B without touching the Dockerfile: any GLAS_*/RSA580_*/STOP_*/SIEVE_* variable set in the local shell is
# forwarded into the image env, where it overrides the Dockerfile's ENV for this run only. Example (3LP smoke test):
#   $env:GLAS_BUCKET_MARGIN="3"; $env:GLAS_SURV_DIV="16"; $env:GLAS_HITS_DIV="4"
#   $env:LPB1="32"; $env:MFB1="99"; $env:RLIM="100000000"; $env:ALIM="130000000"
#   $env:LAMBDA1="2.8"
#   modal run --detach .\modal_rsa580.py --difficulty 580 --seed 12345
# NOTE: the bare NFS knob names (LPB1, MFB1, RLIM, ALIM, ...) are forwarded too, and they are the ones that work:
# factor_c175.sh's `case $LPB1_CONF in 32) ;;` sets nothing, so RSA580_LPB1=32 falls through to `LPB1=${LPB1:-34}`.
ENV_EXACT = {
    "LPB0", "LPB1", "MFB0", "MFB1", "RLIM", "ALIM", "LAMBDA0", "LAMBDA1",
    "NCURVES0", "NCURVES1", "TD", "PS_SECS", "PS_MAX", "FIRST_PROBE", "PROBE_STEP",
    "PS_BATCHES", "PS_ADAPT", "PS_ADAPT_MAXB", "PS_ADAPT_E", "PS_NCPU", "PS_P", "PS_ADMAX",
    "PS_ADMIN", "PS_INCR", "PS_NQ", "PS_ADMAX_GPU", "POLY_ONLY", "POLY_IN", "POLY_TS", "POLY_B64",
}
ENV_OVERRIDE = {
    k: v
    for k, v in os.environ.items()
    if k.startswith(("GLAS_", "RSA580_", "RSA560_", "STOP_", "SIEVE_")) or k in ENV_EXACT
}

app = modal.App("rsa580-remote")

image = (
    modal.Image.from_dockerfile(
        SOLVER_DIR / "Dockerfile",
        context_dir=SOLVER_DIR,
    )
    .dockerfile_commands("RUN ln -sf /usr/bin/python3 /usr/local/bin/python")
    .env(ENV_OVERRIDE)
    .entrypoint([])
)


@app.function(
    image=image,
    gpu="RTX-PRO-6000",
    cpu=24,
    memory=87040,
    timeout=14400,
)
def run_solver(challenge_id: str, problem_json: str) -> int:
    # POLY_B64: base64 of a CADO polynomial file captured from an earlier run (POLY_ONLY=/dev/stdout). It is
    # materialised in the container and handed to the pipeline as POLY_IN, so a same-poly lim sweep skips the
    # polyselect re-roll: polyselect MurphyE varies ~5x run to run and would otherwise swamp the lim comparison.
    _b64 = os.environ.get("POLY_B64", "").strip()
    if _b64:
        with open("/tmp/poly_in.cado", "wb") as _fh:
            _fh.write(base64.b64decode(_b64))
        os.environ["POLY_IN"] = "/tmp/poly_in.cado"
        print("POLY_B64: using supplied polynomial /tmp/poly_in.cado", flush=True)
    return subprocess.run(
        [
            "python3",
            "/app/pipeline_c169/breaking_rsa.py",
            challenge_id,
            problem_json,
        ],
        check=False,
    ).returncode


@app.local_entrypoint()
def main(difficulty: int = 300, seed: int | None = None):
    sys.path.insert(0, str(ENIGMA_DIR))
    from workbench.challenges.breaking_rsa import generate_breaking_rsa

    problem, _, seed_used = generate_breaking_rsa(
        num_bits=difficulty,
        difficulty=difficulty,
        seed=seed,
    )
    challenge_id = f"modal-rsa580-{difficulty}-{seed_used}"
    print(f"Submitting {difficulty}-bit challenge to remote GPU.", flush=True)
    return run_solver.remote(challenge_id, problem.to_json())
