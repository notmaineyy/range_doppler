"""
Build the code-optimisation slide deck + figures.

Run::

    .venv/bin/python make_optimisation_slides.py

Outputs:
    outputs/optimisation/*.png
    optimisation_slides.pptx
"""

import os

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "outputs", "optimisation")
os.makedirs(FIG, exist_ok=True)

DPI = 150
DARK = RGBColor(0x1F, 0x2A, 0x44)
ACCENT = RGBColor(0xC0, 0x39, 0x2B)
GREEN = RGBColor(0x1E, 0x84, 0x49)
GREY = RGBColor(0x55, 0x55, 0x55)

# --------------------------------------------------------------------------- #
# Data (from results.md)
# --------------------------------------------------------------------------- #
METHODS = [
    "numpy\nnaive\nfloat32",
    "numpy\nin-place\nfloat32",
    "numpy\nnaive\nfloat16",
    "numpy\nin-place\nfloat16",
    "numexpr\nfloat64\n10 cores",
    "numexpr\nfloat32\n10 cores",
]
# 300M pixels (all in RAM, stable) : time [s], result memory [GB]
T300 = [0.624, 0.339, 4.544, 4.114, 0.142, 0.116]
M300 = [1.20, 1.20, 0.60, 0.60, 2.40, 1.20]

# 1.1e9 pixels
T11 = [10.74, 1.8, 16.93, 15.27, 0.514, 0.486]
M11 = [4.40, 4.40, 2.20, 2.20, 8.80, 4.40]

# numexpr thread scaling at 1.1e9
THREADS = [1, 2, 4, 8, 10]
F64 = [3.853, 1.559, 0.804, 0.596, 0.604]
F32 = [3.155, 1.607, 0.825, 0.620, 0.550]

COLORS = ["#c0392b", "#e67e22", "#7f8c8d", "#95a5a6", "#2980b9", "#1e8449"]


# --------------------------------------------------------------------------- #
# Figures
# --------------------------------------------------------------------------- #
def fig_bars():
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.8))
    x = np.arange(len(METHODS))

    b0 = axs[0].bar(x, T300, color=COLORS)
    axs[0].set_yscale("log")
    axs[0].set_xticks(x)
    axs[0].set_xticklabels(METHODS, fontsize=8)
    axs[0].set_ylabel("time [s]  (log scale)")
    axs[0].set_title("Speed (300M pixels, all in memory)")
    for rect, v in zip(b0, T300):
        axs[0].text(rect.get_x() + rect.get_width() / 2, v * 1.1, f"{v:.3f}s",
                    ha="center", va="bottom", fontsize=8)
    axs[0].grid(axis="y", alpha=0.3)

    b1 = axs[1].bar(x, M300, color=COLORS)
    axs[1].set_xticks(x)
    axs[1].set_xticklabels(METHODS, fontsize=8)
    axs[1].set_ylabel("result memory [GB]")
    axs[1].set_title("Memory (result size)")
    for rect, v in zip(b1, M300):
        axs[1].text(rect.get_x() + rect.get_width() / 2, v + 0.05, f"{v:.2f}",
                    ha="center", va="bottom", fontsize=8)
    axs[1].grid(axis="y", alpha=0.3)

    fig.suptitle("Same maths, six ways: numexpr on 10 cores wins on speed; "
                 "float16 saves memory but is slow", fontsize=12)
    fig.tight_layout()
    p = os.path.join(FIG, "bars.png")
    fig.savefig(p, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return p


def fig_threads():
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.plot(THREADS, F64, "o-", lw=2, ms=7, color="#2980b9",
            label="float64 result (8.80 GB)")
    ax.plot(THREADS, F32, "s-", lw=2, ms=7, color="#1e8449",
            label="float32 result (4.40 GB)")
    for t, a, b in zip(THREADS, F64, F32):
        ax.annotate(f"{a:.2f}s", (t, a), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=8, color="#2980b9")
        ax.annotate(f"{b:.2f}s", (t, b), textcoords="offset points",
                    xytext=(0, -14), ha="center", fontsize=8, color="#1e8449")
    ax.set_xlabel("CPU cores used (numexpr threads)")
    ax.set_ylabel("time [s]  (1.1e9 pixels)")
    ax.set_title("numexpr thread scaling: strong to ~4-8 cores, then "
                 "memory bandwidth saturates")
    ax.set_xticks(THREADS)
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    p = os.path.join(FIG, "threads.png")
    fig.savefig(p, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return p


# --------------------------------------------------------------------------- #
# Slide helpers
# --------------------------------------------------------------------------- #
def _bg(slide):
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF)


def _title(slide, text):
    tb = slide.shapes.add_textbox(Inches(0.6), Inches(0.3), Inches(12.1), Inches(0.9))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(28)
    p.font.bold = True
    p.font.color.rgb = DARK


def _body(slide, items, left=0.7, top=1.35, width=12.0, height=5.7, size=18):
    tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    first = True
    for item in items:
        text, level = item if isinstance(item, tuple) else (item, 0)
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.text = text
        p.level = level
        p.font.size = Pt(size - 2 * level)
        p.font.color.rgb = DARK if level == 0 else GREY
        p.space_after = Pt(6)
    return tb


def _picture(slide, path, top=1.4, width=11.4, caption=None):
    from PIL import Image
    with Image.open(path) as im:
        w, h = im.size
    left = (13.333 - width) / 2.0
    slide.shapes.add_picture(path, Inches(left), Inches(top), width=Inches(width))
    if caption:
        cap_top = top + width * h / w + 0.08
        tb = slide.shapes.add_textbox(Inches(0.7), Inches(cap_top), Inches(12.0), Inches(0.5))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = caption
        p.font.size = Pt(13)
        p.font.color.rgb = GREY
        p.alignment = PP_ALIGN.CENTER


def add_title_slide(prs, title, subtitle, author):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(slide)
    bar = slide.shapes.add_shape(1, Inches(0), Inches(2.2), Inches(13.333), Inches(0.12))
    bar.fill.solid(); bar.fill.fore_color.rgb = ACCENT; bar.line.fill.background()
    tb = slide.shapes.add_textbox(Inches(0.8), Inches(2.5), Inches(11.7), Inches(2.5))
    tf = tb.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]; p.text = title
    p.font.size = Pt(38); p.font.bold = True; p.font.color.rgb = DARK
    p = tf.add_paragraph(); p.text = subtitle
    p.font.size = Pt(19); p.font.color.rgb = GREY
    p = tf.add_paragraph(); p.text = author
    p.font.size = Pt(13); p.font.color.rgb = GREY


