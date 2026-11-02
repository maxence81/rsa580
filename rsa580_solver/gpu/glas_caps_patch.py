#!/usr/bin/env python3
"""glas_caps_patch.py <gpu-siever/src/sieve_core_gpu.cu> -- env-tunable GPU capacity caps (unblocks 3 large primes).

Why: the production build hardcodes bucket_cap at density x1.25, max_survivors = chunk/64, max_hits = chunk/8 and
fcand_cap = min(max_survivors, FCAND_MAX).  Those caps are sized for 2 large primes per side.  A 3LP regime
(lambda ~2.8 at lim 150M) overflows them: glas then prints "# GPU overflow at q=... falling back to CPU" and resieves
that whole special-q on the CPU, i.e. throughput collapses and the regime is unusable -- which is why
pipeline_c169/factor_c175.sh:134-135 records "the earlier default (c173cog: 30/31, mfb 60/90) overflows glas's GPU
buffers (ledger bake-off 4)" and the pipeline is pinned to 2LP with lim 250M/600M.

That pin is what forces the factor base to 45.0M columns (pi(250M)+pi(600M)), hence a matrix N >= 30M, hence ~11,400 s
of block Lanczos -- the term that made the 2026-10-31 RSA-580 run unable to finish inside 14,400 s.  With the caps
raised, a 3LP regime at lim ~48M/67M becomes testable: 6.84M columns, N ~6-9M, LA ~400-1,000 s.

Runtime knobs (read once at gpu_init; unset = the production values above, byte-for-byte unchanged):
  GLAS_BUCKET_MARGIN  headroom over the estimated hit density (default 1.25; 2LP lambda ~2.1 -> 1.25 is enough,
                      3LP lambda ~2.8 -> 2.5-3.0)
  GLAS_SURV_DIV       max_survivors = chunk / GLAS_SURV_DIV (default 64; 3LP needs several times the 2LP count ->
                      16 or 8)
  GLAS_HITS_DIV       max_hits = chunk / GLAS_HITS_DIV (default 8; -> 4 or 2)
  GLAS_FCAND_MAX      candidate capacity (default FCAND_MAX; raise together with GLAS_SURV_DIV)

Cost: VRAM, not time.  Each of these is a per-slot device allocation, so raising them lowers the slot count glas
reports at init; on the 96 GB card there is room.  Any overflow that remains still falls back to the CPU for that q
(correct, slow), so this patch cannot change a factor: it only changes how much work stays on the GPU.

Idempotent: re-running on a patched file is a no-op.  Fails closed if a target site is missing and no marker is
present (i.e. the source drifted).  Only sieve_core_gpu.cu changes.
"""
import sys

MARKERS = ('GLAS_BUCKET_MARGIN', 'GLAS_SURV_DIV', 'GLAS_FCAND_MAX')

BUCKET_OLD = """        ctx.bucket_cap[side] = ((uint32_t)(SREG * dens * 1.25) & ~31u) + 512;"""

BUCKET_NEW = """        /* GLAS_BUCKET_MARGIN: headroom over the estimated hit density (3LP lambda ~2.8 at lim 150M overflows 1.25) */
        double bucket_margin = 1.25;
        if (char const * e = getenv("GLAS_BUCKET_MARGIN")) bucket_margin = std::max(1.0, atof(e));
        ctx.bucket_cap[side] = ((uint32_t)(SREG * dens * bucket_margin) & ~31u) + 512;"""

CAPS_OLD = """    ctx.max_survivors = chunk / 64;
    ctx.max_hits = chunk / 8;
    if (ctx.assemble)
        ctx.fcand_cap = std::min(ctx.max_survivors, FCAND_MAX);"""

CAPS_NEW = """    {   /* GLAS_SURV_DIV / GLAS_HITS_DIV / GLAS_FCAND_MAX: enlarge the per-chunk survivor, resieve-hit and
         * candidate capacities (3 large primes on a side needs several times the 2LP survivor count) */
        unsigned surv_div = 64, hits_div = 8;
        if (char const * e = getenv("GLAS_SURV_DIV")) surv_div = std::max(1, atoi(e));
        if (char const * e = getenv("GLAS_HITS_DIV")) hits_div = std::max(1, atoi(e));
        ctx.max_survivors = chunk / surv_div;
        ctx.max_hits = chunk / hits_div;
    }
    if (ctx.assemble) {
        uint32_t fcand_max = FCAND_MAX;
        if (char const * e = getenv("GLAS_FCAND_MAX")) fcand_max = (uint32_t)std::max(1, atoi(e));
        ctx.fcand_cap = std::min(ctx.max_survivors, fcand_max);
    }"""

OVERFLOW_OLD = """            fprintf(stderr, "# GPU overflow at q=%lu; falling back to CPU\\n",
                    (unsigned long)task.q);"""

OVERFLOW_NEW = """            fprintf(stderr, "# GPU overflow at q=%lu (caps surv=%u hits=%u); falling back to CPU\\n",
                    (unsigned long)task.q, ctx.max_survivors, ctx.max_hits);"""


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    path = sys.argv[1]
    src = open(path, encoding='utf-8').read()
    done = []
    for marker, old, new, tag in (('GLAS_BUCKET_MARGIN', BUCKET_OLD, BUCKET_NEW, 'bucket_cap margin'),
                                  ('GLAS_SURV_DIV', CAPS_OLD, CAPS_NEW, 'survivor/hit/candidate caps'),
                                  ('caps surv=%u', OVERFLOW_OLD, OVERFLOW_NEW, 'overflow diagnostic')):
        if marker in src:
            done.append('%s: already present' % tag)
            continue
        if src.count(old) != 1:
            sys.exit('glas_caps_patch: target site for %s not found exactly once (%d) and marker %r absent -- '
                     'source drifted; refusing to patch' % (tag, src.count(old), marker))
        src = src.replace(old, new)
        done.append('%s: patched' % tag)
    open(path, 'w', encoding='utf-8', newline='').write(src)
    for m in MARKERS:
        assert m in src, m
    print('glas_caps_patch: ' + '; '.join(done))
    print('glas_caps_patch: markers OK (%s)' % ', '.join(MARKERS))


if __name__ == '__main__':
    main()
