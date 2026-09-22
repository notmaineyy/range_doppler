# Timing results: normalised difference of two images

This document explains how long a common image calculation takes, and why the
*same* calculation can be fast or slow depending on **how you write it** and
**how your computer stores the data**. No prior technical background is assumed.

The numbers come from two scripts, `normdiff_benchmark.py` (plain numpy) and
`normdiff_numexpr.py` (adds numexpr). See `readme_timing.md` for how to run them.

---

## 1. The calculation

For every pixel we compute the "normalised difference" of two images:

```
|I1 - I2| / (I1 + I2 + eps)
```

In plain words:

- `I1` and `I2` are two images of the same size (two greyscale photos, each
  pixel a number from 0 to 255).
- For each pixel we take the absolute difference and divide by the sum. The
  result is a new image where **0 means "identical"** and **1 means "as
  different as possible"**.
- `eps` is a tiny safety number (0.000001) so we never divide by zero.

A **second calculation** is benchmarked in section 4a — a statistics-normalised
ratio that first computes global scalars (median and standard deviations) and
then one elementwise pass:

```
I1 / (I2 + 0.1*median(I1)) + std1 / (std2 + 0.1*median(std1))
```

The rest of the document (sections 3-3b) concern the first formula; section 4a
covers the second.

---

## 2. Test setup

- **Two images, each 1.1 billion pixels** (32,000 rows x 34,375 columns).
- Pixels stored as **`uint8`** (1 byte each, values 0..255) — the normal way
  image files store pixels.
- The maths must be done in a **wider** number format, because on `uint8`:
  `I1 - I2` wraps (underflows) and `I1 + I2` overflows (255 + 255 > 255).
- We compared several ways of doing the maths, and several number formats.

---

## 3. The short version

1. **Store images as `uint8`** to save memory; **compute in `float32`**.
2. **`numexpr` is the fastest** — but only because it uses **all CPU cores**.
3. **Force numexpr to 32-bit (`float32`)** and it is *just as fast* as 64-bit
   while using **half the memory** (4.40 GB instead of 8.80 GB).
4. **`float16` saves memory but is ~12x slower** on a CPU.
5. **If the data does not fit in memory, the computer spills it to disk
   ("swap"), and everything becomes roughly 10x slower.**

---

## 3a. Headline result: numexpr forced to 32-bit (`float32`)

This is the specific experiment "force numexpr to use 32-bit to save RAM". It is
rows **#5 vs #6** in the full table below. Forcing 32-bit output is a free win:
same speed, half the RAM, identical answer.

| numexpr version | Result format | Time (1.1e9 px) | Result memory | Time (3.0e8 px) | Result memory |
|---|---|---:|---:|---:|---:|
| default (`casting='safe'`) | 64-bit float (`float64`) | 0.514 s | 8.80 GB | 0.142 s | 2.40 GB |
| **forced 32-bit (`out=float32`)** | **32-bit float (`float32`)** | **0.486 s** | **4.40 GB** | **0.116 s** | **1.20 GB** |

- **Speed:** essentially unchanged (0.486 s vs 0.514 s at 1.1e9 px; 0.116 s vs
  0.142 s at 3.0e8 px).
- **Memory:** **halved** — 4.40 GB instead of 8.80 GB at 1.1e9 px.
- **Correctness:** the identical checksum (`4.275743e+08` at 1.1e9 px), so the
  forced 32-bit result is the same as the 64-bit one.
- **How:** run with `--out-dtype float32`, which pre-allocates a `float32` buffer
  and passes it as `out=`, with `casting='same_kind'` (numexpr will not do this
  downcast under `'safe'`). Full details in **Method 6** below.

---

## 3b. numexpr thread scaling: float64 vs float32

Same 1.1e9-pixel problem, same expression, varying only the number of CPU cores
numexpr is allowed to use (`--threads 1|2|4|8|10`). Result memory is fixed per
run: **8.80 GB for float64**, **4.40 GB for float32**.

| CPU cores (threads) | float64 time | float32 time |
|--:|--:|--:|
| 1 | 3.853 s | 3.155 s |
| 2 | 1.559 s | 1.607 s |
| 4 | 0.804 s | 0.825 s |
| 8 | 0.596 s | 0.620 s |
| 10 | 0.604 s | **0.550 s** |

Speed-up relative to a single thread (same data, different view):

| CPU cores | float64 speed-up | float32 speed-up |
|--:|--:|--:|
| 1 | 1.0x | 1.0x |
| 2 | 2.5x | 2.0x |
| 4 | 4.8x | 3.8x |
| 8 | 6.5x | 5.1x |
| 10 | 6.4x | 5.7x |

