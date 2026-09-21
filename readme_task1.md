# Task 1 — Interactive SAR Range-Doppler Explorer

**File:** `range_doppler_interactive.py`
**Depends on:** `range_doppler_demo.py` (signal-processing core; the same core
also lives in `radar.py`)
**Companion material:** `task1_slides.pptx` (slide deck), `outputs/slides/*.png`
(result figures), `readme_timing.md` and `results.md` (the separate timing task).

This document explains, in plain language but with the correct **Synthetic
Aperture Radar (SAR)** terms, what the program does, how it works, and what you
can learn by moving its sliders.

---

## 1. What this program is

`range_doppler_interactive.py` is a small, self-contained **SAR simulator with a
live graphical interface**. It:

1. Places a single **point target** (one bright reflector) on the ground.
2. Simulates the **raw radar echo** that a moving SAR platform would receive
   from that target.
3. Processes the echo with the **Range-Doppler Algorithm (RDA)**.
4. Shows the result in **two linked panels** that update **while you drag
   sliders**, so you can watch how each physical parameter changes the image.

It is a teaching tool: every image is generated from first principles (there is
no pre-recorded data), so you can see exactly *why* a SAR image looks the way it
does.

---

## 2. How to run it

From the project root:

```bash
.venv/bin/python range_doppler_interactive.py
```

A window opens with two images and a column of controls. Drag any slider or tick
the checkbox and both panels redraw immediately (about 12 times per second).
Press **`r`** or click **Reset** to return to the defaults.

A web version with the same physics is available as `app.py`
(`.venv/bin/streamlit run app.py`), and a batch version that writes PNG files is
`range_doppler_demo.py`.

---

## 3. Background: what is SAR? (in simple terms)

**Radar** sends out radio waves and listens for the part that bounces back off
objects. From the **time** the echo takes to return, you learn how far away the
object is. From the **change in frequency** of the echo (the Doppler effect),
you learn how fast it is moving toward or away from you.

**SAR (Synthetic Aperture Radar)** puts the radar on a moving platform (a plane
or satellite). As it flies, it sends many pulses and records many echoes of the
same patch of ground. By combining these echoes cleverly, the system behaves as
if it had one **enormous antenna** — a *synthetic aperture* — even though the
real antenna is small. This is what lets SAR produce sharp images.

Two key ideas:

- **Range** = distance from the radar to the target, measured from **echo delay**.
- **Azimuth** (also called **cross-range** or **along-track**) = position along
  the flight direction, measured from the **Doppler history** (how the echo
  frequency changes as the platform flies past).

A SAR image is basically a map of **range** against **azimuth**. This program
shows both that map and an intermediate "range-Doppler" view.

---

## 4. The two dimensions of the image

### Range (cross-track)

The echo from a target at slant range `R` arrives after a two-way delay
`tau = 2R / c` (`c` = speed of light). Range is therefore
`R = c * tau / 2`.

The **sharpness** in range — how small a distance can be told apart — is the
**range resolution**:

```
dR = c / (2 B)
```

where `B` is the **bandwidth** of the transmitted pulse. Wider bandwidth →
smaller `dR` → sharper.

To get good range resolution, SAR transmits a **chirp**: a pulse whose frequency
sweeps across the band `B` during the pulse. A long chirp carries a lot of
energy, and a **matched filter** ("range compression") squeezes that energy into
a very short, sharp peak. This is why even a long pulse gives fine range
resolution.

### Azimuth / Doppler (along-track)

As the platform moves, a target is first slightly ahead, then broadside
(closest), then behind. During this pass, the range to the target changes, which
makes the echo frequency slide — the **Doppler history**. For a broadside target
this history is a **quadratic phase** (a chirp in slow time) with **Doppler
rate**:

```
fR = 2 vp^2 / (lambda * R0)
```

where `vp` is the platform speed, `lambda` the radar wavelength and `R0` the
slant range. Compressing this Doppler history (the **azimuth matched filter**)
gives the target its along-track position and sharpness.

The **azimuth resolution** of an ideal broadside SAR is beautifully simple:

```
rho_az = La / 2
```

where `La` is the **antenna length** — and notice it does *not* depend on range!

### The antenna's role

A real antenna of length `La` has a beamwidth

```
theta = lambda / La
```

A **shorter** antenna has a **wider** beam. A wider beam illuminates the target
for a **longer** time, which builds a **longer synthetic aperture**, which gives
**finer** azimuth resolution (`rho_az = La/2`). This is the counter-intuitive
result that makes SAR special: a smaller real antenna can give a sharper image.
The span of Doppler frequencies collected is the **Doppler bandwidth**:

