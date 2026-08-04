# -*- coding: utf-8 -*-
"""CSV 导出（UTF-8，Excel 请用「数据→自文本」导入）。"""

import csv


def _open(path):
    return open(path, "w", newline="", encoding="utf-8-sig")


def export_month(path, summary, company):
    period = summary["period"]
    with _open(path) as fh:
        writer = csv.writer(fh)
        title = f"{period} 工资对账" + (f"  ·  {company}" if company else "")
        writer.writerow([title])
        writer.writerow([])
        writer.writerow(["=== 收入明细 ==="])
        writer.writerow(["日期", "类型", "工作内容", "时长/件数", "单价", "金额", "节假日"])
        for w in summary["works"]:
            detail = w["content"] or (f"{w['start_time']}-{w['end_time']}" if w["start_time"] else "")
            qty = w["hours"] if w["hours"] else w["units"]
            writer.writerow([
                w["record_date"], w["record_type"], detail,
                qty if qty else "", w["rate"] if w["rate"] else "", w["amount"],
                "是" if w["is_holiday"] else "",
            ])
        writer.writerow(["", "", "", "", "收入合计", summary["income_total"]])
        writer.writerow([])
        writer.writerow(["=== 扣款明细 ==="])
        writer.writerow(["日期", "类别", "备注", "扣款金额"])
        for d in summary["deductions"]:
            writer.writerow([d["record_date"], d["category"], d["note"], d["amount"]])
        writer.writerow(["", "", "扣款合计", summary["deduction_total"]])
        writer.writerow([])
        writer.writerow(["=== 汇总 ==="])
        writer.writerow(["出勤天数", summary["work_days"]])
        writer.writerow(["总工时(小时)", summary["work_hours"]])
        writer.writerow(["收入合计", summary["income_total"]])
        writer.writerow(["扣款合计", summary["deduction_total"]])
        writer.writerow(["应发工资", summary["payable"]])
        actual = summary["actual"]
        if actual is not None:
            writer.writerow(["实发金额", actual])
            writer.writerow(["差额（实发-应发）", summary["diff"]])
            writer.writerow(["对账结果", "已对平" if summary["balanced"] else "有差额，请核对"])
        else:
            writer.writerow(["实发金额", "未登记"])


def export_year(path, annual, company):
    year = annual["year"]
    with _open(path) as fh:
        writer = csv.writer(fh)
        title = f"{year} 年工资年度报表" + (f"  ·  {company}" if company else "")
        writer.writerow([title])
        writer.writerow([])
        writer.writerow(["=== 收入明细 ==="])
        writer.writerow(["日期", "类型", "工作内容", "时长/件数", "单价", "金额", "节假日"])
        for w in annual["works"]:
            detail = w["content"] or (f"{w['start_time']}-{w['end_time']}" if w["start_time"] else "")
            qty = w["hours"] if w["hours"] else w["units"]
            writer.writerow([
                w["record_date"], w["record_type"], detail,
                qty if qty else "", w["rate"] if w["rate"] else "", w["amount"],
                "是" if w["is_holiday"] else "",
            ])
        writer.writerow(["", "", "", "", "全年收入合计", annual["income_total"]])
        writer.writerow([])
        writer.writerow(["=== 扣款明细 ==="])
        writer.writerow(["日期", "类别", "备注", "扣款金额"])
        for d in annual["deductions"]:
            writer.writerow([d["record_date"], d["category"], d["note"], d["amount"]])
        writer.writerow(["", "", "全年扣款合计", annual["deduction_total"]])
        writer.writerow([])
        writer.writerow(["=== 逐月汇总 ==="])
        writer.writerow(["月份", "收入", "扣款", "应发"])
        for m, v in annual["by_month"].items():
            writer.writerow([m, v["income"], v["deduction"], v["payable"]])
        writer.writerow(["全年合计", annual["income_total"],
                         annual["deduction_total"], annual["payable"]])
        writer.writerow([])
        writer.writerow(["出勤天数", annual["work_days"]])
        writer.writerow(["总工时(小时)", annual["work_hours"]])


def export_all(path, db):
    works = db.list_work()
    deductions = db.list_deductions()
    periods = db.list_periods()
    with _open(path) as fh:
        writer = csv.writer(fh)
        writer.writerow(["=== 全部工作记录 ==="])
        writer.writerow(["ID", "日期", "类型", "开始", "结束", "时长/天", "件数",
                         "单价", "金额", "节假日", "工作内容", "备注"])
        for w in works:
            writer.writerow([
                w["id"], w["record_date"], w["record_type"], w["start_time"],
                w["end_time"], w["hours"], w["units"], w["rate"], w["amount"],
                "是" if w["is_holiday"] else "", w["content"], w["note"],
            ])
        writer.writerow([])
        writer.writerow(["=== 全部扣款记录 ==="])
        writer.writerow(["ID", "日期", "类别", "金额", "备注"])
        for d in deductions:
            writer.writerow([d["id"], d["record_date"], d["category"], d["amount"], d["note"]])
        writer.writerow([])
        writer.writerow(["=== 各月发薪 ==="])
        writer.writerow(["月份", "实发金额", "实发日期", "备注"])
        for p in periods:
            pay = db.get_payment(p)
            if pay:
                writer.writerow([p, pay["actual_amount"], pay["paid_date"], pay["note"]])
