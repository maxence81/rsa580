#!/usr/bin/env bash
# probe_3lp.sh -- measure cuda-sieve `bench` on the c175 polynomial across several q bands,
# for several (lim, lpb, mfb) regimes. Writes $OUT/summary.tsv then runs probe_3lp_analyze.py.
#
# Invocation copied from the 530 solution's factor_c160.sh:662 (the only known-good call of this binary):
#   bench --pipeline --cofactor --allowance0 A0 --allowance A1 --bkthresh 65536 --fill-concurrent \
#         --poly JOB --fb1 FB --logI 15 --J 16384 --sq-side 1 --qrange q:qb-1 --relations OUT
# `--fb1` is optional (bench builds the factor base in-process); we drop it if fbgen_gpu fails.
set -u

CS=${CS:-/opt/cuda-sieve}
HERE=${HERE:-/opt/pipeline}
POLY=${POLY:-/opt/poly_P.txt}
OUT=${OUT:-/tmp/probe_out}

LOGI=${LOGI:-15}
JJ=${JJ:-16384}
W=${W:-4000}
BAND_TIMEOUT=${BAND_TIMEOUT:-300}
BANDS=${BANDS:-"2200000 12000000 30000000 60000000"}
BKTHRESH=${BKTHRESH:-65536}
ALLOW_OFF=${ALLOW_OFF:-0}

# name:rlim:alim:lpb0:lpb1:mfb0:mfb1
#  ctl2lp = our measured GLAS 2LP config (control: isolates the 3LP effect at equal lim/lpb)
#  alg3lp = same, mfb1 64 -> 90 (3LP on the algebraic side only)
#  cado   = CADO-NFS's own c175 params (small FB, 3LP algebraic)
REGIMES=${REGIMES:-"ctl2lp:100000000:150000000:32:33:62:64 alg3lp:100000000:150000000:32:33:62:90 cado:48100000:67600000:30:31:60:90"}

PY=$(command -v python3 || command -v python) || { echo "no python"; exit 2; }
mkdir -p "$OUT"; : > "$OUT/summary.tsv"

for b in "$CS/bench" "$CS/fbgen_gpu"; do
  chmod +x "$b" 2>/dev/null
  [ -x "$b" ] || { echo "FATAL: missing $b"; exit 2; }
done
[ -s "$POLY" ] || { echo "FATAL: missing polynomial $POLY"; exit 2; }

echo "### GPU: $(nvidia-smi -L 2>&1 | head -1)"
echo "### poly: $(grep -E '^(n|skew|c5):' "$POLY" | cut -c1-70 | tr '\n' ' ')"
echo "### bench: $("$CS/bench" --help 2>&1 | head -1)"

printf 'regime\tq0\tW\tnq\trel_lines\trq_log\tms_log\twall_s\trc\tskipped\tlpb0\tlpb1\tmfb0\tmfb1\n' > "$OUT/summary.tsv"

for reg in $REGIMES; do
  IFS=: read -r name rlim alim l0 l1 m0 m1 <<< "$reg"
  job="$OUT/$name.job"; fb="$OUT/$name.fb"

  if ! "$PY" "$HERE/polysel160.py" job "$POLY" "$job" "$rlim" "$alim" "$l0" "$l1" "$m0" "$m1"; then
    echo "### [$name] FATAL: job generation failed"; continue
  fi
  echo "### [$name] lim $rlim/$alim lpb $l0/$l1 mfb $m0/$m1 -> $(wc -l < "$job") job lines"

  FBARGS=()
  if "$CS/fbgen_gpu" --poly "$job" --lim "$alim" --maxbits "$LOGI" --out "$fb" \
       > "$OUT/$name.fbgen.log" 2>&1 && [ -s "$fb" ]; then
    echo "### [$name] fbgen ok, $(stat -c%s "$fb") bytes"
    FBARGS=(--fb1 "$fb")
  else
    echo "### [$name] fbgen FAILED -> bench builds its own FB (--fb1 omitted): $(tail -2 "$OUT/$name.fbgen.log" | tr '\n' ' ')"
  fi

  ALLOW=(--allowance0 "$(awk -v m="$m0" 'BEGIN{printf "%.1f", m-0.5}')" \
         --allowance  "$(awk -v m="$m1" 'BEGIN{printf "%.1f", m-0.5}')")
  [ "$ALLOW_OFF" = 1 ] && ALLOW=()
  ALLOW+=(--bkthresh "$BKTHRESH")

  for q in $BANDS; do
    rel="$OUT/$name.q$q.rel"; log="$OUT/$name.q$q.log"
    rm -f "$rel" "$rel".part* 2>/dev/null
    qb=$(( q + W - 1 ))
    t0=$(date +%s.%N)
    timeout -k 10 "$BAND_TIMEOUT" "$CS/bench" --pipeline --cofactor "${ALLOW[@]}" --fill-concurrent \
        --poly "$job" "${FBARGS[@]}" --logI "$LOGI" --J "$JJ" --sq-side 1 \
        --qrange "$q:$qb" --relations "$rel" > "$log" 2>&1
    rc=$?
    wall=$(awk -v a="$t0" -v b="$(date +%s.%N)" 'BEGIN{printf "%.1f", b-a}')

    f="$rel"; [ -s "$f" ] || f=$(ls "$rel".part 2>/dev/null | head -1)
    rl=0
    if [ -n "${f:-}" ] && [ -s "$f" ]; then rl=$(grep -a -vc '^#' "$f"); fi
    nq=$(grep -aoE 'band of [0-9]+ special-q' "$log" | grep -oE '[0-9]+' | head -1)
    rq=$(grep -aE 'ALL RELATIONS/q' "$log" | awk '{print $NF}' | tail -1)
    ms=$(awk '/wall clock per q/{for(i=1;i<=NF;i++) if($i ~ /^[0-9.]+$/ && $(i+1) ~ /ms/){print $i; exit}}' "$log")
    sk=$(grep -ac 'skipped for norm width' "$log")

    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
      "$name" "$q" "$W" "${nq:-}" "$rl" "${rq:-}" "${ms:-}" "$wall" "$rc" "$sk" \
      "$l0" "$l1" "$m0" "$m1" >> "$OUT/summary.tsv"

    { echo "== $name q=$q rc=$rc wall=${wall}s rel_lines=$rl"; tail -30 "$log"; } \
      > "$OUT/$name.q$q.tail.txt"
    grep -aiE 'cofactor|ecm|unresolved|abort|overflow|skipp|warn|error|fatal' "$log" \
      | head -15 > "$OUT/$name.q$q.cof.txt"

    echo "    q=$q rc=$rc wall=${wall}s nq=${nq:-?} rel=$rl rel/q=${rq:-?} ms/q=${ms:-?}"
    rm -f "$rel" "$rel".part* 2>/dev/null
  done
  rm -f "$fb" 2>/dev/null
done

echo "### summary"
column -t -s$'\t' "$OUT/summary.tsv" 2>/dev/null || cat "$OUT/summary.tsv"
echo
"$PY" "$HERE/probe_3lp_analyze.py" "$OUT/summary.tsv" ${ANALYZE_ARGS:-} | tee "$OUT/analysis.txt"