```
Bd = 2 vp / La
```

---

## 5. What you see: the two panels

### Left panel — the Range-Doppler map

This is the data **after range compression** but **before azimuth compression**.
Its axes are:

- **x = Range [m]** (distance to the target),
- **y = Doppler frequency [Hz]** (the frequency shift caused by motion).

A single point target does **not** appear as a point here. Its energy is spread
across a band of Doppler frequencies of width `Bd`, centred on the target's
**Doppler centroid** `f_dc`. The bright vertical streak marks the target's range.
This view shows *what the radar actually measures* before focusing.

### Right panel — the fully compressed SAR image

This is the final image after the **azimuth matched filter**. Its axes are:

- **x = Range [m]**,
- **y = Azimuth `x = vp * t` [m]** (along-track position).

Now the target collapses into a **single sharp point** at `(R0, x0)`. This is the
"focused" SAR image.

Both panels are shown in **decibels (dB)**, normalised so the brightest point is
0 dB, with a display floor of −60 dB. Bright yellow = strong echo; dark purple =
weak. (Decibels let us see both a very bright target and very faint detail at the
same time.)

A live text line under the panels reports the current `dR`, `rho_az`, `f_dc`,
`Bd` and number of azimuth samples `Na`.

---

## 6. The controls, and what each one changes

There are five sliders and one checkbox. Each one targets a specific piece of
radar physics. A crucial distinction runs through all of them:

> **Some parameters change CLARITY (how sharp the target is).**
> **Others change POSITION (where the target appears).**
> **Some do both.**

### 6.1 Bandwidth `B` (20 – 500 MHz, default 200 MHz)

- **Formula:** `dR = c / (2B)`.
- **Effect:** increasing `B` narrows the range mainlobe → the target is **sharper
  in range**.
- **Position:** unchanged. The peak stays at `R0 = 5000 m`.
- **Take-away:** *bandwidth buys range clarity, not position.*

### 6.2 Radial velocity `v_r` (−5 … +5 m/s, default 0)

The target's velocity **along the line of sight** (toward/away from the radar).
Positive means approaching.

- **Formula:** the echo gets an extra Doppler shift
  `f_dc = 2 * v_r / lambda` (the **Doppler centroid**). At λ = 3 cm, 1 m/s of
  radial velocity shifts the Doppler by about 67 Hz.
- **Effect:** the whole Doppler band slides up or down — the target's **position
  along the Doppler axis** changes. The energy also "walks" across range
  (`range walk = v_r * Ta`) because the range changes during the aperture.
- **Position:** changed — this is a genuine **position error** for a target that
  the processor assumes is stationary. If large, the target can also leave the
  synthetic aperture and **defocus**.
- **Take-away:** *radial velocity moves the target's Doppler/azimuth position
  (and can smear it).*

### 6.3 Antenna length `L_a` (0.5 – 5 m, default 2 m)

- **Formulas:** `rho_az = La / 2` and `Bd = 2 * vp / La`.
- **Effect:** a **shorter** antenna gives a **wider** beam, a **larger** Doppler
  bandwidth, and a **finer** azimuth resolution (narrower azimuth mainlobe).
- **Position:** unchanged. The peak stays at `x0 = 0`.
- **Take-away:** *antenna length buys azimuth clarity, not position.*

### 6.4 Target along-track velocity `v_t` (0 – 80 m/s, default 0)

The target's velocity **along the flight direction**.

- **Effect:** a moving target has a different **Doppler rate** than the
  stationary filter expects. The mismatch leaves a residual **quadratic phase
  error**, which **defocuses** the azimuth response — the target smears into a
  broad, dimmer blob.
- **Position:** roughly unchanged, but the peak drops and spreads.
- **Take-away:** *along-track velocity destroys clarity; it does not move the
  target.*

### 6.5 SNR and speckle

- **SNR slider (−10 … +40 dB, default 30 dB):** sets the **signal-to-noise
  ratio** of the compressed image. Lower SNR raises the noise floor until the
  target is buried.
- **Speckle checkbox:** turns on **multiplicative speckle** — the grainy,
  salt-and-pepper texture of real SAR images. It comes from many tiny scatterers
  inside one resolution cell adding up with random phases, giving a **Rayleigh**
  amplitude distribution.
- **Effect:** both reduce **detectability / clarity**; neither changes position.
- **Take-away:** *noise and speckle cost clarity, not position.*

### Summary table

