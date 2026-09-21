# How to run the timing tests

This guide shows how to reproduce the timings in `results.md`, explains the
**methodology** (how the timing is measured), and the **difference between the
numpy and numexpr versions**.

---

## 1. What is in this folder

| file | what it does |
|---|---|
| `normdiff_benchmark.py` | Times the operation using **plain numpy**: a literal one-line ("naive") version and a memory-reusing ("in-place") version. Input and compute number formats are selectable. |
| `normdiff_numexpr.py` | Times the operation using **numexpr** (multithreaded, JIT-compiled) and compares it with the numpy in-place version. |
| `results.md` | The measured results and a plain-English explanation. |
| `readme_timing.md` | This file: how to run and how it is measured. |

The operation being timed is, for every pixel of two images:

```
|I1 - I2| / (I1 + I2 + eps)
```

---

## 2. Setup

From the project root:

```bash
# create a virtual environment (once)
python3 -m venv .venv

# install the packages
.venv/bin/pip install numpy numexpr
```

`numexpr` is only needed for `normdiff_numexpr.py`. `numpy` is needed for both.

---

## 3. Quick start

```bash
# Full 1.1-billion-pixel run with numpy (naive + in-place)
.venv/bin/python normdiff_benchmark.py --pixels 1.1e9 --in-dtype uint8 \
    --compute-dtype float32 --mode naive inplace

# Same, but with numexpr (also runs the numpy in-place baseline)
.venv/bin/python normdiff_numexpr.py --pixels 1.1e9 --mode numpy numexpr

# A smaller, fast, in-memory run (good for a quick check)
.venv/bin/python normdiff_benchmark.py --pixels 3e8 --in-dtype uint8 \
    --compute-dtype float32 --mode naive inplace
```

Start with `--pixels 3e8` (300 million) or `--pixels 1e7` if you just want to
check that everything runs. Only use `1.1e9` when you have plenty of free memory.

---

## 4. Script options

### `normdiff_benchmark.py`

| option | default | meaning |
|---|---|---|
| `--pixels` | `1.1e9` | total number of pixels (array size) |
| `--in-dtype` | `uint8` | how the input images are stored: `uint8`, `uint16`, `int16`, `float32`, `float64` |
| `--compute-dtype` | `float32` | number format used for the maths: `float16`, `float32`, `float64` |
| `--mode` | `naive inplace` | which versions to time |
| `--seed` | `0` | random seed for the generated images |

### `normdiff_numexpr.py`

| option | default | meaning |
|---|---|---|
| `--pixels` | `1.1e9` | total number of pixels |
| `--in-dtype` | `uint8` | input storage: `uint8`, `uint16`, `int16` |
| `--mode` | `numpy numexpr` | run the numpy in-place baseline and/or numexpr |
| `--threads` | `0` | numexpr threads; `0` keeps the default (= number of CPU cores) |
| `--seed` | `0` | random seed |

---

## 5. Methodology (how the timing is measured)

The goal is to measure **the calculation only**, not setup, and to make sure the
answer is real.

1. **Allocate first, time second.** Both images are created *before* the clock
   starts. Allocation time is reported separately. This keeps the measurement
   about the calculation, not about generating random data.
2. **`time.perf_counter()` around the operation.** This is a high-resolution
   wall-clock timer. It is started immediately before the calculation and read
   immediately after.
3. **Force the result to be produced.** After timing, the script computes a
   **checksum** (`result.sum(...)`). This does two things:
   - It proves the result was actually computed and stored (some optimisers
     could otherwise skip work whose result is never used).
   - It lets us confirm that different methods agree (same answer = correct).
4. **Single-shot runs.** At 1.1 billion pixels the arrays are gigabytes, so each
   version is run **once**. For smaller sizes you can run the command repeatedly
   and compare, which averages out noise.
5. **Report both time and rate.** The output gives elapsed seconds, `ns/pixel`
   (nanoseconds per pixel) and `Gpixel/s` (billion pixels per second). Rates let
   you compare runs of different sizes fairly.
6. **Report memory context.** The scripts print how much memory is available and
   whether the run is likely to fit, because **spilling to disk (swap) changes
   the timing by ~10x**.
7. **numexpr specifics.** The script prints the numexpr version and the number
   of threads used. numexpr compiles the expression the first time it is seen
   (JIT); for tiny arrays this compile cost can dominate, which is why tiny runs
   may look slow.

### What the output looks like

