> **Current complete report:** See [readme_task1.md](readme_task1.md) for the authoritative browser-app equations, resolution readouts and experiments. Material below contains historical explanations and older UI descriptions.

# Current webapp: stationary target and moving SAR aircraft

The current default plot is a fixed 10 m × 10 m close-up with 1 m gridlines and a −40 to 0 dB colour scale to reveal sidelobes. The default 150 MHz bandwidth, 2 m antenna and full rectangular broadside aperture give 1 m range and azimuth first-null references; full −3 dB widths are approximately 0.886 m. The grid remains fixed when resolution changes. A separate overview retains the wider scene.

The aircraft flies at a fixed speed V = 150 m/s. The target is stationary. The radial-velocity control now means **aircraft line-of-sight velocity at aperture centre**, positive approaching. It is linked to squint through vr = V sinθ: edit either control and the other updates. The ±15° squint domain corresponds to approximately ±38.82 m/s radial velocity. At broadside vr is zero despite the aircraft moving at 150 m/s.

The local range history is R(t) ≈ R0 − vr t + V² cos²θ t²/(2R0). Aircraft motion produces Doppler centroid 2vr/λ and range migration. The educational processor assumes ideal trajectory-based migration and centroid compensation, then focuses the quadratic phase. Thus a stationary target remains a focused spot at range 5000 m, azimuth 0 m, rather than inheriting a moving-target displacement or butterfly pattern. Squint still changes dwell, Doppler rate and the predicted azimuth width.

The displayed intermediate map is **after** ideal migration and centroid correction, not raw echoes. Its frequency axis is relative to the removed physical aircraft centroid. The linear range-change metric |vr|T is the magnitude of the aircraft's centre-time linear range change over the aperture; it is not residual image blur or the complete curved range excursion. The complete raw-data processor and higher-order squint geometry are outside this approximation.

