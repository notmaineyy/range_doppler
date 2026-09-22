# Task 1 — Interactive SAR Range-Doppler Explorer

**File:** `range_doppler_interactive.py`
**Depends on:** `range_doppler_demo.py` (signal-processing core; the same core
also lives in `radar.py`)
**Companion material:** `task1_slides.pptx` (slide deck), `outputs/slides/*.png`
(result figures), `make_task1_slides.py` (regenerates them).

This document fully describes the task: what the program does, what you see on
screen, how every control changes the result, the equations the code uses, and
how the simulation is built. It uses the correct **Synthetic Aperture Radar
(SAR)** terms and explains them in plain language.

---

## 1. Summary

`range_doppler_interactive.py` is a **SAR simulator with a live graphical
interface**. It:

1. Places a single **point target** (one bright reflector) on the ground at
   slant range `R0 = 5 km`.
2. Simulates the **raw radar echo** a moving SAR platform would receive.
3. Processes the echo with the **Range-Doppler Algorithm (RDA)**.
4. Shows two linked panels that redraw **while you drag the sliders**, so you can
   see exactly how each physical parameter changes the image.

Everything is generated from first principles — there is no recorded data — so
the program is a teaching tool for the physics of SAR image formation.

---

## 2. How to run it

From the project root:

```bash
.venv/bin/python range_doppler_interactive.py
```

A window opens with two images, six sliders, a *speckle* checkbox and a *Reset*
button. Everything redraws live (~12 frames/second). Press **`r`** or click
**Reset** to return to the defaults.

Related programs:

- `range_doppler_demo.py` — the same physics, but writes comparison PNGs to
  `outputs/` instead of an interactive window.
- `app.py` — an earlier Streamlit web view.
- `web/` — a browser version (see `README.md`).

---

## 3. Background: what is SAR?

**Radar** transmits radio waves and listens for the part reflected back. From the
**time** the echo takes, you learn the target's distance. From the **change in
frequency** of the echo (the Doppler effect), you learn how it moves along the
line of sight.

**SAR (Synthetic Aperture Radar)** puts the radar on a moving platform. As it
flies it transmits many pulses and records many echoes of the same patch of
ground. Combining these echoes makes the system behave like one very long
antenna — a **synthetic aperture** — despite a physically small antenna. This is
what gives SAR its fine along-track resolution.

A SAR image has two spatial axes:

- **Slant range** (across-track) — distance from the radar, from **echo delay**:
  `R = c·τ/2`.
- **Azimuth** (along-track / cross-range) — position along the flight direction,
  from the **Doppler history**.

The program also shows the intermediate **range-Doppler** view used to form the
azimuth axis.

Default scene (in `make_cfg`):

| Quantity | Symbol | Value |
|---|---|---|
| Carrier frequency | `fc` | 10 GHz (X-band) |
| Wavelength | `λ = c/fc` | 3 cm |
| Platform speed | `vp` | 150 m/s |
| Antenna length | `La` | 2 m |
| Pulse repetition frequency | `PRF` | 800 Hz |
| Slant range to target | `R0` | 5000 m |
| Bandwidth | `B` | 200 MHz |

---

## 4. The equations the code uses

These are the exact relations implemented in `derive()` in
`range_doppler_demo.py`.

### 4.1 Slant-range spatial resolution

```
δR = (c · b_r) / (2 · B)
```

- `c` — speed of light (3·10⁸ m/s)
- `B` — transmitted bandwidth (Hz)
- `b_r` — **range IPR windowing broadening factor**

The factor `b_r` accounts for the weighting applied along range. With no
weighting (**rectangular**) the impulse response (IPR) is a `sinc` with its first
null at `c/(2B)`, so `b_r = 1`. With a **Hann** taper the mainlobe is wider
(`b_r ≈ 1.30`) but the sidelobes are much lower. This is the classic
resolution-versus-sidelobe trade-off.

### 4.2 Azimuth spatial resolution

```
δx = (λ · R0 · b_a) / (2 · L_syn)
```

- `λ` — wavelength
- `R0` — slant range to the target
- `b_a` — **azimuth IPR windowing broadening factor** (1.0 rectangular, ≈1.30 Hann)
- `L_syn` — **synthetic aperture length**, the along-track distance over which
  the target is coherently observed

The synthetic aperture length and the illumination time are linked by the
platform speed:

```
L_syn = vp · T_a,proc          T_a,proc = α · T_a          T_a = (R0 · θ) / vp
θ = λ / La                     (real-antenna beamwidth)
```

