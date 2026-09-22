# SAR image laboratory

## Smooth browser interface (recommended)

```sh
cd /Users/shermi/range_doppler
python3 server.py
```

Open http://127.0.0.1:8503. No third-party packages are needed for this interface.

Each numeric variable has a synchronized slider, direct input and up/down buttons. All plots update in place without page reloads. The client computes the coherent SAR signal in a Web Worker, leaving the UI thread free. It coalesces intermediate settings while a calculation runs so quick adjustments do not create a backlog. Actual latency depends on the device. The existing plots remain visible while the next result computes.

Controls: bandwidth, aircraft radial velocity, physical antenna length, processed aperture percentage, squint angle, and Rectangular/Hann azimuth weighting. Aircraft radial velocity and squint are synchronized using vr = 150 sinθ. The target is stationary and ideal aircraft-trajectory compensation is always applied. The main image uses a fixed 10 m square close-up with 1 m gridlines and equal spatial scale on both axes. The full-scene overview retains fixed −220 to +220 m azimuth limits. Log power reveals sidelobes by default; linear power is also available. Reset selects 150 MHz, a 2 m antenna, full aperture, rectangular weighting and broadside, giving 1 m first-null resolution references in both dimensions. Grid spacing remains 1 m when parameters change; it is not a substitute for the actual resolution. Reset restores the baseline.

`web/compute.mjs` uses a local quadratic aircraft-trajectory model; `sar_model.py` retains the earlier moving-target reference experiments. The browser uses 0.1 m range display sampling and an 8192-point azimuth FFT. The NumPy reference uses 0.05 m range sampling. Zero padding only interpolates the response. The intermediate Doppler display uses padded FFTs and a coarser display grid. It is independently normalized. The final image and profiles preserve the stationary unit-peak reference.

## Reference model and experiments

```sh
.venv/bin/python sar_assignment.py
.venv/bin/python -m unittest discover -p 'test_sar*.py'
node test_web.mjs
```

Original comparison figures are in `outputs/sar_assignment/`. `readme_task1.md` is the complete current report, including the explicit resolution equations and width conventions. `SAR_EXPLANATION.md` retains historical context. The browser model checks reproduce reference widths and peak values, check cancellation, and cover the combined parameter extremes. Strong range walk can create multiple nearly equal maxima, so the reported brightest pixel can switch between them.

`app.py` is the earlier Streamlit reference view. The scripts `radar.py`, `range_doppler_demo.py`, `range_doppler_interactive.py` and `app_legacy.py` are retained historical experiments and are not the current interactive interface.

## Deploy to GitHub Pages

The browser interface is fully static (HTML + ES modules + a Web Worker), so it
runs directly on GitHub Pages. The app is served from the `web/` directory, and
GitHub Pages serves `.mjs` files with the correct JavaScript MIME type, so no
build step or renaming is required.

### Option A — GitHub Actions (already configured)

`.github/workflows/pages.yml` publishes the `web/` directory whenever `main` is
pushed. One-time setup:

1. Push this repository to GitHub (the workflow only runs on the remote).
2. In the repository, open **Settings → Pages**.
3. Under **Build and deployment → Source**, choose **GitHub Actions**.
4. Push to `main` (or run the workflow from the **Actions** tab).

The site appears at `https://<user>.github.io/<repo>/`
(here `https://notmaineyy.github.io/range_doppler/`). Relative paths mean it
works from that sub-path without changes.

### Option B — Deploy from a branch (no Actions)

1. Copy the static app into a `docs/` folder at the repository root:

   ```sh
   mkdir -p docs && cp web/index.html web/app.mjs web/compute.mjs web/worker.mjs docs/
   ```

2. Commit and push `docs/`.
3. In **Settings → Pages**, set **Source** to **Deploy from a branch**,
   branch `main`, folder `/docs`.

### Notes

- The app is client-side only; no Python or server is needed in production.
- `web/.nojekyll` stops Jekyll from processing the files (needed for Option B;
  harmless for Option A).
- To test the exact production behaviour locally, use `python3 server.py` and
  open http://127.0.0.1:8503 — it serves the same `web/` directory.


The weighting selector explicitly labels Rectangular as **None (rectangular / uniform)**: every pulse has equal weight, with no taper. Selecting Hann overlays the analytic finite uniform-aperture reference on the azimuth profile, so sidelobe suppression and mainlobe broadening can be compared at identical geometry and dwell. Both curves use the same stationary unit-peak normalization.

Nominal resolution metrics use δR = cβr/(2B) and δaz = λRβa/(2Lsyn) at broadside. The along-track squint model includes cos²θ in the denominator. Full half-power widths are reported separately; range taper is fixed to None (βr = 1). See `readme_task1.md` for definitions and worked results.