def add_bullets(prs, title, items, size=18):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(slide); _title(slide, title); _body(slide, items, size=size)


def add_picture_slide(prs, title, path, bullets=None, caption=None, width=9.6):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(slide); _title(slide, title)
    if bullets:
        _body(slide, bullets, left=0.6, top=1.4, width=3.7, height=5.5, size=14)
        _picture(slide, path, top=1.55, width=8.5, caption=caption)
        for shp in slide.shapes:
            if shp.shape_type == 13:
                shp.left = Inches(4.55)
    else:
        _picture(slide, path, top=1.45, width=width, caption=caption)


def add_table(prs, title, headers, rows, size=13):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(slide); _title(slide, title)
    nrows, ncols = len(rows) + 1, len(headers)
    tbl = slide.shapes.add_table(nrows, ncols, Inches(0.6), Inches(1.5),
                                 Inches(12.1), Inches(0.55 * nrows)).table
    for c, htext in enumerate(headers):
        cell = tbl.cell(0, c)
        cell.text = htext
        for para in cell.text_frame.paragraphs:
            para.font.size = Pt(size); para.font.bold = True
            para.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        cell.fill.solid(); cell.fill.fore_color.rgb = DARK
    for r, row in enumerate(rows, start=1):
        for c, val in enumerate(row):
            cell = tbl.cell(r, c)
            cell.text = val
            for para in cell.text_frame.paragraphs:
                para.font.size = Pt(size - 1)
            if r % 2 == 0:
                cell.fill.solid(); cell.fill.fore_color.rgb = RGBColor(0xF2, 0xF5, 0xFA)