where `α` is the **processed-aperture fraction** (the slider, 0.25–1.00) and
`T_a` is the full beam-limited illumination time.

At **full aperture** (`α = 1`) with **rectangular** weighting (`b_a = 1`) this
reduces to the textbook broadside stripmap result:

```
δx = (λ · R0) / (2 · R0 · θ) = λ / (2θ) = La / 2
```

So `La/2` is the special case; the general equation above also covers partial
apertures and windowing.

### 4.3 Supporting relations

| Relation | Equation | Notes |
|---|---|---|
| Range from delay | `R = c·τ / 2` | `τ` = two-way echo delay |
| Doppler rate | `Ka = fR = 2·vp² / (λ·R0)` | slope of the Doppler history |
| Doppler bandwidth | `Bd = 2·vp / La` | span of Doppler collected |
| Doppler centroid | `f_dc = 2·vr / λ` | shift from radial velocity |
| Azimuth displacement | `Δx = vr · R0 / vp` | apparent position error |
| Range walk | `ΔR = vr · T_a,proc` | range drift during aperture |

### 4.4 Worked numbers for the default scene

With `B = 200 MHz`, `La = 2 m`, rectangular weighting, full aperture:

| Quantity | Value |
|---|---|
| `δR = c/(2B)` | **0.75 m** |
| `θ = λ/La` | 0.015 rad |
| `T_a` | 0.50 s |
| `L_syn` | 75 m |
| `δx = λR0/(2L_syn) = La/2` | **1.00 m** |
| `Bd = 2vp/La` | 150 Hz |
| `f_dc` at `vr = 1 m/s` | 67 Hz |

If you change the processed aperture to 50%, `L_syn` halves to 37.5 m and `δx`
**doubles** to 2.00 m — less observation time means a coarser azimuth response.
With Hann weighting the reported `δR` and `δx` grow by the `b` factors.

---

## 5. What you see on screen

The window has **two image panels**, a **live read-out line**, and the controls.

### 5.1 Left panel — the Range-Doppler map

Data **after range compression** but **before azimuth compression**. Axes:

- **x = Range [m]** — distance to the target.
- **y = Doppler frequency [Hz]** — frequency shift caused by motion.

A point target is **not** a point here: its energy is spread across a band of
Doppler frequencies of width `Bd`, centred on the Doppler centroid `f_dc`. A cyan
dashed line marks `f_dc`; a white dotted line marks 0 Hz. The bright vertical
streak shows the target's range. This is *what the radar measures before
focusing*.

### 5.2 Right panel — the fully compressed SAR image

The final image **after the azimuth matched filter**. Axes:

- **x = Range [m]** (distance),
- **y = Azimuth [m]** (along-track position, `x = vp·t`).

The target collapses to a **single sharp point** at `(R0, x0)`. Its width is the
resolution: range width ≈ `δR`, azimuth width ≈ `δx`.

### 5.3 Colour scale and read-out

Both panels are shown in **decibels (dB)**, normalised so the strongest point is
0 dB, with a display floor of −60 dB. Yellow = strong echo, dark purple = weak.
Decibels let a very bright target and faint detail share one image.

The read-out line shows the current values of the equations:

```
δR = c·b_r/2B         (m, with the range broadening factor b_r)
δx = λ·R0·b_a/2L_syn  (m, with the azimuth broadening factor b_a and L_syn)
f_dc = 2vr/λ          (Hz)
Bd = 2vp/La           (Hz)
Na                    (number of azimuth samples)
```

---

## 6. The controls and what each changes

> **Clarity** = how sharp/tall the focused response is.
> **Position** = where the peak appears in the image.
> Some controls affect clarity only; one affects position.

### 6.1 Bandwidth `B` — 20 … 500 MHz (default 200)

- **Equation:** `δR = c·b_r / (2B)`.
- **Effect:** increasing `B` narrows the range mainlobe → sharper in range. At
  50 → 500 MHz, `δR` goes from ~3 m to ~0.3 m.
- **Position:** unchanged — the peak stays at `R0 = 5000 m`.
- **Lesson:** *bandwidth buys range clarity, not position.*

### 6.2 Radial velocity `v_r` — −5 … +5 m/s (default 0)

Velocity along the **line of sight**; positive = approaching.

- **Equation:** `f_dc = 2·v_r / λ`, and apparent azimuth shift `Δx = v_r·R0/vp`.
- **Effect:** the whole Doppler band slides up/down, so the target **moves along
  the Doppler axis**. The range also drifts during the aperture (**range walk**
  `v_r·T_a,proc`), which can smear the response.
