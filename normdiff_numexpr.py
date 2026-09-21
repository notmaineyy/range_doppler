"""
Benchmark: normalised difference with numexpr.

Computes      |I1 - I2| / (I1 + I2 + eps)
on two large 2-D uint8 arrays, comparing:

  * numpy in-place (out= reuse)   -- the efficient pure-numpy baseline
  * numexpr (multithreaded JIT)   -- ne.evaluate(..., casting='safe')

Run::

    .venv/bin/python normdiff_numexpr.py
    .venv/bin/python normdiff_numexpr.py --pixels 1.1e9 --threads 10
    .venv/bin/python normdiff_numexpr.py --mode numpy numexpr

Notes
-----
* Inputs are uint8 (0..255). numexpr reads them and internally widens the
  integer arithmetic, so the subtraction does not wrap.
* numexpr's true division ("/") yields float64, so the result is 8 bytes/pixel.
  With casting='safe' numexpr will *not* silently write that into a float32
  buffer (float64 -> float32 is not a safe cast), which is why we keep float64.
"""

from __future__ import annotations

import argparse
import gc
import sys
import time

import numpy as np
import numexpr as ne

from normdiff_benchmark import (
    parse_pixels,
    factor_close_to_square,
    available_bytes,
    human,
    make_inputs,
)

EPS = 1e-6


# --------------------------------------------------------------------------- #
# Variants
# --------------------------------------------------------------------------- #
def numpy_inplace(I1: np.ndarray, I2: np.ndarray, eps, cdtype=np.float32,
                  out_dtype=None):
    """numpy: reuse two float32 buffers via out=."""
    a = I1.astype(cdtype)
    d = np.empty_like(a)
    np.subtract(a, I2, out=d)      # d = I1 - I2
    np.abs(d, out=d)
    np.add(a, I2, out=a)           # a = I1 + I2
    a += cdtype(eps)
    np.divide(d, a, out=d)
    return d


def numexpr_eval(I1: np.ndarray, I2: np.ndarray, eps, out_dtype="float64"):
    """numexpr: single multithreaded expression.

    out_dtype='float64' -> casting='safe' (default; result is float64).
    out_dtype='float32' -> write into a float32 buffer with casting='same_kind'
                           (float64 -> float32 is not a 'safe' cast, so numexpr
                           refuses it under 'safe'). This halves result memory.
    """
    expr = "abs(I1 - I2) / (I1 + I2 + eps)"
    local = {"I1": I1, "I2": I2, "eps": eps}
    if out_dtype == "float32":
        out = np.empty(I1.shape, dtype=np.float32)
        return ne.evaluate(expr, local_dict=local, out=out, casting="same_kind")
    return ne.evaluate(expr, local_dict=local, casting="safe")


VARIANTS = {"numpy": numpy_inplace, "numexpr": numexpr_eval}


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pixels", type=parse_pixels, default=parse_pixels("1.1e9"),
                    help="total number of pixels (default 1.1e9)")
    ap.add_argument("--in-dtype", default="uint8",
                    choices=["uint8", "uint16", "int16"],
                    help="storage dtype of the inputs (default uint8)")
    ap.add_argument("--mode", nargs="+", default=["numpy", "numexpr"],
                    choices=["numpy", "numexpr"])
    ap.add_argument("--threads", type=int, default=0,
                    help="numexpr threads (0 = leave default)")
    ap.add_argument("--out-dtype", default="float64",
                    choices=["float32", "float64"],
                    help="numexpr result dtype (float32 halves result memory)")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    if args.threads > 0:
        ne.set_num_threads(args.threads)
    nthreads = ne.get_num_threads()

    n = int(args.pixels)
    in_dtype = np.dtype(args.in_dtype)
    rows, cols = factor_close_to_square(n)
    shape = (rows, cols)

    print(f"pixels      : {n:,}  ({rows:,} x {cols:,})")
    print(f"input dtype : {in_dtype}  ({in_dtype.itemsize} bytes/pixel)")
    print(f"input size  : {human(n * in_dtype.itemsize)} per array, "
          f"{human(2 * n * in_dtype.itemsize)} total")
    print(f"numexpr     : v{ne.__version__}, threads={nthreads}, "
          f"cores={ne.detect_number_of_cores()}")
    print(f"epsilon     : {EPS:g}")

    avail = available_bytes()
    if avail is not None:
        print(f"available   : {human(avail)}")

    print("\nallocating ...", flush=True)
    t0 = time.perf_counter()
    try:
        I1, I2 = make_inputs(shape, in_dtype, args.seed)
    except MemoryError:
        print("[ERROR] MemoryError during allocation. Reduce --pixels.")
        return 1
    print(f"allocated in {time.perf_counter() - t0:.2f} s", flush=True)

    # numexpr's "/" produces float64; be explicit about the expected result size
    for mode in args.mode:
        fn = VARIANTS[mode]
        print(f"\n[{mode}] {fn.__doc__.splitlines()[0]}")
        gc.collect()
        t0 = time.perf_counter()
        try:
            result = fn(I1, I2, EPS, out_dtype=args.out_dtype)
        except MemoryError:
            print("  [ERROR] MemoryError during compute; skipped.")
            continue
        elapsed = time.perf_counter() - t0

        print(f"  elapsed time : {elapsed:.3f} s")
        print(f"  ns/pixel     : {elapsed / n * 1e9:.2f}")
        print(f"  throughput   : {n / elapsed / 1e9:.2f} Gpixel/s")
        print(f"  result dtype : {result.dtype}")
        print(f"  {result.nbytes / 1e9:.2f} GB")
        print(f"  checksum     : {float(np.asarray(result).sum(dtype=np.float64)):.6e}")
        del result
        gc.collect()

    del I1, I2
    gc.collect()
    print("\ndone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
