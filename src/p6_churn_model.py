"""Phase 6: churn prediction.

Training data: user_churn_features.csv (Oct-Dec 2019 behaviour -> churn in Jan-Feb 2020).
Leakage guard: label-window columns (future_orders, future_spend, churned) and all timestamps are
excluded from features. Seed 42 everywhere.

Steps
 1. Features: 29 behavioural columns + top-10 purchased-brand one-hots (+ missing-value flags)
 2. Stratified 80/20 holdout; 5-fold stratified CV on the training set for model comparison
    Models: RFM baseline (logistic), logistic regression, Random Forest, XGBoost (class-imbalance handled
    with class_weight / scale_pos_weight)
 3. Holdout evaluation: ROC-AUC, PR-AUC, precision/recall/F1, confusion matrix, lift/gain, precision@top-k
 4. SHAP explanations for the best model
 5. Out-of-fold churn scores for every buyer -> risk tiers
 6. Deployment model (orders-only features, available for any window) trained on Oct-Dec -> Jan-Feb,
    then applied to Dec 2019-Feb 2020 behaviour to score P(no order in Mar-Apr 2020) for current buyers
Run: python src/p6_churn_model.py [data_dir]
"""
import json
import sys
import warnings
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import shap
from sklearn.compose import ColumnTransformer
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, confusion_matrix, f1_score, precision_recall_curve,
                             precision_score, recall_score, roc_auc_score, roc_curve, accuracy_score)
from sklearn.model_selection import StratifiedKFold, cross_val_predict, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import QuantileTransformer
from xgboost import XGBClassifier

from viz_style import AQUA, BLUE, GRAY, INK, INK2, ORANGE, SEQ_BLUE, SURFACE, plt, save, title  # noqa: E402
from config import DATA as DEFAULT_DATA, IMAGES, OUTPUTS  # noqa: E402

warnings.filterwarnings("ignore")
SEED = 42
DATA = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DATA
OUT, CH = OUTPUTS / "phase6", IMAGES / "phase6"
OUT.mkdir(parents=True, exist_ok=True); CH.mkdir(parents=True, exist_ok=True)
metrics_log = {}

# ---------------------------------------------------------------- 1. features
u = pd.read_csv(DATA / "user_churn_features.csv")
LABEL_WINDOW = ["future_orders", "future_spend", "churned"]          # leakage: never features
TIMESTAMPS = ["first_seen_ts", "last_seen_ts", "first_order_ts", "last_order_ts"]
ID = ["user_id"]
y = u["churned"].astype(int).values
X = u.drop(columns=LABEL_WINDOW + TIMESTAMPS + ID)
top_brands = X.top_purchased_brand.value_counts().index[:10]
for b in top_brands:
    X[f"brand_{b}"] = (X.top_purchased_brand == b).astype(int)
X = X.drop(columns="top_purchased_brand")
for c in ["avg_price_viewed", "view_to_cart_rate", "cart_to_purchase_rate", "cart_remove_rate"]:
    X[f"{c}_missing"] = X[c].isna().astype(int)                      # no views / no carts
X["avg_days_between_orders"] = X["avg_days_between_orders"].fillna(-1)  # -1 = single order
FEATURES = list(X.columns)
assert not set(FEATURES) & set(LABEL_WINDOW + TIMESTAMPS), "leakage"
pd.Series(FEATURES, name="feature").to_csv(OUT / "features_used.csv", index=False)
print(f"{len(FEATURES)} features, {len(X):,} buyers, churn rate {y.mean():.4f}")

X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=SEED)
neg_pos = (y_tr == 0).sum() / (y_tr == 1).sum()  # retained / churned (churn is the majority class)