```
pixels      : 1,100,000,000  (32,000 x 34,375)
input dtype : uint8  (1 bytes/pixel)
...
allocated in 1.01 s

[inplace] Reuse two float buffers via out=; I2 is upcast on the fly in the ufunc.
  inplace     4.454 s      4.05 ns/pixel     0.25 Gpixel/s
  checksum  : 4.275758e+08   dtype=float32

done.
```

---

## 6. numpy vs numexpr: what is different

Both compute the *same formula* and produce the *same answer*. They differ in
how they execute it.

### numpy (the `normdiff_benchmark.py` versions)

- You write the formula directly in Python (`np.abs(...) / (...)`).
- Each part of the formula (`subtract`, `abs`, `add`, `divide`) runs as a
  **separate pass over the whole array**.
- By default numpy runs on **one CPU core**.
- The literal ("naive") form lets numpy create several full-size **temporary**
  arrays. The **in-place** form avoids most of them by writing results back into
  memory it already has (`out=`).
- The result format follows numpy's rules; with `float32` inputs you get a
  `float32` result (4 bytes/pixel).

### numexpr (the `normdiff_numexpr.py` version)

- You pass the formula as a **text string** to `ne.evaluate(...)`.
- numexpr **compiles** that string into fast machine code once (JIT), then runs
  it.
- It processes the arrays in **blocks across many CPU cores at once**
  (multithreading) — this is the main reason it is faster.
- It does **not** create a separate full-size temporary for every intermediate;
  it keeps only a couple of small block buffers.
- Its division produces a **`float64`** result (8 bytes/pixel), which is **twice
  the memory** of the numpy `float32` result.
- With `casting='safe'`, numexpr will not silently squeeze that `float64` result
  into a `float32` buffer (that would lose precision), so the result stays
  `float64`.

### Side-by-side

| | numpy (in-place) | numexpr |
|---|---|---|
| How you write it | Python expression | text string expression |
| Runs on | 1 core (default) | all cores (multithreaded) |
| Temporary copies | few (with `out=`) | few (small block buffers) |
| Compile step | none | JIT, once |
| Result format (from `float32` math) | `float32` (4 bytes/px) | `float64` (8 bytes/px) |
| Best for | small/medium arrays, predictable memory | large arrays on multi-core machines |

### Practical rule of thumb

- **Small arrays:** numpy is fine — numexpr's setup/compile overhead can make it
  no faster, sometimes slower.
- **Large arrays on a multi-core machine:** numexpr is usually much faster
  (about 8x on 10 cores in our tests), at the cost of a larger `float64` result.
- In both cases, **memory reuse (in-place / `out=`) and keeping data in RAM**
  matter more than anything else.

---

## 7. Things to watch out for

- **Swap kills timing.** If the run does not fit in memory, the computer uses
  the disk and the numbers become ~10x worse. Reduce `--pixels` until it fits,
  or free up memory first.
- **`uint8` arithmetic wraps.** Do not compute the formula directly in `uint8`:
  `I1 - I2` underflows and `I1 + I2` overflows. Both scripts cast to a wider
  format first. That is why `--compute-dtype` exists.
- **`float16` is slow on CPU.** It saves memory but has no fast CPU path, so it
  is ~12x slower. Use it only when memory is the hard constraint.
- **Thread count matters.** With `--threads 1`, numexpr matches numpy; the
  speed-up comes from using more cores. Your machine's core count will change
  the result.
- **First numexpr call includes compilation.** Ignore very small runs when
  judging numexpr speed.
- **Background load matters.** Other programs using CPU or memory will change
  the numbers; run tests on a quiet machine for fair comparisons.

---

## 8. Quick reference

```bash
# install
python3 -m venv .venv && .venv/bin/pip install numpy numexpr

# numpy: naive vs in-place, float32 compute, 1.1e9 pixels
.venv/bin/python normdiff_benchmark.py --pixels 1.1e9 --in-dtype uint8 \
    --compute-dtype float32 --mode naive inplace

# numpy: float16 compute
.venv/bin/python normdiff_benchmark.py --pixels 1.1e9 --in-dtype uint8 \
    --compute-dtype float16 --mode naive inplace

# numexpr vs numpy in-place
.venv/bin/python normdiff_numexpr.py --pixels 1.1e9 --mode numpy numexpr

# numexpr thread sweep
for t in 1 2 4 8 10; do
  .venv/bin/python normdiff_numexpr.py --pixels 1.1e9 --mode numexpr --threads $t
done

# quick, small, in-memory smoke test
.venv/bin/python normdiff_benchmark.py --pixels 1e7 --mode naive inplace
```