**What this shows**

- **Scaling is strong up to ~4-8 cores, then flattens.** Beyond ~8 cores the
  memory bus is saturated, so extra cores add little (float64 even dips slightly
  at 10 cores). This is a memory-bandwidth-bound calculation.
- **float32 is at least as fast as float64 at every core count**, and clearly
  faster with one core (3.155 s vs 3.853 s) because it moves half the bytes.
  With all 10 cores both land around 0.55-0.60 s.
- **The ~8x win over numpy comes almost entirely from using all 10 cores.** With
  1 thread, numexpr matches numpy (see Method 5).
- **Variance:** timings move by roughly ±15% run to run with machine load, which
  is why the 10-thread float64 value here (0.604 s) differs a little from the
  0.514 s in section 3a.

---

## 4. All methods compared (1.1 billion pixels, `uint8` inputs)

This is the single table with every version. Times are the calculation only.

| # | Method | Compute / result type | CPU cores | Time | Result size | Notes |
|--:|---|---|--:|--:|--:|---|
| 1 | numpy naive (literal) | float32 | 1 | 10.74 s | 4.40 GB | spilled to disk (swap) |
| 2 | numpy in-place (`out=`) | float32 | 1 | ~1.8 s | 4.40 GB | ranged 1.8–4.0 s with memory pressure |
| 3 | numpy naive (literal) | float16 | 1 | 16.93 s | 2.20 GB | float16 is slow on CPU |
| 4 | numpy in-place (`out=`) | float16 | 1 | 15.27 s | 2.20 GB | float16 is slow on CPU |
| 5 | numexpr `casting='safe'` | float64 | 10 | 0.514 s | 8.80 GB | fastest; result is 2x memory |
| 6 | **numexpr forced `out=float32`** (32-bit) | **float32** | **10** | **0.486 s** | **4.40 GB** | same speed as #5, half the memory |

All methods produced the same answer to within rounding: the checksum at 1.1e9
is `4.275743e+08` for every float32/float64 method (float16 differs slightly,
`4.275722e+08`, from its lower precision).

### Same comparison at 300 million pixels (everything fits in memory)

At this smaller size nothing swaps, so these numbers are stable and show the
"true" speed of each method.

| # | Method | Type | Cores | Time | Result size |
|--:|---|---|--:|--:|--:|
| 1 | numpy naive | float32 | 1 | 0.624 s | 1.20 GB |
| 2 | numpy in-place | float32 | 1 | 0.339 s | 1.20 GB |
| 3 | numpy naive | float16 | 1 | 4.544 s | 0.60 GB |
| 4 | numpy in-place | float16 | 1 | 4.114 s | 0.60 GB |
| 5 | numexpr | float64 | 10 | 0.142 s | 2.40 GB |
| 6 | numexpr forced (32-bit) | float32 | 10 | 0.116 s | 1.20 GB |

**Key observations**

- **#6 is the winner overall**: fastest *and* no more memory than numpy float32.
- **#5 and #6 are the same speed** (0.514 s vs 0.486 s) — forcing float32
  costs nothing in time and saves 4.40 GB.
- **#2 is ~2x faster than #1** (in-place beats the literal one-liner).
- **#3/#4 (float16) are ~12x slower than float32** despite using half the
  memory.
- **#1 at 1.1e9 is 10x slower than its 300M rate** purely because it swapped.

---

## 4a. A second calculation: statistics-normalised ratio

A different, statistics-based calculation on the same two `uint8` images:

```
I1 / (I2 + 0.1*median(I1))  +  std1 / (std2 + 0.1*median(std1))
```

where `median(I1)` is the scalar median of image `I1`, and `std1`, `std2` are the
scalar standard deviations of `I1` and `I2`. Because `std1` is a scalar,
`median(std1)` is simply `std1`, so the second term is a constant:

```
c1 = 0.1 * median(I1)            # added inside the division
c2 = std1 / (std2 + 0.1 * std1)  # a scalar offset
out = I1 / (I2 + c1) + c2
```

This is **two stages**: a **global reduction** (median + two standard deviations)
that produces two scalars, then a single **elementwise pass**. The elementwise
pass is timed with the same three variants; the reduction is timed separately.

Script: `normdiff_extra.py` (`--pixels`, `--in-dtype`, `--mode`, `--threads`,
`--seed`).

### Elementwise pass