| Control | Symbol | Affects clarity? | Affects position? | Key formula |
|---|---|---|---|---|
| Bandwidth | `B` | Yes — range | No | `dR = c/2B` |
| Radial velocity | `v_r` | Yes (defocus if large) | **Yes** — Doppler/azimuth | `f_dc = 2 v_r / lambda` |
| Antenna length | `L_a` | Yes — azimuth | No | `rho_az = La/2`, `Bd = 2 vp/La` |
| Along-track velocity | `v_t` | Yes (defocus) | ~No | Doppler-rate mismatch |
| SNR / speckle | — | Yes (detectability) | No | noise floor / Rayleigh |

---

## 7. Methodology: how the simulation works

This section follows the code from raw echo to finished image. All of it is in
`range_doppler_demo.py` (the core), with the interactive glue in
`range_doppler_interactive.py`.

### 7.0 Geometry and derived quantities

The default scene (`make_cfg`) models an **X-band** radar (`fc = 10 GHz`,
`lambda = 3 cm`) on a platform moving at `vp = 150 m/s`, imaging a target at
slant range `R0 = 5 km`. From these, `derive()` computes `theta`, `Ta`, `fR`,
`Bd`, `dR` and `rho_az` using the formulas above.

### 7.1 Building the raw echo

Two time axes are used, exactly as in real radar:

- **Fast time** — the time within a single pulse; this is the **range** axis.
- **Slow time** — the time from pulse to pulse; this is the **azimuth** axis.

For each slow-time instant `t_m`, the code computes the instantaneous slant
range `R(t_m)` to the target (`slant_range`), including the platform motion and
any target velocity. The received **baseband echo** (`raw_echo`) is then:

- a **chirp** delayed by the round-trip time `2R/c`, and
- multiplied by a phase term `exp(-j 4*pi*R/lambda)` that carries the **Doppler
  history**.

The result is a 2-D array of complex numbers: slow-time × fast-time.

### 7.2 Range compression

`range_compress` **matched-filters** each pulse against the transmitted chirp
(implemented efficiently with FFTs). This is the classic **pulse compression**
step: it turns the long, low-power chirp echo into a short, sharp peak whose
position is the target's range and whose width is `dR = c/2B`.

### 7.3 Azimuth FFT → the Range-Doppler map

`rda_compress` takes an **FFT along slow time (azimuth)**. This transforms the
Doppler history into the **Doppler-frequency domain**, giving the
**Range-Doppler map** shown in the left panel. At this stage the target's energy
is spread over its Doppler bandwidth `Bd` around `f_dc`.

### 7.4 Azimuth matched filter (the Range-Doppler Algorithm)

Still inside `rda_compress`, each Doppler bin is multiplied by the **azimuth
reference** `exp(-j*pi*f_a^2 / fR)`, the matched filter for the quadratic Doppler
history, and then an **inverse FFT** returns to the azimuth (spatial) domain.
The target's energy collapses into a **single sharp point** — the right panel.

Applying the azimuth filter in the **Doppler (frequency) domain** is exactly the
**Range-Doppler Algorithm**, and it is what makes the program fast enough to
update in real time.

### 7.5 Noise, speckle and display

Finally `simulate` (in the interactive file):

- normalises the image,
- optionally multiplies by **speckle** (unit-mean complex Gaussian → Rayleigh
  magnitude), and
- optionally adds **thermal noise** at the chosen SNR,
- converts both panels to **dB** with `to_dB` for display.

A **fixed random seed** is used so the speckle/noise pattern does not flicker as
you move unrelated sliders.

### 7.6 Why it is fast

Every step is vectorised NumPy, and the azimuth filter is a single FFT-based
multiply rather than a per-range-bin convolution. A full simulate-and-redraw is
roughly 80–100 ms, giving the smooth live update.

---

## 8. Code map

| Location | What it does |
|---|---|
| `range_doppler_interactive.py` | The GUI and the `simulate()` pipeline used for display. |
| `rda_compress()` (interactive) | FFT azimuth + reference multiply + inverse FFT. |
| `to_dB()` | Convert magnitude to decibels for display. |
| `simulate()` | Full pipeline: geometry → echo → range compression → RDA → noise/speckle → display. |
| `Explorer` class | Builds the figure, sliders, checkbox, reset button; wires callbacks. |
| `Explorer.update()` | Re-runs `simulate()` and refreshes images, axes, the `f_dc` line and the read-out. |
| `Explorer.reset()` / `on_key()` | Restore defaults (button or `r` key). |
| `range_doppler_demo.py` | Core physics: `make_cfg`, `derive`, `slow_time`, `fast_time`, `slant_range`, `raw_echo`, `range_compress`, `axes`, `azimuth_compress`, and the batch figure routines. |
| `radar.py` | A plotting-free copy of the same core, used by the web app and the slide generator. |

---

## 9. Results: what toggling shows

