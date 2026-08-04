# -*- coding: utf-8 -*-
"""Excel 导出（基于 openpyxl）：月度对账、年度报表、全部数据。"""

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


def _header_sheet(ws, title):
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=6)
    ws.cell(row=1, column=1, value=title).font = Font(bold=True, size=14)
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=6)
    ws.cell(row=2, column=1, value="应发 = 收入合计 - 扣款合计").font = Font(size=10, color="666666")


def _title_row(ws, row, values):
    fill = PatternFill("solid", fgColor="DDEBF7")
    for col, text in enumerate(values, start=1):
        cell = ws.cell(row=row, column=col, value=text)
        cell.font = Font(bold=True)
        cell.fill = fill
        cell.alignment = Alignment(horizontal="center")


def export_month(path, summary, company):
    wb = Workbook()
    period = summary["period"]
    title = f"{period} 工资对账" + (f"  ·  {company}" if company else "")

    ws = wb.active
    ws.title = "收入明细"
    _header_sheet(ws, title)
    _title_row(ws, 4, ["日期", "类型", "工作内容", "时长/件数", "单价", "金额", "节假日"])
    row = 5
    for w in summary["works"]:
        detail = w["content"] or (f"{w['start_time']}-{w['end_time']}" if w["start_time"] else "")
        qty = w["hours"] if w["hours"] else w["units"]
        ws.cell(row=row, column=1, value=w["record_date"])
        ws.cell(row=row, column=2, value=w["record_type"])
        ws.cell(row=row, column=3, value=detail)
        ws.cell(row=row, column=4, value=qty if qty else None)
        ws.cell(row=row, column=5, value=w["rate"] if w["rate"] else None)
        ws.cell(row=row, column=6, value=w["amount"])
        ws.cell(row=row, column=7, value="是" if w["is_holiday"] else "")
        row += 1
    ws.cell(row=row, column=5, value="收入合计").font = Font(bold=True)
    ws.cell(row=row, column=6, value=summary["income_total"]).font = Font(bold=True)

    ws2 = wb.create_sheet("扣款明细")
    _header_sheet(ws2, title)
    _title_row(ws2, 4, ["日期", "类别", "备注", "扣款金额"])
    row = 5
    for d in summary["deductions"]:
        ws2.cell(row=row, column=1, value=d["record_date"])
        ws2.cell(row=row, column=2, value=d["category"])
        ws2.cell(row=row, column=3, value=d["note"])
        ws2.cell(row=row, column=4, value=d["amount"])
        row += 1
    ws2.cell(row=row, column=3, value="扣款合计").font = Font(bold=True)
    ws2.cell(row=row, column=4, value=summary["deduction_total"]).font = Font(bold=True)

    ws3 = wb.create_sheet("汇总")
    _header_sheet(ws3, title)
    rows = [
        ("出勤天数", summary["work_days"]),
        ("总工时(小时)", summary["work_hours"]),
        ("收入合计", summary["income_total"]),
        ("扣款合计", summary["deduction_total"]),
        ("应发工资", summary["payable"]),
    ]
    actual = summary["actual"]
    if actual is not None:
        rows.append(("实发金额", actual))
        rows.append(("差额（实发-应发）", summary["diff"]))
        rows.append(("对账结果", "已对平" if summary["balanced"] else "有差额，请核对"))
    else:
        rows.append(("实发金额", "未登记"))
    for i, (label, val) in enumerate(rows, start=4):
        ws3.cell(row=i, column=1, value=label).font = Font(bold=True)
        ws3.cell(row=i, column=2, value=val)

    for sheet in (ws, ws2, ws3):
        for col in range(1, 8):
            letter = get_column_letter(col)
            sheet.column_dimensions[letter].width = {1: 14, 2: 12, 3: 28,
                                                     4: 14, 5: 12, 6: 12, 7: 10}.get(col, 10)

    wb.save(path)