rfm_cols = ["recency_days", "n_orders", "total_spend"]
models = {
    "RFM baseline (logistic)": Pipeline([
        ("sel", ColumnTransformer([("rfm", "passthrough", rfm_cols)])),
        ("q", QuantileTransformer(output_distribution="normal", random_state=SEED)),
        ("lr", LogisticRegression(class_weight="balanced", max_iter=2000))]),
    "Logistic regression": Pipeline([
        ("imp", SimpleImputer(strategy="median")),
        ("q", QuantileTransformer(output_distribution="normal", random_state=SEED)),
        ("lr", LogisticRegression(class_weight="balanced", C=0.5, max_iter=3000))]),
    "Random Forest": Pipeline([
        ("imp", SimpleImputer(strategy="median")),
        ("rf", RandomForestClassifier(n_estimators=400, min_samples_leaf=20, max_features="sqrt",
                                      class_weight="balanced_subsample", n_jobs=-1, random_state=SEED))]),
    "XGBoost": XGBClassifier(n_estimators=500, max_depth=5, learning_rate=0.04, subsample=0.8,
                             colsample_bytree=0.8, min_child_weight=5, reg_lambda=1.0,
                             scale_pos_weight=neg_pos, eval_metric="logloss", n_jobs=4, random_state=SEED),
}
COLORS = {"RFM baseline (logistic)": GRAY, "Logistic regression": AQUA, "Random Forest": ORANGE, "XGBoost": BLUE}

# ---------------------------------------------------------------- 2. stratified 5-fold CV
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
pr_auc_retained = lambda est, Xv, yv: average_precision_score(1 - yv, 1 - est.predict_proba(Xv)[:, 1])  # noqa: E731
cv_rows = []
for name, m in models.items():
    r = cross_validate(m, X_tr, y_tr, cv=cv, n_jobs=1,
                       scoring={"roc_auc": "roc_auc", "pr_auc_churn": "average_precision",
                                "pr_auc_retained": pr_auc_retained, "f1_churn": "f1"})
    row = {"model": name}
    for k in ["roc_auc", "pr_auc_churn", "pr_auc_retained", "f1_churn"]:
        row[f"{k}_mean"] = r[f"test_{k}"].mean(); row[f"{k}_std"] = r[f"test_{k}"].std()
    cv_rows.append(row)
    print(f"CV {name}: ROC-AUC {row['roc_auc_mean']:.4f} ± {row['roc_auc_std']:.4f}, "
          f"PR-AUC(retained) {row['pr_auc_retained_mean']:.4f}")
cvdf = pd.DataFrame(cv_rows).round(4)
cvdf.to_csv(OUT / "cv_results.csv", index=False)

# ---------------------------------------------------------------- 3. holdout evaluation
base_churn = y_te.mean()
hold, probs = [], {}
for name, m in models.items():
    m.fit(X_tr, y_tr)
    p = m.predict_proba(X_te)[:, 1]; probs[name] = p
    pred = (p >= 0.5).astype(int)
    order = np.argsort(-p)
    prec_at = {f"precision_churn_top{k}pct": y_te[order[: int(len(p) * k / 100)]].mean() for k in (10, 20)}
    # The minority class (retained) is the hard part: how well do LOW scores find the buyers who stay?
    order_r = np.argsort(p)
    prec_ret = {f"precision_retained_top{k}pct": (1 - y_te[order_r[: int(len(p) * k / 100)]]).mean() for k in (10, 20)}
    hold.append(dict(model=name, roc_auc=roc_auc_score(y_te, p), pr_auc_churn=average_precision_score(y_te, p),
                     pr_auc_retained=average_precision_score(1 - y_te, 1 - p), accuracy=accuracy_score(y_te, pred),
                     precision_churn=precision_score(y_te, pred), recall_churn=recall_score(y_te, pred),
                     f1_churn=f1_score(y_te, pred), precision_retained=precision_score(1 - y_te, 1 - pred),
                     recall_retained=recall_score(1 - y_te, 1 - pred), f1_retained=f1_score(1 - y_te, 1 - pred),
                     **prec_at, **prec_ret))
