# Large-image arithmetic performance study

**Prepared for:** supervisor review
**Topic:** timing and optimising element-wise arithmetic on very large image pairs
**Repository:** `range_doppler`
**Scripts:** `normdiff_benchmark.py`, `normdiff_numexpr.py`, `normdiff_extra.py`

This single document combines the methodology, the measured results, the run
instructions, and the conclusions. It is self-contained.

---

## 1. Executive summary

We measured how long it takes to compute a normalised difference on two
**1.1-billion-pixel** `uint8` images (32,000 x 34,375), and how the choice of
library, data type, memory strategy and CPU core count change the result.

**Headline findings**

| Finding | Evidence |
|---|---|
| **numexpr on all cores is the fastest** | 0.486 s vs 10.74 s for the numpy one-liner |
| **Forcing numexpr's result to 32-bit is a free win** | same speed (0.486 vs 0.514 s), half the RAM (4.40 vs 8.80 GB), identical answer |
| **Reusing memory (`out=`) roughly halves numpy's time** | 0.339 s vs 0.624 s at 300M px |
| **`float16` saves memory but is ~12x slower on CPU** | 4.11 s vs 0.339 s at 300M px |
| **The speed-up is from parallelism, not a cleverer algorithm** | 1-thread numexpr equals numpy; 10 threads is ~8x faster |
| **Spilling to disk (swap) costs ~10x** | the same work took ~1 s in RAM, ~12 s when it did not fit |

**Recommended configuration:**

> `uint8` inputs + `numexpr` + all cores + forced `float32` result
> → **~0.49 s and 4.40 GB** for 1.1 billion pixels.

---

## 2. The problem

For every pixel of two images we compute a "normalised difference":

```
|I1 - I2| / (I1 + I2 + eps)
```

- `I1`, `I2` are two images of the same size (values 0-255).
- The result is 0 where the images agree and approaches 1 where they differ.
- `eps` (1e-6) prevents division by zero.

**Setup.** Two images, each 1.1e9 pixels, stored as `uint8` (1 byte/pixel, the
normal image format). The arithmetic must be performed in a wider format,
because on `uint8`: subtraction wraps (underflows) and addition overflows
(255 + 255 > 255).

A **second calculation** was also benchmarked (section 6) — a
statistics-normalised ratio:

```
I1 / (I2 + 0.1*median(I1)) + std1 / (std2 + 0.1*median(std1))
```

---

## 3. Methodology (how the timings were measured)

The goal is to measure **the calculation only**, not setup, and to confirm the
answer is real.

1. **Allocate first, time second.** Images are created before the clock starts;
   allocation time is reported separately.
2. **`time.perf_counter()`** wraps the operation (high-resolution wall clock).
3. **Force the result to be produced.** A checksum (`result.sum(...)`) is taken
   afterwards. This (a) prevents the optimiser from skipping unused work and
   (b) confirms every method returns the same answer.
4. **Single-shot runs at 1.1e9** (gigabyte arrays); repeated runs at smaller
   sizes.
5. **Report memory context.** The scripts print available memory and whether the
   run is likely to fit, because swapping to disk changes the timing ~10x.
6. **numexpr specifics.** The script prints its version and thread count. numexpr
   JIT-compiles the expression once; the first (tiny) call can look slow.

### All methods

| Method | How it works |
|---|---|
| numpy naive | Literal expression; numpy makes several full-size temporary arrays; 1 core |
| numpy in-place | Same maths, writes into pre-existing buffers via `out=`; 1 core |
| numpy float16 | As above but in `float16`; halves memory, no fast CPU path |
| numexpr float64 | Formula passed as a text string; JIT-compiled, multithreaded; result is float64 |
| numexpr forced float32 | As above but into a pre-allocated `float32` buffer (`out=`, `casting='same_kind'`) |

---

## 4. Results

### 4.1 All methods — 1.1 billion pixels (`uint8` inputs)