def export_year(path, annual, company):
    wb = Workbook()
    year = annual["year"]
    title = f"{year} 年工资年度报表" + (f"  ·  {company}" if company else "")

    ws = wb.active
    ws.title = "收入明细"
    _header_sheet(ws, title)
    _title_row(ws, 4, ["日期", "类型", "工作内容", "时长/件数", "单价", "金额", "节假日"])
    row = 5
    for w in annual["works"]:
        detail = w["content"] or (f"{w['start_time']}-{w['end_time']}" if w["start_time"] else "")
        qty = w["hours"] if w["hours"] else w["units"]
        ws.cell(row=row, column=1, value=w["record_date"])
        ws.cell(row=row, column=2, value=w["record_type"])
        ws.cell(row=row, column=3, value=detail)
        ws.cell(row=row, column=4, value=qty if qty else None)
        ws.cell(row=row, column=5, value=w["rate"] if w["rate"] else None)
        ws.cell(row=row, column=6, value=w["amount"])
        ws.cell(row=row, column=7, value="是" if w["is_holiday"] else "")
        row += 1
    ws.cell(row=row, column=5, value="全年收入合计").font = Font(bold=True)
    ws.cell(row=row, column=6, value=annual["income_total"]).font = Font(bold=True)

    ws2 = wb.create_sheet("扣款明细")
    _header_sheet(ws2, title)
    _title_row(ws2, 4, ["日期", "类别", "备注", "扣款金额"])
    row = 5
    for d in annual["deductions"]:
        ws2.cell(row=row, column=1, value=d["record_date"])
        ws2.cell(row=row, column=2, value=d["category"])
        ws2.cell(row=row, column=3, value=d["note"])
        ws2.cell(row=row, column=4, value=d["amount"])
        row += 1
    ws2.cell(row=row, column=3, value="全年扣款合计").font = Font(bold=True)
    ws2.cell(row=row, column=4, value=annual["deduction_total"]).font = Font(bold=True)

    ws3 = wb.create_sheet("逐月汇总")
    _header_sheet(ws3, title)
    _title_row(ws3, 4, ["月份", "收入", "扣款", "应发"])
    row = 5
    for m, v in annual["by_month"].items():
        ws3.cell(row=row, column=1, value=m)
        ws3.cell(row=row, column=2, value=v["income"])
        ws3.cell(row=row, column=3, value=v["deduction"])
        ws3.cell(row=row, column=4, value=v["payable"])
        row += 1
    ws3.cell(row=row, column=1, value="全年合计").font = Font(bold=True)
    ws3.cell(row=row, column=2, value=annual["income_total"]).font = Font(bold=True)
    ws3.cell(row=row, column=3, value=annual["deduction_total"]).font = Font(bold=True)
    ws3.cell(row=row, column=4, value=annual["payable"]).font = Font(bold=True)

    ws4 = wb.create_sheet("年度总结")
    _header_sheet(ws4, title)
    rows = [
        ("出勤天数", annual["work_days"]),
        ("总工时(小时)", annual["work_hours"]),
        ("全年收入合计", annual["income_total"]),
        ("全年扣款合计", annual["deduction_total"]),
        ("全年应发合计", annual["payable"]),
    ]
    for i, (label, val) in enumerate(rows, start=4):
        ws4.cell(row=i, column=1, value=label).font = Font(bold=True)
        ws4.cell(row=i, column=2, value=val)

    for sheet in (ws, ws2, ws3, ws4):
        for col in range(1, 8):
            letter = get_column_letter(col)
            sheet.column_dimensions[letter].width = {1: 14, 2: 12, 3: 28,
                                                     4: 14, 5: 12, 6: 12, 7: 10}.get(col, 10)
    wb.save(path)


def export_all(path, db, company=""):
    """导出全部数据到 Excel：工作记录 / 扣款记录 / 发薪记录 三个工作表。"""
    from . import calc
    settings = db.get_settings()
    wb = Workbook()
    title = "薪资记录账本 · 全部数据" + (f"  ·  {company}" if company else "")

    ws = wb.active
    ws.title = "工作记录"
    _header_sheet(ws, title)
    _title_row(ws, 4, ["日期", "类型", "开始", "结束", "时长/天", "件数",
                       "单价", "金额", "节假日", "工作内容", "备注"])
    row = 5
    for w in db.list_work():
        # 金额按当前工资规则实时重算，保证与界面一致
        w["amount"] = calc.compute_work_amount(w, settings)
        ws.cell(row=row, column=1, value=w["record_date"])
        ws.cell(row=row, column=2, value=w["record_type"])
        ws.cell(row=row, column=3, value=w["start_time"])
        ws.cell(row=row, column=4, value=w["end_time"])
        ws.cell(row=row, column=5, value=w["hours"] if w["hours"] else None)
        ws.cell(row=row, column=6, value=w["units"] if w["units"] else None)
        ws.cell(row=row, column=7, value=w["rate"] if w["rate"] else None)
        ws.cell(row=row, column=8, value=w["amount"] if w["amount"] else None)
        ws.cell(row=row, column=9, value="是" if w["is_holiday"] else "")
        ws.cell(row=row, column=10, value=w["content"])
        ws.cell(row=row, column=11, value=w["note"])
        row += 1

    ws2 = wb.create_sheet("扣款记录")
    _header_sheet(ws2, title)
    _title_row(ws2, 4, ["日期", "类别", "金额", "备注"])
    row = 5
    for d in db.list_deductions():
        ws2.cell(row=row, column=1, value=d["record_date"])
        ws2.cell(row=row, column=2, value=d["category"])
        ws2.cell(row=row, column=3, value=d["amount"])
        ws2.cell(row=row, column=4, value=d["note"])
        row += 1

    ws3 = wb.create_sheet("发薪记录")
    _header_sheet(ws3, title)
    _title_row(ws3, 4, ["月份", "实发金额", "实发日期", "备注"])
    row = 5
    for p in db.list_periods():
        pay = db.get_payment(p)
        if pay:
            ws3.cell(row=row, column=1, value=pay["period"])
            ws3.cell(row=row, column=2, value=pay["actual_amount"])
            ws3.cell(row=row, column=3, value=pay["paid_date"])
            ws3.cell(row=row, column=4, value=pay["note"])
            row += 1

    for sheet in (ws, ws2, ws3):
        for col in range(1, 12):
            letter = get_column_letter(col)
            sheet.column_dimensions[letter].width = {1: 13, 2: 10, 3: 10, 4: 10,
                                                     5: 10, 6: 9, 7: 9, 8: 11,
                                                     9: 9, 10: 26, 11: 18}.get(col, 12)
    wb.save(path)