hdf = pd.DataFrame(hold).round(4)
hdf.loc[len(hdf)] = {"model": "Always predict churn (naive)", "roc_auc": 0.5, "pr_auc_churn": round(base_churn, 4),
                     "pr_auc_retained": round(1 - base_churn, 4) and round(1 - base_churn, 4),
                     "accuracy": round(base_churn, 4), "precision_churn": round(base_churn, 4), "recall_churn": 1.0,
                     "f1_churn": round(2 * base_churn / (1 + base_churn), 4), "precision_retained": 0.0,
                     "recall_retained": 0.0, "f1_retained": 0.0}
hdf.to_csv(OUT / "holdout_results.csv", index=False)
print(hdf.T.to_string())
# Choose the model on cross-validation (not on the holdout, which stays an unbiased final check)
best = cvdf.sort_values("roc_auc_mean", ascending=False).model.iloc[0]
print("best model (by CV ROC-AUC):", best)
pb = probs[best]
cm = confusion_matrix(y_te, (pb >= 0.5).astype(int))
pd.DataFrame(cm, index=["actual retained", "actual churned"], columns=["pred retained", "pred churned"]).to_csv(
    OUT / "confusion_matrix_best.csv")
metrics_log.update(best_model=best, base_churn_test=float(base_churn), n_train=int(len(y_tr)), n_test=int(len(y_te)),
                   confusion_matrix=cm.tolist())

# Charts: ROC + PR(retained)
fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.3))
for name, p in probs.items():
    fpr, tpr, _ = roc_curve(y_te, p)
    axes[0].plot(fpr, tpr, color=COLORS[name], linewidth=2, label=f"{name} ({roc_auc_score(y_te, p):.3f})")
    pr, rc, _ = precision_recall_curve(1 - y_te, 1 - p)
    axes[1].plot(rc, pr, color=COLORS[name], linewidth=2, label=f"{name} ({average_precision_score(1 - y_te, 1 - p):.3f})")
axes[0].plot([0, 1], [0, 1], color=GRAY, linestyle=":", linewidth=1)
axes[1].axhline(1 - base_churn, color=GRAY, linestyle=":", linewidth=1)
axes[1].text(0.98, 1 - base_churn + 0.02, f"random = {1-base_churn:.3f}", ha="right", fontsize=8.5, color=INK2)
axes[0].set_xlabel("False positive rate"); axes[0].set_ylabel("True positive rate (churners caught)")
axes[1].set_xlabel("Recall (retained buyers found)"); axes[1].set_ylabel("Precision")
axes[0].set_title("ROC curve (AUC in legend)", loc="left", fontsize=10, color=INK2)
axes[1].set_title("Precision-recall for the minority class: buyers who stay", loc="left", fontsize=10, color=INK2)
for ax in axes:
    ax.legend(loc="lower right", fontsize=8)
fig.suptitle(f"Holdout performance (n={len(y_te):,}): {best} ranks churn best", x=0.01, ha="left", fontsize=11)
save(fig, CH / "p6_01_roc_pr_curves.png")

# Confusion matrix
fig, ax = plt.subplots(figsize=(5.2, 4.2))
ax.imshow(cm, cmap=SEQ_BLUE)
labels = [["True retained", "False churn alarm"], ["Missed churner", "True churner"]]
for i in range(2):
    for j in range(2):
        ax.text(j, i, f"{labels[i][j]}\n{cm[i, j]:,}\n({100*cm[i, j]/cm.sum():.1f}%)", ha="center", va="center",
                fontsize=9.5, color="white" if cm[i, j] > cm.max() * 0.5 else INK)
ax.set_xticks([0, 1], ["Predicted retained", "Predicted churn"]); ax.set_yticks([0, 1], ["Actual retained", "Actual churn"])
ax.grid(False); ax.tick_params(length=0)
for sp in ax.spines.values():
    sp.set_visible(False)
title(ax, f"{best}: confusion matrix (threshold 0.5)", "Class weighting trades some churn recall for finding stayers")
save(fig, CH / "p6_02_confusion_matrix.png")

