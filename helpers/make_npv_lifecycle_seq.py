"""Generate the animated PNG sequence of life-cycle NPV components per plan (NB05 Task 2.2 layout).

Run from the repo root with the project venv:
    uv run --no-sync python helpers/make_npv_lifecycle_seq.py [--tag scenario_ctt_bike_18_7]

Reads results/<tag>/05_appraisal/05_niba_pathway_trajectories.csv, writes 40 frames to
figures/<tag>/npv_lifecycle_seq/npv_lifecycle_year_XX.png.

Styling (2026-11-22): Inter font, ink #222222, pale-pastel palette, thin lines,
extra headroom at the top so the zero line sits in the lower third (matches the
static plan's y-axis placement). Y axis is locked across all frames.
"""
import argparse
import glob
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[1]

# --- Inter font: prefer a vendored copy in the repo, then the tectonic-dir download, else fallback
INK = "#222222"
FONT_CANDIDATES = [
    ROOT / "helpers" / "fonts",                                   # vendored (preferred)
    Path.home() / "AppData/Local/tectonic/fonts/inter",           # downloaded at setup
]
FONT = None
for cand in FONT_CANDIDATES:
    if not cand.is_dir():
        continue
    for f in glob.glob(str(cand / "**/*.ttf"), recursive=True):
        if "Regular" in f or "Variable.ttf" in f:
            try:
                font_manager.fontManager.addfont(f)
            except Exception:
                pass
    if any("Inter" in f.name for f in font_manager.fontManager.ttflist):
        FONT = "Inter"
        break
if FONT is None:
    FONT = "DejaVu Sans"  # fallback
plt.rcParams.update({
    "font.family": FONT,
    "text.color": INK,
    "axes.edgecolor": INK,
    "axes.labelcolor": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "axes.linewidth": 0.7,
    "font.size": 9,
})

