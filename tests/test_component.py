# -*- coding: utf-8 -*-
"""组件级测试：工资计算 / 数据库层 / JSON 同步 / 局域网服务。"""
import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from salary_app import calc, csvio, db as dbmod, discovery, lanserver, sync  # noqa: E402

SETTINGS = {
    "hourly_rate": "100", "daily_rate": "300", "piece_rate": "2", "monthly_salary": "6000",
    "overtime_multiplier": "1.5", "holiday_multiplier": "3", "payday": "10",
}


def make_db(tmp, name):
    d = dbmod.Database(os.path.join(tmp, name))
    d.save_settings(dict(SETTINGS))
    return d


class CalcTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="salbk_calc_")
        self.db = make_db(self.tmp, "calc.db")
        self.s = self.db.get_settings()

    def test_hourly(self):
        rec = {"record_type": "计时", "hours": 8, "rate": 100, "start_time": "", "end_time": ""}
        self.assertEqual(800.0, calc.compute_work_amount(rec, self.s))

    def test_hourly_falls_back_to_settings_rate(self):
        rec = {"record_type": "计时", "hours": 8, "rate": 0, "start_time": "", "end_time": ""}
        self.assertEqual(800.0, calc.compute_work_amount(rec, self.s))

    def test_overtime_multiplier(self):
        rec = {"record_type": "加班", "hours": 2, "rate": 0}
        self.assertEqual(300.0, calc.compute_work_amount(rec, self.s))  # 2h * 1.5 * 100

    def test_holiday_multiplier(self):
        rec = {"record_type": "计时", "hours": 8, "rate": 100, "is_holiday": 1}
        self.assertEqual(2400.0, calc.compute_work_amount(rec, self.s))

    def test_piece(self):
        rec = {"record_type": "计件", "units": 120, "rate": 2}
        self.assertEqual(240.0, calc.compute_work_amount(rec, self.s))

    def test_daily(self):
        rec = {"record_type": "按天", "hours": 0, "rate": 0}
        self.assertEqual(300.0, calc.compute_work_amount(rec, self.s))  # days 默认 1

    def test_monthly(self):
        rec = {"record_type": "按月", "hours": 0, "rate": 0}
        self.assertEqual(6000.0, calc.compute_work_amount(rec, self.s))

    def test_hours_from_time_range(self):
        rec = {"record_type": "计时", "hours": 0, "rate": 100,
               "start_time": "09:00", "end_time": "18:00"}
        self.assertEqual(900.0, calc.compute_work_amount(rec, self.s))

    def test_overnight_time_range(self):
        rec = {"record_type": "计时", "hours": 0, "rate": 100,
               "start_time": "22:00", "end_time": "06:00"}
        self.assertEqual(800.0, calc.compute_work_amount(rec, self.s))  # 跨夜 8h

    def test_monthly_summary_balanced(self):
        self.db.add_work({"record_date": "2026-08-01", "record_type": "计时",
                          "hours": 8, "rate": 100, "amount": 800})
        self.db.add_deduction({"record_date": "2026-08-02", "category": "请假", "amount": 100})
        s = calc.monthly_summary(self.db, "2026-08")
        self.assertEqual(800.0, s["income_total"])
        self.assertEqual(100.0, s["deduction_total"])
        self.assertEqual(700.0, s["payable"])
        self.assertIsNone(s["actual"])
        self.db.save_payment("2026-08", 700, "2026-08-10", "")
        s = calc.monthly_summary(self.db, "2026-08")
        self.assertEqual(0.0, s["diff"])
        self.assertTrue(s["balanced"])

    def test_annual_summary_by_month(self):
        self.db.add_work({"record_date": "2026-01-05", "record_type": "计时",
                          "hours": 8, "rate": 100, "amount": 800})
        self.db.add_work({"record_date": "2026-02-05", "record_type": "计时",
                          "hours": 8, "rate": 100, "amount": 800})
        a = calc.annual_summary(self.db, "2026")
        self.assertEqual(1600.0, a["income_total"])
        self.assertEqual(set(a["by_month"]), {"2026-01", "2026-02"})

    def test_attendance_counts_unique_days(self):
        self.db.add_work({"record_date": "2026-08-01", "record_type": "计时",
                          "hours": 4, "rate": 100})
        self.db.add_work({"record_date": "2026-08-01", "record_type": "计时",
                          "hours": 4, "rate": 100})
        self.db.add_work({"record_date": "2026-08-02", "record_type": "按天", "hours": 1})
        s = calc.monthly_summary(self.db, "2026-08")
        self.assertEqual(2, s["work_days"])
        self.assertEqual(9.0, s["work_hours"])


class DbTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="salbk_db_")

    def test_default_settings_seeded(self):
        d = dbmod.Database(os.path.join(self.tmp, "a.db"))
        s = d.get_settings()
        for key in dbmod.DEFAULT_SETTINGS:
            self.assertIn(key, s)
        self.assertEqual("1.5", s["overtime_multiplier"])

    def test_backup_restore_roundtrip(self):
        d = make_db(self.tmp, "b.db")
        d.add_work({"record_date": "2026-08-01", "record_type": "计时",
                    "hours": 8, "rate": 100, "amount": 800, "content": "盘点"})
        bak = os.path.join(self.tmp, "bak", "b.bak")
        d.backup_to(bak)
        d2 = dbmod.Database(os.path.join(self.tmp, "c.db"))
        d2.restore_from(bak)
        works = d2.list_work()
        self.assertEqual(1, len(works))
        self.assertEqual("盘点", works[0]["content"])

    def test_backup_restore_roundtrip_after_write(self):
        """restore 目标库先写入过数据（WAL 场景），restore 后必须完全等于备份内容。"""
        d = make_db(self.tmp, "src.db")
        d.add_work({"record_date": "2026-08-01", "record_type": "计时",
                    "hours": 8, "rate": 100, "amount": 800})
        bak = os.path.join(self.tmp, "b.bak")
        d.backup_to(bak)

        d2 = make_db(self.tmp, "dst.db")
        d2.add_work({"record_date": "2026-07-01", "record_type": "计件", "units": 5, "rate": 2})
        d2.restore_from(bak)
        works = d2.list_work()
        self.assertEqual(1, len(works))
        self.assertEqual("2026-08-01", works[0]["record_date"])

    def test_merge_dedup_and_append(self):
        base = make_db(self.tmp, "m.db")
        base.add_work({"record_date": "2026-08-01", "record_type": "计时",
                       "hours": 8, "rate": 100, "amount": 800})
        base.add_deduction({"record_date": "2026-08-02", "category": "迟到", "amount": 20})
        r = base.merge_data(
            {},
            [{"record_date": "2026-08-01", "record_type": "计时", "hours": 8,
              "rate": 100, "amount": 800, "is_holiday": False},
             {"record_date": "2026-08-03", "record_type": "计件", "units": 10, "rate": 2}],
            [{"record_date": "2026-08-02", "category": "迟到", "amount": 20, "note": ""}],
            [{"period": "2026-08", "actual_amount": 700}])
        self.assertEqual(1, r["added_work"])
        self.assertEqual(1, r["dup_work"])
        self.assertEqual(0, r["added_ded"])
        self.assertEqual(1, r["dup_ded"])
        self.assertEqual(1, r["pay_new"])
        # bool 与 int 的 is_holiday 签名必须等价（Android 端传 bool）
        r2 = base.merge_data(
            {},
            [{"record_date": "2026-08-01", "record_type": "计时", "hours": 8,
              "rate": 100, "amount": 800, "is_holiday": 0}],
            [], [])
        self.assertEqual(1, r2["dup_work"])

    def test_list_periods_merges_sources(self):
        d = make_db(self.tmp, "p.db")
        d.add_work({"record_date": "2026-08-01", "record_type": "计时", "hours": 8})
        d.add_deduction({"record_date": "2026-09-01", "category": "其他", "amount": 1})
        d.save_payment("2026-10", 100, "", "")
        self.assertEqual(["2026-10", "2026-09", "2026-08"], d.list_periods())


class SyncJsonTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="salbk_sync_")

    def test_export_import_roundtrip(self):
        src = make_db(self.tmp, "s.db")
        src.add_work({"record_date": "2026-08-01", "record_type": "计时", "hours": 8,
                      "rate": 100, "amount": 800, "content": "盘点", "is_holiday": 1})
        src.add_deduction({"record_date": "2026-08-02", "category": "请假",
                           "amount": 100, "note": "事假"})
        src.save_payment("2026-08", 700, "2026-08-10", "现金")

        dst = make_db(self.tmp, "d.db")
        text = sync.export_json(src)
        stats = sync.import_json(dst, text)

        works = dst.list_work()
        self.assertEqual(1, len(works))
        self.assertEqual("盘点", works[0]["content"])
        self.assertEqual(1, works[0]["is_holiday"])
        deds = dst.list_deductions()
        self.assertEqual("事假", deds[0]["note"])
        pay = dst.get_payment("2026-08")
        self.assertEqual(700.0, pay["actual_amount"])
        # 重复导入应全部去重
        stats2 = sync.import_json(dst, text)
        self.assertIn("相同 1 条", stats2)

    def test_import_rejects_foreign_app(self):
        dst = make_db(self.tmp, "x.db")
        with self.assertRaises(ValueError):
            sync.import_json(dst, json.dumps({"app": "other", "version": 1}))


class LanServerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="salbk_lan_")
        self.db = make_db(self.tmp, "lan.db")
        self.db.add_work({"record_date": "2026-08-01", "record_type": "计时",
                          "hours": 8, "rate": 100, "amount": 800})
        self.server = lanserver.SyncServer(self.db, port=0)
        # port=0 由系统分配，取实际端口
        self.server.start()
        self.port = self.server.httpd.server_address[1]

    def tearDown(self):
        self.server.stop()

    def _url(self, path):
        return f"http://127.0.0.1:{self.port}{path}"

    def test_ping(self):
        out = lanserver.ping_device("127.0.0.1", self.port)
        data = json.loads(out)
        self.assertTrue(data["ok"])
        self.assertEqual("salary-book", data["app"])

    def test_pull_data(self):
        out = lanserver.pull_device("127.0.0.1", self.port)
        data = json.loads(out)
        self.assertEqual("salary-book", data["app"])
        self.assertEqual(1, len(data["work_records"]))

    def test_push_data_merges(self):
        payload = {"app": "salary-book", "version": 1, "settings": {},
                   "work_records": [{"record_date": "2026-09-01", "record_type": "计时",
                                     "hours": 4, "rate": 100, "amount": 400}],
                   "deductions": [], "payments": []}
        out = lanserver.push_device("127.0.0.1", self.port, json.dumps(payload))
        data = json.loads(out)
        self.assertTrue(data["ok"])
        self.assertIn("新增工作 1 条", data["imported"])
        self.assertEqual(2, len(self.db.list_work()))


class DiscoveryTest(unittest.TestCase):
    def test_two_instances_discover_each_other(self):
        a = discovery.DiscoveryService("设备A", lambda: 18081)
        b = discovery.DiscoveryService("设备B", lambda: 18082)
        try:
            a.start()
            time.sleep(0.1)
            b.start()
            deadline = time.time() + 8
            while time.time() < deadline:
                if a.devices and b.devices:
                    break
                time.sleep(0.2)
            self.assertEqual(1, len(a.devices), "A 应发现 B")
            self.assertEqual(1, len(b.devices), "B 应发现 A")
            names = {d["name"] for d in a.devices.values()}
            self.assertEqual({"设备B"}, names)
        finally:
            a.stop()
            b.stop()


if __name__ == "__main__":
    unittest.main()