See [MathWorks’ aircraft SAR example](https://www.mathworks.com/help/radar/ug/synthetic-aperture-radar-system-simulation-and-image-formation.html) for the platform/target distinction.

The current browser regressions check both radial-velocity signs, stationary focus, linked squint geometry, removed centroid, fixed axes, antenna/aperture scaling and Hann factors. The Python/Streamlit examples and material below are **historical moving-target experiments**, not the current browser control semantics.

---

# Understanding range and Doppler in a SAR image

A SAR image locates scattering energy in two spatial dimensions: **range** across the flight track and **azimuth** along it. Range comes from echo delay, R = cτ/2. Doppler is a processing dimension: the changing phase over many pulses encodes along-track position. A range–Doppler map is an intermediate representation, not the final range–azimuth image or a conventional target range–speed plot.

This demonstration forms the complex image coherently and displays linear power or logarithmic power. A single bright scatterer makes the point-spread function, sidelobes, and position error visible. Its actual position at the middle of the aperture is slant range 5000 m and azimuth 0 m. Cyan crosses mark this location; green circles mark the predicted apparent image position.

## Controlled experiments

Other parameters stay fixed while each requested variable changes. The platform travels at 150 m/s and the wavelength is 0.03 m. Positive radial velocity means approaching the radar.

| Variable | Values | Image effect | Position effect |
|---|---|---|---|
| Transmitted bandwidth B | 20, 100, 500 MHz | Ideal slant-range resolution c/(2B) = 7.5, 1.5, 0.30 m | Stationary peak stays at (5000 m, 0 m) |
| Target radial velocity vr | −3, 0, +3 m/s | Residual range walk can smear and reduce the focused peak | Apparent azimuth becomes −100, 0, +100 m |
| Along-track physical antenna length La | 0.5, 2, 5 m | Ideal stripmap azimuth resolution La/2 = 0.25, 1, 2.5 m | Stationary peak stays at (5000 m, 0 m) |

### Bandwidth: range clarity

A larger bandwidth compresses the response into a narrower range interval. In the current browser image, horizontal azimuth stays the same while the vertical slant-range response narrows. The model's resolution is the peak-to-first-null separation, not pixel spacing or the full −3 dB width. For a rectangular spectrum the full power −3 dB width is approximately 0.886 c/(2B). Finer display pixels alone do not increase physical resolution.

### Radial velocity: physical motion versus apparent position

For the sign convention used here, fc = 2vr/λ and Δx = vr R0/V. A +3 m/s target has a +200 Hz centroid offset and appears +100 m along-track when processed under a stationary-scene assumption. This is a location error: its true along-track position remains zero in this model. Its true range changes approximately as 5000 − vr t, so an image needs a reference time to define the actual position.

With a 2 m antenna the aperture lasts 0.5 s. At ±3 m/s the target traverses 1.5 m in range during that aperture, twice the nominal 0.75 m range resolution. The measured peak amplitude falls to about 0.589 of the stationary reference (−4.59 dB). Both velocity signs produce the predicted ±100 m peak. The symmetric aperture leaves the brightest range sample at the centre-time range in these examples; motion does not require the peak to shift in both image dimensions.

### Antenna length: SAR azimuth clarity

For broadside stripmap SAR, the along-track beamwidth is approximately λ/La, illumination time is T = R0 λ/(V La), and Doppler bandwidth is Bd = 2V/La. Coherent processing gives δx ≈ V/Bd = La/2. The shorter antenna illuminates a target for longer, enabling a longer synthetic aperture and finer azimuth resolution. This assumes the complete beam-limited aperture is acquired and focused. It does not describe fixed-aperture spotlight imaging or the antenna-gain/SNR tradeoff.

## What the code computes

The paraxial range history is R(t) ≈ R0 − vr t + V²t²/(2R0). The model starts after ideal range compression and ideal stationary range-migration correction. For range offset r relative to R0, the signal is

    s(r,t) = sinc((r + vr*t)/δR) * exp(j*2π*fc*t − j*π*Ka*t²)
    Ka = 2V²/(λR0)

The range envelope keeps moving-target residual range walk. The intermediate range–Doppler map is FFT_t(s). Multiplication by exp(+jπKa t²) removes the nominal quadratic phase, then an FFT coherently forms the azimuth response. Its frequency coordinate maps to spatial position x = f V/Ka. Thus fc becomes the apparent displacement vr R0/V.

This is an idealized **deramp/FFT SAR image former**, not an implementation of the complete raw-data Range-Doppler Algorithm. It explicitly assumes range compression and stationary migration correction instead of claiming to implement them. The model omits terrain, higher-order geometry, noise, speckle, calibration errors, and antenna gain. The range axis is slant range: conversion to ground range requires incidence angle, with local δR_ground ≈ δR/sin θ.

The image uses a common stationary unit-peak reference so motion-related peak loss remains visible. The intermediate map is normalized separately. The PRF is 1600 Hz; the selected parameter domain has maximum nominal Doppler extent |fc| + Bd/2 = 633.3 Hz, below the 800 Hz Nyquist boundary. The rectangular finite aperture has sidelobes beyond this nominal support. Zero padding interpolates image samples without improving resolution.

## Validation

Four automated checks cover stationary range response and peak location across bandwidth, finite-aperture azimuth response across antenna lengths, signed moving-target displacement and peak loss, and supported extreme parameter sampling/array consistency. Streamlit was exercised at baseline, nonzero radial velocity, and maximum bandwidth with minimum antenna length. The comparison script records numerical results in `outputs/sar_assignment/measurements.json`.

## Reference

[ESA: Introduction to a SAR System](https://www.esa.int/Enabling_Support/Space_Engineering_Technology/Onboard_Data_Processing/Introduction_to_a_SAR_System) explains range/azimuth focusing, migration compensation, and the distinction between slant-range and ground-range imagery. The equations above specify the educational model used here.

## Additional processing controls

The smooth browser interface at http://127.0.0.1:8503 adds **processed aperture percentage** and **azimuth weighting**. It provides sliders, typed inputs and up/down buttons together. Run `python3 server.py` to launch it.

If α is the processed fraction, Tprocessed = α R0 λ/(V La). The ideal rectangular first-null reference becomes La/(2α). At the 2 m baseline antenna, 100%, 50% and 25% aperture give 1, 2 and 4 m references. The corresponding measured full −3 dB widths are approximately 0.883, 1.771 and 3.543 m. Smaller apertures also reduce residual moving-target range walk.

Hann azimuth weighting suppresses sidelobes but broadens the stationary half-power width from approximately 0.883 to 1.441 m at baseline. The processor normalizes by the sum of weights, keeping the stationary peak at one. This demonstration does not include weighting-related SNR loss. The range response stays unchanged.

At +3 m/s, shortening the aperture from 100% to 25% reduces range walk from 1.50 to 0.375 m. The peak rises from 0.589 to approximately 0.966 under the normalized model, while the moving response widens from about 1.25 to 3.60 m. Its apparent +100 m azimuth displacement remains. More concentrated peak amplitude does not automatically mean finer resolution or correct position.


## Expert-review corrections: fixed axes, focus and squint

The main SAR view uses fixed horizontal azimuth coordinates −220 to +220 m and vertical absolute slant range 4985 to 5015 m. It no longer recentres or rescales with velocity or antenna length. The separate detail and azimuth profile use fixed relative offsets −10 to +10 m from the predicted peak; read the main image or location caption for absolute position. Max pooling when downsampling the overview preserves visible narrow peaks; it does not improve resolution.

A stationary point produces a compact mainlobe plus sinc sidelobes, not an ideal single pixel. Linear power is now the default; the −40 dB view deliberately exposes weaker sidelobes. An uncompensated moving target also has range–azimuth coupling: the time-varying range envelope produces a wing-like response. This is an output of this idealized model, not a claim that every real moving target has a butterfly shape. The new **Known radial motion** diagnostic removes the specified linear phase and range walk and restores the stationary point response. It assumes velocity is known exactly; it does not estimate it. The observed intermediate range–Doppler map does not change when the processor changes.

Physical and synthetic aperture lengths must be distinguished. A longer physical antenna narrows the beam, shortens stripmap dwell and makes the fully processed stripmap response coarser. Increasing the processed synthetic aperture at fixed physical antenna instead sharpens it. Both lengths are now displayed. The relationship is supported by [ICEYE’s SAR explanation](https://sar.iceye.com/6.0.4/foundations/OverviewOfSAR/remarkableStory/).

Squint θ is measured from broadside, positive forward-looking, limited to ±15°. The local quadratic model uses:

- Platform Doppler centroid: 2 V sin(θ) / λ, analytically removed **before sampling**.
- Azimuth chirp rate: Ka = 2 V² cos²(θ) / (λ R0).
- Beam-limited processed dwell: T ≈ α R0 λ / (V La cos(θ)).
- Stationary rectangular first-null reference: V/(Ka T) ≈ La/(2α cos(θ)).
- Uncompensated radial-motion apparent displacement: vr R0/(V cos²(θ)).

The intermediate frequency axis is relative to the removed squint centroid. The Nyquist check concerns this residual spectrum, not the original centroid, which can exceed PRF/2. This is an ideal centroid-corrected local model with ideal stationary RCMC, not a full raw-data squinted SAR processor. It excludes higher-order range–azimuth coupling and exact off-axis geolocation. Existing broadside equations above are θ = 0 special cases.

### What does the weighting broadening factor mean?

For full power −3 dB mainlobe width **relative to Rectangular at the same dwell**:

| Window | Broadening β | Full −3 dB width in units of 1/T | Equivalent noise bandwidth in bins |
|---|---:|---:|---:|
| Rectangular | 1.00 | ≈0.8859 | 1.00 |
| Hann | ≈1.63 | ≈1.4406 | ≈1.50 |

Thus Hann 1.50 is a noise-bandwidth factor, not this resolution-broadening factor. The app computes the half-power crossing of the actual discrete window DTFT, so a finite symmetric Hann has a slightly different factor (about 1.628 at the 800-pulse baseline). Predicted stationary image width is β × rectangular full −3 dB width; motion defocus is measured separately. See [Harris, On the Use of Windows for Harmonic Analysis with the DFT](https://amst.ece.iastate.edu/paper/comparative_study/window_1.pdf).

The JS regression suite covers fixed axes across controls, sinc response, signed motion, exact ideal compensation, physical/synthetic aperture scaling, ±15° squint, window-width factors and parameter extremes. The NumPy reference and earlier Streamlit tests also pass in the project virtual environment.
