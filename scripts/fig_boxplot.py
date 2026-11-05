#!/usr/bin/env python3
"""Figure 12: boxplot of the RQ1 per-experiment median precision and recall."""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("pdf")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "derived_results" / "appendix_precision_recall_authoritative.csv"
OUT = ROOT / "derived_results" / "rq1_boxplot.pdf"

rows = [r for r in csv.DictReader(open(CSV)) if r["n_scored"] and int(r["n_scored"]) > 0]
P = [float(r["precision_median"]) for r in rows]
R = [float(r["recall_median"]) for r in rows]

plt.rcParams.update({"font.size": 15})
fig, ax = plt.subplots(figsize=(4.6, 3.5))
ax.boxplot([P, R], tick_labels=["Precision", "Recall"], showmeans=True, widths=0.55,
           boxprops=dict(color="blue"),
           medianprops=dict(color="red"),
           whiskerprops=dict(color="black"),
           capprops=dict(color="black", linewidth=2),
           flierprops=dict(marker="+", markeredgecolor="red", markersize=8),
           meanprops=dict(marker="D", markerfacecolor="lightgreen",
                          markeredgecolor="green", markersize=12))
ax.set_ylabel("Percentage [%]")
ax.set_ylim(50, 102)
ax.set_yticks([50, 60, 70, 80, 90, 100])
ax.grid(True, color="0.85")
ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig(OUT, metadata={"CreationDate": None})
print(f"Figure 12: {len(rows)} scored experiments -> {OUT.relative_to(ROOT)}")
