"""Phase 9: size the expected impact of each recommendation from project results only.

Every input is a Phase 1-8 result or a stated ASSUMPTION (Phase 7 [K134] unless noted). Deterministic.
Output: outputs/phase9/impacts.json and outputs/phase9/second_order_breakeven.csv
"""
import json
import numpy as np
import pandas as pd

from config import DATA, OUTPUTS

OUT = OUTPUTS / "phase9"
OUT.mkdir(parents=True, exist_ok=True)

MARGIN, DISCOUNT, CONTACT = 0.40, 0.10, 0.50          # Phase 7 ASSUMPTIONS [K134]
AUTOMATED_CONTACT = 0.10                              # ASSUMPTION: automated push/email cost; low end of Phase 7 contact grid
AUTOMATE_SAVE_RATE = 0.025                            # ASSUMPTION: low end of Phase 7 save-rate grid (no-discount nudge)
BASE_REPEAT, MDE, NEW_PER_MONTH = 0.17885198975528915, 0.02, 21189   # [K139], [K140], [K141]
K = {}

orders = pd.read_csv(DATA / "orders.csv", parse_dates=["order_ts"]).sort_values(["user_id", "order_ts", "order_id"])
orders["seq"] = orders.groupby("user_id").cumcount() + 1
v2 = orders.loc[orders.seq == 2, "order_value"].mean()
K["avg_second_order_value"] = v2

# 1. Second-order journey for first-time buyers (H1). Per 1,000 enrolled first-time buyers and per month at scale.
#    Offer arm: every buyer who places a 2nd order gets the 10% discount (incl. those who would anyway).
def second_order_net(uplift, offer, contact):
    repeaters = BASE_REPEAT + uplift
    gain = MARGIN * uplift * v2
    disc = DISCOUNT * v2 * repeaters if offer else 0.0
    return gain - disc - contact                      # net gross profit per enrolled buyer

be_offer = (DISCOUNT * v2 * BASE_REPEAT + CONTACT) / ((MARGIN - DISCOUNT) * v2)
be_msg = CONTACT / (MARGIN * v2)
be_msg_auto = AUTOMATED_CONTACT / (MARGIN * v2)
K.update(be_uplift_offer=be_offer, be_uplift_message=be_msg, be_uplift_message_automated=be_msg_auto,
         extra_repeat_buyers_per_month_at_mde=NEW_PER_MONTH * MDE,
         msg_auto_net_per_month_at_mde=NEW_PER_MONTH * second_order_net(MDE, False, AUTOMATED_CONTACT),
         offer_net_per_month_at_mde=NEW_PER_MONTH * second_order_net(MDE, True, CONTACT))
pd.DataFrame([{"uplift_pp": u * 100,
               "message_only_auto_net_per_month": NEW_PER_MONTH * second_order_net(u, False, AUTOMATED_CONTACT),
               "message_only_net_per_month": NEW_PER_MONTH * second_order_net(u, False, CONTACT),
               "offer_10pct_net_per_month": NEW_PER_MONTH * second_order_net(u, True, CONTACT)}
              for u in (0.01, 0.02, 0.03, 0.05, 0.10, 0.15)]).round(2).to_csv(OUT / "second_order_breakeven.csv", index=False)

# A/B with an added message-only arm: same MDE / alpha / power as Phase 7, so the same n per arm [K140]
n_arm = json.load(open(OUTPUTS / "phase7/phase7_numbers.json"))["ab_n_per_arm"]
K.update(ab3_n_per_arm=n_arm, ab3_total=3 * n_arm, ab3_enrol_weeks=int(np.ceil(3 * n_arm / NEW_PER_MONTH * 52 / 12)))

# 2. Save-now win-back (Phase 7 result, read back)
camp = pd.read_csv(OUTPUTS / "phase7/campaign_strategies.csv", index_col=0)
sn, hv = camp.iloc[0], camp.loc["All high-value buyers (top 30% CLV)"]
K.update(save_now_net=sn.net_profit, save_now_inc_rev=sn.incremental_revenue,
         discount_avoided_by_not_discounting_protect=hv.discount_cost - sn.discount_cost)

# 3. Silence trigger: no-discount automated nudge to the Automate quadrant
vr = pd.read_csv(OUTPUTS / "phase7/current_buyers_value_risk.csv")
au = vr[vr.quadrant.str.startswith("Automate")]
inc = AUTOMATE_SAVE_RATE * (au.churn_score_mar_apr * au.value_if_retained_60d).sum()
cost = AUTOMATED_CONTACT * len(au)
K.update(automate_buyers=len(au), automate_inc_rev=inc, automate_cost=cost, automate_net=MARGIN * inc - cost,
         automate_roi=(MARGIN * inc - cost) / cost,
         automate_be_save_rate=cost / (MARGIN * (au.churn_score_mar_apr * au.value_if_retained_60d).sum()))

# 4. Cart recovery: value of 1 pp lower session cart abandonment (Oct-Feb, 5 months)
ss = pd.read_csv(DATA / "session_summary.csv")
cart_sessions = ss.sessions_with_cart.sum()
aov = orders.order_value.mean()
K.update(cart_sessions=int(cart_sessions), orders_per_pp_abandonment=cart_sessions * 0.01,
         revenue_per_pp_abandonment_5m=cart_sessions * 0.01 * aov,
         revenue_per_pp_abandonment_per_month=cart_sessions * 0.01 * aov / 5,
         gap_to_baymard_pp=100 * ss.abandoned_cart_sessions.sum() / cart_sessions - 70.22)

# 5. Holiday cohort: extra repeat buyers if Dec-acquired matched Nov-acquired 60-day repeat rate (H3)
h3 = pd.read_csv(OUTPUTS / "phase5/h3_no_repeat_60d.csv").set_index("acq")
gap = (h3.loc["Dec", "no_repeat_pct"] - h3.loc["Nov", "no_repeat_pct"]) / 100
K.update(dec_gap_pp=100 * gap, dec_extra_repeaters=gap * h3.loc["Dec", "n"],
         dec_extra_revenue_at_v2=gap * h3.loc["Dec", "n"] * v2)

json.dump(K, open(OUT / "impacts.json", "w"), indent=2, default=float)
for k, v in K.items():
    print(f"{k:45s} {v:,.4f}" if isinstance(v, float) else f"{k:45s} {v}")
