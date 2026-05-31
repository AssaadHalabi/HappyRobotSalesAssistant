from __future__ import annotations

from html import escape
from typing import Any


def money(value: Any) -> str:
    if value in (None, ""):
        return "-"
    return f"${float(value):,.0f}"


def percent(value: Any) -> str:
    return f"{float(value or 0):.0%}"


def title(value: Any) -> str:
    return escape(str(value or "unclassified").replace("_", " ").title())


def bar_list(items: list[dict[str, Any]], total: int) -> str:
    if not items:
        return '<p class="empty">No data yet.</p>'
    rows = []
    for item in items:
        count = int(item.get("count") or 0)
        width = 0 if total == 0 else max(8, round((count / total) * 100))
        rows.append(
            f"""
            <div class="bar-row">
              <div class="bar-label"><span>{title(item.get("name"))}</span><strong>{count}</strong></div>
              <div class="bar-track"><div class="bar-fill" style="width:{width}%"></div></div>
            </div>
            """
        )
    return "\n".join(rows)


def render_dashboard(metrics: dict[str, Any]) -> str:
    recent_rows = []
    for row in metrics["recent_calls"]:
        recent_rows.append(
            f"""
            <tr>
              <td>{escape(str(row.get("carrier_name") or "-"))}</td>
              <td>{escape(str(row.get("mc_number") or "-"))}</td>
              <td>{escape(str(row.get("load_id") or "-"))}</td>
              <td>{escape(str(row.get("origin") or "-"))} to {escape(str(row.get("destination") or "-"))}</td>
              <td>{money(row.get("loadboard_rate"))}</td>
              <td>{money(row.get("final_rate"))}</td>
              <td>{escape(str(row.get("negotiation_rounds") or "-"))}</td>
              <td><span class="pill">{title(row.get("call_outcome"))}</span></td>
              <td>{title(row.get("carrier_sentiment"))}</td>
            </tr>
            """
        )

    recent_table = "\n".join(recent_rows) or '<tr><td colspan="9" class="empty">No calls have been logged yet.</td></tr>'
    avg_rounds = "-" if metrics["avg_rounds"] is None else f"{float(metrics['avg_rounds']):.1f}"
    avg_spread = money(metrics["avg_rate_spread"]) if metrics["avg_rate_spread"] is not None else "-"
    offer_total = sum(int(item.get("count") or 0) for item in metrics["offer_decisions"])

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Inbound Carrier Sales Dashboard</title>
  <style>
    :root {{
      --bg: #f6f7f9;
      --panel: #ffffff;
      --ink: #17202a;
      --muted: #667085;
      --line: #d8dde6;
      --green: #1f7a4d;
      --blue: #2563a6;
      --amber: #a6651f;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Arial, Helvetica, sans-serif;
      line-height: 1.45;
    }}
    header {{
      background: #111827;
      color: #fff;
      padding: 28px 32px;
      border-bottom: 4px solid var(--green);
    }}
    header h1 {{ margin: 0 0 6px; font-size: 28px; letter-spacing: 0; }}
    header p {{ margin: 0; color: #cbd5e1; }}
    main {{ max-width: 1220px; margin: 0 auto; padding: 28px 20px 44px; }}
    .kpis {{
      display: grid;
      grid-template-columns: repeat(5, minmax(150px, 1fr));
      gap: 14px;
      margin-bottom: 18px;
    }}
    .kpi, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05);
    }}
    .kpi {{ padding: 16px; min-height: 112px; }}
    .kpi span {{ color: var(--muted); font-size: 13px; text-transform: uppercase; letter-spacing: 0; }}
    .kpi strong {{ display: block; font-size: 30px; margin-top: 8px; }}
    .kpi small {{ color: var(--muted); }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 18px;
      margin-bottom: 18px;
    }}
    .panel {{ padding: 18px; }}
    .panel h2 {{ margin: 0 0 14px; font-size: 18px; letter-spacing: 0; }}
    .bar-row {{ margin: 12px 0; }}
    .bar-label {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      font-size: 14px;
      margin-bottom: 6px;
    }}
    .bar-track {{ height: 10px; background: #eef1f5; border-radius: 999px; overflow: hidden; }}
    .bar-fill {{ height: 100%; background: var(--blue); }}
    .panel:nth-child(2) .bar-fill {{ background: var(--green); }}
    .panel:nth-child(3) .bar-fill {{ background: var(--amber); }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ padding: 11px 10px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0; }}
    .pill {{
      display: inline-block;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 3px 8px;
      background: #f8fafc;
      white-space: nowrap;
    }}
    .empty {{ color: var(--muted); }}
    footer {{ color: var(--muted); font-size: 13px; margin-top: 18px; }}
    @media (max-width: 980px) {{
      .kpis {{ grid-template-columns: repeat(2, minmax(150px, 1fr)); }}
      .grid {{ grid-template-columns: 1fr; }}
      table {{ display: block; overflow-x: auto; white-space: nowrap; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Inbound Carrier Sales Dashboard</h1>
    <p>Operational metrics from HappyRobot call outcomes, post-call extraction, and negotiation API decisions.</p>
  </header>
  <main>
    <section class="kpis" aria-label="Key metrics">
      <article class="kpi"><span>Total Calls</span><strong>{metrics["total_calls"]}</strong><small>Logged summaries</small></article>
      <article class="kpi"><span>Booked</span><strong>{metrics["booked_calls"]}</strong><small>{percent(metrics["acceptance_rate"])} acceptance</small></article>
      <article class="kpi"><span>Eligible Carriers</span><strong>{metrics["eligible_calls"]}</strong><small>{percent(metrics["eligibility_rate"])} eligible</small></article>
      <article class="kpi"><span>Avg Rounds</span><strong>{avg_rounds}</strong><small>Negotiation depth</small></article>
      <article class="kpi"><span>Avg Rate Spread</span><strong>{avg_spread}</strong><small>Loadboard minus final</small></article>
    </section>
    <section class="grid" aria-label="Breakdowns">
      <article class="panel"><h2>Call Outcomes</h2>{bar_list(metrics["outcome_counts"], metrics["total_calls"])}</article>
      <article class="panel"><h2>Carrier Sentiment</h2>{bar_list(metrics["sentiment_counts"], metrics["total_calls"])}</article>
      <article class="panel"><h2>Offer Decisions</h2>{bar_list(metrics["offer_decisions"], offer_total)}</article>
    </section>
    <section class="panel">
      <h2>Recent Calls</h2>
      <table>
        <thead>
          <tr>
            <th>Carrier</th><th>MC</th><th>Load</th><th>Lane</th><th>Listed</th><th>Final</th><th>Rounds</th><th>Outcome</th><th>Sentiment</th>
          </tr>
        </thead>
        <tbody>{recent_table}</tbody>
      </table>
    </section>
    <footer>Dashboard access is protected with the shared API key.</footer>
  </main>
</body>
</html>"""
