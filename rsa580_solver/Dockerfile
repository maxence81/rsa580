# Dockerfile -- the RSA-580 SUBMISSION image (Enigma SN63 "Breaking RSA", 580-bit / c175). The validator builds
# it itself from the submission zip (gpu/ops/make_submission.sh puts this file at the zip root as `Dockerfile`, next to
# the vendored CADO tree and the pipeline), so the build is kept lean and fail-closed: pinned base images (tag@digest)
# and pip versions, the CADO-NFS source VENDORED in the context (no clone at build time), no optional stages.
#
#   /app/glas/glas-gpu, gps1       Cognition glas + gps1 (LGPL-2.1, gpu-siever/ of Cognition CADO-NFS b5ca9c4), sm_120,
#                                  the production patch stack of gpu/sandbox_bootstrap.sh (same patches, same order)
#   /app/cado-filter/*, /app/msieve-gpu/*, /app/bwc, /app/pipeline_c169   CADO binaries + the c169/c175 pipeline
#   CuPy stack pinned to the 530 image's versions (gpu_la.py)
# The cuda-sieve/gchilders bench and cofac_cpu (SIEVER=bench only) were dropped 2026-10-25: production is SIEVER=glas.
#
# build (x86_64 host; context = the flattened submission zip):
#   docker build -t rsa580 .
# run EXACTLY as the validator (two positional args, stdout = logs + separator + base64 zip):
#   docker run --rm --gpus all --network none --read-only --tmpfs /tmp:rw,noexec,nosuid,size=10g --memory 85g --cpus 24 \
#     --user miner rsa580 <challenge_id> '{"difficulty":580,"num":"<N>","num_bits":580}'
# runtime = non-root `miner`, ENTRYPOINT breaking_rsa.py, CONTAINER=1 (the validator profile of factor_c169.sh,
# docs/rsa560_container_audit.md), HOME/caches on /tmp, RSA580_LPB1=34 (the large-prime switch, see the ENV below).
# Every binary at -march=x86-64-v3 (never -march=native / AVX-512: the validator CPU is EPYC 9555 or Xeon 6980P).
# make -j is capped at 32 (an unknown validator build host may have 192+ threads and a memory-capped builder).
ARG CUDA_IMAGE=nvidia/cuda:13.0.1-devel-ubuntu24.04@sha256:7d2f6a8c2071d911524f95061a0db363e24d27aa51ec831fcccf9e76eb72bc92
FROM ${CUDA_IMAGE} AS build
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential cmake git libgmp-dev libhwloc-dev zlib1g-dev python3 python3-flask python3-requests \
        python3-numpy gzip bc procps util-linux coreutils perl patch ca-certificates binutils \
    && rm -rf /var/lib/apt/lists/*

# ---- CADO-NFS (Cognition tree b5ca9c4, vendored; FLAGS_SIZE 64-bit p_r values: lpb 33 needs them in freerel/renumber/
#      dup2/purge/characters/sqrt). Patches exactly as gpu/sandbox_bootstrap.sh: symlink write-through, SQRT_L00, CHARS_PRE.
#      (cado-characters-parallel.patch is NOT applied: no measured run used it.) -march=x86-64-v3, checked for zmm/kmask.
COPY third_party/cado-nfs-public /src/cado-nfs
COPY pipeline_c169/vendor/cado-symlink-writethrough-cognition.patch gpu/chars_pre_patch.py gpu/sqrt_l00_patch.py gpu/sqrt_l00.hpp gpu/purge_parts_patch.py /src/patches/
# the validator's unzip (copyfileobj) drops every mode bit: restore +x on each script (a '#!' first line) before make
# (CADO's Makefile execs scripts/call_cmake.sh); gpu/ops/make_submission.sh also dereferences the tree's symlinks
RUN set -e; cd /src/cado-nfs; python3 -c 'import os,sys; [os.chmod(q, os.stat(q).st_mode | 0o755) for t in sys.argv[1:] for r, _, fs in os.walk(t) for q in (os.path.join(r, f) for f in fs) if not os.path.islink(q) and open(q, "rb").read(2) == b"#!"]' /src/cado-nfs; \
    [ -x scripts/call_cmake.sh ] || { echo "scripts/call_cmake.sh not executable"; exit 1; }; \
    grep -q b5ca9c4fd3e331edc8978f93830f8de1e8dda70c COGNITION_COMMIT || { echo "CADO tree is not b5ca9c4"; exit 1; }; \
    p=/src/patches/cado-symlink-writethrough-cognition.patch; \
    if patch -p1 -N --dry-run -s < "$p" >/dev/null 2>&1; then patch -p1 -N -s < "$p"; echo "applied $p"; \
    elif patch -p1 -R --dry-run -s < "$p" >/dev/null 2>&1; then echo "already present $p"; \
    else echo "PATCH $p DOES NOT APPLY"; exit 1; fi; \
    python3 /src/patches/sqrt_l00_patch.py sqrt/sqrt.cpp; python3 /src/patches/chars_pre_patch.py linalg/characters.cpp; \
    python3 /src/patches/purge_parts_patch.py filter/purge.cpp; \
    grep -q CADO_PURGE_ORDERED filter/purge.cpp || { echo "PURGE_ORDERED patch missing"; exit 1; }; \
    grep -q SQRT_L00 sqrt/sqrt.cpp || { echo "SQRT_L00 patch missing"; exit 1; }; \
    grep -q CADO_CHARS_SCMAT linalg/characters.cpp || { echo "CHARS_PRE patch missing"; exit 1; }; \
    rm -f local.sh; \
    printf 'CFLAGS="-O3 -march=x86-64-v3"\nCXXFLAGS="-O3 -march=x86-64-v3 -std=c++20"\nFLAGS_SIZE="-DSIZEOF_P_R_VALUES=8"\n' > local.sh; \
    NO_PYTHON_CHECK=1 make -j"$(n=$(nproc); [ "$n" -gt 32 ] && n=32; echo "$n")"; \
    B=$(ls -d build/*/ | head -1); echo "$B" > /src/cado-build-dir; \
    for b in filter/purge filter/merge filter/dup1 filter/dup2 filter/replay sieve/las sieve/makefb sieve/freerel linalg/characters sqrt/sqrt \
             polyselect/polyselect polyselect/polyselect_ropt polyselect/sopt; do \
        [ -x "$B/$b" ] || { echo "missing $B/$b"; exit 1; }; \
        n=$(objdump -d "$B/$b" | grep -cE '%zmm|\{%k[0-7]\}' || true); echo "$b zmm/kmask insns: $n"; [ "$n" = 0 ]; done

