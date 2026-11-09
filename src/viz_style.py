"""Shared chart style for all phases (reference palette, light mode)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

BLUE, ORANGE, AQUA, YELLOW, MAGENTA = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"
GRAY, INK, INK2, SURFACE, GRID = "#8a8984", "#0b0b0b", "#52514e", "#fcfcfb", "#ecebe7"
SEQ_BLUE = LinearSegmentedColormap.from_list(
    "seq_blue", ["#f4f8fd", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"])

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": "#d6d5d0", "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.8, "font.size": 10, "axes.titlesize": 11,
    "axes.titlelocation": "left", "legend.frameon": False,
})


def title(ax, main: str, sub: str | None = None) -> None:
    """Left-aligned title; the subtitle carries the 'so what'."""
    ax.set_title(main + (f"\n{sub}" if sub else ""), loc="left", fontsize=11)


def save(fig, path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
