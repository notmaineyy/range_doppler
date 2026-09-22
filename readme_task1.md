# Task 1 — SAR image laboratory: range, azimuth, motion and windowing

This report describes the **current browser application in `web/`**, including its equations, plots, controls and limitations. It supersedes the earlier report about `range_doppler_interactive.py`. The older Python demonstrations and slide decks are historical material and may use different assumptions.

## 1. Aim and current implementation

The task is to explain how a synthetic aperture radar (SAR) forms an **image**, and how bandwidth, aircraft radial velocity, physical antenna length, processed aperture, squint and azimuth weighting affect the image of a point target.

The aircraft moves; the target is **stationary**. The target's reference image location is slant range **5000 m**, azimuth **0 m**, at the centre of the observation. This is an idealized **stripmap** SAR model. A point appearing as a bright spot does not make the acquisition mode “spotlight SAR.”

The output is a coherent point impulse response (IPR): a mainlobe and sidelobes in two spatial dimensions. It is not a conventional range–speed detection plot. The intermediate range–Doppler map has frequency on one axis, but the final SAR image has metres on both axes.

The current implementation starts **after ideal range compression, aircraft range-migration correction and Doppler-centroid removal**. It uses quadratic phase cancellation and an FFT to focus azimuth. It does not generate raw transmitted/received chirps or implement a complete raw-data Range-Doppler Algorithm (RDA).

## 2. Run and navigate

