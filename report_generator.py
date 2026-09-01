#!/usr/bin/env python3
"""
Turns the structured output of audit_engine.run_audit() into the polished
HTML report used throughout this project - fully automatic, no hand-written
findings required.
"""
from datetime import date

CSS = """
:root{
  --surface-1:#fcfcfb; --page:#f9f9f7;
  --text-primary:#0b0b0b; --text-secondary:#52514e; --text-muted:#898781;
  --border:rgba(11,11,11,0.10); --gridline:#e1e0d9;
  --good:#0ca30c; --good-bg:#eaf7ea;
  --warning:#c98500; --warning-bg:#fff6e3;
  --critical:#d03b3b; --critical-bg:#fceaea;
  --blue:#2a78d6; --blue-bg:#eaf1fb;
}
*{box-sizing:border-box;}
body{margin:0; background:var(--page); color:var(--text-primary);
  font-family:system-ui,-apple-system,"Segoe UI",sans-serif; line-height:1.5;}
.wrap{max-width:840px;margin:0 auto;padding:32px 20px 80px;}
.card{background:var(--surface-1); border:1px solid var(--border); border-radius:12px; padding:28px; margin-bottom:20px;}
header.card{display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:16px;}
.brand{font-size:13px; color:var(--text-muted); letter-spacing:.02em; text-transform:uppercase; font-weight:600;}
h1{font-size:22px; margin:4px 0 6px;}
.meta{color:var(--text-secondary); font-size:14px;}
.scorewrap{display:flex; align-items:center; gap:24px; flex-wrap:wrap;}
.scoretile{text-align:center; min-width:140px;}
.scoreval{font-size:56px; font-weight:600; line-height:1;}
.scorelabel{font-size:13px; color:var(--text-secondary); margin-top:6px;}
.status-pill{display:inline-flex; align-items:center; gap:6px; padding:5px 12px; border-radius:999px; font-size:13px; font-weight:600; margin-top:10px;}
.meter-track{height:10px; border-radius:999px; background:var(--gridline); overflow:hidden; flex:1; min-width:180px;}
.meter-fill{height:100%; border-radius:999px;}
.score-summary{flex:1; min-width:220px; color:var(--text-secondary); font-size:14px;}
h2{font-size:16px; margin:0 0 14px;}
.section-count{color:var(--text-muted); font-weight:400; font-size:13px;}
.finding{display:flex; gap:12px; padding:14px 0; border-top:1px solid var(--gridline);}
.finding:first-child{border-top:none; padding-top:0;}
.icon{flex:0 0 22px; height:22px; width:22px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:13px; font-weight:700; color:#fff; margin-top:2px;}
.icon.critical{background:var(--critical);}
.icon.warning{background:var(--warning);}
.icon.good{background:var(--good);}
.finding-body strong{display:block; font-size:14.5px; margin-bottom:3px;}
.finding-body p{margin:0; font-size:13.5px; color:var(--text-secondary);}
.finding-body .fix{margin-top:6px; font-size:13px; color:var(--text-primary); background:var(--blue-bg); padding:8px 10px; border-radius:6px;}
.finding-body .fix b{color:var(--blue);}
.critical-card{border-color:rgba(208,59,59,0.25);}
.warning-card{border-color:rgba(201,133,0,0.25);}
.good-card{border-color:rgba(12,163,12,0.2);}
.cta{background:var(--text-primary); color:#fff; border-radius:12px; padding:28px; text-align:center;}
.cta h2{color:#fff;}
.cta p{color:#d8d7d2; font-size:14px; max-width:520px; margin:8px auto 18px;}
.cta .price{font-size:28px; font-weight:600; margin-bottom:4px;}
.cta .btn{display:inline-block; background:#fff; color:#0b0b0b; padding:10px 22px; border-radius:8px; font-weight:600; font-size:14px; text-decoration:none; margin-top:6px;}
footer{text-align:center; color:var(--text-muted); font-size:12px; margin-top:24px;}
form.audit-form{display:flex; flex-direction:column; gap:12px; max-width:440px;}
form.audit-form input{padding:10px 12px; border:1px solid var(--border); border-radius:8px; font-size:14px; font-family:inherit;}
form.audit-form button{padding:11px 16px; border:none; border-radius:8px; background:var(--text-primary); color:#fff; font-weight:600; font-size:14px; cursor:pointer;}
"""