# --------------------------------------------------------------------------- #
# Deck
# --------------------------------------------------------------------------- #
def build_deck(figs):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    add_title_slide(
        prs,
        "Optimising a large image operation",
        "|I1 - I2| / (I1 + I2 + eps)  on two 1.1-billion-pixel images",
        "Timing study: numpy vs numexpr, dtypes, memory and CPU cores",
    )

    add_bullets(prs, "The problem", [
        "Compute, pixel by pixel:   |I1 - I2| / (I1 + I2 + eps)",
        "Two images of 1.1 billion pixels each (32,000 x 34,375).",
        ("Stored as uint8 (0..255) - the normal image format, 1 byte/pixel.", 1),
        "The arithmetic must be done in a wider type:",
        ("on uint8, subtraction wraps and addition overflows.", 1),
        "Goal: get the answer as fast as possible, using as little RAM as possible.",
    ])

    add_bullets(prs, "What we varied (the experiments)", [
        "1. Input storage:  uint8  vs  float32.",
        "2. Compute/result type:  float16 / float32 / float64.",
        "3. How the code is written:  naive one-liner  vs  in-place (out=).",
        "4. Library:  numpy  vs  numexpr (JIT + multithreaded).",
        "5. Number of CPU cores:  1, 2, 4, 8, 10.",
        "6. Forcing the result type:  numexpr float64  vs  forced float32.",
        "Everything measured with time.perf_counter, arrays allocated first,",
        ("and a checksum taken afterwards to prove the result is real and correct.", 1),
    ])

    add_table(
        prs, "Results at 1.1e9 pixels (uint8 inputs)",
        ["Method", "Type", "Cores", "Time", "Gpixel/s", "Result RAM"],
        [
            ["numpy naive", "float32", "1", "10.74 s", "0.10", "4.40 GB"],
            ["numpy in-place (out=)", "float32", "1", "~1.8 s", "~0.62", "4.40 GB"],
            ["numpy naive", "float16", "1", "16.93 s", "0.06", "2.20 GB"],
            ["numpy in-place", "float16", "1", "15.27 s", "0.07", "2.20 GB"],
            ["numexpr (safe)", "float64", "10", "0.514 s", "2.14", "8.80 GB"],
            ["numexpr forced out=float32", "float32", "10", "0.486 s", "2.26", "4.40 GB"],
        ],
    )

    add_picture_slide(
        prs, "In-memory comparison (300M pixels)", figs["bars"],
        bullets=[
            "Stable, fair comparison (nothing swaps).",
            "in-place ~2x faster than naive.",
            "float16 ~12x slower than float32.",
            "numexpr on 10 cores ~3-6x faster than numpy.",
            "float32 result halves memory.",
        ],
        width=11.6,
    )

    add_picture_slide(
        prs, "Thread scaling: numexpr (1.1e9 pixels)", figs["threads"],
        bullets=[
            "1 thread = numpy speed.",
            "Big gains up to ~4-8 cores.",
            "Then the memory bus saturates.",
            "float32 is as fast or faster, at half the RAM.",
        ],
        width=8.6,
    )

    add_table(
        prs, "Headline: force numexpr to 32-bit",
        ["numexpr version", "Result type", "Time (1.1e9)", "Result RAM"],
        [
            ["default, casting='safe'", "float64", "0.514 s", "8.80 GB"],
            ["forced out=float32", "float32", "0.486 s", "4.40 GB"],
        ],
    )
    add_bullets(prs, "Why forcing 32-bit is a free win", [
        "Same speed: 0.486 s vs 0.514 s.",
        "Half the RAM: 4.40 GB vs 8.80 GB.",
        "Identical answer (same checksum).",
        "How: pass a pre-allocated float32 buffer as out=,",
        ("with casting='same_kind' (numexpr refuses the downcast under 'safe').", 1),
    ])

    add_bullets(prs, "Lessons for code optimisation", [
        "1. Keep inputs small: uint8, not float32 (4x less data).",
        "2. Compute in float32 - never in uint8 (wraps/overflows).",
        "3. Reuse memory: in-place / out= avoids full-size temporaries (~2x).",
        "4. Parallelise: numexpr uses all cores (the single biggest speed win).",
        "5. Force the 32-bit result - same speed, half the memory.",
        "6. Keep data in RAM - swapping to disk cost ~10x.",
        "7. If it cannot fit: process in chunks (row blocks) to avoid swap.",
    ], size=17)

    add_bullets(prs, "The winning configuration", [
        "uint8 inputs  +  numexpr  +  all cores  +  forced float32 result.",
        "Result: ~0.49 s and 4.40 GB for 1.1 billion pixels.",
        ("vs the naive float32 numpy one-liner: 10.74 s and swapping.", 1),
        "",
        "Run it:",
        ("normdiff_numexpr.py --pixels 1.1e9 --mode numpy numexpr --out-dtype float32", 1),
        "Report timings with context: input dtype, compute dtype, cores, in-RAM or swap.",
    ], size=17)

    path = os.path.join(HERE, "optimisation_slides.pptx")
    prs.save(path)
    return path


def main():
    figs = {"bars": fig_bars(), "threads": fig_threads()}
    for n, p in figs.items():
        print("figure:", p)
    print("deck  :", build_deck(figs))


if __name__ == "__main__":
    main()