# Gain / lift (churn class and retained class)
def gain_table(yv, p, positive_is_churn=True):
    order = np.argsort(-p) if positive_is_churn else np.argsort(p)
    yy = yv[order] if positive_is_churn else 1 - yv[order]
    rows = []
    for d in range(1, 11):
        k = int(len(yy) * d / 10)
        rows.append(dict(decile=d, cum_pct_customers=10 * d, cum_gain_pct=100 * yy[:k].sum() / yy.sum(),
                         decile_rate=yy[int(len(yy) * (d - 1) / 10):k].mean(), lift=yy[int(len(yy) * (d - 1) / 10):k].mean() / yy.mean()))
    return pd.DataFrame(rows)

gc, gr = gain_table(y_te, pb, True), gain_table(y_te, pb, False)
gc.round(4).to_csv(OUT / "gain_lift_churn.csv", index=False); gr.round(4).to_csv(OUT / "gain_lift_retained.csv", index=False)
fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2))
axes[0].plot([0] + list(gr.cum_pct_customers), [0] + list(gr.cum_gain_pct), color=BLUE, linewidth=2, marker="o",
             markersize=6, markeredgecolor=SURFACE, label="Model")
axes[0].plot([0, 100], [0, 100], color=GRAY, linestyle=":", label="Random")
axes[0].annotate(f"Top 20% lowest-risk → {gr.cum_gain_pct[1]:.0f}% of stayers", (20, gr.cum_gain_pct[1]),
                 xytext=(28, gr.cum_gain_pct[1] - 12), fontsize=9)
axes[0].set_xlabel("% of buyers, ranked from lowest churn score"); axes[0].set_ylabel("% of retained buyers captured")
axes[0].set_title("Cumulative gain: finding buyers who stay", loc="left", fontsize=10, color=INK2); axes[0].legend(loc="lower right")
bars = axes[1].bar(gc.decile.astype(str), gc.lift, color=BLUE, width=0.6)
for b, v in zip(bars, gc.decile_rate):
    axes[1].text(b.get_x() + b.get_width() / 2, b.get_height() + 0.01, f"{100*v:.0f}%", ha="center", fontsize=8, color=INK)
axes[1].axhline(1, color=GRAY, linestyle=":")
axes[1].set_xlabel("Churn-score decile (1 = highest risk)"); axes[1].set_ylabel("Lift vs average churn rate")
axes[1].set_title("Churn lift by decile (labels = actual churn rate)", loc="left", fontsize=10, color=INK2)
axes[1].grid(axis="x", visible=False)
fig.suptitle("The model separates near-certain churners from the buyers most likely to stay", x=0.01, ha="left", fontsize=11)
save(fig, CH / "p6_03_gain_lift.png")

# ---------------------------------------------------------------- 4. SHAP (best tree model)
tree_name = best if best in ("XGBoost", "Random Forest") else "XGBoost"
tree_model = models[tree_name]
sample = X_te.sample(3000, random_state=SEED)
if tree_name == "XGBoost":
    explainer = shap.TreeExplainer(tree_model)
    sv = explainer.shap_values(sample)
else:
    explainer = shap.TreeExplainer(tree_model.named_steps["rf"])
    sv = explainer.shap_values(tree_model.named_steps["imp"].transform(sample))[..., 1]
imp = pd.DataFrame({"feature": FEATURES, "mean_abs_shap": np.abs(sv).mean(0),
                    "corr_value_vs_shap": [np.corrcoef(sample[f].fillna(sample[f].median()), sv[:, i])[0, 1]
                                           if sample[f].nunique() > 1 else 0 for i, f in enumerate(FEATURES)]})