# --- pale pastel palette (benefits warm-cool, costs muted earth tones)
PALETTE = {
    "Cycling time savings": "#A8C8E8",   # pale blue
    "Cycling health benefit": "#F5CBA7",  # pale apricot
    "Car time savings": "#A3D9A4",        # pale green
    "Car externalities": "#C8E6C9",       # pale mint
    "PT time savings": "#D7BDE2",         # pale lilac
    "CAPEX": "#D7B8A8",                   # pale clay
    "OPEX": "#F5B7B1",                    # pale rose
    "Option premium": "#CCCCCC",          # pale grey
    "Construction CO2": "#E8E3B0",        # pale khaki
    "Residual value (credit)": "#A9DFBF", # pale jade
}
THIN = 1.1  # line weight for the total-NPV line


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="scenario_ctt_bike_18_7")
    ap.add_argument("--years", default="1-40")
    args = ap.parse_args()

    tag = args.tag
    lo, hi = (int(x) for x in args.years.split("-"))
    years = list(range(lo, hi + 1))

    traj_path = ROOT / "results" / tag / "05_appraisal" / "05_niba_pathway_trajectories.csv"
    df = pd.read_csv(traj_path)
    disc = df["discount_rate"].iloc[0]

    base_cols = ["bike_time_cost", "bike_health_cost", "car_time_cost", "car_co2_cost",
                 "car_noise_cost", "car_air_cost", "car_acc_cost", "pt_time_cost",
                 "inv_cost", "op_cost", "upfront_cost", "residual_value", "construction_co2_cost"]
    base = df[df.plan == "baseline"][["scenario", "year"] + base_cols]
    d = df.merge(base, on=["scenario", "year"], suffixes=("", "_base"))
    d = d[d.plan != "baseline"].copy()
    d["car_ext"] = sum(d[c] - d[c + "_base"] for c in ["car_co2_cost", "car_noise_cost", "car_air_cost", "car_acc_cost"])
    d["disc_factor"] = 1.0 / (1 + disc) ** d["year_idx"]

    BENEFITS = {
        "Cycling time savings": lambda g: -(g["bike_time_cost"] - g["bike_time_cost_base"]),
        "Cycling health benefit": lambda g: -(g["bike_health_cost"] - g["bike_health_cost_base"]),
        "Car time savings": lambda g: -(g["car_time_cost"] - g["car_time_cost_base"]),
        "Car externalities": lambda g: -g["car_ext"],
        "PT time savings": lambda g: -(g["pt_time_cost"] - g["pt_time_cost_base"]),
    }
    COSTS = {
        "CAPEX": lambda g: -(g["inv_cost"] - g["inv_cost_base"]),
        "OPEX": lambda g: -(g["op_cost"] - g["op_cost_base"]),
        "Option premium": lambda g: -(g["upfront_cost"] - g["upfront_cost_base"]),
        "Construction CO2": lambda g: -(g["construction_co2_cost"] - g["construction_co2_cost_base"]),
        "Residual value (credit)": lambda g: (g["residual_value"] - g["residual_value_base"]),
    }
    PLANS = ["static1", "static2", "staged1", "staged2", "flexible"]
    LABELS = {"static1": "Static 1", "static2": "Static 2", "staged1": "Staged 1",
              "staged2": "Staged 2", "flexible": "Adaptive"}

    all_keys = list(BENEFITS) + list(COSTS)
    series = {}
    for name, fn in {**BENEFITS, **COSTS}.items():
        d["_v"] = fn(d) * d["disc_factor"]
        series[name] = d.groupby(["plan", "year"])["_v"].mean().unstack("year").cumsum(axis=1) / 1e6
    tot = sum(series[k] for k in all_keys)

    ymax = float(max(np.abs(series[k].values).max() for k in all_keys + ["__tot__"] if k != "__tot__") if False else np.abs(tot.values).max())
    ymax = max(ymax, float(max(np.abs(series[k].values).max() for k in all_keys))) * 1.06
    # move everything down: generous top headroom, zero line in lower third
    Y_TOP = ymax * 1.55
    Y_BOT = -ymax * 0.85

    out = ROOT / "figures" / tag / "npv_lifecycle_seq"
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("*.png"):
        f.unlink()

    for year in years:
        fig, ax = plt.subplots(figsize=(10, 6))
        x = np.arange(len(PLANS))
        bp = np.zeros(len(PLANS))
        bn = np.zeros(len(PLANS))
        for name in all_keys:
            v = np.array([series[name].loc[p, year] for p in PLANS])
            pos = np.where(v >= 0, v, 0.0)
            neg = np.where(v < 0, v, 0.0)
            ax.bar(x, pos, bottom=bp, color=PALETTE[name], label=name, width=0.72,
                   edgecolor="none")
            ax.bar(x, neg, bottom=bn, color=PALETTE[name], width=0.72, edgecolor="none")
            bp += pos
            bn += neg
        totals = bp + bn
        ax.plot(x, totals, color=INK, lw=THIN, marker="o", ms=4, label="Total NPV", zorder=5)
        for xi, t in zip(x, totals):
            ax.annotate(f"{t:.0f}", (xi, t), textcoords="offset points", xytext=(0, 5),
                        ha="center", fontsize=8, color=INK)
        ax.axhline(0, color=INK, lw=0.6, alpha=0.55)
        ax.set_xticks(x)
        ax.set_xticklabels([LABELS[p] for p in PLANS])
        ax.set_ylabel("cumulative discounted NPV vs baseline (MCHF)")
        ax.set_ylim(Y_BOT, Y_TOP)
        ax.set_title(f"NB05 Task 2.2 layout --- life-cycle NPV components per plan, cumulative through Year {year} of 40\n"
                     f"run {tag}: discount {disc:.0%}, 200 scenarios",
                     fontsize=10, color=INK)
        handles = [Patch(facecolor=PALETTE[k], edgecolor="none", label=k) for k in all_keys]
        handles.append(plt.Line2D([0], [0], color=INK, lw=THIN, marker="o", ms=4, label="Total NPV"))
        ax.legend(handles=handles, fontsize=7, ncol=2, loc="upper left", frameon=False)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.grid(axis="y", alpha=0.18, lw=0.5)
        fig.tight_layout()
        fig.savefig(out / f"npv_lifecycle_year_{year:02d}.png", dpi=110)
        plt.close(fig)
        if year % 10 == 0 or year == years[-1]:
            print("wrote year", year, "->", out / f"npv_lifecycle_year_{year:02d}.png")

    print(f"done: {len(list(out.glob('*.png')))} frames in {out} (font={FONT}, ink={INK})")


if __name__ == "__main__":
    main()
