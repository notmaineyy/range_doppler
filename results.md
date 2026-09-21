# Timing results: normalised difference of two images

This document explains how long a common image calculation takes, and why the
*same* calculation can be fast or slow depending on **how you write it** and
**how your computer stores the data**. No prior technical background is assumed.

The raw results come from two scripts, `normdiff_benchmark.py` and
`normdiff_numexpr.py`. See `readme_timing.md` for how to run them.

---

## 1. The calculation

For every pixel we compute the "normalised difference" of two images:

```
|I1 - I2| / (I1 + I2 + eps)
```

In plain words:

- `I1` and `I2` are two images of the same size. Think of two greyscale photos,
  where each pixel is a number from 0 (black) to 255 (white).
- For each pixel we take the absolute difference of the two images, and divide
  it by their sum. The result is a new image where **0 means "identical"** and
  **1 means "as different as possible"**.
- `eps` is a tiny safety number (0.000001) so we never divide by zero.

This kind of formula is common in remote sensing and image comparison (for
example, checking how much two satellite images changed).

---

## 2. The test setup

- **Two images, each 1.1 billion pixels**, laid out as 32,000 rows by 34,375
  columns (`32,000 x 34,375 = 1,100,000,000`).
- Each pixel is stored as **`uint8`** — one byte, holding a number 0..255. This
  is how normal image files store pixels.
- We compared several ways of doing the maths, and several number formats.

---

## 3. The short version (if you read nothing else)

1. **Store images as `uint8`** (1 byte per pixel) to save memory.
2. **Do the maths in `float32`** (or `int16`). Do *not* do it in `uint8` — the
   numbers wrap around and you get wrong answers.
3. **Reuse memory ("in-place")** instead of creating lots of temporary copies.
4. **`numexpr` is the fastest** option — but it uses multiple CPU cores, uses
   more memory for the result, and needs a fast machine.
5. **`float16` saves memory but is about 12x slower** — use it only when memory
   is the hard limit, not for speed.
6. **If the data does not fit in memory, the computer spills it to disk
   ("swap"), and everything becomes roughly 10x slower.**

---

## 4. The results, explained simply

All runs below use two `uint8` images of 1.1 billion pixels each. "Time" is how
long the calculation alone took.

### 4a. Plain numpy, working in float32 (the everyday choice)

| how it was written | time | speed |
|---|---:|---:|
| Reusing memory (in-place) | 4.45 s | 0.25 billion pixels/s |
| Literal one-line expression ("naive") | not run at this size | — |
| *Smaller 300M-pixel test:* literal expression | 0.76 s | 0.39 billion pixels/s |
| *Smaller 300M-pixel test:* reusing memory | 0.35 s | 0.87 billion pixels/s |

**Reading it:** reusing memory is about **twice as fast** as the literal
one-liner, and uses far less memory.

### 4b. Plain numpy, working in float16 (the memory-saving choice)

| how it was written | time | speed |
|---|---:|---:|
| Reusing memory (in-place) | 15.9 s | 0.07 billion pixels/s |
| Literal one-line expression ("naive") | 17.5 s | 0.06 billion pixels/s |
| *Smaller 300M-pixel test:* literal expression | 4.54 s | 0.07 billion pixels/s |
| *Smaller 300M-pixel test:* reusing memory | 4.06 s | 0.07 billion pixels/s |

**Reading it:** float16 uses half the memory but is roughly **12x slower**.
Saving memory here costs a lot of speed.

### 4c. numexpr (the fastest option — uses all CPU cores)

Same two `uint8` images, 1.1 billion pixels, comparing how many CPU cores it
uses:

| method | CPU cores used | time | speed | result size |
|---|---:|---:|---:|---:|
| numpy, reusing memory | 1 | 4.40 s | 0.25 billion/s | 4.40 GB |
| numexpr | 1 | 4.34 s | 0.25 billion/s | 8.80 GB |
| numexpr | 2 | 1.56 s | 0.70 billion/s | 8.80 GB |
| numexpr | 4 | 0.79 s | 1.39 billion/s | 8.80 GB |
| numexpr | 8 | 0.58 s | 1.89 billion/s | 8.80 GB |
| numexpr | 10 | **0.52 s** | **2.12 billion/s** | 8.80 GB |

**Reading it:** with a single core, numexpr is the same speed as numpy. With all
10 cores it is about **8.4x faster**. The speed comes entirely from using more
cores — not from a smarter formula. The trade-off is that numexpr produces a
`float64` result, which is **twice as big** (8.80 GB instead of 4.40 GB).

### 4d. An older run with float32 *inputs* (shows the disk-swap problem)

Earlier we stored the input images as `float32` instead of `uint8`. That made
each image 4x bigger, and the 1.1-billion-pixel run no longer fit in memory:

| method | time | speed | what happened |
|---|---:|---:|---|
| numpy, literal expression | 11.97 s | 0.09 billion/s | spilled to disk (swap) |
| numpy, reusing memory | 10.73 s | 0.10 billion/s | spilled to disk (swap) |
| *Smaller 300M-pixel test:* literal expression | 0.35 s | 0.87 billion/s | fit in memory |
| *Smaller 300M-pixel test:* reusing memory | 0.23 s | 1.32 billion/s | fit in memory |

