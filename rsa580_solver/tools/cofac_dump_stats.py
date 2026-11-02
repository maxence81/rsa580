#!/usr/bin/env python3
"""cofac_dump_stats.py -- inspect a GLAS_COFAC_DUMP file.

Why this exists
---------------
GLAS writes, for every *candidate* it collects, the two leftover cofactors
(before host-side facul).  That distribution is the single number that decides
whether a 3LP regime is viable at all:

  * leftovers of 50-65 bits  -> facul (MR + a few ECM curves) splits them in
                                microseconds; 3LP is a pure win.
  * leftovers of 85-95 bits  -> facul needs many ECM curves per candidate; the
                                host-side cofactorisation cost explodes and the
                                chunk never completes.  This is the failure mode
                                we measured (0 relations, no error, no overflow).

GLAS_COFAC_DUMP was in the source but wired to nothing in this tree, so this
was never measured.  Run a short 3LP glas session with the variable set, then:

    python3 cofac_dump_stats.py /tmp/cof.bin

File format (src/glas.cpp, dump_cofac_pairs):
  header  9 x uint64 = 72 B : magic, then per side {lim, lpb, mfb, ncurves}
  records 4 x uint64 = 32 B : side0 limbs 0,1 then side1 limbs 0,1
Only the low 128 bits are stored, which is exact for any mfb <= 128.
"""

import struct
import sys
from collections import Counter

MAGIC = 0x676C61732D636F66
HDR = struct.Struct("<9Q")
REC = struct.Struct("<4Q")


def bitlen_128(lo: int, hi: int) -> int:
    """Bit length of the 128-bit value hi*2^64 + lo."""
    if hi:
        return 64 + hi.bit_length()
    return lo.bit_length()


def main(path: str) -> int:
    with open(path, "rb") as fh:
        raw = fh.read()

    if len(raw) < HDR.size:
        print(f"file too short ({len(raw)} B): no header")
        return 1

    hdr = HDR.unpack_from(raw, 0)
    if hdr[0] != MAGIC:
        print(f"bad magic {hdr[0]:#x} (expected {MAGIC:#x})")
        return 1

    sides = []
    for s in range(2):
        lim, lpb, mfb, ncurves = hdr[1 + 4 * s: 5 + 4 * s]
        sides.append((lim, lpb, mfb, ncurves))

    body = len(raw) - HDR.size
    if body % REC.size:
        print(f"warning: {body} body bytes not a multiple of {REC.size}; truncating")
    n = body // REC.size
    if n == 0:
        print("header OK but ZERO candidates recorded.")
        print("That means the GPU never produced a candidate: the rejection is")
        print("upstream of cofactorisation (survivor filter / bucket caps), not facul.")
        return 0

    print(f"{path}: {n:,} candidates")
    for s, (lim, lpb, mfb, ncurves) in enumerate(sides):
        print(f"  side {s}: lim={lim:,} lpb={lpb} mfb={mfb} ncurves={ncurves}")

    for s in range(2):
        lim, lpb, mfb, _ = sides[s]
        bits = []
        for i in range(n):
            lo, hi = REC.unpack_from(raw, HDR.size + i * REC.size)[2 * s: 2 * s + 2]
            bits.append(bitlen_128(lo, hi))

        bits.sort()
        med = bits[len(bits) // 2]
        p90 = bits[int(len(bits) * 0.90)]
        mx = bits[-1]
        # how many are beyond the "one more prime above lpb" threshold:
        # a leftover above 2*lpb needs at least 3 large primes, above 3*lpb needs 4.
        n_2lp = sum(1 for b in bits if b <= 2 * lpb)
        n_3lp = sum(1 for b in bits if 2 * lpb < b <= 3 * lpb)
        n_4lp = sum(1 for b in bits if b > 3 * lpb)

        print(f"\nside {s} leftover bit-length:")
        print(f"  min {bits[0]}  median {med}  p90 {p90}  max {mx}")
        print(f"  <=2*lpb ({2*lpb} b) : {n_2lp:>10,}  {100*n_2lp/n:5.1f}%   facul splits easily")
        print(f"  <=3*lpb ({3*lpb} b) : {n_3lp:>10,}  {100*n_3lp/n:5.1f}%   needs 3LP chain")
        print(f"  > 3*lpb           : {n_4lp:>10,}  {100*n_4lp/n:5.1f}%   needs 4LP chain")

        hist = Counter(b // 5 * 5 for b in bits)
        print("  histogram (5-bit buckets):")
        for bucket in sorted(hist):
            share = 100 * hist[bucket] / n
            bar = "#" * max(1, int(share / 2))
            print(f"    {bucket:>3}-{bucket+4:>3} b : {share:5.1f}% {bar}")

    print("\nInterpretation")
    print("  median <= 65 b  -> 3LP should work; if it did not, look at the caps.")
    print("  median >= 85 b  -> facul cost per candidate is the blocker; 3LP is")
    print("                     out of reach with host-side cofactorisation.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
