# -*- coding: utf-8 -*-
"""回归测试：Excel 报表导入必须保留原始字段（曾因列偏移导致金额/内容丢失）。"""
import os
import sys
import tempfile
import unittest
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from salary_app import calc, db as dbmod, excel  # noqa: E402


SETTINGS = {
    "hourly_rate": "100", "daily_rate": "0", "piece_rate": "0", "monthly_salary": "0",
    "overtime_multiplier": "1.5", "holiday_multiplier": "3", "payday": "10",
}


class ExcelRoundTripTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="salbk_test_")
        self.src = dbmod.Database(os.path.join(self.tmp, "src.db"))
        self.src.save_settings(dict(SETTINGS))
        self.dst = dbmod.Database(os.path.join(self.tmp, "dst.db"))
        self.dst.save_settings(dict(SETTINGS))

    def tearDown(self):
        pass

    def _roundtrip(self, name, exporter):
        path = os.path.join(self.tmp, name)
        exporter(path)
        excel.import_excel(path, self.dst)

    def test_month_report_keeps_fields(self):
        self.src.add_work({"record_date": "2026-08-01", "record_type": "计时", "start_time": "09:00",
                           "end_time": "18:00", "hours": 8, "rate": 100, "amount": 800,
                           "content": "仓库盘点", "note": "正常班", "is_holiday": 0})
        self.src.add_work({"record_date": "2026-08-02", "record_type": "计件", "hours": 0,
                           "units": 120, "rate": 2, "amount": 240,
                           "content": "打包", "note": "", "is_holiday": 0})
        self.src.add_deduction({"record_date": "2026-08-03", "category": "请假",
                                "amount": 100, "note": "请假一天"})

        self._roundtrip("month.xlsx", lambda p: excel.export_month(
            p, calc.monthly_summary(self.src, "2026-08"), "测试公司"))

        works = sorted(self.dst.list_work(), key=lambda w: w["record_date"])
        self.assertEqual(["仓库盘点", "打包"], [w["content"] for w in works])
        self.assertEqual([8.0, 0.0], [w["hours"] for w in works])
        self.assertEqual([0.0, 120.0], [w["units"] for w in works])
        self.assertEqual([100.0, 2.0], [w["rate"] for w in works])
        self.assertEqual([800.0, 240.0], [w["amount"] for w in works])

        ded = self.dst.list_deductions()[0]
        self.assertEqual(100.0, ded["amount"])
        self.assertEqual("请假一天", ded["note"])

    def test_year_report_keeps_fields(self):
        self.src.add_work({"record_date": "2026-03-05", "record_type": "计时", "start_time": "09:00",
                           "end_time": "17:00", "hours": 7, "rate": 100, "amount": 700,
                           "content": "巡检", "note": "", "is_holiday": 0})
        self.src.add_deduction({"record_date": "2026-03-06", "category": "迟到",
                                "amount": 20, "note": "迟到 10 分钟"})

        self._roundtrip("year.xlsx", lambda p: excel.export_year(
            p, calc.annual_summary(self.src, "2026"), "测试公司"))

        work = self.dst.list_work()[0]
        self.assertEqual("巡检", work["content"])
        self.assertEqual(7.0, work["hours"])
        self.assertEqual(700.0, work["amount"])
        ded = self.dst.list_deductions()[0]
        self.assertEqual(20.0, ded["amount"])
        self.assertEqual("迟到 10 分钟", ded["note"])

    def test_datetime_cells_are_normalised(self):
        # 用户在 Excel 里重新保存后，日期列可能变成日期类型而不是文本
        from openpyxl import Workbook
        path = os.path.join(self.tmp, "edited.xlsx")
        wb = Workbook()
        ws = wb.active
        ws.title = "收入明细"
        ws.append(["公司", "测试公司"])
        ws.append(["月份", "2026-08"])
        ws.append([])
        ws.append(["日期", "类型", "工作内容", "时长/件数", "单价", "金额", "节假日"])
        ws.append([datetime.datetime(2026, 8, 1), "计时", "巡检", 8, 100, 800, ""])
        wb.save(path)

        excel.import_excel(path, self.dst)
        work = self.dst.list_work()[0]
        self.assertEqual("2026-08-01", work["record_date"])
        self.assertEqual("巡检", work["content"])
        self.assertEqual(800.0, work["amount"])


if __name__ == "__main__":
    unittest.main()