| # | Method | Compute / result type | CPU cores | Time | Result size | Notes |
|--:|---|---|--:|--:|--:|---|
| 1 | numpy naive (literal) | float32 | 1 | 10.74 s | 4.40 GB | spilled to disk (swap) |
| 2 | numpy in-place (`out=`) | float32 | 1 | ~1.8 s | 4.40 GB | 1.8-4.0 s under memory pressure |
| 3 | numpy naive (literal) | float16 | 1 | 16.93 s | 2.20 GB | float16 is slow on CPU |
| 4 | numpy in-place (`out=`) | float16 | 1 | 15.27 s | 2.20 GB | float16 is slow on CPU |
| 5 | numexpr `casting='safe'` | float64 | 10 | 0.514 s | 8.80 GB | fastest; result is 2x memory |
| 6 | **numexpr forced `out=float32`** | **float32** | **10** | **0.486 s** | **4.40 GB** | **best overall** |

All float32/float64 methods produced the same checksum (`4.275743e+08`); float16
differs slightly (`4.275722e+08`) due to lower precision.

### 4.2 Stable in-memory comparison — 300 million pixels

At this size nothing swaps, so these numbers are reproducible and show the "true"
speed of each method.

| # | Method | Type | Cores | Time | Result size |
|--:|---|---|--:|--:|--:|
| 1 | numpy naive | float32 | 1 | 0.624 s | 1.20 GB |
| 2 | numpy in-place | float32 | 1 | 0.339 s | 1.20 GB |
| 3 | numpy naive | float16 | 1 | 4.544 s | 0.60 GB |
| 4 | numpy in-place | float16 | 1 | 4.114 s | 0.60 GB |
| 5 | numexpr | float64 | 10 | 0.142 s | 2.40 GB |
| 6 | numexpr forced (32-bit) | float32 | 10 | 0.116 s | 1.20 GB |

### 4.3 numexpr thread scaling — 1.1 billion pixels

Varying only the number of CPU cores. Result memory is fixed: 8.80 GB (float64),
4.40 GB (float32).

| CPU cores | float64 time | float32 time | float64 speed-up | float32 speed-up |
|--:|--:|--:|--:|--:|
| 1 | 3.853 s | 3.155 s | 1.0x | 1.0x |
| 2 | 1.559 s | 1.607 s | 2.5x | 2.0x |
| 4 | 0.804 s | 0.825 s | 4.8x | 3.8x |
| 8 | 0.596 s | 0.620 s | 6.5x | 5.1x |
| 10 | 0.604 s | **0.550 s** | 6.4x | 5.7x |

Scaling is strong to ~4-8 cores, then flattens as the memory bus saturates.
**With 1 thread numexpr matches numpy**, so the win comes from using all cores.
float32 is at least as fast as float64 everywhere, at half the memory.

### 4.4 Forcing numexpr to 32-bit — the key result

| numexpr version | Result type | Time (1.1e9) | Result RAM | Time (3.0e8) | Result RAM |
|---|---|---:|---:|---:|---:|
| default (`casting='safe'`) | float64 | 0.514 s | 8.80 GB | 0.142 s | 2.40 GB |
| **forced (`out=float32`)** | **float32** | **0.486 s** | **4.40 GB** | **0.116 s** | **1.20 GB** |

Same speed, half the memory, identical checksum.

---

## 5. How each method is performed

**1. numpy naive.** The formula written literally. numpy evaluates one
sub-operation at a time and allocates a fresh full-size temporary for each
(`I1-I2`, `abs`, `I1+I2`, `+eps`, divide), and casts each input twice. One core.

**2. numpy in-place.**
```python
a = I1.astype(np.float32)      # buffer 1
d = np.empty_like(a)           # buffer 2
np.subtract(a, I2, out=d)      # d = I1 - I2
np.abs(d, out=d)
np.add(a, I2, out=a)           # a = I1 + I2
a += np.float32(1e-6)
np.divide(d, a, out=d)         # d = |I1-I2|/(I1+I2+eps)
```
Two buffers instead of many temporaries; `I2` is converted on the fly. One core.