- **Position:** changed — a genuine **position error** for a target the processor
  assumes is stationary. If large, the target leaves the synthetic aperture and
  **defocuses**.
- **Lesson:** *radial velocity moves the target (and can smear it).*

### 6.3 Antenna length `L_a` — 0.5 … 5 m (default 2)

- **Equations:** `δx = λR0b_a / (2 L_syn)`; at full aperture `= La/2`. Also
  `Bd = 2vp/La` and `θ = λ/La`.
- **Effect:** a **shorter** antenna → **wider** beam → **longer** illumination →
  **larger** `L_syn` → **finer** azimuth resolution (narrower mainlobe) and a
  **wider** Doppler band.
- **Position:** unchanged — the peak stays at `x0 = 0`.
- **Lesson:** *antenna length buys azimuth clarity, not position.*

### 6.4 Target along-track velocity `v_t` — 0 … 80 m/s (default 0)

Velocity **along the flight direction**.

- **Effect:** a moving target has a different **Doppler rate** than the
  stationary filter expects. The residual **quadratic phase error** defocuses the
  azimuth response — it smears into a broad, dimmer blob.
- **Position:** roughly unchanged; the peak drops and spreads.
- **Lesson:** *along-track velocity destroys clarity; it does not move the
  target.*

### 6.5 Processed aperture `α` — 25 … 100 % (default 100)

The fraction of the full illumination time that is coherently processed.

- **Equations:** `T_a,proc = α·T_a`, `L_syn = vp·T_a,proc`, and therefore
  `δx = λR0b_a / (2 L_syn)`.
- **Effect:** processing **less** of the aperture shortens `L_syn` and
  **broadens** the azimuth response (worse `δx`). It also reduces the range walk
  of a moving target, because there is less time for the range to drift.
- **Position:** unchanged.
- **Lesson:** *azimuth clarity needs observation time; partial apertures trade
  clarity for robustness.*

### 6.6 SNR and speckle

- **SNR slider — −10 … +40 dB (default 30):** sets the signal-to-noise ratio of
  the compressed image. Lower SNR raises the noise floor until the target is
  buried. (40 dB disables the added noise.)
- **Speckle checkbox:** enables **multiplicative speckle** — the grainy texture
  of real SAR images. It arises when many sub-resolution scatterers add with
  random phases, giving a **Rayleigh** amplitude distribution.
- **Effect:** both reduce **detectability / clarity**; neither changes position.
- **Lesson:** *noise and speckle cost clarity, not position.*

### 6.7 Summary table

| Control | Symbol | Affects `δR`? | Affects `δx`? | Affects position? | Key equation |
|---|---|---|---|---|---|
| Bandwidth | `B` | **Yes** (∝1/B) | No | No | `δR = c·b_r/(2B)` |
| Radial velocity | `v_r` | No | No | **Yes** | `f_dc = 2v_r/λ`, `Δx = v_rR0/vp` |
| Antenna length | `L_a` | No | **Yes** (via `L_syn`, `θ`) | No | `δx = λR0b_a/(2L_syn)` |
| Along-track velocity | `v_t` | No | Defocus | ~No | Doppler-rate mismatch |
| Processed aperture | `α` | No | **Yes** (∝1/`L_syn`) | No | `L_syn = vp·α·T_a` |
| Window weighting | `b_r`,`b_a` | **Yes** | **Yes** | No | broadening factors |
| SNR / speckle | — | No | No | No | noise floor / Rayleigh |

---

## 7. Methodology: how the simulation works

This section follows the signal from raw echo to finished image. The physics is
in `range_doppler_demo.py`; `range_doppler_interactive.py` drives it and adds the
display.

### 7.1 Geometry and derived quantities — `derive()`

From `{fc, B, La, vp, R0, aperture_fraction, windows}` the code computes `λ`,
`θ = λ/La`, `T_a = R0·θ/vp`, `T_a,proc = α·T_a`, `L_syn = vp·T_a,proc`,
`Ka = 2vp²/(λR0)`, `Bd = 2vp/La`, and the two resolutions
`δR = c·b_r/(2B)` and `δx = λR0·b_a/(2L_syn)`.

### 7.2 Two time axes

- **Fast time** — time within one pulse; the **range** axis.
- **Slow time** — pulse-to-pulse time; the **azimuth** axis.

`slow_time` samples the processed aperture at the PRF: `Na = PRF·T_a,proc`
samples centred on 0. `fast_time` samples the range window around `R0`.