def import_excel(path, db):
    """从本软件导出的 Excel 导入并合并数据，返回统计文本。

    兼容两种格式：
      - 月度对账/年度报表（含「收入明细」「扣款明细」工作表）
      - 全部数据（含「工作记录」「扣款记录」「发薪记录」工作表）
    """
    from openpyxl import load_workbook

    wb = load_workbook(path, data_only=True)
    names = set(wb.sheetnames)

    def _read_work_sheet(sheet):
        works = []
        for row in sheet.iter_rows(min_row=5):
            if row[0].value is None:
                continue
            rtype = str(row[1].value or "计时")
            qty = row[3].value if len(row) > 3 else None
            units = row[4].value if len(row) > 4 else None
            rate = row[5].value if len(row) > 5 else None
            amount = row[6].value if len(row) > 6 else None
            holiday = row[7].value if len(row) > 7 else None
            content = row[8].value if len(row) > 8 else None
            note = row[9].value if len(row) > 9 else None
            works.append({
                "record_date": str(row[0].value),
                "record_type": rtype,
                "start_time": "",
                "end_time": "",
                "hours": 0.0,
                "units": 0.0,
                "rate": _num(rate),
                "amount": _num(amount),
                "content": str(content or ""),
                "note": str(note or ""),
                "is_holiday": 1 if (holiday and str(holiday).strip() == "是") else 0,
            })
        return works

    def _read_all_work_sheet(sheet):
        works = []
        for row in sheet.iter_rows(min_row=5):
            if row[0].value is None:
                continue
            works.append({
                "record_date": str(row[0].value),
                "record_type": str(row[1].value or "计时"),
                "start_time": str(row[2].value or ""),
                "end_time": str(row[3].value or ""),
                "hours": _num(row[4].value),
                "units": _num(row[5].value),
                "rate": _num(row[6].value),
                "amount": _num(row[7].value),
                "is_holiday": 1 if (row[8].value and str(row[8].value).strip() == "是") else 0,
                "content": str(row[9].value or ""),
                "note": str(row[10].value or ""),
            })
        return works

    def _read_ded_sheet(sheet, col_amount=3, col_note=4, col_date=1, col_cat=2):
        deds = []
        for row in sheet.iter_rows(min_row=5):
            if row[0].value is None:
                continue
            deds.append({
                "record_date": str(row[col_date - 1].value),
                "category": str(row[col_cat - 1].value or "其他"),
                "amount": _num(row[col_amount - 1].value),
                "note": str(row[col_note - 1].value or ""),
            })
        return deds

    settings = db.get_settings()
    works = []
    deductions = []
    payments = []
    if "工作记录" in names and "扣款记录" in names:
        works = _read_all_work_sheet(wb["工作记录"])
        deductions = _read_ded_sheet(wb["扣款记录"])
        if "发薪记录" in names:
            for row in wb["发薪记录"].iter_rows(min_row=5):
                if row[0].value is None:
                    continue
                payments.append({
                    "period": str(row[0].value),
                    "actual_amount": _num(row[1].value),
                    "paid_date": str(row[2].value or ""),
                    "note": str(row[3].value or ""),
                })
    elif "收入明细" in names or "扣款明细" in names:
        if "收入明细" in names:
            works = _read_work_sheet(wb["收入明细"])
        if "扣款明细" in names:
            deductions = _read_ded_sheet(wb["扣款明细"])
    else:
        raise ValueError("无法识别的 Excel 格式（需要本软件导出的表格）")

    r = db.merge_data(settings, works, deductions, payments)
    return (f"新增工作 {r['added_work']} 条、相同 {r['dup_work']} 条；"
            f"新增扣款 {r['added_ded']} 条、相同 {r['dup_ded']} 条；"
            f"发薪新增 {r['pay_new']} 条、更新 {r['pay_upd']} 条")


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
