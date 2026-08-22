"""Excel writer with embedded charts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, PieChart, Reference
from openpyxl.styles import Alignment, Font, PatternFill, numbers
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.utils import get_column_letter

OUTPUT_DIR = Path("output")
HEADER_FILL = PatternFill(start_color="1A1A28", end_color="1A1A28", fill_type="solid")
HEADER_FONT = Font(name="Inter", bold=True, color="E4E4EC", size=10)
CELL_FONT = Font(name="JetBrains Mono", color="E4E4EC", size=9)
WEAK_FILL = PatternFill(start_color="1A0808", end_color="1A0808", fill_type="solid")
MODERATE_FILL = PatternFill(start_color="1A1808", end_color="1A1808", fill_type="solid")
STRONG_FILL = PatternFill(start_color="0A1A0F", end_color="0A1A0F", fill_type="solid")


def _style_sheet(ws, num_rows: int, num_cols: int) -> None:
    for col in range(1, num_cols + 1):
        cell = ws.cell(row=1, column=col)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="left", vertical="center")
    for row in range(2, num_rows + 1):
        for col in range(1, num_cols + 1):
            cell = ws.cell(row=row, column=col)
            cell.font = CELL_FONT
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    # auto-width
    for col in range(1, num_cols + 1):
        max_len = 0
        for row in range(1, min(num_rows + 1, 50)):
            val = ws.cell(row=row, column=col).value
            if val:
                max_len = max(max_len, min(len(str(val)), 60))
        ws.column_dimensions[get_column_letter(col)].width = max_len + 2


def _sanitize(val: Any) -> Any:
    if isinstance(val, str):
        return val
    if hasattr(val, "tzinfo") and getattr(val, "tzinfo", None) is not None:
        return val.replace(tzinfo=None)
    return val


def _sanitize_datetimes(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        series = df[col]
        try:
            first = series.dropna().iloc[0] if len(series.dropna()) > 0 else None
        except Exception:
            first = None
        if first is not None and hasattr(first, "tzinfo") and getattr(first, "tzinfo", None) is not None:
            df[col] = series.apply(lambda x: str(x).replace("+00:00", "").rstrip("Z").strip() if x is not None and str(x) != "nan" else None)
    return df


def write_signals_sheet(wb: Workbook, signals: list[dict[str, Any]]) -> None:
    ws = wb.active
    ws.title = "Signals"

    cols = ["signal_id", "source_type", "source_name", "url", "author_handle",
            "raw_text", "matched_pattern", "triage_score", "triage_reason",
            "posted_at", "captured_at"]
    df = pd.DataFrame(signals, columns=cols)
    if "raw_text" in df.columns:
        df["raw_text"] = df["raw_text"].apply(lambda x: (x or "")[:200])
    df = _sanitize_datetimes(df)

    for row in dataframe_to_rows(df, index=False, header=True):
        ws.append(row)

    _style_sheet(ws, len(signals) + 1, len(cols))
    _add_source_bar_chart(ws, df, len(signals))


def _add_source_bar_chart(ws, df: pd.DataFrame, num_rows: int) -> None:
    if df.empty or "source_name" not in df.columns:
        return
    counts = df["source_name"].value_counts()
    if counts.empty:
        return

    chart_start_row = num_rows + 4
    ws.cell(row=chart_start_row, column=1, value="Source").font = HEADER_FONT
    ws.cell(row=chart_start_row, column=2, value="Count").font = HEADER_FONT
    for i, (name, cnt) in enumerate(counts.items(), 1):
        ws.cell(row=chart_start_row + i, column=1, value=name).font = CELL_FONT
        ws.cell(row=chart_start_row + i, column=2, value=int(cnt)).font = CELL_FONT

    chart = BarChart()
    chart.type = "col"
    chart.title = "Signals by Source"
    chart.y_axis.title = "Count"
    chart.x_axis.title = "Source"
    chart.style = 2
    data_ref = Reference(ws, min_col=2, min_row=chart_start_row, max_row=chart_start_row + len(counts))
    cats_ref = Reference(ws, min_col=1, min_row=chart_start_row + 1, max_row=chart_start_row + len(counts))
    chart.add_data(data_ref, titles_from_data=True)
    chart.set_categories(cats_ref)
    chart.width = 18
    chart.height = 10
    ws.add_chart(chart, f"D{chart_start_row}")


def write_leads_sheet(
    wb: Workbook,
    leads: list[dict[str, Any]],
    sheet_index: int = 1,
) -> None:
    if sheet_index >= len(wb.sheetnames):
        ws = wb.create_sheet("Leads")
    else:
        ws = wb.create_sheet("Leads")
        if len(wb.sheetnames) > 1:
            idx = wb.sheetnames.index("Leads")
            if idx != 1:
                wb.move_sheet("Leads", offset=1 - idx)

    cols = ["lead_id", "signal_id", "triage_score", "company_name", "contact_name",
            "contact_email", "gap_hypothesis", "facts_strong", "facts_moderate",
            "facts_weak", "offer_subject", "offer_body", "unresolved"]
    df = pd.DataFrame(leads, columns=cols)
    for col in ("offer_body", "gap_hypothesis"):
        if col in df.columns:
            df[col] = df[col].apply(lambda x: (x or "")[:300])

    for row in dataframe_to_rows(df, index=False, header=True):
        ws.append(row)

    _style_sheet(ws, len(leads) + 1, len(cols))

    _add_grade_pie_chart(ws, df, len(leads))
    _add_facts_stacked_bar(ws, df, len(leads))


def _add_grade_pie_chart(ws, df: pd.DataFrame, num_rows: int) -> None:
    if df.empty:
        return
    strong = int(df["facts_strong"].sum()) if "facts_strong" in df.columns else 0
    moderate = int(df["facts_moderate"].sum()) if "facts_moderate" in df.columns else 0
    weak = int(df["facts_weak"].sum()) if "facts_weak" in df.columns else 0

    chart_start_row = num_rows + 4
    ws.cell(row=chart_start_row, column=1, value="Grade").font = HEADER_FONT
    ws.cell(row=chart_start_row, column=2, value="Count").font = HEADER_FONT
    for i, (grade, count) in enumerate([("Strong", strong), ("Moderate", moderate), ("Weak", weak)], 1):
        ws.cell(row=chart_start_row + i, column=1, value=grade).font = CELL_FONT
        ws.cell(row=chart_start_row + i, column=2, value=count).font = CELL_FONT

    chart = PieChart()
    chart.title = "Evidence Grade Distribution"
    data_ref = Reference(ws, min_col=2, min_row=chart_start_row, max_row=chart_start_row + 3)
    cats_ref = Reference(ws, min_col=1, min_row=chart_start_row + 1, max_row=chart_start_row + 3)
    chart.add_data(data_ref, titles_from_data=True)
    chart.set_categories(cats_ref)
    chart.width = 14
    chart.height = 10
    ws.add_chart(chart, f"D{chart_start_row}")


def _add_facts_stacked_bar(ws, df: pd.DataFrame, num_rows: int) -> None:
    if df.empty:
        return
    chart_start_row = num_rows + 20
    ws.cell(row=chart_start_row, column=1, value="Lead").font = HEADER_FONT
    ws.cell(row=chart_start_row, column=2, value="Strong").font = HEADER_FONT
    ws.cell(row=chart_start_row, column=3, value="Moderate").font = HEADER_FONT
    ws.cell(row=chart_start_row, column=4, value="Weak").font = HEADER_FONT
    for i, (_, row) in enumerate(df.iterrows(), 1):
        label = str(row.get("company_name") or row.get("contact_name") or f"Lead {i}")[:20]
        ws.cell(row=chart_start_row + i, column=1, value=label).font = CELL_FONT
        ws.cell(row=chart_start_row + i, column=2, value=int(row.get("facts_strong", 0) or 0)).font = CELL_FONT
        ws.cell(row=chart_start_row + i, column=3, value=int(row.get("facts_moderate", 0) or 0)).font = CELL_FONT
        ws.cell(row=chart_start_row + i, column=4, value=int(row.get("facts_weak", 0) or 0)).font = CELL_FONT

    chart = BarChart()
    chart.type = "col"
    chart.grouping = "stacked"
    chart.title = "Facts per Lead (by Grade)"
    chart.y_axis.title = "Count"
    chart.style = 2
    data_ref = Reference(ws, min_col=2, max_col=4, min_row=chart_start_row, max_row=chart_start_row + len(df))
    cats_ref = Reference(ws, min_col=1, min_row=chart_start_row + 1, max_row=chart_start_row + len(df))
    chart.add_data(data_ref, titles_from_data=True)
    chart.set_categories(cats_ref)
    chart.width = 18
    chart.height = 10
    ws.add_chart(chart, f"F{chart_start_row}")


def create_workbook(
    signals: list[dict[str, Any]],
    leads: list[dict[str, Any]],
    filename: str,
) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / filename

    wb = Workbook()
    write_signals_sheet(wb, signals)
    write_leads_sheet(wb, leads)
    wb.save(path)
    return path