### 7.3 Raw echo — `slant_range()` + `raw_echo()`

For each slow-time instant `t_m`, `slant_range` computes the instantaneous
two-way path:

```
across = R0 − v_r·t_m
along  = (vp − v_t·t_m) ... i.e. (vp − vt)·t_m − x0
R(t_m) = sqrt(across² + along²)
```

The received baseband echo is then a **chirp** delayed by `2R/c`:

```
s(t̂, t_m) = exp(−j·4π·R(t_m)/λ) · exp(+j·π·Kr·(t̂ − 2R/c)²)
```

- the first exponential carries the **Doppler history** (the azimuth phase),
- the second is the **range chirp** with rate `Kr = B/Tp`.

The result is a 2-D complex array (slow × fast time).

### 7.4 Range compression — `range_compress()`

Each pulse is **matched-filtered** against the transmitted chirp (FFT-based, with
the optional range window applied to the reference). This is **pulse
compression**: it turns the long chirp echo into a short, sharp peak whose
position is the range and whose width is `δR = c·b_r/(2B)`.

### 7.5 Azimuth FFT → the Range-Doppler map

`rda_compress` takes an FFT along slow time, transforming the Doppler history
into the Doppler-frequency domain — the **Range-Doppler map** (left panel). Here
the target's energy spans the Doppler bandwidth `Bd` around `f_dc`.

### 7.6 Azimuth matched filter (the Range-Doppler Algorithm)

In the same function, each Doppler bin is multiplied by the azimuth reference

```
H(f_a) = exp(−j·π·f_a² / Ka)     (optionally × a Hann taper)
```

the matched filter for the quadratic Doppler history, then an **inverse FFT**
returns to the spatial azimuth axis. The energy collapses to a single point
(right panel). Applying the azimuth filter in the **Doppler domain** is exactly
the **Range-Doppler Algorithm**, and it is what keeps the program fast enough for
live updates.

### 7.7 Noise, speckle and display

`simulate()` normalises the focused image, optionally multiplies by **speckle**
(unit-mean complex Gaussian → Rayleigh magnitude), optionally adds **thermal
noise** at the chosen SNR, and converts both panels to **dB** with `to_dB`. A
**fixed random seed** prevents speckle/noise flicker while moving unrelated
sliders.

### 7.8 Why it is fast

All steps are vectorised NumPy, and the azimuth filter is a single FFT-based
multiply rather than a per-range-bin convolution. A full simulate-and-redraw is
roughly 80–100 ms.

---

## 8. Code map

| Location | What it does |
|---|---|
| `range_doppler_demo.py::make_cfg` | Default scene and the window/aperture options. |
| `range_doppler_demo.py::derive` | All derived quantities and the two resolution equations. |
| `range_doppler_demo.py::slow_time` / `fast_time` | Azimuth / range sample axes. |
| `range_doppler_demo.py::slant_range` | Target geometry including platform and target motion. |
| `range_doppler_demo.py::raw_echo` | Chirp + Doppler-phase raw signal. |
| `range_doppler_demo.py::range_compress` | Range matched filter with the range window. |
| `range_doppler_demo.py::azimuth_compress` | Time-domain azimuth matched filter (batch/PNG use). |
| `range_doppler_demo.py::axes` | Doppler, range and azimuth coordinate axes. |
| `range_doppler_interactive.py::rda_compress` | Doppler-domain azimuth filter (the live RDA path). |
| `range_doppler_interactive.py::to_dB` | Magnitude → decibels for display. |
| `range_doppler_interactive.py::simulate` | Full pipeline used by the GUI. |
| `range_doppler_interactive.py::Explorer` | Figure, sliders, checkbox, Reset; wires callbacks and the read-out. |
| `radar.py` | Plotting-free copy of the core for the web app and slides. |

---

## 9. Results you can reproduce interactively

Defaults unless stated. Figures are generated by `make_task1_slides.py` into
`outputs/slides/` and included in `task1_slides.pptx`.

- **Baseline** — `B=200 MHz`, `La=2 m`: the target focuses to a bright point at
  (5000 m, 0 m). `δR = 0.75 m`, `δx = 1.00 m`, `Bd = 150 Hz`.
- **Bandwidth** — `B` = 50 → 500 MHz narrows the range mainlobe ~3 m → ~0.3 m;
  the peak never moves.
- **Radial velocity** — `v_r` = 0, 1, 2 m/s shifts the Doppler band to
  +0, +67, +133 Hz; the target moves along Doppler and range-walks.