imp = imp.sort_values("mean_abs_shap", ascending=False)
imp.round(4).to_csv(OUT / "shap_importance.csv", index=False)
print(imp.head(15).to_string(index=False))
top = imp.head(12)
fig, ax = plt.subplots(figsize=(8, 4.8))
cols = [ORANGE if c > 0 else BLUE for c in top.corr_value_vs_shap[::-1]]
ax.barh(top.feature[::-1], top.mean_abs_shap[::-1], color=cols, height=0.62)
ax.grid(axis="y", visible=False); ax.set_xlabel("Mean |SHAP value| (impact on churn log-odds)")
title(ax, f"What drives the churn score ({tree_name}, SHAP, 3,000 holdout buyers)",
      "Orange = higher value raises churn risk; blue = higher value lowers it")
save(fig, CH / "p6_04_shap_importance.png")
plt.figure()
shap.summary_plot(sv, sample, max_display=12, show=False, plot_size=(8.5, 5.2), color_bar_label="Feature value")
fig = plt.gcf(); fig.patch.set_facecolor(SURFACE)
plt.title("SHAP beeswarm: each dot is one buyer (right = pushes towards churn)", loc="left", fontsize=11)
save(fig, CH / "p6_05_shap_beeswarm.png")

# ---------------------------------------------------------------- 5. out-of-fold scores & risk tiers
# Class weighting distorts raw scores, so wrap the model in isotonic calibration: tier probabilities then
# mean what they say (a 0.9 score ~ 90% actual churn). Out-of-fold, so no buyer is scored by a model
# that saw their label.
calibrated = CalibratedClassifierCV(models[best], method="isotonic", cv=3)
oof = cross_val_predict(calibrated, X, y, cv=cv, method="predict_proba")[:, 1]
metrics_log["oof_roc_auc_calibrated"] = float(roc_auc_score(y, oof))
metrics_log["oof_brier_calibrated"] = float(np.mean((oof - y) ** 2))
bins = [0, 0.6, 0.8, 0.9, 1.0001]
tier_names = ["Low (<0.60)", "Medium (0.60-0.80)", "High (0.80-0.90)", "Very high (>=0.90)"]
scored = u[["user_id", "n_orders", "total_spend", "recency_days", "churned", "future_spend"]].assign(
    churn_score=oof.round(4), risk_tier=pd.cut(oof, bins=bins, labels=tier_names, right=False))
scored.to_csv(OUT / "oof_churn_scores_oct_dec_cohort.csv", index=False)
tiers = scored.groupby("risk_tier", observed=True).agg(
    buyers=("user_id", "count"), avg_score=("churn_score", "mean"), actual_churn=("churned", "mean"),
    oct_dec_spend=("total_spend", "sum"), jan_feb_spend=("future_spend", "sum")).reset_index()
tiers["buyer_share"] = tiers.buyers / tiers.buyers.sum()
tiers["jan_feb_spend_share"] = tiers.jan_feb_spend / tiers.jan_feb_spend.sum()
tiers.round(4).to_csv(OUT / "risk_tiers.csv", index=False)
print(tiers.round(4).to_string(index=False))
fig, ax = plt.subplots(figsize=(8.5, 3.8))
bars = ax.bar(tiers.risk_tier.astype(str), 100 * tiers.actual_churn, color=["#86b6ef", "#3987e5", "#256abf", "#0d366b"], width=0.6)
for b, (_, r) in zip(bars, tiers.iterrows()):
    ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1.5, f"actual {100*r.actual_churn:.1f}%\npredicted {100*r.avg_score:.1f}%\n{r.buyers:,} buyers",
            ha="center", fontsize=8.5, color=INK)
ax.set_ylim(0, 125); ax.grid(axis="x", visible=False); ax.set_ylabel("Actual churn in Jan-Feb (%)")
title(ax, "Risk tiers from calibrated out-of-fold churn probabilities",
      "Actual churn in each tier matches its predicted probability band")
save(fig, CH / "p6_06_risk_tiers.png")

# ---------------------------------------------------------------- 6. deployment model (orders-only) and current scoring
con = duckdb.connect()
con.sql(f"CREATE VIEW orders AS SELECT * FROM read_csv_auto('{DATA / 'orders.csv'}')")


