"""
Benchmark an extra, statistics-normalised ratio on two large uint8 images.

Formula (as requested):

    I1 / (I2 + 0.1*median(I1))  +  std1 / (std2 + 0.1*median(std1))

with
    median(I1)     : scalar median of image I1
    std1, std2     : scalar standard deviations of I1 and I2
    median(std1)   : std1 is a scalar, so this is just std1

So the calculation is a global reduction (median + two standard deviations)
followed by one elementwise pass:

    out = I1 / (I2 + 0.1*m1) + s1 / (s2 + 0.1*s1)

The elementwise pass is timed three ways (numpy naive, numpy in-place, numexpr),
and the shared reduction is timed separately, because the median is expensive.

Run::

    .venv/bin/python normdiff_extra.py
    .venv/bin/python normdiff_extra.py --pixels 3e8 --mode naive inplace numexpr
"""

from __future__ import annotations

import argparse
import gc
import sys
import time

import numpy as np
import numexpr as ne

from normdiff_benchmark import (
    parse_pixels, factor_close_to_square, available_bytes, human, make_inputs,
)


# --------------------------------------------------------------------------- #
# Reductions (shared by all elementwise variants)
# --------------------------------------------------------------------------- #
def median_u8(a: np.ndarray) -> float:
    """Exact median of a uint8 array using an in-place partition (no float64 copy)."""
    b = a.reshape(-1).copy()          # 1 byte/pixel, not 8
    n = b.size
    k = n // 2
    if n % 2:
        b.partition(k)
        return float(b[k])
    b.partition([k - 1, k])
    return 0.5 * (float(b[k - 1]) + float(b[k]))


def reductions(I1: np.ndarray, I2: np.ndarray):
    m1 = median_u8(I1)
    s1 = float(I1.std(dtype=np.float64))
    s2 = float(I2.std(dtype=np.float64))
    return m1, s1, s2


# --------------------------------------------------------------------------- #
# Elementwise variants
# --------------------------------------------------------------------------- #
def naive(I1, I2, c1, c2):
    """Literal expression; casts each input and makes temporaries."""
    return I1.astype(np.float32) / (I2.astype(np.float32) + c1) + c2


def inplace(I1, I2, c1, c2):
    """Reuse two float32 buffers via out=."""
    a = I1.astype(np.float32)
    d = I2.astype(np.float32)
    d += c1
    np.divide(a, d, out=a)
    a += c2
    return a


def numexpr_eval(I1, I2, c1, c2):
    """numexpr single expression into a float32 buffer."""
    out = np.empty(I1.shape, dtype=np.float32)
    ne.evaluate("I1 / (I2 + c1) + c2",
                local_dict={"I1": I1, "I2": I2,
                            "c1": np.float32(c1), "c2": np.float32(c2)},
                out=out, casting="same_kind")
    return out


VARIANTS = {"naive": naive, "inplace": inplace, "numexpr": numexpr_eval}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pixels", type=parse_pixels, default=parse_pixels("1.1e9"))
    ap.add_argument("--in-dtype", default="uint8", choices=["uint8", "uint16", "int16"])
    ap.add_argument("--mode", nargs="+", default=["naive", "inplace", "numexpr"],
                    choices=list(VARIANTS))
    ap.add_argument("--threads", type=int, default=0)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    if args.threads > 0:
        ne.set_num_threads(args.threads)
    nthreads = ne.get_num_threads()

    n = int(args.pixels)
    in_dtype = np.dtype(args.in_dtype)
    rows, cols = factor_close_to_square(n)
    shape = (rows, cols)

    print(f"formula     : I1/(I2 + 0.1*median(I1)) + std1/(std2 + 0.1*std1)")
    print(f"pixels      : {n:,}  ({rows:,} x {cols:,})")
    print(f"input dtype : {in_dtype}  ({in_dtype.itemsize} bytes/pixel)")
    print(f"numexpr     : v{ne.__version__}, threads={nthreads}")
    avail = available_bytes()
    if avail is not None:
        print(f"available   : {human(avail)}")

    print("\nallocating ...", flush=True)
    t0 = time.perf_counter()
    I1, I2 = make_inputs(shape, in_dtype, args.seed)
    print(f"allocated in {time.perf_counter() - t0:.2f} s", flush=True)

    # --- shared reduction (median is the expensive part) ---
    gc.collect()
    t0 = time.perf_counter()
    m1, s1, s2 = reductions(I1, I2)
    t_red = time.perf_counter() - t0
    c1 = np.float32(0.1 * m1)
    c2 = np.float32(s1 / (s2 + 0.1 * s1))
    print(f"\n[reductions] median(I1)={m1:.1f}  std1={s1:.4f}  std2={s2:.4f}  "
          f"-> c1={float(c1):.3f}  c2={float(c2):.6f}")
    print(f"  reduction time : {t_red:.3f} s   "
          f"({t_red / n * 1e9:.2f} ns/pixel, median + 2 std)")

    for mode in args.mode:
        fn = VARIANTS[mode]
        print(f"\n[{mode}] {fn.__doc__.splitlines()[0]}")
        gc.collect()
        t0 = time.perf_counter()
        try:
            out = fn(I1, I2, c1, c2)
        except MemoryError:
            print("  [ERROR] MemoryError during compute; skipped.")
            continue
        dt = time.perf_counter() - t0
        print(f"  elementwise    : {dt:.3f} s   {dt / n * 1e9:.2f} ns/pixel   "
              f"{n / dt / 1e9:.2f} Gpixel/s")
        print(f"  total (red+el) : {t_red + dt:.3f} s")
        print(f"  result dtype   : {out.dtype}   {out.nbytes / 1e9:.2f} GB")
        print(f"  checksum       : {float(out.sum(dtype=np.float64)):.6e}")
        del out
        gc.collect()

    del I1, I2
    gc.collect()
    print("\ndone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
