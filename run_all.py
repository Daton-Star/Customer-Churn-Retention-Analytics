"""Run the full analysis pipeline in order (Phase 1 -> Phase 10).

Reads the Stage 1 tables in stage1_kaggle/data and regenerates outputs/, images/ and dashboard/.
Stops at the first failing step. Phase 6 (model CV) dominates the runtime (about 4-12 minutes depending on the machine).
Usage: python run_all.py
"""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

STEPS = [
    ("Phase 1  baseline sizing", ["p1_baseline.py"]),
    ("Phase 2  SQL validation + business queries", ["p2_run_sql.py", "00_validation.sql", "01_business_queries.sql"]),
    ("Phase 3  churn definition", ["p3_churn_definition.py"]),
    ("Phase 4  EDA & funnel", ["p4_eda.py"]),
    ("Phase 5  hypothesis tests", ["p5_hypothesis_tests.py"]),
    ("Phase 6  churn model", ["p6_churn_model.py"]),
    ("Phase 7  CLV & retention economics", ["p7_clv_economics.py"]),
    ("Phase 8a dashboard data (Power BI CSVs + JSON)", ["p8_build_dashboard_data.py"]),
    ("Phase 8b verify DAX measures", ["p8_verify_measures.py"]),
    ("Phase 8c HTML dashboard", ["p8_build_html_dashboard.py"]),
    ("Phase 8d Excel workbook", ["p8_build_excel_workbook.py"]),
    ("Phase 9  recommendation impacts", ["p9_recommendation_impacts.py"]),
    ("Phase 9  impact-effort chart", ["p9_impact_effort_chart.py"]),
    ("Phase 10 LinkedIn carousel PDF", ["p10_linkedin_carousel.py"]),
]


def main() -> int:
    timings, t_all = [], time.perf_counter()
    for name, (script, *args) in STEPS:
        print(f"\n{'=' * 72}\n>> {name}: src/{script} {' '.join(args)}\n{'=' * 72}", flush=True)
        t0 = time.perf_counter()
        rc = subprocess.run([sys.executable, str(SRC / script), *args], cwd=ROOT).returncode
        dt = time.perf_counter() - t0
        timings.append((name, dt, rc))
        if rc != 0:
            print(f"\nFAILED: {name} (exit code {rc}) after {dt:.1f}s. Stopping.", flush=True)
            break
    print(f"\n{'=' * 72}\nTimings")
    for name, dt, rc in timings:
        print(f"  {'ok  ' if rc == 0 else 'FAIL'} {dt:8.1f}s  {name}")
    print(f"  total {time.perf_counter() - t_all:.1f}s")
    return 0 if all(rc == 0 for _, _, rc in timings) and len(timings) == len(STEPS) else 1


if __name__ == "__main__":
    sys.exit(main())