def _status(score):
    if score >= 80:
        return "var(--good)", "var(--good-bg)", "On Track"
    if score >= 60:
        return "var(--warning)", "var(--warning-bg)", "Needs Improvement"
    return "var(--critical)", "var(--critical-bg)", "Action Needed"


def _finding(icon_cls, symbol, label, detail, fix=None):
    fix_html = f'<div class="fix"><b>Fix:</b> {fix}</div>' if fix else ""
    return f"""
    <div class="finding">
      <div class="icon {icon_cls}">{symbol}</div>
      <div class="finding-body">
        <strong>{label}</strong>
        <p>{detail}</p>
        {fix_html}
      </div>
    </div>"""


def render_report(result, prepared_by="[Your Company Name]", price="$49"):
    """result is the dict returned by audit_engine.run_audit()."""
    business = result.get("business_name") or result.get("url")
    url = result.get("url")
    city = result.get("city") or ""
    score = result.get("score", 0)
    checks = result.get("checks", [])

    color, bg, label = _status(score)

    failed = [c for c in checks if not c["passed"]]
    passed = [c for c in checks if c["passed"]]
    # Critical = failed checks worth 10+ points; Warning = failed checks worth less
    critical = [c for c in failed if c["weight"] >= 10]
    warning = [c for c in failed if c["weight"] < 10]

    def render_group(group, icon_cls, symbol):
        return "".join(
            _finding(icon_cls, symbol, c["label"], c["detail"], c.get("fix"))
            for c in group
        )

    critical_html = render_group(critical, "critical", "!")
    warning_html = render_group(warning, "warning", "▲")
    good_html = render_group(passed, "good", "✓")

    priority_card_class = "critical-card" if critical else "warning-card"
    priority_section = ""
    if critical or warning:
        priority_section = f"""
  <div class="card {priority_card_class}">
    <h2>Priority Issues <span class="section-count">(fix these first)</span></h2>
    {critical_html}{warning_html}
  </div>"""

    good_section = ""
    if passed:
        good_section = f"""
  <div class="card good-card">
    <h2>What's Already Working</h2>
    {good_html}
  </div>"""

    today = date.today().strftime("%b %d, %Y")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Local SEO Audit — {business}</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <header class="card">
    <div>
      <div class="brand">Free Local SEO Snapshot</div>
      <h1>{business}</h1>
      <div class="meta">{url} &middot; {city} &middot; Prepared {today}</div>
    </div>
    <div class="meta" style="text-align:right;">
      Prepared by<br><strong style="color:var(--text-primary);">{prepared_by}</strong>
    </div>
  </header>

  <div class="card scorewrap">
    <div class="scoretile">
      <div class="scoreval" style="color:{color};">{score}</div>
      <div class="scorelabel">out of 100</div>
      <div class="status-pill" style="background:{bg}; color:{color};">&#9679; {label}</div>
    </div>
    <div style="flex:1; min-width:220px;">
      <div class="meter-track"><div class="meter-fill" style="width:{score}%; background:{color};"></div></div>
      <div class="score-summary" style="margin-top:10px;">
        {len(critical)} critical issue(s) and {len(warning)} warning(s) found out of
        {len(checks)} checks — see the breakdown below.
      </div>
    </div>
  </div>
  {priority_section}
  {good_section}

  <div class="cta">
    <h2>Want ongoing monitoring &amp; automatic fixes?</h2>
    <p>This is a free automated snapshot. Ongoing monitoring alerts you the moment
    something breaks and tracks your ranking over time.</p>
    <div class="price">{price}<span style="font-size:15px;font-weight:400;">/month per location</span></div>
    <a class="btn" href="#">Get Started</a>
  </div>

  <footer>Prepared by {prepared_by} &middot; Automated preview based on the site's
  public HTML — may not reflect every ranking factor.</footer>
</div>
</body>
</html>
"""