- **Antenna length** — `La` = 1, 2, 4 m gives `δx` = 0.5, 1.0, 2.0 m (shorter =
  sharper), all centred at 0 m.
- **Along-track velocity** — `v_t` = 40, 80 m/s turn the sharp azimuth spike into
  a broad, low smear (defocus).
- **Processed aperture** — 100 / 50 / 25 % gives `δx` = 1, 2, 4 m.
- **Windowing** — switching to Hann widens `δR`/`δx` by ≈1.3× but suppresses
  sidelobes.
- **SNR / speckle** — lowering SNR raises the noise floor; speckle adds grainy
  Rayleigh texture.

---

## 10. Assumptions and limitations

A deliberately simple, **educational** model — not a full SAR processor.

- **One point target**, not a scene of many scatterers. The speckle demo is
  therefore illustrative rather than a true multi-scatterer simulation.
- **Broadside geometry, no squint**; straight, constant-velocity path.
- **No range-cell migration correction (RCMC)** is applied. For these parameters
  the migration is below a range cell, so it does not matter; at large squint or
  long apertures it would.
- **Parabolic (quadratic) approximation** of the Doppler history.
- **Idealised antenna pattern**, no platform attitude/roll.
- **Windowing broadening factors are scalar constants** (1.0 / 1.30) applied for
  reporting the resolution; the actual taper is applied to the reference/weights.
- Noise and speckle are added at the **image level** for a clear, fast demo.

These simplifications are standard for teaching the Range-Doppler Algorithm; the
qualitative lessons (what sets range vs azimuth clarity, and what moves a target)
hold in a full processor.

---

## 11. Glossary of SAR terms

| Term | Meaning |
|---|---|
| **Range / slant range** | Radar-to-target distance, from echo delay: `R = c·τ/2`. |
| **Azimuth / cross-range** | Along-track position, from the Doppler history. |
| **Slant-range resolution `δR`** | Smallest separable range: `c·b_r/(2B)` (first null). |
| **Azimuth resolution `δx`** | Smallest separable along-track distance: `λR0b_a/(2L_syn)`. |
| **IPR (impulse response)** | The focused shape of a point target (a `sinc`-like peak). |
| **Windowing / weighting / taper** | Amplitude shaping that lowers sidelobes but widens the mainlobe. |
| **Broadening factor `b`** | How much a window widens the mainlobe vs rectangular (≈1.30 for Hann). |
| **Chirp** | A pulse whose frequency sweeps across bandwidth `B`. |
| **Pulse / range compression** | Matched filtering that sharpens the chirp echo in range. |
| **Doppler history** | How the echo frequency changes as the platform passes the target. |
| **Doppler rate `Ka`** | Slope of the Doppler history: `2vp²/(λR0)`. |
| **Doppler centroid `f_dc`** | Mean Doppler shift; `2v_r/λ` for a moving target. |
| **Doppler bandwidth `Bd`** | Span of Doppler collected: `2vp/La`. |
| **Synthetic aperture `L_syn`** | Along-track distance the target is coherently observed: `vp·T_a,proc`. |
| **Beamwidth `θ`** | Antenna beam angular width: `λ/La`. |
| **Processed aperture `α`** | Fraction of the full illumination time processed. |
| **Fast time / slow time** | Time within a pulse (range) / between pulses (azimuth). |
| **PRF** | Pulse Repetition Frequency — pulses per second. |
| **Range-Doppler Algorithm (RDA)** | Process range first, then azimuth via the Doppler domain. |
| **Matched filter** | Optimal filter for detecting a known signal in noise. |
| **RCMC** | Range-Cell Migration Correction — fixes a target drifting across range bins. |
| **Speckle** | Grainy multiplicative noise (Rayleigh) from many sub-resolution scatterers. |
| **SNR** | Signal-to-Noise Ratio. |
| **dB (decibel)** | Logarithmic power scale; lets bright and faint features share an image. |

---

## 12. Files for this task

| File | Contents |
|---|---|
| `readme_task1.md` | This document. |
| `range_doppler_interactive.py` | The interactive program. |
| `range_doppler_demo.py` | Core physics + batch figures. |
| `task1_slides.pptx` | Slide deck version of this material. |
| `make_task1_slides.py` | Regenerates the figures and the deck. |
| `outputs/slides/*.png` | Result figures (geometry, pipeline, baseline, bandwidth, radial, antenna, along-track, SNR/speckle). |

Regenerate the figures and deck:

```bash
.venv/bin/python make_task1_slides.py
```