| pixels | Method | Type | Cores | Elementwise time | Result size |
|--:|---|---|--:|--:|--:|
| 1.1e9 | numpy naive | float32 | 1 | 1.354 s | 4.40 GB |
| 1.1e9 | numpy in-place | float32 | 1 | 1.255 s | 4.40 GB |
| 1.1e9 | **numexpr forced 32-bit** | float32 | 10 | **0.286 s** | 4.40 GB |
| 3.0e8 | numpy naive | float32 | 1 | 0.472 s | 1.20 GB |
| 3.0e8 | numpy in-place | float32 | 1 | 0.221 s | 1.20 GB |
| 3.0e8 | **numexpr forced 32-bit** | float32 | 10 | **0.068 s** | 1.20 GB |

All three variants produced the identical checksum (`2.692861e+09` at 1.1e9,
`7.344372e+08` at 3.0e8), so the fast forms are correct.

### The reduction (median + 2 std)

| pixels | Reduction time |
|--:|--:|
| 1.1e9 | 10.714 s |
| 3.0e8 | 2.488 s |

The reduction costs about **10-30x more than the numexpr elementwise pass**. The
exact median costs the most: it partitions a copy of the image
(`numpy.partition`), which is `O(n)` but with random access and a full pass. The
two `std` calls add two more passes.

### Totals (reduction + elementwise)

| pixels | Method | Reduction | Elementwise | Total |
|--:|---|---|--:|--:|
| 1.1e9 | numpy naive | 10.714 s | 1.354 s | 12.068 s |
| 1.1e9 | numpy in-place | 10.714 s | 1.255 s | 11.969 s |
| 1.1e9 | numexpr 32-bit | 10.714 s | 0.286 s | 11.000 s |
| 3.0e8 | numpy naive | 2.488 s | 0.472 s | 2.959 s |
| 3.0e8 | numpy in-place | 2.488 s | 0.221 s | 2.709 s |
| 3.0e8 | numexpr 32-bit | 2.488 s | 0.068 s | 2.556 s |

### What this shows

- **The reduction dominates.** At 1.1e9 px the median + standard deviations cost
  ~10.7 s, while the best elementwise pass is ~0.29 s. Optimising the elementwise
  part from 1.354 s to 0.286 s (4.7x) only improves the total by ~11%.
- **numexpr still wins the elementwise stage** — 0.286 s versus 1.255-1.354 s for
  the numpy variants. This calculation is a good fit for numexpr because it is a
  pure elementwise expression with no full-size temporaries and no reduction.
- **The median is the bottleneck.** For speed, replace the exact median with an
  approximate one (subsample, P² algorithm) or a cheaper statistic (mean). The
  standard deviations can also be fused into a single pass instead of two.
- **The formula itself is cheap; the statistics are expensive.** This is a useful
  general lesson: measure the whole pipeline, not just the inner loop.

---

## 5. How each method is performed

### Method 1 — numpy naive (literal expression)

```python
return np.abs(I1.astype(np.float32) - I2.astype(np.float32)) / (
    I1.astype(np.float32) + I2.astype(np.float32) + np.float32(1e-6))
```

- Write the formula exactly as it reads.
- numpy evaluates **one sub-operation at a time**, and each one creates a
  **brand-new full-size temporary array** (`I1-I2`, then `abs(...)`, then
  `I1+I2`, then `+eps`, then the division).
- It also **casts each input twice** (once for the numerator, once for the
  denominator), so several extra copies are made.
- Runs on **one CPU core**.

### Method 2 — numpy in-place (`out=` reuse)

```python
a = I1.astype(np.float32)      # buffer 1 = I1
d = np.empty_like(a)           # buffer 2 = result
np.subtract(a, I2, out=d)      # d = I1 - I2
np.abs(d, out=d)
np.add(a, I2, out=a)           # a = I1 + I2   (I1 no longer needed)
a += np.float32(1e-6)
np.divide(d, a, out=d)         # d = |I1-I2| / (I1+I2+eps)
```

- Same maths, but each step writes into memory that **already exists** (`out=`).
- Uses only **two** float buffers instead of many temporaries.
- `I2` (uint8) is converted to float **on the fly** inside the operation, so it
  is never materialised as a separate float array.
- Runs on **one CPU core**.

### Methods 3 & 4 — numpy in `float16`

- Identical code to methods 1 and 2, but with `float16` as the working type
  (`a = I1.astype(np.float16)`, etc.).
- Halves the bytes moved, but numpy has **no fast float16 CPU kernels**, so it
  falls back to a slow path — hence ~12x slower.

### Method 5 — numexpr, `casting='safe'` (float64)

```python
ne.evaluate("abs(I1 - I2) / (I1 + I2 + eps)",
            local_dict={"I1": I1, "I2": I2, "eps": eps},
            casting="safe")
```

