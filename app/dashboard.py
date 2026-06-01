from __future__ import annotations

import json
from html import escape
from typing import Any


def money(value: Any) -> str:
    if value in (None, "", 0):
        return "-"
    return f"${float(value):,.0f}"


def percent(value: Any) -> str:
    return f"{float(value or 0):.0%}"


def title(value: Any) -> str:
    return escape(str(value or "unclassified").replace("_", " ").title())


def duration_fmt(seconds: Any) -> str:
    if seconds in (None, "", 0):
        return "-"
    s = int(float(seconds))
    if s < 60:
        return f"{s}s"
    return f"{s // 60}m {s % 60}s"


def bar_list(items: list[dict[str, Any]], total: int, color: str = "var(--blue)") -> str:
    if not items:
        return '<p class="empty">No data yet.</p>'
    rows = []
    for item in items:
        count = int(item.get("count") or 0)
        width = 0 if total == 0 else max(8, round((count / total) * 100))
        rows.append(
            f'<div class="bar-row">'
            f'<div class="bar-label"><span>{title(item.get("name"))}</span><strong>{count}</strong></div>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{width}%;background:{color}"></div></div>'
            f'</div>'
        )
    return "\n".join(rows)


def funnel_section(metrics: dict[str, Any]) -> str:
    stages = [
        ("Total Calls", metrics["total_calls"]),
        ("Carrier Verified", metrics["eligible_calls"]),
        ("Load Matched", metrics["load_matched_calls"]),
        ("Negotiated", metrics["negotiated_calls"]),
        ("Booked", metrics["booked_calls"]),
    ]
    peak = max((s[1] for s in stages), default=1) or 1
    rows = []
    for label, count in stages:
        width = max(12, round((count / peak) * 100))
        rows.append(
            f'<div class="funnel-row">'
            f'<div class="funnel-label">{label}</div>'
            f'<div class="funnel-bar-track"><div class="funnel-bar" style="width:{width}%">{count}</div></div>'
            f'</div>'
        )
    return "\n".join(rows)


