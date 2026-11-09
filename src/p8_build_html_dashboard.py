"""Phase 8c: inject dashboard_data.json into the HTML template.

Writes dashboard/index.html and docs/index.html (the GitHub Pages copy), a standalone page
(Chart.js loads from cdnjs; everything else is inline).
Run p8_build_dashboard_data.py first.
"""
from config import DASHBOARD, ROOT

HTML = DASHBOARD
body = (HTML / "dashboard_template.html").read_text()
data = (HTML / "dashboard_data.json").read_text()
assert "/*__DATA__*/null" in body
body = body.replace("/*__DATA__*/null", data.replace("</", "<\\/"))

page = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        + body.split("</style>", 1)[0] + "</style>\n</head>\n<body>\n" + body.split("</style>", 1)[1] + "\n</body>\n</html>\n")
(HTML / "index.html").write_text(page)
# GitHub Pages serves docs/ (Settings > Pages > main /docs)
(ROOT / "docs").mkdir(exist_ok=True)
(ROOT / "docs" / "index.html").write_text(page)
(ROOT / "docs" / ".nojekyll").touch()
print("index.html", round(len(page) / 1e3), "KB")