- The formula is passed as a **text string**. numexpr **compiles** it once
  (JIT) and runs it **block-by-block across all CPU cores**.
- It does **not** create a full-size temporary for every sub-expression; it
  keeps only a couple of small block buffers.
- The `/` operator produces **float64**, and `casting='safe'` does not allow
  narrowing it, so the result is float64 (8 bytes/pixel → 8.80 GB at 1.1e9).

### Method 6 — numexpr forced to 32-bit (`float32`)

```python
out = np.empty(I1.shape, dtype=np.float32)
ne.evaluate("abs(I1 - I2) / (I1 + I2 + eps)",
            local_dict={"I1": I1, "I2": I2, "eps": eps},
            out=out, casting="same_kind")
```

- Same as method 5, but we **pre-allocate a float32 result buffer** and pass it
  as `out=`.
- Because `float64 -> float32` is **not** a "safe" cast, the casting rule must
  be relaxed to `'same_kind'` (or `'unsafe'`). This is the one trade-off: you
  give up the automatic "safe" guarantee to save memory.
- The result is float32 (4 bytes/pixel → 4.40 GB), and it is **just as fast** as
  method 5.

> There is also a neat alternative that needs no `out=` and no relaxed casting:
> add a `float32` zero to force float32 throughout, e.g.
> `abs(I1 - I2 + zero32) / (I1 + I2 + eps)` with `zero32 = np.float32(0)`.
> All three float32 routes give the identical answer.

---

## 6. Pros and cons of each method

### 1. numpy naive (literal) — float32

- **Pros:** easiest to read and write; correct; ideal for small/medium arrays.
- **Cons:** creates many full-size temporaries, so peak memory is high; at 1.1e9
  it spilled to disk and became ~10x slower; single-threaded.

### 2. numpy in-place (`out=`) — float32

- **Pros:** about **2x faster** than the naive form; roughly **half the peak
  memory**; no extra dependencies; deterministic, single-threaded; result is
  float32 (4.40 GB).
- **Cons:** more verbose and less obvious than the one-liner; still uses only
  **one core**, so it is slower than numexpr on a multi-core machine.

### 3 & 4. numpy — float16

- **Pros:** **half the memory** of float32 (2.20 GB); may let an array fit in
  RAM that otherwise would not.
- **Cons:** **~12x slower** on a CPU (no fast float16 kernels); less precision
  (~3 significant digits); use only when memory is the hard limit.

### 5. numexpr — float64 (`casting='safe'`)

- **Pros:** **fastest** by a wide margin (uses all cores, no full temporaries);
  the expression stays a single readable string; keeps full float64 precision.
- **Cons:** the **result is float64 — twice the memory** (8.80 GB); requires the
  `numexpr` package; the speed-up depends on the number of CPU cores (1 core =
  no gain); the first call includes JIT compilation.

### 6. numexpr forced to 32-bit (`float32`) — the recommended default

- **Pros:** **fastest *and* memory-efficient** — the same 4.40 GB as numpy
  float32, at ~8.5x the speed of numpy in-place; identical answer to float64.
- **Cons:** requires `out=` and a relaxed casting rule (`'same_kind'`/`'unsafe'`)
  instead of `'safe'`; still needs multiple cores to beat numpy; result precision
  is float32 (amply sufficient here).

### Quick chooser