These figures are generated by `make_task1_slides.py` into `outputs/slides/` and
are also in `task1_slides.pptx`.

- **Baseline** (`baseline.png`): with defaults (`B=200 MHz`, `La=2 m`), the
  target focuses to a bright point at range 5000 m, azimuth 0 m. `dR = 0.75 m`,
  `rho_az = 1.0 m`, `Bd = 150 Hz`.
- **Bandwidth** (`bandwidth.png`): increasing `B` from 50 → 500 MHz narrows the
  range mainlobe from ~3 m to ~0.3 m. The peak never moves off 5000 m.
- **Radial velocity** (`radial.png`): `v_r` = 0, 1, 2 m/s shifts the Doppler band
  to +0, +67, +133 Hz respectively. The target moves along the Doppler axis.
- **Antenna length** (`antenna.png`): `La` = 1, 2, 4 m gives azimuth mainlobes of
  ~0.5, 1.0, 2.0 m (shorter antenna = sharper), all centred at 0 m.
- **Along-track velocity** (`alongtrack.png`): `v_t` = 40 and 80 m/s turn the
  sharp azimuth spike into a broad, low smear — defocus.
- **SNR / speckle** (`snr_speckle.png`): lowering SNR raises the noise floor, and
  speckle adds a grainy Rayleigh texture.

---

## 10. Assumptions and limitations

This is a deliberately simple, **educational** model. It is not a full SAR
processor.

- **One point target** (not a scene of many scatterers). This keeps the physics
  visible; it also means the speckle demo is illustrative rather than a true
  multi-scatterer simulation.
- **Broadside geometry, no squint**, and a **straight, constant-velocity** path.
- **No range-cell migration correction (RCMC)** is applied; for these parameters
  the migration is smaller than a range cell, so it does not matter, but at
  larger squint or longer apertures it would.
- **Parabolic (quadratic) approximation** of the Doppler history.
- **Idealised antenna pattern** and no platform attitude/roll effects.
- Noise and speckle are added at the **image level** for a clear, fast demo.

These simplifications are standard for teaching the Range-Doppler Algorithm, and
the qualitative lessons (what sets range vs azimuth clarity, and what moves a
target) all hold in a full processor.

---

## 11. Glossary of SAR terms

| Term | Meaning |
|---|---|
| **Range** | Distance to the target, from echo delay: `R = c*tau/2`. |
| **Azimuth / cross-range** | Along-track position, from the Doppler history. |
| **Slant range `R0`** | Straight-line radar-to-target distance. |
| **Chirp** | A pulse whose frequency sweeps across the bandwidth `B`. |
| **Pulse / range compression** | Matched filtering that turns a chirp echo into a sharp range peak. |
| **Range resolution `dR`** | Smallest separable range: `c/(2B)`. |
| **Azimuth resolution `rho_az`** | Smallest separable along-track distance: `La/2` (ideal). |
| **Doppler history** | How the echo frequency changes as the platform passes the target. |
| **Doppler centroid `f_dc`** | Mean Doppler shift; `2 v_r / lambda` for a moving target. |
| **Doppler rate `fR`** | Slope of the Doppler history: `2 vp^2/(lambda R0)`. |
| **Doppler bandwidth `Bd`** | Span of Doppler frequencies collected: `2 vp/La`. |
| **Synthetic aperture** | The long effective antenna formed by platform motion. |
| **Beamwidth `theta`** | Angular width of the antenna beam: `lambda/La`. |
| **Fast time / slow time** | Time within a pulse (range) / between pulses (azimuth). |
| **PRF** | Pulse Repetition Frequency — pulses per second. |
| **Range-Doppler Algorithm (RDA)** | Process range first, then azimuth via the Doppler domain. |
| **Matched filter** | The optimal filter for detecting a known signal in noise. |
| **RCMC** | Range-Cell Migration Correction — fixes a target drifting across range bins. |
| **Speckle** | Grainy multiplicative noise (Rayleigh) from many sub-resolution scatterers. |
| **SNR** | Signal-to-Noise Ratio. |
| **dB (decibel)** | Logarithmic scale for power; lets bright and faint features share one image. |

---

## 12. Files produced for this task

| File | Contents |
|---|---|
| `readme_task1.md` | This document. |
| `task1_slides.pptx` | 15-slide presentation with figures and results. |
| `make_task1_slides.py` | Script that generates the figures and the slide deck. |
| `outputs/slides/*.png` | The result figures (geometry, pipeline, baseline, bandwidth, radial, antenna, along-track, SNR/speckle). |

Regenerate everything with:

```bash
.venv/bin/python make_task1_slides.py
```
