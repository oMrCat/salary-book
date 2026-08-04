package com.salarybook.app.sync

import com.salarybook.app.data.Deduction
import com.salarybook.app.data.Payment
import com.salarybook.app.data.SalaryDao
import com.salarybook.app.data.WorkRecord

/**
 * Excel 导入/导出数据映射（与 Windows 端格式一致：前 3 行标题占位、第 4 行表头、第 5 行起为数据）。
 */
object XlsxSync {

    fun exportSheets(dao: SalaryDao, company: String): List<Pair<String, List<List<Any>>>> {
        val title = "薪资记录账本 · 全部数据" + (if (company.isNotBlank()) " · $company" else "")
        val blank = listOf("", "", "", "", "", "", "", "", "", "", "")
        val workHeader = listOf("日期", "类型", "开始", "结束", "时长/天", "件数", "单价", "金额", "节假日", "工作内容", "备注")
        val workRows = ArrayList<List<Any>>()
        workRows.add(listOf(title)); workRows.add(blank); workRows.add(blank); workRows.add(workHeader)
        val settings = dao.getSettings()
        dao.allWorks().forEach { w ->
            // 金额按当前工资规则实时重算，保证与界面一致
            val amount = com.salarybook.app.calc.computeWorkAmount(w, settings)
            workRows.add(listOf(
                w.date, w.type, w.startTime, w.endTime,
                if (w.hours > 0) w.hours else "", if (w.units > 0) w.units else "",
                if (w.rate > 0) w.rate else "", if (amount > 0) amount else "",
                if (w.isHoliday) "是" else "", w.content, w.note,
            ))
        }

        val dedHeader = listOf("日期", "类别", "金额", "备注")
        val dedRows = ArrayList<List<Any>>()
        dedRows.add(listOf(title)); dedRows.add(listOf("")); dedRows.add(listOf("")); dedRows.add(dedHeader)
        dao.allDeductions().forEach { d ->
            dedRows.add(listOf(d.date, d.category, d.amount, d.note))
        }

        val payHeader = listOf("月份", "实发金额", "实发日期", "备注")
        val payRows = ArrayList<List<Any>>()
        payRows.add(listOf(title)); payRows.add(listOf("")); payRows.add(listOf("")); payRows.add(payHeader)
        dao.listPeriods().forEach { p ->
            dao.getPayment(p)?.let { pay ->
                payRows.add(listOf(pay.period, pay.actualAmount, pay.paidDate, pay.note))
            }
        }

        return listOf(
            "工作记录" to workRows,
            "扣款记录" to dedRows,
            "发薪记录" to payRows,
        )
    }

    fun importSheets(dao: SalaryDao, sheets: List<Xlsx.Sheet>): String {
        val byName = sheets.associateBy { it.name }
        val works = ArrayList<WorkRecord>()
        val deductions = ArrayList<Deduction>()
        val payments = ArrayList<Payment>()

        val workSheet = byName["工作记录"] ?: byName["收入明细"]
        if (workSheet != null) {
            val isAll = byName.containsKey("工作记录")
            workSheet.rows.forEach { row ->
                if (row.number < 5 || row.cells.isEmpty() || row.cells[0].isBlank()) return@forEach
                val c = row.cells
                val date = c[0].trim()
                val type = c.getOrElse(1) { "计时" }.trim()
                if (isAll) {
                    works.add(WorkRecord(
                        date = date, type = type,
                        startTime = c.getOrElse(2) { "" }.trim(),
                        endTime = c.getOrElse(3) { "" }.trim(),
                        hours = c.getOrElse(4) { "" }.toDoubleOrNull() ?: 0.0,
                        units = c.getOrElse(5) { "" }.toDoubleOrNull() ?: 0.0,
                        rate = c.getOrElse(6) { "" }.toDoubleOrNull() ?: 0.0,
                        amount = c.getOrElse(7) { "" }.toDoubleOrNull() ?: 0.0,
                        isHoliday = c.getOrElse(8) { "" }.trim() == "是",
                        content = c.getOrElse(9) { "" }.trim(),
                        note = c.getOrElse(10) { "" }.trim(),
                    ))
                } else {
                    val content = c.getOrElse(2) { "" }.trim()
                    val qty = c.getOrElse(3) { "" }.toDoubleOrNull() ?: 0.0
                    val rate = c.getOrElse(4) { "" }.toDoubleOrNull() ?: 0.0
                    val amount = c.getOrElse(5) { "" }.toDoubleOrNull() ?: 0.0
                    val holiday = c.getOrElse(6) { "" }.trim() == "是"
                    works.add(WorkRecord(
                        date = date, type = type, content = content,
                        hours = if (type == "出勤") qty else 0.0,
                        units = if (type == "计件") qty else 0.0,
                        rate = rate, amount = amount, isHoliday = holiday,
                    ))
                }
            }
        }

        val dedSheet = byName["扣款记录"] ?: byName["扣款明细"]
        dedSheet?.rows?.forEach { row ->
            if (row.number < 5 || row.cells.isEmpty() || row.cells[0].isBlank()) return@forEach
            val c = row.cells
            deductions.add(Deduction(
                date = c[0].trim(),
                category = c.getOrElse(1) { "其他" }.trim(),
                amount = c.getOrElse(2) { "" }.toDoubleOrNull() ?: 0.0,
                note = c.getOrElse(3) { "" }.trim(),
            ))
        }

        val paySheet = byName["发薪记录"]
        paySheet?.rows?.forEach { row ->
            if (row.number < 5 || row.cells.isEmpty() || row.cells[0].isBlank()) return@forEach
            val c = row.cells
            payments.add(Payment(
                period = c[0].trim(),
                actualAmount = c.getOrElse(1) { "" }.toDoubleOrNull() ?: 0.0,
                paidDate = c.getOrElse(2) { "" }.trim(),
                note = c.getOrElse(3) { "" }.trim(),
            ))
        }

        return dao.mergeData(dao.getSettings(), works, deductions, payments)
    }
}
