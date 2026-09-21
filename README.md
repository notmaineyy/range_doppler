# SAR image laboratory

## Smooth browser interface (recommended)

```sh
cd /Users/shermi/range_doppler
python3 server.py
```

Open http://127.0.0.1:8503. No third-party packages are needed for this interface.

Each numeric variable has a synchronized slider, direct input and up/down buttons. All plots update in place without page reloads. The client computes the coherent SAR signal in a Web Worker, leaving the UI thread free. It coalesces intermediate settings while a calculation runs so quick adjustments do not create a backlog. Actual latency depends on the device. The existing plots remain visible while the next result computes.

Controls: bandwidth, target radial velocity, physical antenna length, processed aperture percentage, and Rectangular/Hann azimuth weighting. The full-position checkbox shows both true and apparent locations for moving targets. Reset restores the baseline.

`web/compute.mjs` uses the same paraxial signal model as `sar_model.py`. The browser uses 0.1 m range display sampling and an 8192-point azimuth FFT. The NumPy reference uses 0.05 m range sampling. Zero padding only interpolates the response. The intermediate Doppler display uses padded FFTs and a coarser display grid. It is independently normalized. The final image and profiles preserve the stationary unit-peak reference.

## Reference model and experiments

```sh
.venv/bin/python sar_assignment.py
.venv/bin/python -m unittest discover -p 'test_sar*.py'
node test_web.mjs
```

Original comparison figures are in `outputs/sar_assignment/`. `SAR_EXPLANATION.md` describes the physics. The browser model checks reproduce reference widths and peak values, check cancellation, and cover the combined parameter extremes. Strong range walk can create multiple nearly equal maxima, so the reported brightest pixel can switch between them.

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

