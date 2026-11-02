"""Minimal Modal probe: tells us whether the active workspace can still start a GPU container.

Used to pick a profile with remaining credits before spending on a real RSA-580 run.
Costs ~nothing (a few seconds of a cheap CPU container).
"""

import modal

app = modal.App("rsa580-probe")


@app.function(image=modal.Image.debian_slim(python_version="3.11"), cpu=1, timeout=60)
def ping() -> str:
    return "ok"


@app.local_entrypoint()
def main() -> None:
    print("PROBE_RESULT:", ping.remote(), flush=True)
