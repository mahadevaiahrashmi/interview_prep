"""Render a PrepPlan as the three downloadable table formats.

  - Markdown (.md)  : paste into GitHub / Notion; courses stacked with <br>.
  - CSV (.csv)      : one row per course, opens cleanly in Excel/Sheets.
  - HTML (.html)    : a styled, standalone page you can open or print to PDF.

These consume `PrepPlan` from `schema.py`, so the schema is the single contract
between model output and the rendered table.
"""
from __future__ import annotations

import csv
import html
import io

from .schema import PrepPlan


def _md_cell(text: str) -> str:
    """Escape a Markdown table cell: pipes and stray newlines break the grid."""
    return text.replace("|", "\\|").replace("\n", " ").strip()


def render_markdown(plan: PrepPlan) -> str:
    lines: list[str] = []
    if plan.role:
        lines.append(f"# Interview prep plan — {plan.role.strip()}")
        lines.append("")
    lines.append("All courses below are free. Degree and years-of-experience "
                 "requirements are intentionally excluded.")
    lines.append("")
    if plan.guidance:
        lines.append(f"> {_md_cell(plan.guidance)}")
        lines.append("")
    lines.append("| # | Requirement | Free courses |")
    lines.append("| - | ----------- | ------------ |")
    for i, row in enumerate(plan.rows, 1):
        course_md = "<br>".join(
            f"[{_md_cell(c.title)}]({c.url})"
            + (f" — {_md_cell(c.platform)}" if c.platform else "")
            for c in row.courses
        ) or "—"
        req_md = _md_cell(row.requirement)
        if row.timebox:
            req_md = f"**{_md_cell(row.timebox)}**<br>{req_md}"
        lines.append(f"| {i} | {req_md} | {course_md} |")
    lines.append("")
    return "\n".join(lines)


def render_csv(plan: PrepPlan) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["#", "Requirement", "Course", "Platform", "URL"])
    for i, row in enumerate(plan.rows, 1):
        # Fold any study window into the requirement text so the CSV column set
        # stays stable (e.g. "[Day 1] Build REST APIs in Python").
        req = f"[{row.timebox}] {row.requirement}" if row.timebox else row.requirement
        if not row.courses:
            writer.writerow([i, req, "", "", ""])
            continue
        for j, c in enumerate(row.courses):
            # Repeat the index/requirement only on the first course of the row,
            # so the spreadsheet reads as grouped blocks.
            writer.writerow([
                i if j == 0 else "",
                req if j == 0 else "",
                c.title, c.platform, c.url,
            ])
    return buf.getvalue()


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Interview prep plan{title_suffix}</title>
<style>
  body {{ font-family: -apple-system, "Segoe UI", Arial, sans-serif; color: #1c2733;
         margin: 32px auto; max-width: 980px; line-height: 1.45; padding: 0 16px; }}
  h1 {{ color: #1f3b5b; font-size: 22px; }}
  p.note {{ color: #555; font-size: 13px; }}
  p.guidance {{ color: #1f3b5b; font-size: 13px; background: #eef3f9;
               border-left: 3px solid #2e5a88; padding: 8px 12px; border-radius: 4px; }}
  span.timebox {{ display: inline-block; font-size: 11px; font-weight: 700;
                 color: #1f3b5b; background: #e6edf6; border-radius: 4px;
                 padding: 1px 7px; margin-bottom: 4px; }}
  table {{ border-collapse: collapse; width: 100%; margin-top: 16px; }}
  th, td {{ border: 1px solid #d9e0ea; padding: 9px 11px; vertical-align: top;
           text-align: left; font-size: 14px; }}
  th {{ background: #1f3b5b; color: #fff; }}
  tr:nth-child(even) td {{ background: #f4f6f9; }}
  td.num {{ text-align: center; color: #555; width: 34px; }}
  ul {{ margin: 0; padding-left: 18px; }}
  li {{ margin-bottom: 4px; }}
  a {{ color: #2e5a88; }}
  .platform {{ color: #555; }}
</style>
</head>
<body>
<h1>Interview prep plan{title_suffix}</h1>
<p class="note">All courses below are free. Degree and years-of-experience
requirements are intentionally excluded.</p>
{guidance}<table>
<thead><tr><th>#</th><th>Requirement</th><th>Free courses</th></tr></thead>
<tbody>
{rows}
</tbody>
</table>
</body>
</html>
"""


def render_html(plan: PrepPlan) -> str:
    suffix = f" — {html.escape(plan.role.strip())}" if plan.role else ""
    guidance = (
        f'<p class="guidance">{html.escape(plan.guidance)}</p>\n' if plan.guidance else ""
    )
    body_rows: list[str] = []
    for i, row in enumerate(plan.rows, 1):
        items = "".join(
            f'<li><a href="{html.escape(c.url, quote=True)}" target="_blank" '
            f'rel="noopener">{html.escape(c.title)}</a>'
            + (f' <span class="platform">— {html.escape(c.platform)}</span>' if c.platform else "")
            + "</li>"
            for c in row.courses
        )
        badge = (
            f'<span class="timebox">{html.escape(row.timebox)}</span><br>'
            if row.timebox else ""
        )
        body_rows.append(
            f'<tr><td class="num">{i}</td>'
            f"<td>{badge}{html.escape(row.requirement)}</td>"
            f"<td><ul>{items}</ul></td></tr>"
        )
    return _HTML_TEMPLATE.format(
        title_suffix=suffix, guidance=guidance, rows="\n".join(body_rows)
    )