# ---- glas-gpu + gps1 (gpu-siever/ of the same tree; the plain CADO build is what they link against) ----
#      CUDA_ARCH=120 (sm_120, RTX PRO 6000 / 5070 / 5090). No NCCL, no MPI: only the siever and the GPU polyselect.
#      Production patch stack, SAME order as gpu/sandbox_bootstrap.sh (every measured siever win; fail closed: a patch error
#      aborts the build instead of shipping a partially patched siever). Added 2026-10-23: the image had only glas_adjust.
COPY gpu/glas_adjust_patch.py gpu/glas_coprime_patch.py gpu/glas_prefetch_patch.py gpu/glas_xfuse_patch.py gpu/glas_region_patch.py \
     gpu/glas_xfgrid_patch.py gpu/glas_session_patch.py gpu/glas_narrow_patch.py gpu/glas_p1_patch.py \
     gpu/glas_caps_patch.py gpu/glas_empty_pattern_patch.py gpu/gps1_stats_patch.py gpu/gps1_fastsort_patch.py /src/patches/
RUN cd /src/cado-nfs/gpu-siever && set -e && python3 /src/patches/glas_adjust_patch.py src/glas.cpp && \
    python3 /src/patches/glas_coprime_patch.py src/sieve_core_gpu.cu && python3 /src/patches/glas_prefetch_patch.py src/sieve_core_gpu.cu && \
    python3 /src/patches/glas_xfuse_patch.py src/sieve_core_gpu.cu && python3 /src/patches/glas_region_patch.py src/sieve_core_gpu.cu && \
    python3 /src/patches/glas_xfgrid_patch.py src/sieve_core_gpu.cu && python3 /src/patches/glas_session_patch.py src/glas.cpp src/sieve_core_gpu.cu && \
    python3 /src/patches/glas_narrow_patch.py src/sieve_core_gpu.cu && python3 /src/patches/glas_p1_patch.py src/sieve_core_gpu.cu && \
    python3 /src/patches/glas_caps_patch.py src/sieve_core_gpu.cu && \
    python3 /src/patches/glas_empty_pattern_patch.py src/sieve_core_gpu.cu && sed -i 's/^#define GLAS_EMPTY_PATTERN 0$/#define GLAS_EMPTY_PATTERN 1/' src/sieve_core_gpu.cu && \
    grep -q "^#define GLAS_EMPTY_PATTERN 1$" src/sieve_core_gpu.cu && \
    python3 /src/patches/gps1_stats_patch.py . && python3 /src/patches/gps1_fastsort_patch.py . && grep -q GPS1_FASTSORT polyselect/gps1_kernels.cu && \
    for m in GLAS_XFUSE_GRID GLAS_SESSION GLAS_IDIV GLAS_REGION_RX GLAS_P1 GLAS_BUCKET_MARGIN GLAS_SURV_DIV; do grep -q "$m" src/sieve_core_gpu.cu src/glas.cpp || { echo "patch marker $m missing"; exit 1; }; done && \
    B=/src/cado-nfs/$(cat /src/cado-build-dir) && \
    make glas-gpu gps1 CADO_SRC=/src/cado-nfs CADO_BUILD="$B" CUDA_ARCH=120 \
         CXXFLAGS="-O3 -std=c++20 -march=x86-64-v3 -Wall" -j"$(n=$(nproc); [ "$n" -gt 32 ] && n=32; echo "$n")" && \
    mkdir -p /app/glas && cp glas-gpu gps1 /app/glas/ && \
    for m in GLAS_XFUSE_GRID GLAS_SESSION GLAS_IDIV GLAS_REGION_RX GLAS_P1 GLAS_BUCKET_MARGIN GLAS_SURV_DIV; do strings glas-gpu | grep -q "$m" || { echo "glas-gpu lacks marker $m"; exit 1; }; done && \
    { strings gps1 | grep -q GPS1_FASTSORT || { echo "gps1 lacks GPS1_FASTSORT"; exit 1; }; } && \
    for b in glas-gpu gps1; do n=$(objdump -d "$b" | grep -cE '%zmm|\{%k[0-7]\}' || true); echo "$b zmm/kmask insns: $n"; [ "$n" = 0 ]; done

