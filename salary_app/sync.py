# -*- coding: utf-8 -*-
"""与 Android 端共用的 JSON 同步格式：导出 / 导入。"""

import json
from datetime import datetime

APP = "salary-book"
VERSION = 1


def export_json(db):
    """把整个数据库导出为与 Android 端一致的 JSON 字符串。"""
    periods = db.list_periods()
    payments = []
    for p in periods:
        pay = db.get_payment(p)
        if pay:
            payments.append({
                "period": pay["period"],
                "actual_amount": pay["actual_amount"],
                "paid_date": pay["paid_date"],
                "note": pay["note"],
            })
    root = {
        "app": APP,
        "version": VERSION,
        "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "settings": db.get_settings(),
        "work_records": [
            {
                "record_date": w["record_date"],
                "record_type": w["record_type"],
                "start_time": w["start_time"],
                "end_time": w["end_time"],
                "hours": w["hours"],
                "units": w["units"],
                "rate": w["rate"],
                "amount": w["amount"],
                "content": w["content"],
                "note": w["note"],
                "is_holiday": bool(w["is_holiday"]),
            }
            for w in db.list_work()
        ],
        "deductions": [
            {
                "record_date": d["record_date"],
                "category": d["category"],
                "amount": d["amount"],
                "note": d["note"],
            }
            for d in db.list_deductions()
        ],
        "payments": payments,
    }
    return json.dumps(root, ensure_ascii=False, indent=2)


def import_json(db, text):
    """把 JSON 字符串合并导入当前数据库（相同去重、不同追加），返回统计文本。"""
    root = json.loads(text)
    if root.get("app") != APP:
        raise ValueError("不是有效的工资对账数据文件（app 标识不匹配）")
    settings = {str(k): str(v) for k, v in (root.get("settings") or {}).items()}
    works = root.get("work_records") or []
    deductions = root.get("deductions") or []
    payments = root.get("payments") or []
    r = db.merge_data(settings, works, deductions, payments)
    return (f"新增工作 {r['added_work']} 条、相同 {r['dup_work']} 条；"
            f"新增扣款 {r['added_ded']} 条、相同 {r['dup_ded']} 条；"
            f"发薪新增 {r['pay_new']} 条、更新 {r['pay_upd']} 条")