**3 & 4. float16.** Same code, working type `float16`. Halves bytes moved but has
no fast CPU kernel path.

**5. numexpr float64.**
```python
ne.evaluate("abs(I1 - I2) / (I1 + I2 + eps)",
            local_dict={...}, casting="safe")
```
Formula as a text string, JIT-compiled, run block-by-block across all cores, with
only small block buffers. `/` yields float64, and `casting='safe'` will not narrow
it.

**6. numexpr forced float32.**
```python
out = np.empty(I1.shape, dtype=np.float32)
ne.evaluate("abs(I1 - I2) / (I1 + I2 + eps)",
            local_dict={...}, out=out, casting="same_kind")
```
Same as 5 but writes into a pre-allocated float32 buffer. The casting rule is
relaxed because `float64 -> float32` is not a "safe" cast.

---

## 6. Second calculation: statistics-normalised ratio

```
I1 / (I2 + 0.1*median(I1))  +  std1 / (std2 + 0.1*median(std1))
```

`median(I1)`, `std1`, `std2` are global scalars (`median(std1)` is just `std1`,
since `std1` is a scalar), giving constants
`c1 = 0.1*median(I1)` and `c2 = std1/(std2 + 0.1*std1)`, then
`out = I1/(I2 + c1) + c2`. This is a **reduction** (median + two standard
deviations) followed by one **elementwise pass**.