# ---- pipeline layout (as docker/Dockerfile.c169-cpu) ----
RUN B=/src/cado-nfs/$(cat /src/cado-build-dir) && mkdir -p /app/cado-filter /app/msieve-gpu && \
    for p in sieve/las sieve/makefb sieve/freerel polyselect/polyselect polyselect/polyselect_ropt polyselect/sopt \
             filter/dup1 filter/dup2 filter/purge filter/merge filter/replay; do cp "$B/$p" /app/cado-filter/; done && \
    cp "$B/linalg/characters" /app/msieve-gpu/characters && cp "$B/sqrt/sqrt" /app/msieve-gpu/sqrt && \
    cp "$B/filter/replay" /app/msieve-gpu/replay && cp -r "$B/linalg/bwc" /app/bwc
COPY pipeline_c169 /app/pipeline_c169
RUN ln -s /app/pipeline_c169 /app/pipeline_c175
# the production downstream (gpu/sandbox_bootstrap.sh section 5): gpu_la_fast.py (GPU combine) + the .cu kernel sources
# gpu_la.py reads at run time + the C host algebra (ctypes-loaded FROM /app: never built or loaded from /tmp, noexec) +
# abx (SQRT_ABX) + gpu_mul.so (CADO sqrt's GPU NTT multiply, PAR_MUL_GPU; dlopen'ed from /app). Portable flags only.
RUN cc -O2 -o /app/cado-filter/cado2msieve2 /app/pipeline_c169/cado-filter/cado2msieve2.c && \
    cp /app/pipeline_c169/cado-filter/cado_filter160.sh /app/pipeline_c169/cado-filter/cado_incdup.sh /app/cado-filter/ && \
    for f in ds_cado.sh gpu_la.py gpu_la_fast.py cado_mat.py segspmv.py ks256.cu ks256g.cu ks256v2.cu ks256v3.cu; do \
        cp /app/pipeline_c169/msieve-gpu/$f /app/msieve-gpu/; done && \
    gcc -O2 -march=x86-64-v3 -shared -fPIC -o /app/msieve-gpu/la128host.so /app/pipeline_c169/msieve-gpu/la128host.c && \
    gcc -O2 -march=x86-64-v3 -shared -fPIC -o /app/msieve-gpu/la256host.so /app/pipeline_c169/msieve-gpu/la256host.c && \
    gcc -O2 -march=x86-64-v3 -pthread -o /app/msieve-gpu/abx /app/pipeline_c169/msieve-gpu/abx.c && \
    nvcc -O3 -std=c++17 -arch=sm_120 -shared -Xcompiler -fPIC,-march=x86-64-v3 -o /app/msieve-gpu/gpu_mul.so /src/cado-nfs/sqrt/gpu_mul.cu -lcudart && \
    chmod +x /app/pipeline_c169/*.sh /app/cado-filter/*.sh /app/msieve-gpu/*.sh && \
    python3 -c 'import os,sys; [os.chmod(q, os.stat(q).st_mode | 0o755) for t in sys.argv[1:] for r, _, fs in os.walk(t) for q in (os.path.join(r, f) for f in fs) if not os.path.islink(q) and open(q, "rb").read(2) == b"#!"]' /app/pipeline_c169 && \
    chmod -R a+rX /app

# ---- runtime image: CUDA runtime + the pinned CuPy stack of the 530 image (gpu_la.py) ----
FROM nvidia/cuda:13.0.1-runtime-ubuntu24.04@sha256:c3fde347d52d578c84fd644bc177bc7ec333feaf11550d990da4084d7612e4c7
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip bash coreutils findutils gzip zstd bc procps util-linux perl \
        libgmp10 libgomp1 libhwloc15 libstdc++6 zlib1g \
    && rm -rf /var/lib/apt/lists/*
RUN pip3 install --no-cache-dir --break-system-packages \
        numpy==2.4.6 "cupy-cuda13x[ctk]==14.2.0" gmpy2==2.3.1 \
    && pip3 install --no-cache-dir --break-system-packages \
        "cuda-toolkit[cublas,cudart,cufft,curand,cusolver,cusparse,nvrtc]==13.0.1" \
        "nvidia-cublas==13.0.2.14" "cuda-pathfinder==1.8.2" "nvidia-nvjitlink==13.4.92"
COPY --from=build /app /app
# the stdout protocol (engine/enigma_challenges/solution_output.py, vendored from the validator SDK)
COPY engine/enigma_challenges /app/engine/enigma_challenges
# THE large-prime switch (factor_c169.sh CONTAINER=1 profile).
#
# 2026-11-02 CORRECTION: this used to be `LPB1=34 MFB1=68 RLIM=250M ALIM=600M`, i.e. FB = pi(250M)+pi(600M)
# ~= 45.2M columns. Measured at ~38,700 s end-to-end (JOURNAL_TENTATIVES.md 9, HANDOFF 9-10): 2.7x the 14,400 s
# budget, because the relation count is proportional to the FB (raw ~= 29 * FB -> 1.31G relations) and the rate
# gain from a bigger lim (+27% at best) does not come close to covering it. The image was therefore shipping the
# worst known configuration.
#
# Now pinned to the 560-bit PRODUCTION set (rsa560_solver/pipeline_c169/README.md, measured 2026-10-17:
# "lpb 32/33, mfb 63/65, lambda 2.1, ncurves 17/17, lim 100M/150M"), which is the best point our own 580 sweep
# found too: FB 14.41M -> 418M raw, ~29.6k rel/s -> ~14,100 s sieving + ~2,200 s LA. Still ~13% over the budget,
# but 2.4x better than 250/600, and the correct baseline for anyone resuming.
#
# NOTE the 560 script's own default (factor_c169.sh:170) is 200M/450M, justified by "+8.8..15.1% rel/s vs
# 100M/150M". That optimises rel/s, not total time: at FB 34.9M it needs ~1.01G relations, so it is slower
# end-to-end. Do not copy that default here.
ENV RSA580_LPB1=33 RSA580_LPB0=32 RSA580_MFB1=66 RSA580_MFB0=64 RSA580_ALIM=150000000 RSA580_RLIM=100000000
# Backward compatibility aliases
ENV RSA560_LPB1=33 RSA560_LPB0=32
# S2 (2026-10-25): the deadline telemetry (breaking_rsa.py) keeps its stage-coded status for an overtime run but fires at
# 14385 s instead of 14330 s -- 15 s before the validator's own kill at 14400 s is all the margin the emit needs; a tooling
# failure exits 3 (RunFailure) at once instead of holding. TELEMETRY=0 switches the watchdog off entirely.
ENV TELEMETRY_DEADLINE=14385
# S2: CADO's native binary renumber table (freerel -renumber renumber.bin, mmap-shared by every dup2): no 12.8 GB inflated
# text table in RAM, incremental dedup ~10x faster per step (codex-lpb, exact mapping equivalence verified, c100 PASS).
ENV RENUMBER_FORMAT=binary
ENV LA_SEG_HINT=2 SQRT_POOL=1 SQRT_STAGGER=30 SQRT_TPD=12 LA_RANK64=fast RSA560_CPU24=1 RSA580_CPU24=1 TELEMETRY_LATE_DEADLINE=14460 TELEMETRY_MAP=overshoot
ENV RSA580_LPB0=32 RSA560_LPB0=32 FIRST_PROBE_AUTO=1 PROBE_LATE_NT=12 RES_CPU=1 STOP_FINAL_GROUPS=16 REPLAY_INDEX_PLAIN=1 STOP_SHAPE=1 STOP_NFAC=0.246 STOP_PROBE_TAX=6 STOP_PROBE_EVERY=2 RSA560_CPU_LAS=1 RSA580_CPU_LAS=1 PS_MEMO_ROLL=1
# STOP_LA_SCALE (slow_card.md; default 1 = unchanged): the cost rule's LA price relative to the GCP g4 card its constants were
# calibrated on; a molab-class RTX PRO 6000 measures x1.28 (laparts_sb111.txt; -33 s/key modelled there, 0 on GCP). It scales
# the secant rule's LA term AND the STOP_SHAPE kappa (set this, not a scaled STOP_KAPPA). Unset until the validator's card
# class is known from S4rung's overshoot bucket. Range [0.5, 2]; out of range dies at startup.
# ENV STOP_LA_SCALE=1.28
# CANDIDATE, default OFF (docs/research/agents_2026-10-25/container.md, idea 1): the CPU-bound stages that run with the GPU
# idle (polyselect tail, makefb, stop-time incdup + purge, merge, replay, characters/abx, sqrt) on all 24 vCPUs of the
# validator quota instead of the sieve phase's NCPU=20 budget (factor_c169.sh CONTAINER=1 profile, STAGE_NT). Gates before
# it is switched on: c100 under the official flags (the "[0s] threads:" banner line shows the resolved profile), a saved-matrix
# merge/replay/sqrt AB/BA inside the exact container, then one blind c169 e2e. Enable with the next line uncommented.
# ENV RSA560_CPU24=1
# CANDIDATES, default OFF (docs/research/agents_2026-10-26/downstream.md #1, #3): STOP_FINAL_GROUPS=16 -- the stop-time incdup
# of the last chunk ran as STOP_FINAL_GROUPS=INC_GROUPS=2 dup2 processes at 363-432 % CPU for 50 s on the 24 idle vCPUs (arm B
# docker stats, 2026-10-25; 55 s of the 136 s handoff); 16 one-slice groups (cado_incdup.sh:72 allows 16) -> est. 15-25 s.
# REPLAY_INDEX_PLAIN=1 -- replay writes c.index plain instead of through one gzip (13.0 s serial of replay's 50 s, key 28).
# Gates: c100 under the official flags, then replay_gate.sh on ckpt-key29f with EXTRA_ENV (see gpu/gcp/replay_gate.sh).
# S5 ships both on the RSA560_LPB0 line above.
# ENV STOP_FINAL_GROUPS=16 REPLAY_INDEX_PLAIN=1
# TELEMETRY_LATE_DEADLINE (candidate, default unset; container.md idea 3): a run that is in its last stages (LA >= 50 % or
# sqrt) at TELEMETRY_DEADLINE may still finish before the validator's 14,400 s; hold the telemetry kill until this later
# second instead (python t0 is < 1 s after docker's StartedAt; the payload write is milliseconds).
# ENV TELEMETRY_LATE_DEADLINE=14396
# Non-root runtime user (the validator runs --user miner --read-only); /app stays root-owned and read-only.
# chmod a+rX (here for engine/, in the build stage for the rest of /app): readable by miner whatever umask the unzip had
RUN chmod -R a+rX /app/engine && useradd -r -s /usr/sbin/nologin -d /tmp -U miner && python3 -c "import cupy, numpy; print('cupy', cupy.__version__)"
ENV CF_DIR=/app/cado-filter MSV_DIR=/app/msieve-gpu BWC_DIR=/app/bwc GLAS=/app/glas/glas-gpu \
    CONTAINER=1 HOME=/tmp TMPDIR=/tmp CUPY_CACHE_DIR=/tmp/.cupy CUDA_CACHE_PATH=/tmp/.nv \
    PYTHONPATH=/app/engine PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /tmp
USER miner
# the validator: docker run ... IMAGE <challenge_id> '<problem_json>'  (debug shell: --entrypoint bash)
ENTRYPOINT ["python3", "/app/pipeline_c169/breaking_rsa.py"]