Public site: [SAR image laboratory](https://notmaineyy.github.io/range_doppler/).

Run the current working copy locally:

```sh
cd /Users/shermi/range_doppler
python3 server.py
```

Open `http://127.0.0.1:8503/`. This interface needs no third-party Python packages. JavaScript ES modules and a Web Worker perform the calculations in the browser.

Every numeric control has a slider, direct entry and up/down buttons. Valid changes update the existing plots without a reload. Invalid entries are rejected. Rapid changes are coalesced so intermediate requests do not build an unlimited calculation queue. Runtime depends on the device; the displayed update time is computation timing, not a guaranteed frame rate.

**Reset to 1 m reference** restores the baseline and logarithmic image display. The 1 m grid stays fixed when parameters change; it is a visual ruler, not a statement that every setting has 1 m resolution.

## 3. Scene, symbols and defaults

| Quantity | Symbol | Value or meaning |
|---|---|---|
| Speed of light used by the model | c | 300,000,000 m/s |
| Wavelength | λ | 0.03 m; equivalent carrier frequency 10 GHz |
| Reference slant range | R₀ | 5000 m |
| Aircraft speed | V | 150 m/s, straight constant-velocity flight |
| Pulse repetition frequency | PRF | 1600 Hz |
| Transmitted bandwidth | B | 150 MHz default; 20–500 MHz |
| Physical along-track antenna length | Lₐ | 2 m default; 0.5–5 m |
| Processed aperture fraction | α | 1 default; 0.25–1 |
| Squint from broadside | θ | 0° default; −15° to +15° |
| Aircraft radial velocity at aperture centre | vᵣ | 0 default; approximately ±38.82 m/s, linked to θ |
| Processed observation time | T | Derived from antenna length, aperture fraction and squint |
| Processed synthetic aperture length | Lsyn | VT; aircraft travel distance during processing |
| Range IPR windowing broadening factor | βᵣ | 1: range has no taper in this app |
| Azimuth IPR windowing broadening factor | βₐ | Calculated from None, Hann or Hamming |

Slant range is the radar-to-target distance. It is not horizontal ground range. Azimuth is the local along-track image coordinate. Physical antenna length **Lₐ** and synthetic aperture length **Lsyn** are different quantities.

## 4. Required spatial-resolution equations

### 4.1 Slant-range spatial resolution

The code explicitly evaluates the requested equation:

$$\delta_R = \frac{c\,\beta_r}{2B}.$$

B is in **Hz**, not MHz. The control value is multiplied by 10⁶. Range weighting is fixed to None, so βᵣ = 1. Increasing bandwidth narrows the range response without moving the target.

### 4.2 Azimuth spatial resolution

For broadside, the code explicitly evaluates:

$$\delta_{az,0} = \frac{\lambda R_0\,\beta_a}{2L_{syn}}.$$

The aperture length in this equation is the **processed synthetic aperture length**, not the physical antenna length. A longer processed synthetic aperture improves the nominal azimuth resolution; applying a taper increases βₐ and broadens the response.

The current image coordinate is along-track, and the app also supports squint. Its local quadratic model requires:

$$\delta_{az} = \frac{\lambda R_0\,\beta_a}{2L_{syn}\cos^2\theta}.$$

Equivalently, define an **effective along-track aperture**:

$$L_{eff}=L_{syn}\cos^2\theta,\qquad
\delta_{az}=\frac{\lambda R_0\,\beta_a}{2L_{eff}}.$$

This is an algebraic way to include the model's squint geometry, not a claim that the aircraft travels only Leff. At broadside θ = 0, Leff = Lsyn and the requested equation applies directly. The on-screen equations panel shows **both the broadside formula value using Lsyn and the geometry-adjusted along-track value using Leff**. The main azimuth metric reports the latter.

Simply omitting the cos²θ correction while keeping the current squinted signal model would make the reported resolution inconsistent with the plotted response. This correction is specific to the local along-track coordinate and approximation used here; it is not a universal high-squint imaging formula.

### 4.3 Resolution convention: nominal value versus actual IPR width

The equations above use a clearly defined **nominal engineering resolution convention**, with β = 1 for uniform weighting. The factors are ratios of full half-power widths at the same aperture:

$$\beta_w = \frac{W_{3dB,w}}{W_{3dB,rect}}.$$

An unwindowed sinc has full half-power width approximately **0.8859 times** its peak-to-first-null separation. Consequently:

$$W_{R,3dB}\approx0.8859\,\delta_R,$$

$$W_{az,3dB}=q_{rect}(N)\,\delta_{az},\qquad q_{rect}(N)\approx0.8859.$$

The app reports nominal resolution in the top metrics and measured full half-power width on the graph. These must not be treated as identical. A nominal 1 m reference produces a full half-power width near 0.886 m. A **weighted nominal resolution is not the weighted first-null position** either.

If one instead wants the requested equations themselves to output full half-power widths, their coefficients must be defined as absolute width coefficients q, rather than rectangle-normalized β. The app deliberately keeps these conventions separate instead of silently exchanging them.

At the 800-pulse baseline:

| Azimuth weighting | βₐ, relative broadening | Full half-power width coefficient q | Nominal resolution | Measured graph width |
|---|---:|---:|---:|---:|
| None / Rectangular | 1.000 | ≈0.8859 | 1.000 m | ≈0.882 m |
| Hann | ≈1.628 | ≈1.4424 | ≈1.628 m | ≈1.441 m |
| Hamming | ≈1.472 | ≈1.3041 | ≈1.472 m | ≈1.302 m |

Small prediction/measurement differences come from FFT interpolation and the 0.1 m display sampling. In particular, the old report's “Hann ≈1.30” broadening factor was incorrect under this definition.

**Equivalent noise bandwidth (ENBW)** is another quantity: approximately 1.00 bins for Rectangular, 1.50 for Hann and 1.36 for Hamming. ENBW is not the β used in these resolution equations.

## 5. Geometry and supporting equations

### Aircraft radial velocity and squint

Let uLOS be the unit vector from the aircraft toward the stationary target. Positive radial velocity means approaching:

$$v_r=\mathbf{v}\cdot\mathbf{u}_{LOS}=V\sin\theta.$$

The app fixes V and defines squint relative to broadside to that velocity vector, so the two controls are synchronized. At broadside, vᵣ = 0 even though the aircraft moves at 150 m/s. At 15°, vᵣ ≈38.82 m/s.

This relationship does not mean antenna steering can arbitrarily change the radial velocity of an already fixed target. Steering toward another scene centre changes the relevant line of sight. Different aircraft speed, turns, climb or a different angle definition require a more general geometry model.

For straight flight, the centre-target range history is:

$$R(t)=\sqrt{R_0^2-2R_0v_rt+V^2t^2}
\approx R_0-v_rt+\frac{V^2\cos^2\theta}{2R_0}t^2.$$

The code uses the quadratic approximation, with ideal correction of the associated migration and centroid. The actual target is stationary throughout.

### Dwell, synthetic aperture and Doppler

The physical angular beamwidth reference is approximately λ/Lₐ radians. The model's beam-limited processed dwell is:

$$T_{ideal}=\frac{\alpha R_0\lambda}{VL_a\cos\theta},\quad
N=\operatorname{round}(PRF\,T_{ideal}),\quad T=\frac{N}{PRF},\quad L_{syn}=VT.$$

Sampling rounds dwell to an integer number of pulses. The positive magnitude of the azimuth chirp rate is:

$$K_a=\frac{2V^2\cos^2\theta}{\lambda R_0}.$$

Other displayed quantities are:

$$f_{dc}=\frac{2v_r}{\lambda},\quad B_D=K_aT,\quad
\Delta R_{linear}=|v_r|T.$$

The last quantity is the magnitude of the **linear aircraft range-change term** across the aperture. It is not residual blur and not the complete curved range excursion.

At broadside and ignoring pulse-count rounding, the requested azimuth equation reduces to:

$$L_{syn}=\frac{\alpha R_0\lambda}{L_a},\qquad
\delta_{az}=\frac{\beta_a L_a}{2\alpha}.$$

A longer physical antenna makes a narrower illumination beam, but shortens stripmap dwell and the synthetic aperture. Thus it broadens the focused stripmap image response. Increasing the processed synthetic aperture has the opposite effect. This explains why the bottom-right curve is not an antenna angular beam-pattern plot. [ICEYE's stripmap explanation](https://sar.iceye.com/6.0.4/foundations/OverviewOfSAR/remarkableStory/) discusses this distinction.

## 6. Signal model and actual computation

Let r = R − R₀ and define sinc(u) = sin(πu)/(πu). Before tapering, the ideal range response is:

$$g(r)=\operatorname{sinc}\left(\frac{r}{c/(2B)}\right).$$

After the assumed ideal range compression, aircraft migration correction and centroid removal, the simulated signal is:

$$s(r,t)=g(r)\exp(-j\pi K_at^2).$$

The intermediate map is FFT over slow time t of s(r,t). Its frequency axis is **relative to the removed aircraft Doppler centroid**. The physical centroid can exceed PRF/2 at squint; the app assumes it has been removed before residual slow-time sampling. It does not simulate sampling that high centroid directly and then recovering aliased data.

Azimuth focusing cancels the quadratic phase, applies the selected weights and transforms coherently:

$$I(r,f)=\frac{\operatorname{FFT}_t\{w(t)s(r,t)\exp(+j\pi K_at^2)\}}{\sum_n w[n]},\qquad
x=\frac{fV}{K_a}.$$

The sum-of-weights normalization keeps a stationary point's peak amplitude at 1 for all windows. It allows shape comparison; it does not model the SNR penalty of weighting. The final point response is separable in this ideal model: a range sinc multiplied by the azimuth aperture response.

For sample index n = 0,…,N−1:

$$w_{none}[n]=1,$$

$$w_{Hann}[n]=0.5-0.5\cos\left(\frac{2\pi n}{N-1}\right),$$

$$w_{Hamming}[n]=0.54-0.46\cos\left(\frac{2\pi n}{N-1}\right).$$

“None” means no taper: every acquired pulse has equal weight. Mathematically, the finite observation interval is still a rectangular window. There is no additional untapered option that removes the finite-aperture sidelobes.

The function `windowFactors()` evaluates the normalized discrete window transform, finds its half-power crossing by bisection, and divides its full width by the rectangular full width. It uses the actual N, not a hard-coded constant for every aperture. Range has no window selector and βᵣ remains 1.

The browser uses an 8192-point azimuth FFT and interpolates magnitude onto fixed 0.1 m image samples. Zero padding and display interpolation do not increase physical resolution. The intermediate map uses a separately padded FFT and coarser display sampling. A Web Worker keeps calculations off the main interface thread.

## 7. What every on-screen result means

### Top metrics and equations panel

- **Nominal slant-range resolution:** cβᵣ/(2B), in metres.
- **Nominal azimuth resolution:** λR₀βₐ/(2Leff), for the current along-track geometry.
- **Predicted azimuth displacement:** zero, because the stationary target is focused using the known aircraft trajectory.
- **Aircraft linear range change:** |vᵣ|T, before ideal compensation.
- **Measured azimuth −3 dB width:** the full contiguous half-power mainlobe width, interpolated from the displayed response.
- **Weighting broadening β:** the azimuth window's width ratio to uniform weighting at the same dwell.
- **Stationary prediction:** the predicted full half-power width, not the nominal resolution metric.
- **Sampling caption:** dwell, synthetic and physical lengths, removed aircraft centroid, zero residual centroid and nominal Doppler span.
- **Resolution equations panel:** equations, both factors, Lsyn, Leff, broadside and corrected azimuth values, and predicted range half-power width.

### Upper-left: intermediate range–Doppler map

Horizontal axis: residual Doppler frequency, −800…+800 Hz. Vertical axis: absolute slant range, 4985…5015 m. This is after ideal range and centroid corrections but before azimuth phase cancellation. The cyan line marks zero residual centroid.

A point spreads across Doppler because its phase changes throughout the synthetic aperture. This map is neither a final spatial image nor a target-speed chart. Azimuth window selection does not change this pre-window intermediate map. Its own peak is normalized to 0 dB.

### Upper-right: focused SAR image with 1 m grid

Horizontal axis: azimuth −5…+5 m. Vertical axis: absolute slant range 4995…5005 m. The view is a fixed 10 m square with equal spatial scale and 1 m gridlines. Cyan marks the true centre-time point; green marks the predicted position. They coincide in this stationary compensated model.

A finite-bandwidth, finite-aperture point has a mainlobe plus sidelobes, not an infinitely narrow pixel. The default −40…0 dB view makes the sidelobes visible in nearby grid squares. Those lobes belong to the same reflector. Linear power emphasizes the central spot instead. With low bandwidth or very short processed aperture, the response can extend beyond this close-up; inspect the wider overview and profiles.

### Bottom-left profile: range IPR

A vertical slice through the brightest image pixel: horizontal plot axis is slant range in metres, vertical plot axis is relative power in dB. The large central peak is the range mainlobe; the smaller oscillations are range sidelobes. Higher B narrows it. Azimuth tapering does not suppress these range sidelobes.

### Bottom-right profile: focused azimuth IPR

A horizontal slice through the brightest image pixel at a fixed slant range. Horizontal plot axis: along-track offset from the predicted centre, −10…+10 m. Vertical axis: relative power, −60…0 dB.

The central peak is the azimuth mainlobe. Smaller peaks are sidelobes of that same point. They are not additional targets and this is not antenna gain versus angle. The yellow dashed line is half power (−3.0103 dB relative to the peak); the shaded region and bracket mark full half-power width. A narrower mainlobe means finer spatial detail, though two-target distinguishability also depends on relative strength and sidelobes.

For Hann or Hamming, cyan is the selected weighted response and dashed grey is the analytic finite uniform-aperture reference at the same geometry and dwell. Both use unit peak. The reference uses the finite Dirichlet response, not an unrelated Gaussian curve. Hann and Hamming lower sidelobes while widening the peak. Hamming's weak sidelobes become visible on the −60 dB profile even when they are below the image's −40 dB floor.

### Full-scene overview and diagnostics

The overview retains fixed azimuth −220…+220 m and range 4985…5015 m. Its spatial axes do not auto-rescale with controls. Max pooling during image downsampling keeps narrow peaks visible but is not added resolution. Diagnostics explain motion compensation, window factors and the difference between physical and synthetic aperture lengths.

### Colour, amplitude and power

For normalized complex amplitude I:

$$D=20\log_{10}|I|=10\log_{10}|I|^2.$$

Thus 0 dB is reference power 1, −20 dB is 0.01 and −40 dB is 0.0001. The final image and profiles share the stationary unit-peak reference; only the intermediate map normalizes independently. The data are floored at −80 dB, the image displays to −40 dB, and profiles display to −60 dB. A dark pixel can therefore contain nonzero energy below the colour floor.

## 8. Controls and expected effects

| Control | What changing it does | Position effect in this model |
|---|---|---|
| Bandwidth, 20–500 MHz | Higher B narrows range response and lowers δR; azimuth resolution unchanged | None |
| Aircraft radial velocity, approximately ±38.82 m/s | Updates squint; changes physical Doppler centroid, dwell and azimuth geometry | None after ideal trajectory correction |
| Physical antenna length, 0.5–5 m | Longer antenna narrows illumination beam, shortens stripmap aperture and broadens azimuth IPR | None |
| Processed aperture, 25–100% | Larger fraction increases T and Lsyn, narrows azimuth response and increases collected Doppler span | None |
| Squint, ±15° | Updates vᵣ; changes Ka and T; finite squint slightly worsens along-track resolution here | None after ideal trajectory correction |
| None / Hann / Hamming | Changes azimuth IPR, βₐ and nominal azimuth resolution; no range taper is applied | None |
| Log / linear image scale | Changes display visibility of weak features, not the signal or resolution | None |
| Reset to 1 m reference | Restores all baseline controls and log image scale | Baseline position |

Aircraft radial velocity must not be interpreted as target velocity. The earlier simulation's target-motion displacement and butterfly-like uncompensated response are not part of the current model. Conversely, this ideal stationary model cannot demonstrate errors from an incorrectly known aircraft trajectory.

## 9. Reproducible findings

Reset before each experiment and change only the listed setting. Values below come from the current browser compute module; “azimuth resolution” uses the requested nominal convention, and measured width uses the separate half-power definition.

| Experiment | Range resolution | Azimuth resolution | Measured azimuth half-power width | Synthetic length |
|---|---:|---:|---:|---:|
| Baseline: B=150 MHz, Lₐ=2 m, α=100%, None, θ=0 | 1.000 m | 1.000 m | 0.882 m | 75.000 m |
| B=500 MHz | 0.300 m | 1.000 m | 0.882 m | 75.000 m |
| Lₐ=4 m | 1.000 m | 2.000 m | 1.770 m | 37.500 m |
| α=50% | 1.000 m | 2.000 m | 1.770 m | 37.500 m |
| Hann | 1.000 m | 1.628 m | 1.441 m | 75.000 m |
| Hamming | 1.000 m | 1.472 m | 1.302 m | 75.000 m |
| θ=+15°, vᵣ≈+38.82 m/s | 1.000 m | 1.036 m | 0.912 m | 77.625 m |

All peaks remain at (range 5000 m, azimuth 0 m). At 15°, the effective aperture is about 72.425 m, less than the physical travel distance 77.625 m; the removed centroid is about 2588.19 Hz. Negative squint gives the opposite centroid but the same ideal width.

At baseline the equations can be evaluated directly:

$$\delta_R=\frac{3\times10^8\times1}{2\times150\times10^6}=1\text{ m},$$

$$\delta_{az}=\frac{0.03\times5000\times1}{2\times75}=1\text{ m}.$$

A useful presentation sequence is: reset; increase bandwidth; reset and increase physical antenna length; reset and reduce aperture fraction; compare None/Hann/Hamming; reset and change squint. Explain mainlobe width, sidelobe visibility and correct peak position separately.

## 10. Code map and validation

| File / function | Current responsibility |
|---|---|
| `web/index.html` | Controls, plot descriptions, equations and model limits |
| `web/app.mjs` | Synchronized inputs, metrics, 1 m image grid, profiles and reference overlay |
| `web/compute.mjs::compute()` | Ideal corrected signal, coherent FFT image, fixed axes and measured width |
| `web/compute.mjs::spatialResolutions()` | Requested resolution equations, explicit β factors and squint correction |
| `web/compute.mjs::windowFactors()` | Actual discrete-window half-power width and rectangle-relative broadening |
| `web/worker.mjs` | Background calculation and transferable arrays |
| `server.py` | Local static server for the same web files |
| `test_web.mjs` | Browser-model numerical regression tests |
| `.github/workflows/pages.yml` | Publishes `web/` to GitHub Pages when main is pushed |

Run:

```sh
node --check web/app.mjs
node test_web.mjs
```

Checks cover the sinc range cut, stationary position, signed aircraft radial geometry, centroid removal, fixed axes, aperture/antenna scaling, squint, Hann/Hamming normalization and half-power widths, Hamming sidelobe suppression, requested resolution equations, invalid parameters and cancellation. Predicted half-power width is cross-checked against the FFT image width within display-sampling tolerance.

The static Pages deployment runs the same files; there is no server-side simulation. A local edit is not automatically on the public site until it is committed, pushed and the Pages workflow succeeds.

The older `sar_model.py`, `app.py`, `radar.py`, `range_doppler_demo.py`, `range_doppler_interactive.py` and previous slides are not the current webapp's processing path. Their historical moving-target or noise controls should not be used to explain this interface.

## 11. Scope and limitations

- One stationary point, ideal known straight aircraft trajectory; no moving targets, trajectory errors or autofocus.
- Local quadratic range/phase approximation, ±15° squint; no exact high-squint geolocation, higher-order coupling or terrain geometry.
- Ideal range compression, migration and pre-sampling centroid correction are assumed, not implemented from raw echoes.
- No noise, speckle, antenna gain, radiometry or realistic scene reflectivity. Unit-peak normalization hides the SNR cost of windowing.
- Uniform range spectrum; βᵣ is explicitly 1. There is no range-window control.
- Fixed wavelength, reference range, speed and PRF. Their appearances in equations explain the model but do not imply extra UI controls.
- Finite display sampling limits measured widths, especially for the narrowest responses. A 1 m grid cell, a 0.1 m sample and physical resolution are different things.
- First-null spacing, full half-power width, nominal resolution and ENBW are distinct quantities. Definitions accompany every reported factor.

## 12. References and terminology

[ESA: Introduction to a SAR System](https://www.esa.int/Enabling_Support/Space_Engineering_Technology/Onboard_Data_Processing/Introduction_to_a_SAR_System) provides SAR image-formation context. [MathWorks: sarazres](https://www.mathworks.com/help/radar/ref/sarazres.html) describes synthetic aperture length and azimuth broadening inputs; its broadside example uses the requested λRβ/(2L) form. Always check width conventions before transferring numerical factors between sources.

[ICEYE: The Remarkable Story of SAR](https://sar.iceye.com/6.0.4/foundations/OverviewOfSAR/remarkableStory/) explains physical versus synthetic aperture and stripmap versus spotlight. [Harris: On the Use of Windows for Harmonic Analysis with the DFT](https://amst.ece.iastate.edu/paper/comparative_study/window_1.pdf) is the window-analysis reference. The app's factors are calculated from its own discrete weights, rather than copied without a width definition.

**IPR:** response to one ideal point. **Mainlobe:** central peak. **Sidelobes:** smaller responses from that same point. **RCMC:** range-cell migration correction. **PRF:** pulse repetition frequency. **Slow time:** time across aircraft pulses. **Fast time:** echo delay within a pulse, already compressed into range here. **Doppler centroid:** centre frequency of the phase history. **Synthetic aperture:** the coherent aircraft travel interval, distinct from the physical antenna.