| Situation | Best choice |
|---|---|
| Small/medium array, simple code | numpy naive (#1) |
| Large array, no extra packages | numpy in-place (#2) |
| Array barely fits in RAM | float16 (#3/#4) or chunk the work |
| Many CPU cores, want max speed | numexpr (#5/#6) |
| Max speed **and** minimum memory | **numexpr forced float32 (#6)** |

---

## 7. The words, in plain English

### About the data

- **Pixel** — one dot in an image; here, one number.
- **Array / 2-D array** — a rectangular grid of numbers (an image). "Shape
  32,000 x 34,375" means that many rows and columns.
- **Byte** — the smallest unit of computer memory (8 bits).
- **GB vs GiB** — two ways to count memory. `GB` = 1,000,000,000 bytes,
  `GiB` = 1,073,741,824 bytes. They are close.
- **`uint8`** — a whole number 0..255, stored in 1 byte. The normal way to store
  image pixels.
- **`float16` / `float32` / `float64`** — decimal number formats:
  - `float16`: 2 bytes, ~3 significant digits (rough, small).
  - `float32`: 4 bytes, ~7 digits (the everyday choice).
  - `float64`: 8 bytes, ~16 digits (precise, big).
- **`eps` (epsilon)** — a tiny constant added to the denominator to avoid
  dividing by zero.
- **Checksum** — a single number summarising the whole result, used to prove
  different methods produced the same answer.

### About how the code is written

- **Vectorised / matrix operation** — doing the maths on the whole image at once
  instead of looping pixel by pixel.
- **Naive ("literal one-line")** — writing the formula exactly as it reads; the
  computer quietly makes several full-size temporary copies.
- **In-place** — reusing memory instead of making new copies (like reusing one
  whiteboard rather than grabbing a fresh sheet for every step).
- **`out=` reuse** — the technical way to say "write the answer back into memory
  I already have".
- **Temporary** — a short-lived extra copy of the whole image.
- **JIT (just-in-time) compilation** — numexpr "translates" the formula the
  first time it sees it, then reuses the translation.
- **Multithreading** — splitting the work across several CPU cores at once.
- **`casting`** — the rule for whether a result may be stored in a smaller
  number format. `'safe'` only allows it when no precision is lost; `'same_kind'`
  is more permissive.

### About speed and memory

- **Memory bandwidth** — how fast numbers move between the processor and memory.
  This calculation is **limited by moving data**, not by arithmetic.
- **In RAM** — the data fits in the computer's working memory; fast.
- **Swap / swap-bound** — when data does not fit, the computer uses the **hard
  disk as overflow** (your desk is full, so you keep running to a filing
  cabinet). A "swap-bound" run is slow because of disk traffic, not the maths.

---

## 8. Why the times differ so much

| Effect | Simple reason | Size of the effect |
|---|---|---|
| `uint8` vs `float32` inputs | 4x less data to move | removed a 10x disk penalty |
| In-place vs naive | fewer memory copies | ~2x faster |
| `float16` vs `float32` compute | half the data, but no fast CPU float16 path | ~12x **slower** |
| numexpr with 10 cores vs 1 | work shared across cores | ~8.4x faster |
| numexpr forced 32-bit vs 64-bit | same speed, half the result memory | 8.80 GB -> 4.40 GB |
| Fits in memory vs spills to disk | disk is far slower than memory | ~10x slower |

---

## 9. Bottom line

- **Keep images as `uint8`**, and **compute in `float32`** (never in `uint8`).
- **Use `numexpr` forced to `float32`** for the best of both worlds: fastest
  *and* no more memory than numpy float32.
- **If you cannot add numexpr**, use **numpy in-place (`out=`)**.
- **Avoid `float16`** unless memory is the hard limit.
- **Keep the data in memory** — the single biggest slowdown was swapping to disk.
- **When reporting timings, always state**: input format, compute format, number
  of cores, and whether it fit in memory. Each changes the result by large
  factors. Timings also vary (~30%) with background load and memory state.
- **Measure the whole pipeline.** In the statistics-normalised ratio (section
  4a) the median/standard-deviation reduction cost ~10.7 s while the optimised
  elementwise pass cost only ~0.29 s — optimising the inner loop barely changed
  the total.

---

## 10. Reproducing

```bash
# numpy naive + in-place, float32 compute, 1.1e9 pixels
.venv/bin/python normdiff_benchmark.py --pixels 1.1e9 --in-dtype uint8 \
    --compute-dtype float32 --mode naive inplace

# numpy float16
.venv/bin/python normdiff_benchmark.py --pixels 1.1e9 --in-dtype uint8 \
    --compute-dtype float16 --mode naive inplace

# numexpr float64 (casting='safe')
.venv/bin/python normdiff_numexpr.py --pixels 1.1e9 --mode numpy numexpr \
    --out-dtype float64

# numexpr forced float32 (out=float32, casting='same_kind')
.venv/bin/python normdiff_numexpr.py --pixels 1.1e9 --mode numpy numexpr \
    --out-dtype float32

# thread sweep
for t in 1 2 4 8 10; do
  .venv/bin/python normdiff_numexpr.py --pixels 1.1e9 --mode numexpr --threads $t
done

# statistics-normalised ratio (section 4a): reduction + elementwise
.venv/bin/python normdiff_extra.py --pixels 1.1e9
.venv/bin/python normdiff_extra.py --pixels 3e8 --mode naive inplace numexpr
```

Options: `normdiff_benchmark.py` accepts `--pixels`, `--in-dtype`,
`--compute-dtype`, `--mode`, `--seed`. `normdiff_numexpr.py` accepts `--pixels`,
`--in-dtype`, `--mode`, `--threads`, `--out-dtype`, `--seed`.
`normdiff_extra.py` accepts `--pixels`, `--in-dtype`, `--mode`, `--threads`,
`--seed`.