def order_features(start, end):
    """RFM-style features from orders in [start, end), measured at `end`."""
    return con.sql(f"""
        WITH o AS (SELECT *, LAG(order_ts) OVER (PARTITION BY user_id ORDER BY order_ts) AS prev
                   FROM orders WHERE order_ts >= '{start}' AND order_ts < '{end}')
        SELECT user_id,
               DATE_DIFF('second', MAX(order_ts), TIMESTAMP '{end}') / 86400.0 AS recency_days,
               DATE_DIFF('second', MIN(order_ts), TIMESTAMP '{end}') / 86400.0 AS tenure_days,
               COUNT(*) AS n_orders, SUM(order_value) AS total_spend, AVG(order_value) AS aov,
               MAX(order_value) AS max_order_value, SUM(items) AS total_items, AVG(items) AS avg_items,
               AVG(distinct_brands) AS avg_brands_per_order,
               COALESCE(AVG(DATE_DIFF('second', prev, order_ts) / 86400.0), -1) AS avg_gap_days,
               SUM(CASE WHEN order_ts >= TIMESTAMP '{end}' - INTERVAL 31 DAY THEN 1 ELSE 0 END) AS orders_last_31d
        FROM o GROUP BY user_id
        ORDER BY user_id""").df()   # fixed row order: CV folds and calibration depend on it


ORDER_FEATS = ["recency_days", "tenure_days", "n_orders", "total_spend", "aov", "max_order_value", "total_items",
               "avg_items", "avg_brands_per_order", "avg_gap_days", "orders_last_31d"]
train_o = order_features("2019-10-01", "2020-01-01").merge(u[["user_id", "churned"]], on="user_id")
assert len(train_o) == len(u)
dep = XGBClassifier(n_estimators=400, max_depth=4, learning_rate=0.04, subsample=0.8, colsample_bytree=0.8,
                    min_child_weight=5, scale_pos_weight=neg_pos, eval_metric="logloss", n_jobs=4, random_state=SEED)
dep_cv = cross_validate(dep, train_o[ORDER_FEATS], train_o.churned, cv=cv, scoring="roc_auc")
metrics_log["deployment_model_cv_roc_auc_mean"] = float(dep_cv["test_score"].mean())
metrics_log["deployment_model_cv_roc_auc_std"] = float(dep_cv["test_score"].std())
dep_cal = CalibratedClassifierCV(dep, method="isotonic", cv=5).fit(train_o[ORDER_FEATS], train_o.churned)
current = order_features("2019-12-01", "2020-03-01")       # same 3-month window length, ending 29 Feb 2020
current["churn_score_mar_apr"] = dep_cal.predict_proba(current[ORDER_FEATS])[:, 1].round(4)
current["risk_tier"] = pd.cut(current.churn_score_mar_apr, bins=bins, labels=tier_names, right=False)
current.round(2).to_csv(OUT / "current_buyers_churn_scores_mar_apr.csv", index=False)
ct = current.groupby("risk_tier", observed=True).agg(buyers=("user_id", "count"),
                                                     avg_score=("churn_score_mar_apr", "mean"),
                                                     dec_feb_spend=("total_spend", "sum")).reset_index()
ct.round(4).to_csv(OUT / "current_risk_tiers_mar_apr.csv", index=False)
metrics_log["current_buyers_scored"] = int(len(current))
metrics_log["current_expected_churners"] = float(current.churn_score_mar_apr.sum())
print("\ncurrent buyers (Dec-Feb) scored:", len(current)); print(ct.round(4).to_string(index=False))
print(f"deployment model CV ROC-AUC {dep_cv['test_score'].mean():.4f} ± {dep_cv['test_score'].std():.4f}")
json.dump(metrics_log, open(OUT / "metrics_summary.json", "w"), indent=2)
print(json.dumps(metrics_log, indent=2))
