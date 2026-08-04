# -*- coding: utf-8 -*-
"""SQLite 数据层：建表与增删改查。"""

import os
import shutil
import sqlite3

DEFAULT_SETTINGS = {
    "hourly_rate": "0",        # 时薪（元/小时）
    "daily_rate": "0",         # 日薪（元/天）
    "monthly_salary": "0",     # 固定月薪（元/月）
    "piece_rate": "0",         # 计件单价（元/件）
    "overtime_multiplier": "1.5",  # 加班倍数
    "holiday_multiplier": "3",     # 节假日倍数
    "payday": "10",            # 每月发薪日
    "company": "",             # 公司名称
    "password": "",            # 启动密码（sha256 散列）
    "remind_payday": "1",      # 是否开启发薪日提醒
}

RECORD_TYPES = ["计时", "计件", "按天", "按月", "加班"]  # 兼容旧数据里的"出勤"
DEDUCTION_CATEGORIES = ["请假", "迟到", "社保", "公积金", "其他"]


def _default_db_path():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base, "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "salary.db")


def _to_real(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _norm_sig_value(value):
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(round(float(value), 2))
    return str(value or "")


def _work_sig(rec):
    keys = ("record_date", "record_type", "start_time", "end_time", "hours",
            "units", "rate", "amount", "content", "note", "is_holiday")
    parts = []
    for k in keys:
        v = rec.get(k) if isinstance(rec, dict) else rec[k]
        if k == "is_holiday":
            parts.append("1" if v else "0")
        else:
            parts.append(_norm_sig_value(v))
    return "|".join(parts)


def _ded_sig(rec):
    keys = ("record_date", "category", "amount", "note")
    parts = []
    for k in keys:
        v = rec.get(k) if isinstance(rec, dict) else rec[k]
        parts.append(_norm_sig_value(v))
    return "|".join(parts)


class Database:
    def __init__(self, db_path=None):
        self.db_path = db_path or _default_db_path()
        self._init_schema()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS work_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_date TEXT NOT NULL,
                    record_type TEXT NOT NULL,
                    start_time TEXT DEFAULT '',
                    end_time TEXT DEFAULT '',
                    hours REAL DEFAULT 0,
                    units REAL DEFAULT 0,
                    rate REAL DEFAULT 0,
                    amount REAL DEFAULT 0,
                    content TEXT DEFAULT '',
                    note TEXT DEFAULT '',
                    is_holiday INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS deductions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_date TEXT NOT NULL,
                    category TEXT NOT NULL,
                    amount REAL DEFAULT 0,
                    note TEXT DEFAULT ''
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    period TEXT NOT NULL,
                    actual_amount REAL DEFAULT 0,
                    paid_date TEXT DEFAULT '',
                    note TEXT DEFAULT '',
                    UNIQUE(period)
                )
            """)
            # 旧库迁移：补齐 is_holiday 列
            cols = {r[1] for r in conn.execute("PRAGMA table_info(work_records)").fetchall()}
            if "is_holiday" not in cols:
                conn.execute("ALTER TABLE work_records ADD COLUMN is_holiday INTEGER DEFAULT 0")
            for key, value in DEFAULT_SETTINGS.items():
                conn.execute(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                    (key, value),
                )

    # ---------- 设置 ----------
    def get_settings(self):
        with self._connect() as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
        return {row["key"]: row["value"] for row in rows}

    def save_settings(self, data):
        with self._connect() as conn:
            for key, value in data.items():
                conn.execute(
                    "INSERT INTO settings (key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (key, str(value)),
                )

    # ---------- 工作记录 ----------
    def add_work(self, rec):
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO work_records "
                "(record_date, record_type, start_time, end_time, hours, units, "
                " rate, amount, content, note, is_holiday) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    rec["record_date"], rec["record_type"], rec.get("start_time", ""),
                    rec.get("end_time", ""), rec.get("hours", 0), rec.get("units", 0),
                    rec.get("rate", 0), rec.get("amount", 0),
                    rec.get("content", ""), rec.get("note", ""),
                    1 if rec.get("is_holiday") else 0,
                ),
            )
            return cur.lastrowid

    def update_work(self, rec_id, rec):
        with self._connect() as conn:
            conn.execute(
                "UPDATE work_records SET record_date=?, record_type=?, start_time=?, "
                "end_time=?, hours=?, units=?, rate=?, amount=?, content=?, note=?, "
                "is_holiday=? WHERE id=?",
                (
                    rec["record_date"], rec["record_type"], rec.get("start_time", ""),
                    rec.get("end_time", ""), rec.get("hours", 0), rec.get("units", 0),
                    rec.get("rate", 0), rec.get("amount", 0),
                    rec.get("content", ""), rec.get("note", ""),
                    1 if rec.get("is_holiday") else 0, rec_id,
                ),
            )

    def delete_work(self, rec_id):
        with self._connect() as conn:
            conn.execute("DELETE FROM work_records WHERE id=?", (rec_id,))

    def list_work(self, year_month=None, keyword=None):
        sql = "SELECT * FROM work_records"
        conds, params = [], []
        if year_month:
            conds.append("record_date LIKE ?")
            params.append(year_month + "%")
        if keyword:
            conds.append("(content LIKE ? OR note LIKE ? OR record_date LIKE ?)")
            kw = "%" + keyword + "%"
            params += [kw, kw, kw]
        if conds:
            sql += " WHERE " + " AND ".join(conds)
        sql += " ORDER BY record_date DESC, id DESC"
        with self._connect() as conn:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]

    # ---------- 扣款记录 ----------
    def add_deduction(self, rec):
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO deductions (record_date, category, amount, note) "
                "VALUES (?, ?, ?, ?)",
                (rec["record_date"], rec["category"], rec["amount"], rec.get("note", "")),
            )
            return cur.lastrowid

    def update_deduction(self, rec_id, rec):
        with self._connect() as conn:
            conn.execute(
                "UPDATE deductions SET record_date=?, category=?, amount=?, note=? "
                "WHERE id=?",
                (rec["record_date"], rec["category"], rec["amount"], rec.get("note", ""), rec_id),
            )

    def delete_deduction(self, rec_id):
        with self._connect() as conn:
            conn.execute("DELETE FROM deductions WHERE id=?", (rec_id,))

    def list_deductions(self, year_month=None, keyword=None):
        sql = "SELECT * FROM deductions"
        conds, params = [], []
        if year_month:
            conds.append("record_date LIKE ?")
            params.append(year_month + "%")
        if keyword:
            conds.append("(note LIKE ? OR category LIKE ? OR record_date LIKE ?)")
            kw = "%" + keyword + "%"
            params += [kw, kw, kw]
        if conds:
            sql += " WHERE " + " AND ".join(conds)
        sql += " ORDER BY record_date DESC, id DESC"
        with self._connect() as conn:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]

    # ---------- 发薪记录 ----------
    def get_payment(self, period):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM payments WHERE period=?", (period,)
            ).fetchone()
        return dict(row) if row else None

    def save_payment(self, period, actual, paid_date, note):
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO payments (period, actual_amount, paid_date, note) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(period) DO UPDATE SET actual_amount=excluded.actual_amount, "
                "paid_date=excluded.paid_date, note=excluded.note",
                (period, actual, paid_date, note),
            )

    def delete_payment(self, period):
        with self._connect() as conn:
            conn.execute("DELETE FROM payments WHERE period=?", (period,))

    def list_periods(self):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT substr(record_date, 1, 7) AS p FROM work_records "
                "UNION SELECT DISTINCT substr(record_date, 1, 7) FROM deductions "
                "UNION SELECT period FROM payments ORDER BY p DESC"
            ).fetchall()
        return [r["p"] for r in rows if r["p"]]

    # ---------- 备份 / 恢复 ----------
    def backup_to(self, dest):
        with self._connect() as conn:
            conn.execute("PRAGMA wal_checkpoint(FULL);")
        os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
        shutil.copy2(self.db_path, dest)

    def restore_from(self, src):
        with self._connect() as conn:
            conn.execute("PRAGMA wal_checkpoint(FULL);")
        shutil.copy2(src, self.db_path)

    def replace_all(self, settings, works, deductions, payments):
        """用同步数据整体替换（用于导入/局域网拉取）。"""
        with self._connect() as conn:
            conn.execute("DELETE FROM settings")
            for key, value in DEFAULT_SETTINGS.items():
                conn.execute(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                    (key, value),
                )
            for key, value in settings.items():
                conn.execute(
                    "INSERT INTO settings (key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (key, str(value)),
                )
            conn.execute("DELETE FROM work_records")
            for w in works:
                conn.execute(
                    "INSERT INTO work_records "
                    "(record_date, record_type, start_time, end_time, hours, units, "
                    " rate, amount, content, note, is_holiday) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        w.get("record_date", ""), w.get("record_type", "计时"),
                        w.get("start_time", ""), w.get("end_time", ""),
                        _to_real(w.get("hours")), _to_real(w.get("units")),
                        _to_real(w.get("rate")), _to_real(w.get("amount")),
                        w.get("content", ""), w.get("note", ""),
                        1 if w.get("is_holiday") else 0,
                    ),
                )
            conn.execute("DELETE FROM deductions")
            for d in deductions:
                conn.execute(
                    "INSERT INTO deductions (record_date, category, amount, note) "
                    "VALUES (?, ?, ?, ?)",
                    (d.get("record_date", ""), d.get("category", "其他"),
                     _to_real(d.get("amount")), d.get("note", "")),
                )
            conn.execute("DELETE FROM payments")
            for p in payments:
                conn.execute(
                    "INSERT INTO payments (period, actual_amount, paid_date, note) "
                    "VALUES (?, ?, ?, ?)",
                    (p.get("period", ""), _to_real(p.get("actual_amount")),
                     p.get("paid_date", ""), p.get("note", "")),
                )

    def merge_data(self, settings, works, deductions, payments):
        """合并导入：完全相同的记录去重，不同的记录追加；发薪按月份去重/更新。

        返回统计 dict。
        """
        added_work = dup_work = added_ded = dup_ded = pay_new = pay_upd = 0
        with self._connect() as conn:
            for key, value in settings.items():
                conn.execute(
                    "INSERT INTO settings (key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (key, str(value)),
                )

            existing_w = set()
            rows = conn.execute(
                "SELECT record_date, record_type, start_time, end_time, hours, "
                "units, rate, amount, content, note, is_holiday FROM work_records"
            ).fetchall()
            for r in rows:
                existing_w.add(_work_sig(dict(r)))

            for w in works:
                sig = _work_sig(w)
                if sig in existing_w:
                    dup_work += 1
                    continue
                conn.execute(
                    "INSERT INTO work_records "
                    "(record_date, record_type, start_time, end_time, hours, units, "
                    " rate, amount, content, note, is_holiday) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        w.get("record_date", ""), w.get("record_type", "计时"),
                        w.get("start_time", ""), w.get("end_time", ""),
                        _to_real(w.get("hours")), _to_real(w.get("units")),
                        _to_real(w.get("rate")), _to_real(w.get("amount")),
                        w.get("content", ""), w.get("note", ""),
                        1 if w.get("is_holiday") else 0,
                    ),
                )
                existing_w.add(sig)
                added_work += 1

            existing_d = set()
            rows = conn.execute(
                "SELECT record_date, category, amount, note FROM deductions"
            ).fetchall()
            for r in rows:
                existing_d.add(_ded_sig(dict(r)))

            for d in deductions:
                sig = _ded_sig(d)
                if sig in existing_d:
                    dup_ded += 1
                    continue
                conn.execute(
                    "INSERT INTO deductions (record_date, category, amount, note) "
                    "VALUES (?, ?, ?, ?)",
                    (d.get("record_date", ""), d.get("category", "其他"),
                     _to_real(d.get("amount")), d.get("note", "")),
                )
                existing_d.add(sig)
                added_ded += 1

            for p in payments:
                period = p.get("period", "")
                if not period:
                    continue
                row = conn.execute(
                    "SELECT actual_amount, paid_date, note FROM payments WHERE period=?",
                    (period,),
                ).fetchone()
                if row is None:
                    conn.execute(
                        "INSERT INTO payments (period, actual_amount, paid_date, note) "
                        "VALUES (?, ?, ?, ?)",
                        (period, _to_real(p.get("actual_amount")),
                         p.get("paid_date", ""), p.get("note", "")),
                    )
                    pay_new += 1
                else:
                    same = (_to_real(p.get("actual_amount")) == _to_real(row["actual_amount"])
                            and (p.get("paid_date", "") or "") == (row["paid_date"] or "")
                            and (p.get("note", "") or "") == (row["note"] or ""))
                    if not same:
                        conn.execute(
                            "UPDATE payments SET actual_amount=?, paid_date=?, note=? "
                            "WHERE period=?",
                            (_to_real(p.get("actual_amount")), p.get("paid_date", ""),
                             p.get("note", ""), period),
                        )
                        pay_upd += 1

        return {
            "added_work": added_work, "dup_work": dup_work,
            "added_ded": added_ded, "dup_ded": dup_ded,
            "pay_new": pay_new, "pay_upd": pay_upd,
        }
