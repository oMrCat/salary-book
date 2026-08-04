# -*- coding: utf-8 -*-
"""工资计算与月度/年度汇总逻辑。"""

from datetime import datetime


def to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def compute_work_amount(record, settings):
    """根据记录类型与规则，计算单条工作记录的应得金额。"""
    rtype = record.get("record_type", "")
    is_holiday = bool(record.get("is_holiday"))
    rate = to_float(record.get("rate")) or 0.0
    if rate <= 0:
        if rtype in ("计时", "加班"):
            rate = to_float(settings.get("hourly_rate"))
        elif rtype == "计件":
            rate = to_float(settings.get("piece_rate"))
        elif rtype in ("按天", "出勤"):
            rate = to_float(settings.get("daily_rate"))
        elif rtype == "按月":
            rate = to_float(settings.get("monthly_salary"))

    if rtype == "计件":
        units = to_float(record.get("units"))
        return round(units * rate, 2)

    if rtype in ("按天", "出勤"):
        days = to_float(record.get("hours"))
        if days <= 0:
            days = 1
        return round(days * rate, 2)

    if rtype == "按月":
        months = to_float(record.get("hours"))
        if months <= 0:
            months = 1
        return round(months * rate, 2)

    hours = to_float(record.get("hours"))
    if hours <= 0:
        start = record.get("start_time", "")
        end = record.get("end_time", "")
        hours = _diff_hours(start, end)

    if rtype == "加班":
        multiplier = to_float(settings.get("holiday_multiplier"), 3) if is_holiday \
            else to_float(settings.get("overtime_multiplier"), 1.5)
        hours = hours * multiplier
    elif is_holiday and rtype == "计时":
        hours = hours * to_float(settings.get("holiday_multiplier"), 3)
    return round(hours * rate, 2)


def _diff_hours(start, end):
    fmt = "%H:%M"
    try:
        s = datetime.strptime(start.strip(), fmt)
        e = datetime.strptime(end.strip(), fmt)
    except (ValueError, AttributeError):
        return 0.0
    delta = (e - s).total_seconds() / 3600.0
    if delta < 0:
        delta += 24
    return delta


def monthly_summary(db, year_month, settings=None):
    """汇总某月（YYYY-MM）的收入、扣款与发薪记录。"""
    if settings is None:
        settings = db.get_settings()
    works = db.list_work(year_month)
    deductions = db.list_deductions(year_month)

    items = []
    income_total = 0.0
    for w in works:
        w["amount"] = compute_work_amount(w, settings)
        items.append(w)
        income_total += w["amount"]
    income_total = round(income_total, 2)

    ded_total = round(sum(to_float(d["amount"]) for d in deductions), 2)
    payable = round(income_total - ded_total, 2)

    payment = db.get_payment(year_month)
    actual = round(to_float(payment["actual_amount"]), 2) if payment else None
    diff = round(actual - payable, 2) if actual is not None else None
    balanced = actual is not None and abs(diff or 0) < 0.005

    by_type = {}
    for w in works:
        t = w["record_type"]
        by_type.setdefault(t, 0.0)
        by_type[t] = round(by_type[t] + w["amount"], 2)

    days, hours = month_attendance(works)

    return {
        "period": year_month,
        "works": items,
        "income_total": income_total,
        "income_by_type": by_type,
        "deductions": deductions,
        "deduction_total": ded_total,
        "payable": payable,
        "payment": payment,
        "actual": actual,
        "diff": diff,
        "balanced": balanced,
        "work_days": days,
        "work_hours": hours,
    }


def month_attendance(works):
    """根据工作记录统计出勤天数与总时长（按月记录不计入）。"""
    days = set()
    hours = 0.0
    for w in works:
        rtype = w["record_type"]
        if rtype == "按月":
            continue
        if rtype in ("出勤", "按天"):
            days.add(w["record_date"])
            hours += to_float(w.get("hours"))
        else:
            days.add(w["record_date"])
            h = to_float(w.get("hours"))
            if h <= 0 and w.get("start_time") and w.get("end_time"):
                h = _diff_hours(w["start_time"], w["end_time"])
            if h > 0:
                hours += h
    return len(days), round(hours, 1)


def trend(db, periods):
    """返回近 N 个期间的趋势数据（用于柱状图/折线图/对账差额标记）。"""
    settings = db.get_settings()
    out = []
    for p in periods:
        s = monthly_summary(db, p, settings)
        out.append({
            "period": p,
            "income": s["income_total"],
            "payable": s["payable"],
            "actual": s["actual"] if s["actual"] is not None else 0,
            "diff": s["diff"] if s["diff"] is not None else 0,
            "paid": s["payment"] is not None,
        })
    return out


def annual_summary(db, year, settings=None):
    """汇总某年（YYYY）的收入、扣款、出勤与逐月数据。"""
    if settings is None:
        settings = db.get_settings()
    prefix = year + "-"
    works = [w for w in db.list_work() if w["record_date"].startswith(prefix)]
    deductions = [d for d in db.list_deductions() if d["record_date"].startswith(prefix)]

    income_total = 0.0
    for w in works:
        w["amount"] = compute_work_amount(w, settings)
        income_total += w["amount"]
    income_total = round(income_total, 2)
    ded_total = round(sum(to_float(d["amount"]) for d in deductions), 2)
    payable = round(income_total - ded_total, 2)

    by_month = {}
    for w in works:
        m = w["record_date"][:7]
        by_month.setdefault(m, {"income": 0.0, "deduction": 0.0, "payable": 0.0})
        by_month[m]["income"] = round(by_month[m]["income"] + w["amount"], 2)
    for d in deductions:
        m = d["record_date"][:7]
        by_month.setdefault(m, {"income": 0.0, "deduction": 0.0, "payable": 0.0})
        by_month[m]["deduction"] = round(by_month[m]["deduction"] + d["amount"], 2)
    for m in by_month:
        by_month[m]["payable"] = round(by_month[m]["income"] - by_month[m]["deduction"], 2)

    by_type = {}
    for w in works:
        t = w["record_type"]
        by_type[t] = round(by_type.get(t, 0.0) + w["amount"], 2)

    days, hours = month_attendance(works)
    return {
        "year": year,
        "works": works,
        "deductions": deductions,
        "income_total": income_total,
        "income_by_type": by_type,
        "deduction_total": ded_total,
        "payable": payable,
        "work_days": days,
        "work_hours": hours,
        "by_month": dict(sorted(by_month.items())),
    }
