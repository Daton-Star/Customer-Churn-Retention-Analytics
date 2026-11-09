"""Phase 10: LinkedIn carousel (portrait PDF, 1080 x 1350 per page) built from the project charts.

Every number on the slides is a rounded form logged in key_numbers.csv (K161, K165).
Output: reports/career/linkedin_carousel.pdf. Run after Phases 4-9 (it reuses images/).
"""
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from config import ROOT
from viz_style import BLUE, INK, INK2, ORANGE, SURFACE

IMG = ROOT / "images"
OUT = ROOT / "reports" / "career" / "linkedin_carousel.pdf"
W, H = 10.8, 13.5  # inches at 100 dpi = 1080 x 1350 px

SLIDES = [  # (kicker, headline, body, chart or None)
    ("Customer churn & retention · cosmetics e-commerce",
     "85% of buyers never came back.\nSo who's worth saving?",
     "20.7M clickstream events · 110K buyers\nREES46 store, Oct 2019 – Feb 2020\nSQL · Python · XGBoost · Power BI · Excel", None),
    ("1 · The size of the problem",
     "Buyers who didn't return brought\n74% of Oct–Dec revenue",
     "85% of Oct–Dec buyers placed no order in Jan–Feb.", IMG / "dashboard" / "01_executive_overview.png"),
    ("2 · The moment that matters",
     "One-time buyers churned at 90%,\nrepeat buyers at 61%",
     "Every extra order lowers churn, so the second order is the target.", IMG / "phase4" / "p4_17_churn_by_orders.png"),
    ("3 · The early warning",
     "A silent last month adds\nabout 16 points of churn",
     "Cart removals did not predict churn: they signal engaged shoppers.", IMG / "phase5" / "p5_01_churn_gaps_ci.png"),
    ("4 · Predicting who leaves",
     "XGBoost ranks risk with AUC 0.80\n(vs 0.73 for an RFM baseline)",
     "\"Everyone churns\" is 85% accurate and useless, so I used AUC, PR-AUC and lift.", IMG / "phase6" / "p6_04_shap_importance.png"),
    ("5 · Who to save",
     "Target 12.7K high-value, high-risk\nbuyers: projected +81% ROI",
     "About 14.6K net per wave; breaks even below a 5% save rate.\nBlanket discounts only break even.", IMG / "phase7" / "p7_03_value_risk_matrix.png"),
    ("6 · What I'd do next",
     "Three quick wins now,\none big bet tested properly",
     "Win-back, no-discount nudges and cart recovery, each with a holdout.\nA 10% offer to every new buyer needs a ~10-point lift,\nso it goes to a 3-arm A/B test first.", IMG / "phase9" / "p9_01_impact_effort.png"),
]


def slide(pdf, i, kicker, headline, body, chart):
    fig = plt.figure(figsize=(W, H), facecolor=SURFACE)
    fig.text(0.07, 0.94, kicker.upper(), fontsize=15, color=BLUE, weight="bold", va="top")
    fig.text(0.07, 0.89, headline, fontsize=34 if chart else 44, color=INK, weight="bold", va="top", linespacing=1.15)
    if chart:
        fig.text(0.07, 0.765, body, fontsize=17, color=INK2, va="top", linespacing=1.4)
        img = mpimg.imread(chart)
        ax = fig.add_axes([0.05, 0.08, 0.90, 0.60])
        ax.imshow(img); ax.axis("off")
    else:
        fig.text(0.07, 0.62, body, fontsize=22, color=INK2, va="top", linespacing=1.6)
        fig.add_artist(plt.Rectangle((0.07, 0.30), 0.12, 0.012, color=ORANGE, transform=fig.transFigure))
    fig.text(0.07, 0.035, "Pooja Ingale · portfolio project on public data · money in the dataset's currency units",
             fontsize=12, color=INK2)
    fig.text(0.93, 0.035, f"{i} / {len(SLIDES)}", fontsize=12, color=INK2, ha="right")
    pdf.savefig(fig, facecolor=SURFACE)
    plt.close(fig)


with PdfPages(OUT) as pdf:
    for i, s in enumerate(SLIDES, start=1):
        slide(pdf, i, *s)
print(OUT, round(OUT.stat().st_size / 1e6, 1), "MB,", len(SLIDES), "pages")