For reproducibility: the median is the exact median of the `uint8` values, and
the standard deviations are the **population** standard deviation (`ddof=0`,
numpy's default). The constants measured were `median(I1)=127`,
`std1≈73.90`, `std2≈73.90`, giving `c1≈12.7` and `c2≈0.909`.

**Elementwise pass**

| pixels | Method | Cores | Time | Result size |
|--:|---|--:|--:|--:|
| 1.1e9 | numpy naive | 1 | 1.354 s | 4.40 GB |
| 1.1e9 | numpy in-place | 1 | 1.255 s | 4.40 GB |
| 1.1e9 | **numexpr forced 32-bit** | 10 | **0.286 s** | 4.40 GB |
| 3.0e8 | numpy naive | 1 | 0.472 s | 1.20 GB |
| 3.0e8 | numpy in-place | 1 | 0.221 s | 1.20 GB |
| 3.0e8 | **numexpr forced 32-bit** | 10 | **0.068 s** | 1.20 GB |

**Reduction (median + 2 std)**

| pixels | Reduction time |
|--:|--:|
| 1.1e9 | 10.714 s |
| 3.0e8 | 2.488 s |

**Totals**

| pixels | Method | Reduction | Elementwise | Total |
|--:|---|---|--:|--:|
| 1.1e9 | numpy naive | 10.714 s | 1.354 s | 12.068 s |
| 1.1e9 | numpy in-place | 10.714 s | 1.255 s | 11.969 s |
| 1.1e9 | numexpr 32-bit | 10.714 s | 0.286 s | 11.000 s |
| 3.0e8 | numpy naive | 2.488 s | 0.472 s | 2.959 s |
| 3.0e8 | numpy in-place | 2.488 s | 0.221 s | 2.709 s |
| 3.0e8 | numexpr 32-bit | 2.488 s | 0.068 s | 2.556 s |

**What this shows.** The reduction dominates: ~10.7 s of the ~11 s total, versus
~0.29 s for the best elementwise pass. Optimising the inner loop 4.7x improved the
total by only ~11%. The exact median is the bottleneck. **Measure the whole
pipeline, not just the inner loop.**

---

## 7. Pros and cons

| Method | Pros | Cons |
|---|---|---|
| numpy naive | simplest to write; fine for small arrays | many full-size temporaries; high peak memory; swapped at 1.1e9; 1 core |
| numpy in-place | ~2x faster than naive; ~half peak memory; no extra packages | more verbose; still 1 core |
| numpy float16 | half the memory | ~12x slower; ~3-digit precision |
| numexpr float64 | fastest by far; single readable expression; full precision | result is float64 (2x memory); needs numexpr; 1 core = no gain |
| **numexpr forced float32** | **fastest and memory-efficient; identical answer** | needs `out=` + relaxed casting; still needs multiple cores to beat numpy |

**Chooser**

| Situation | Best choice |
|---|---|
| Small/medium array, simple code | numpy naive |
| Large array, no extra packages | numpy in-place (`out=`) |
| Array barely fits in RAM | `float16` or chunk the work |
| Many cores, max speed | numexpr |
| Max speed **and** min memory | **numexpr forced `float32`** |

---

## 8. How to run

### Setup

```bash
python3 -m venv .venv
.venv/bin/pip install numpy numexpr
```

### Main commands

```bash
# numpy naive + in-place, float32 compute, 1.1e9 pixels
.venv/bin/python normdiff_benchmark.py --pixels 1.1e9 --in-dtype uint8 \
    --compute-dtype float32 --mode naive inplace

# numpy float16
.venv/bin/python normdiff_benchmark.py --pixels 1.1e9 --in-dtype uint8 \
    --compute-dtype float16 --mode naive inplace

# numexpr float64 vs numpy in-place
.venv/bin/python normdiff_numexpr.py --pixels 1.1e9 --mode numpy numexpr

# numexpr forced to float32 (half the result memory)
.venv/bin/python normdiff_numexpr.py --pixels 1.1e9 --mode numpy numexpr \
    --out-dtype float32

# numexpr thread sweep
for dt in float64 float32; do
  for t in 1 2 4 8 10; do
    .venv/bin/python normdiff_numexpr.py --pixels 1.1e9 --mode numexpr \
        --threads $t --out-dtype $dt
  done
done

# statistics-normalised ratio (section 6)
.venv/bin/python normdiff_extra.py --pixels 1.1e9

# quick in-memory smoke test
.venv/bin/python normdiff_benchmark.py --pixels 1e7 --mode naive inplace
```

### Options

| Script | Options |
|---|---|
| `normdiff_benchmark.py` | `--pixels`, `--in-dtype {uint8,uint16,int16,float32,float64}`, `--compute-dtype {float16,float32,float64}`, `--mode {naive,inplace}`, `--seed` |
| `normdiff_numexpr.py` | `--pixels`, `--in-dtype {uint8,uint16,int16}`, `--mode {numpy,numexpr}`, `--threads`, `--out-dtype {float32,float64}`, `--seed` |
| `normdiff_extra.py` | `--pixels`, `--in-dtype {uint8,uint16,int16}`, `--mode {naive,inplace,numexpr}`, `--threads`, `--seed` |

---

## 9. Caveats

- **Timings vary ~15-30%** with machine load and memory state. The 1.1e9 runs
  were affected by background memory pressure (a running system already used
  several GB), which is why some numbers (numpy in-place) move between runs.
- **The 300M numbers are the reliable comparison** — nothing swaps there.
- **`uint8` arithmetic wraps**; all scripts cast to a wider type first.
- **Swap changes the timing by ~10x**; reduce `--pixels` until the run fits.
- **Core count matters**; results depend on the machine (10 cores used here).

---

## 10. Conclusions and recommendations

1. **Use `uint8` for storage** (4x smaller) and **compute in `float32`** (never in
   `uint8`).
2. **Use `numexpr` forced to `float32`** for the best combination of speed and
   memory. This was the fastest method and produced the correct answer.
3. **If `numexpr` is unavailable, use numpy in-place (`out=`)**.
4. **Avoid `float16` on CPU** unless memory is the hard constraint.
5. **Keep data in RAM.** The single largest slowdown observed was swapping to
   disk (~10x).
6. **Optimise the whole pipeline.** In the second calculation the reduction
   dominated the cost, so inner-loop tuning had little effect on the total.
7. **Report timings with context**: input dtype, compute dtype, core count, and
   whether the data fit in memory.
