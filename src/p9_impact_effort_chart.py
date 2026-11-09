"""Phase 9: impact-vs-effort matrix for the eight recommendations (qualitative placement, see 09_recommendations.md)."""
import pandas as pd

from config import IMAGES, OUTPUTS
from viz_style import AQUA, BLUE, GRAY, INK2, ORANGE, plt, save, title

OUT, CH = OUTPUTS / "phase9", IMAGES / "phase9"
OUT.mkdir(parents=True, exist_ok=True); CH.mkdir(parents=True, exist_ok=True)
LEVEL = {"Low": 1, "Medium": 2, "High": 3}
# id, short name, impact, effort, offset (x, y) to keep labels apart inside a cell
REC = pd.DataFrame([
    ("R1", "Save-now win-back", "High", "Low", (-0.3, 0.25)),
    ("R2", "Silence-trigger nudges", "High", "Low", (-0.3, 0.0)),
    ("R3", "Second-order journey (A/B first)", "High", "Medium", (-0.3, 0.0)),
    ("R4", "Cart-recovery flow", "High", "Low", (-0.3, -0.25)),
    ("R5", "Protect without discounts", "Medium", "Medium", (-0.3, 0.15)),
    ("R6", "Post-holiday follow-up", "Low", "Low", (-0.3, 0.0)),
    ("R7", "Fix brand data at source", "Medium", "High", (-0.3, 0.0)),
    ("R8", "Monthly rescoring + holdouts", "Medium", "Medium", (-0.3, -0.15)),
], columns=["id", "name", "impact", "effort", "off"])
REC.drop(columns="off").to_csv(OUT / "impact_effort.csv", index=False)

fig, ax = plt.subplots(figsize=(9, 6))
ax.axvspan(0.5, 1.5, ymin=2 / 3, ymax=1, color=AQUA, alpha=0.08, lw=0)
ax.axvspan(1.5, 3.5, ymin=2 / 3, ymax=1, color=BLUE, alpha=0.06, lw=0)
for name, x, y in [("Quick wins", 0.55, 3.45), ("Big bets", 1.55, 3.45), ("Fill-ins", 0.55, 0.62), ("Plan / enablers", 1.55, 0.62)]:
    ax.text(x, y, name.upper(), fontsize=8.5, color=INK2, va="top" if y > 2 else "bottom", fontweight="bold")
ax.axhline(2.5, color="#d6d5d0", lw=1); ax.axvline(1.5, color="#d6d5d0", lw=1)
for r in REC.itertuples():
    x, y = LEVEL[r.effort] + r.off[0], LEVEL[r.impact] + r.off[1]
    c = ORANGE if r.id in ("R1", "R2", "R4") else BLUE if r.id == "R3" else GRAY
    ax.scatter(x, y, s=420, color=c, zorder=3, edgecolor="white", lw=1.5)
    ax.text(x, y, r.id, ha="center", va="center", color="white", fontsize=8.5, fontweight="bold", zorder=4)
    ax.text(x + 0.11, y, r.name, ha="left", va="center", fontsize=8.5, color=INK2, zorder=4)
ax.set_xlim(0.5, 3.5); ax.set_ylim(0.5, 3.5)
ax.set_xticks([1, 2, 3], ["Low", "Medium", "High"]); ax.set_yticks([1, 2, 3], ["Low", "Medium", "High"])
ax.set_xlabel("Effort (build + run)"); ax.set_ylabel("Expected impact"); ax.grid(False)
title(ax, "Retention actions: impact vs effort",
      "Three quick wins first; the second-order journey is the big bet, tested before it scales")
save(fig, CH / "p9_01_impact_effort.png")