**Reading it:** when the data fits in memory, the same work takes about
**1 second**. When it spills to disk, it takes about **12 seconds** — roughly
10x slower, purely because of the disk.

### 4e. Do the methods agree?

Yes. Every method produced the same answer to within tiny rounding differences
(about 0.0003%). This confirms the fast versions are correct, not just quick.

---

## 5. The words, in plain English

### About the data

- **Pixel** — one dot in an image. Here it is one number.
- **Array / 2-D array** — a rectangular grid of numbers (an image is a 2-D
  array). "Shape 32,000 x 34,375" just means that many rows and columns.
- **Byte** — the smallest unit of computer memory (8 bits).
- **GB vs GiB** — two ways to count memory. `GB` = 1,000,000,000 bytes,
  `GiB` = 1,073,741,824 bytes. They are close; the difference is just how we
  count.
- **`uint8`** — a whole number from 0 to 255, stored in 1 byte. The normal way
  to store image pixels.
- **`float16` / `float32` / `float64`** — number formats for decimals:
  - `float16` uses 2 bytes and keeps ~3 significant digits (rough, small).
  - `float32` uses 4 bytes and keeps ~7 digits (the everyday choice).
  - `float64` uses 8 bytes and keeps ~16 digits (very precise, big).
  - Bigger format = more precision but more memory and slower to move around.

### About how the code is written

- **Vectorised / matrix operation** — doing the maths on the *whole image at
  once* instead of looping pixel by pixel. This is what makes it fast.
- **Naive ("literal one-line")** — writing the formula exactly as
  `|I1 - I2| / (I1 + I2 + eps)`. It is correct and easy to read, but the
  computer secretly makes several full-size **temporary** copies along the way.
- **In-place** — doing the same maths while **reusing memory** instead of making
  new copies. Think of reusing the same whiteboard rather than grabbing a fresh
  sheet for every step. Faster and uses much less memory.
- **`out=` reuse** — the technical way to say "write the answer back into the
  memory I already have" instead of allocating new memory.
- **Temporary** — a short-lived extra copy of the whole image that the computer
  creates while calculating. Too many temporaries waste memory and time.

### About speed and memory

- **Memory bandwidth** — how fast the computer can move numbers between its
  processor and its memory. This calculation is **limited by moving data**, not
  by arithmetic, so bandwidth is the real bottleneck.
- **ns/pixel (nanoseconds per pixel)** — how long one pixel takes. Smaller is
  better.
- **Gpixel/s (billion pixels per second)** — how many pixels are processed each
  second. Bigger is better.
- **In RAM** — the data fits in the computer's working memory, so everything is
  fast.
- **Swap / swap-bound** — when data does not fit in memory, the computer uses
  the **hard disk as overflow**. Imagine your desk is full, so you keep running
  to a filing cabinet — much slower. A run that is "swap-bound" is slow because
  of this disk traffic, not because the calculation is hard.
- **Checksum** — a single number summarising the whole result, used only to
  prove that different methods produced the same answer.

### About using more CPU cores

- **Core** — an independent processor inside your computer's chip. This machine
  has 10 cores, so it can do up to 10 pieces of work at once.
- **Multithreading** — splitting the work across several cores at the same time.
  Think of one worker vs ten workers on the same pile of boxes.
- **`numexpr`** — a tool that takes the formula written as text, turns it into
  fast machine code, and runs it across all your cores at once.
- **JIT (just-in-time) compilation** — numexpr "translates" the formula the
  first time it sees it, then reuses the translation. This is why the very first
  (tiny) run can look slow.
- **`casting='safe'`** — a rule that only allows an answer to be saved in a
  smaller number format if no precision is lost. Because numexpr's division
  produces `float64`, it refuses to squeeze that into a `float32` result under
  this rule — so the result stays `float64` (and is twice as big).

---

## 6. Why the times differ so much

| effect | simple reason | size of the effect |
|---|---|---|
| `uint8` vs `float32` inputs | 4x less data to move | removed a 10x disk penalty |
| In-place vs naive | fewer memory copies | ~2x faster |
| `float16` vs `float32` compute | half the data, but the CPU has no fast float16 path | ~12x **slower** |
| numexpr with 10 cores vs 1 | work shared across cores | ~8.4x faster |
| Fits in memory vs spills to disk | disk is far slower than memory | ~10x slower |

---

## 7. Bottom line

- **Keep images as `uint8`** — it is 4x smaller and usually keeps everything in
  memory.
- **Compute in `float32`** (or `int16`). Never compute in `uint8` itself.
- **Reuse memory (`out=` / in-place)** when you want speed with modest memory.
- **Use `numexpr`** when you have spare CPU cores and want maximum speed — but
  budget twice the memory for its `float64` result.
- **Avoid `float16`** unless memory is the hard limit; on a CPU it is much
  slower.
- **Keep the data in memory.** The single biggest slowdown was the computer
  spilling to disk.
- **When reporting timings, always say**: input format, compute format, number
  of cores, and whether it fit in memory. Each of these changes the result by
  large factors.