def render_dashboard(metrics: dict[str, Any]) -> str:
    recent_rows = []
    for row in metrics["recent_calls"]:
        has_data = any(row.get(k) for k in ("carrier_name", "mc_number", "reference_number", "origin"))
        row_cls = "" if has_data else ' class="dim-row"'
        recent_rows.append(
            f'<tr{row_cls}>'
            f'<td>{escape(str(row.get("carrier_name") or "-"))}</td>'
            f'<td>{escape(str(row.get("mc_number") or "-"))}</td>'
            f'<td>{escape(str(row.get("reference_number") or "-"))}</td>'
            f'<td>{escape(str(row.get("origin") or "-"))} &rarr; {escape(str(row.get("destination") or "-"))}</td>'
            f'<td>{money(row.get("loadboard_rate"))}</td>'
            f'<td>{money(row.get("final_rate"))}</td>'
            f'<td>{escape(str(row.get("negotiation_rounds") or "-"))}</td>'
            f'<td><span class="pill">{title(row.get("call_outcome"))}</span></td>'
            f'<td>{title(row.get("carrier_sentiment"))}</td>'
            f'<td>{duration_fmt(row.get("duration_seconds"))}</td>'
            f'</tr>'
        )

    recent_table = "\n".join(recent_rows) or '<tr><td colspan="10" class="empty">No calls logged yet.</td></tr>'
    avg_rounds = "-" if metrics["avg_rounds"] is None else f"{float(metrics['avg_rounds']):.1f}"
    avg_spread = money(metrics["avg_rate_spread"]) if metrics["avg_rate_spread"] is not None else "-"
    avg_dur = duration_fmt(metrics["avg_duration"])
    offer_total = sum(int(item.get("count") or 0) for item in metrics["offer_decisions"])

    # Group negotiation history by call_id
    negotiations_by_call: dict[str, list[dict[str, Any]]] = {}
    for ev in metrics.get("negotiation_history", []):
        cid = ev.get("call_id") or "unknown"
        negotiations_by_call.setdefault(cid, []).append(ev)

    negotiation_cards = []
    for call_id, rounds in list(negotiations_by_call.items())[:8]:
        first = rounds[0]
        carrier = escape(str(first.get("carrier_name") or "Unknown carrier"))
        ref = escape(str(first.get("reference_number") or "-"))
        listed = money(first.get("loadboard_rate"))

        steps_html = []
        for r in sorted(rounds, key=lambda x: int(x.get("negotiation_round") or 0)):
            rnd = r.get("negotiation_round", "?")
            offer = money(r.get("offer_rate"))
            decision = escape(str(r.get("decision") or "-"))
            counter = money(r.get("counter_rate"))
            accepted = money(r.get("accepted_rate"))

            decision_color = {
                "accept": "var(--green)",
                "counter": "var(--blue)",
                "reject": "#dc2626",
            }.get(decision.lower(), "var(--muted)")

            if decision.lower() == "accept":
                result_text = f"Accepted at {accepted}"
            elif decision.lower() == "counter":
                result_text = f"Countered {counter}"
            else:
                result_text = "Rejected"

            steps_html.append(
                f'<div class="neg-step">'
                f'<div class="neg-round">R{rnd}</div>'
                f'<div class="neg-detail">'
                f'<span>Carrier offered {offer}</span>'
                f'<span class="neg-decision" style="color:{decision_color}">&rarr; {result_text}</span>'
                f'</div></div>'
            )

        negotiation_cards.append(
            f'<div class="neg-card">'
            f'<div class="neg-header"><strong>{carrier}</strong><span class="neg-meta">Ref {ref} &middot; Listed {listed}</span></div>'
            f'{"".join(steps_html)}'
            f'</div>'
        )

    negotiation_section = "\n".join(negotiation_cards) if negotiation_cards else '<p class="empty">No negotiations recorded yet.</p>'

    chart_labels = json.dumps([d["day"] for d in metrics["calls_per_day"]])
    chart_data = json.dumps([d["count"] for d in metrics["calls_per_day"]])

    filter_days = metrics.get("filter_days")
    active = {None: "all", 7: "7", 30: "30"}

    def btn_cls(key):
        return "filter-btn active" if active.get(filter_days, "") == key else "filter-btn"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Inbound Carrier Sales Dashboard</title>
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📞</text></svg>">
  <style>
    :root {{
      --bg: #f6f7f9;
      --panel: #ffffff;
      --ink: #17202a;
      --muted: #667085;
      --line: #d8dde6;
      --green: #1f7a4d;
      --green-light: #d1fae5;
      --blue: #2563a6;
      --blue-light: #dbeafe;
      --amber: #a6651f;
      --amber-light: #fef3c7;
      --purple: #7c3aed;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; background:var(--bg); color:var(--ink); font-family:Inter,Arial,Helvetica,sans-serif; line-height:1.45; }}
    header {{ background:#111827; color:#fff; padding:24px 32px; border-bottom:4px solid var(--green); display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; }}
    header h1 {{ margin:0; font-size:24px; }}
    header p {{ margin:4px 0 0; color:#cbd5e1; font-size:14px; }}
    .header-left {{ flex:1; }}
    .filter-bar {{ display:flex; gap:6px; }}
    .filter-btn {{ padding:6px 14px; border-radius:6px; border:1px solid rgba(255,255,255,0.2); background:transparent; color:#cbd5e1; font-size:13px; cursor:pointer; text-decoration:none; }}
    .filter-btn.active {{ background:var(--green); color:#fff; border-color:var(--green); }}
    .filter-btn:hover {{ border-color:#fff; color:#fff; }}
    main {{ max-width:1280px; margin:0 auto; padding:24px 20px 44px; }}
    .kpis {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(170px, 1fr)); gap:12px; margin-bottom:20px; }}
    .kpi,.panel {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; box-shadow:0 1px 2px rgba(16,24,40,0.05); }}
    .kpi {{ padding:16px; }}
    .kpi span {{ color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:0.3px; }}
    .kpi strong {{ display:block; font-size:28px; margin-top:6px; }}
    .kpi small {{ color:var(--muted); font-size:12px; }}
    .kpi.highlight {{ border-left:4px solid var(--green); }}
    .grid {{ display:grid; grid-template-columns:repeat(2, 1fr); gap:16px; margin-bottom:18px; }}
    .grid-3 {{ display:grid; grid-template-columns:repeat(3, 1fr); gap:16px; margin-bottom:18px; }}
    .panel {{ padding:18px; }}
    .panel h2 {{ margin:0 0 14px; font-size:16px; }}
    .bar-row {{ margin:10px 0; }}
    .bar-label {{ display:flex; justify-content:space-between; gap:10px; font-size:13px; margin-bottom:4px; }}
    .bar-track {{ height:8px; background:#eef1f5; border-radius:999px; overflow:hidden; }}
    .bar-fill {{ height:100%; border-radius:999px; }}
    .funnel-row {{ display:flex; align-items:center; gap:12px; margin:8px 0; }}
    .funnel-label {{ width:120px; font-size:13px; color:var(--muted); text-align:right; flex-shrink:0; }}
    .funnel-bar-track {{ flex:1; height:28px; background:#f1f5f9; border-radius:6px; overflow:hidden; }}
    .funnel-bar {{ height:100%; background:linear-gradient(90deg, var(--green), var(--blue)); color:#fff; font-size:13px; font-weight:600; display:flex; align-items:center; padding-left:10px; border-radius:6px; min-width:40px; }}
    table {{ width:100%; border-collapse:collapse; font-size:13px; }}
    th,td {{ padding:10px 8px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }}
    th {{ color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:0.3px; }}
    .pill {{ display:inline-block; border:1px solid var(--line); border-radius:999px; padding:2px 8px; background:#f8fafc; white-space:nowrap; font-size:12px; }}
    .empty {{ color:var(--muted); }}
    .dim-row {{ opacity:0.45; }}
    .neg-card {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:14px 16px; margin-bottom:12px; }}
    .neg-header {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; flex-wrap:wrap; gap:6px; }}
    .neg-header strong {{ font-size:14px; }}
    .neg-meta {{ color:var(--muted); font-size:12px; }}
    .neg-step {{ display:flex; align-items:center; gap:10px; padding:6px 0; border-top:1px solid var(--line); }}
    .neg-round {{ width:30px; height:30px; border-radius:50%; background:var(--blue-light); color:var(--blue); font-size:12px; font-weight:700; display:flex; align-items:center; justify-content:center; flex-shrink:0; }}
    .neg-detail {{ display:flex; gap:8px; font-size:13px; flex-wrap:wrap; }}
    .neg-decision {{ font-weight:600; }}
    footer {{ color:var(--muted); font-size:12px; margin-top:18px; display:flex; justify-content:space-between; }}
    @media (max-width:980px) {{
      .kpis {{ grid-template-columns:repeat(2,1fr); }}
      .grid,.grid-3 {{ grid-template-columns:1fr; }}
      table {{ display:block; overflow-x:auto; white-space:nowrap; }}
      .funnel-label {{ width:80px; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="header-left">
      <h1>Inbound Carrier Sales</h1>
      <p>Live metrics from HappyRobot voice AI &mdash; call outcomes, negotiation, and revenue.</p>
    </div>
    <nav class="filter-bar">
      <a class="{btn_cls('7')}" href="?days=7">7 days</a>
      <a class="{btn_cls('30')}" href="?days=30">30 days</a>
      <a class="{btn_cls('all')}" href="/dashboard">All time</a>
    </nav>
  </header>
  <main>
    <!-- Revenue + Core KPIs -->
    <section class="kpis" aria-label="Key metrics">
      <article class="kpi highlight"><span>Booked Revenue</span><strong>{money(metrics["total_booked_revenue"])}</strong><small>Total final rates (booked)</small></article>
      <article class="kpi highlight"><span>Negotiation Savings</span><strong>{money(metrics["negotiation_savings"])}</strong><small>vs. carrier first offers</small></article>
      <article class="kpi"><span>Total Calls</span><strong>{metrics["total_calls"]}</strong><small>{metrics["unique_carriers"]} unique carriers</small></article>
      <article class="kpi"><span>Booked</span><strong>{metrics["booked_calls"]}</strong><small>{percent(metrics["acceptance_rate"])} conversion</small></article>
      <article class="kpi"><span>Avg Rounds</span><strong>{avg_rounds}</strong><small>Negotiation depth</small></article>
      <article class="kpi"><span>Avg Duration</span><strong>{avg_dur}</strong><small>Per call</small></article>
      <article class="kpi"><span>Rate Spread</span><strong>{avg_spread}</strong><small>Loadboard vs final</small></article>
    </section>

    <!-- Funnel + Trend -->
    <section class="grid">
      <article class="panel">
        <h2>Conversion Funnel</h2>
        {funnel_section(metrics)}
      </article>
      <article class="panel">
        <h2>Call Volume (14 days)</h2>
        <div style="position:relative;height:180px"><canvas id="trendChart"></canvas></div>
      </article>
    </section>

    <!-- Breakdowns -->
    <section class="grid-3" aria-label="Breakdowns">
      <article class="panel"><h2>Call Outcomes</h2>{bar_list(metrics["outcome_counts"], metrics["total_calls"], "var(--blue)")}</article>
      <article class="panel"><h2>Carrier Sentiment</h2>{bar_list(metrics["sentiment_counts"], metrics["total_calls"], "var(--green)")}</article>
      <article class="panel"><h2>Decline Reasons</h2>{bar_list(metrics["decline_reasons"], metrics["total_calls"], "var(--amber)")}</article>
    </section>

    <!-- Offer Decisions (if data exists) -->
    {"" if not metrics["offer_decisions"] else f'''
    <section class="grid-3">
      <article class="panel"><h2>Offer Decisions (API)</h2>{bar_list(metrics["offer_decisions"], offer_total, "var(--purple)")}</article>
    </section>
    '''}

    <!-- Negotiation History -->
    <section class="panel">
      <h2>Negotiation History</h2>
      {negotiation_section}
    </section>

    <!-- Recent Calls -->
    <section class="panel">
      <h2>Recent Calls</h2>
      <table>
        <thead>
          <tr>
            <th>Carrier</th><th>MC</th><th>Load</th><th>Lane</th><th>Listed</th><th>Final</th><th>Rounds</th><th>Outcome</th><th>Sentiment</th><th>Duration</th>
          </tr>
        </thead>
        <tbody>{recent_table}</tbody>
      </table>
    </section>
    <footer>
      <span>Auto-refreshes every 30s.</span>
      <span id="genTime"></span>
    </footer>
  </main>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
  <script>
    const labels = {chart_labels};
    const data = {chart_data};
    if (labels.length > 0) {{
      const ctx = document.getElementById('trendChart').getContext('2d');
      new Chart(ctx, {{
        type: 'bar',
        data: {{
          labels: labels.map(d => {{ const p = d.split('-'); return p[1]+'/'+p[2]; }}),
          datasets: [{{ label: 'Calls', data: data, backgroundColor: '#2563a6', borderRadius: 4 }}]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{ legend: {{ display: false }} }},
          scales: {{
            y: {{ beginAtZero: true, ticks: {{ stepSize: 1 }} }},
            x: {{ grid: {{ display: false }} }}
          }}
        }}
      }});
    }} else {{
      document.getElementById('trendChart').parentElement.innerHTML += '<p class="empty">No trend data yet.</p>';
    }}
    const genAt = "{metrics.get('generated_at', '')}";
    if (genAt) {{
      const d = new Date(genAt);
      document.getElementById('genTime').textContent = 'Updated ' + d.toLocaleString();
    }}
    setTimeout(() => location.reload(), 30000);
  </script>
</body>
</html>"""
