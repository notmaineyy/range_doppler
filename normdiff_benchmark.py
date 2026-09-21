"""
Benchmark: vectorised normalised difference of two large 2-D arrays.

Computes      |I1 - I2| / (I1 + I2 + eps)
where the input arrays are stored as uint8 (0..255), as they are for real
image bands. The arithmetic is done in a wider floating type because
uint8 subtraction wraps (underflows) and the division with eps needs floats.

Run::

    .venv/bin/python normdiff_benchmark.py
    .venv/bin/python normdiff_benchmark.py --pixels 1.1e9 --in-dtype uint8
    .venv/bin/python normdiff_benchmark.py --mode naive inplace

Notes
-----
* Default: 1.1e9 pixels as 32000 x 34375 (exactly 1.1e9), inputs uint8.
* uint8 inputs cost ~1.02 GiB each (2.05 GiB total) -- 4x smaller than
  float32 inputs. The float32 working arrays dominate the peak memory.
* "naive"   : the literal expression, which allocates several temporaries.
* "inplace" : same maths but reusing buffers via out= to cap peak memory.
"""

from __future__ import annotations

import argparse
import gc
import sys
import time

import numpy as np

EPS = 1e-6


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def parse_pixels(s: str) -> int:
    return int(float(s))


def factor_close_to_square(n: int) -> tuple[int, int]:
    """Return (rows, cols) with rows*cols == n, as square as possible."""
    r = int(np.sqrt(n))
    while r > 0 and n % r != 0:
        r -= 1
    return r, n // r


def available_bytes() -> int | None:
    """Best-effort free-memory estimate (macOS / Linux)."""
    try:
        import psutil  # type: ignore
        return psutil.virtual_memory().available
    except Exception:
        pass
    try:
        if sys.platform == "darwin":
            import subprocess
            out = subprocess.check_output(["vm_stat"], text=True)
            page = 16384
            for line in out.splitlines():
                if "page size of" in line:
                    page = int(line.split("page size of")[1].split()[0])
            free = inactive = 0
            for line in out.splitlines():
                if line.startswith("Pages free:"):
                    free = int(line.split(":")[1].strip().rstrip("."))
                elif line.startswith("Pages inactive:"):
                    inactive = int(line.split(":")[1].strip().rstrip("."))
            return (free + inactive) * page
        with open("/proc/meminfo") as fh:
            for line in fh:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) * 1024
    except Exception:
        pass
    return None


def human(nbytes: float) -> str:
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(nbytes) < 1024.0:
            return f"{nbytes:.2f} {unit}"
        nbytes /= 1024.0
    return f"{nbytes:.2f} PiB"


def report(name: str, dt: float, n: int) -> None:
    per_pixel_ns = dt / n * 1e9
    print(f"  {name:<8} {dt:8.3f} s   "
          f"{per_pixel_ns:7.2f} ns/pixel   "
          f"{n / dt / 1e9:6.2f} Gpixel/s")


def make_inputs(shape, in_dtype, seed):
    """Random inputs: integers 0..max for integer dtypes, [0,1) for floats."""
    rng = np.random.default_rng(seed)
    if np.issubdtype(in_dtype, np.integer):
        hi = np.iinfo(in_dtype).max
        I1 = rng.integers(0, hi + 1, size=shape, dtype=in_dtype)
        I2 = rng.integers(0, hi + 1, size=shape, dtype=in_dtype)
    else:
        I1 = rng.random(shape, dtype=in_dtype)
        I2 = rng.random(shape, dtype=in_dtype)
    return I1, I2


# --------------------------------------------------------------------------- #
# The two variants (inputs uint8, maths in cdtype)
# --------------------------------------------------------------------------- #
def naive(I1: np.ndarray, I2: np.ndarray, eps: np.float32, cdtype) -> np.ndarray:
    """Literal expression; casts each input twice and allocates temporaries."""
    return np.abs(I1.astype(cdtype) - I2.astype(cdtype)) / (
        I1.astype(cdtype) + I2.astype(cdtype) + eps)


def inplace(I1: np.ndarray, I2: np.ndarray, eps: np.float32, cdtype) -> np.ndarray:
    """Reuse two float buffers via out=; I2 is upcast on the fly in the ufunc."""
    a = I1.astype(cdtype)              # buffer 1 = I1
    d = np.empty_like(a)               # buffer 2 = result
    np.subtract(a, I2, out=d)          # d = I1 - I2
    np.abs(d, out=d)
    np.add(a, I2, out=a)               # a = I1 + I2   (I1 no longer needed)
    a += eps
    np.divide(d, a, out=d)             # d = |I1-I2| / (I1+I2+eps)
    return d


VARIANTS = {"naive": naive, "inplace": inplace}


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pixels", type=parse_pixels, default=parse_pixels("1.1e9"),
                    help="total number of pixels (default 1.1e9)")
    ap.add_argument("--in-dtype", default="uint8",
                    choices=["uint8", "uint16", "int16", "float32", "float64"],
                    help="storage dtype of the input arrays (default uint8)")
    ap.add_argument("--compute-dtype", default="float32",
                    choices=["float16", "float32", "float64"],
                    help="dtype used for the arithmetic (default float32)")
    ap.add_argument("--mode", nargs="+", default=["naive", "inplace"],
                    choices=["naive", "inplace"])
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    n = int(args.pixels)
    in_dtype = np.dtype(args.in_dtype)
    c_dtype = np.dtype(args.compute_dtype).type
    rows, cols = factor_close_to_square(n)
    shape = (rows, cols)

    print(f"pixels      : {n:,}  ({rows:,} x {cols:,})")
    print(f"input dtype : {in_dtype}  ({in_dtype.itemsize} bytes/pixel)")
    print(f"compute type: {c_dtype.__name__}  ({np.dtype(c_dtype).itemsize} bytes/pixel)")
    print(f"input size  : {human(n * in_dtype.itemsize)} per array, "
          f"{human(2 * n * in_dtype.itemsize)} total")
    print(f"work array  : {human(n * np.dtype(c_dtype).itemsize)} each")
    print(f"epsilon     : {EPS:g}")

    avail = available_bytes()
    if avail is not None:
        print(f"available   : {human(avail)}")
        work = n * np.dtype(c_dtype).itemsize
        need_naive = 2 * n * in_dtype.itemsize + 6 * work      # rough peak
        if need_naive > avail:
            print(f"\n[WARN] estimated naive peak (~{human(need_naive)}) exceeds "
                  f"available memory ({human(avail)}). Expect swapping.")

    print("\nallocating ...", flush=True)
    t0 = time.perf_counter()
    try:
        I1, I2 = make_inputs(shape, in_dtype, args.seed)
    except MemoryError:
        print("[ERROR] MemoryError during allocation. Reduce --pixels.")
        return 1
    print(f"allocated in {time.perf_counter() - t0:.2f} s", flush=True)

    eps = c_dtype(EPS)
    for mode in args.mode:
        fn = VARIANTS[mode]
        print(f"\n[{mode}] {fn.__doc__.splitlines()[0]}")
        gc.collect()
        t0 = time.perf_counter()
        try:
            out = fn(I1, I2, eps, c_dtype)
        except MemoryError:
            print("  [ERROR] MemoryError during compute; skipped.")
            continue
        dt = time.perf_counter() - t0
        report(mode, dt, n)
        print(f"  checksum  : {float(out.sum(dtype=np.float64)):.6e}   dtype={out.dtype}")
        del out
        gc.collect()

    del I1, I2
    gc.collect()
    print("\ndone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
