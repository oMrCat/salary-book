package com.salarybook.app.data

import android.content.ContentValues
import android.database.sqlite.SQLiteDatabase

/**
 * 数据访问对象：全部方法与 Windows 端 salary_app/db.py 的 Database 类语义一致。
 *
 * mergeData 的去重签名算法与 Windows 端 _work_sig/_ded_sig 保持一致
 * （数值按两位小数归一、is_holiday 归一为 1/0），确保跨端同步去重结果相同。
 */
class SalaryDao(private val db: SalaryDb) {

    private val database: SQLiteDatabase get() = db.writableDatabase

    // ---------- 设置 ----------

    fun getSettings(): Map<String, String> {
        db.seedSettings()
        val out = HashMap<String, String>()
        database.rawQuery("SELECT key, value FROM settings", null).use { c ->
            while (c.moveToNext()) out[c.getString(0)] = c.getString(1) ?: ""
        }
        return out
    }

    fun saveSettings(data: Map<String, String>) {
        database.beginTransaction()
        try {
            for ((key, value) in data) {
                val cv = ContentValues().apply {
                    put("key", key)
                    put("value", value)
                }
                database.insertWithOnConflict(
                    "settings", null, cv, SQLiteDatabase.CONFLICT_REPLACE)
            }
            database.setTransactionSuccessful()
        } finally {
            database.endTransaction()
        }
    }

    // ---------- 工作记录 ----------

    fun insertWork(rec: WorkRecord): Long = database.insert("work_records", null, workCv(rec))

    fun updateWork(rec: WorkRecord) {
        database.update("work_records", workCv(rec), "id=?", arrayOf(rec.id.toString()))
    }

    fun deleteWork(id: Int) {
        database.delete("work_records", "id=?", arrayOf(id.toString()))
    }

    fun listWork(month: String? = null, keyword: String? = null): List<WorkRecord> {
        val sql = StringBuilder(
            "SELECT id, record_date, record_type, start_time, end_time, hours, " +
                "units, rate, amount, content, note, is_holiday FROM work_records")
        val args = mutableListOf<String>()
        val conds = mutableListOf<String>()
        if (!month.isNullOrEmpty()) {
            conds.add("record_date LIKE ?")
            args.add("$month%")
        }
        if (!keyword.isNullOrEmpty()) {
            conds.add("(content LIKE ? OR note LIKE ? OR record_date LIKE ?)")
            val kw = "%$keyword%"
            args += listOf(kw, kw, kw)
        }
        if (conds.isNotEmpty()) sql.append(" WHERE ").append(conds.joinToString(" AND "))
        sql.append(" ORDER BY record_date DESC, id DESC")
        val out = ArrayList<WorkRecord>()
        database.rawQuery(sql.toString(), args.toTypedArray()).use { c ->
            while (c.moveToNext()) out.add(workFromCursor(c))
        }
        return out
    }

    fun allWorks(): List<WorkRecord> = listWork(null)

    private fun workCv(r: WorkRecord) = ContentValues().apply {
        put("record_date", r.date)
        put("record_type", r.type)
        put("start_time", r.startTime)
        put("end_time", r.endTime)
        put("hours", r.hours)
        put("units", r.units)
        put("rate", r.rate)
        put("amount", r.amount)
        put("content", r.content)
        put("note", r.note)
        put("is_holiday", if (r.isHoliday) 1 else 0)
    }

    private fun workFromCursor(c: android.database.Cursor) = WorkRecord(
        id = c.getInt(0),
        date = c.getString(1) ?: "",
        type = c.getString(2) ?: "计时",
        startTime = c.getString(3) ?: "",
        endTime = c.getString(4) ?: "",
        hours = c.getDouble(5),
        units = c.getDouble(6),
        rate = c.getDouble(7),
        amount = c.getDouble(8),
        content = c.getString(9) ?: "",
        note = c.getString(10) ?: "",
        isHoliday = c.getInt(11) != 0,
    )

    // ---------- 扣款记录 ----------

    fun insertDeduction(d: Deduction): Long = database.insert("deductions", null, dedCv(d))

    fun updateDeduction(d: Deduction) {
        database.update("deductions", dedCv(d), "id=?", arrayOf(d.id.toString()))
    }

    fun deleteDeduction(id: Int) {
        database.delete("deductions", "id=?", arrayOf(id.toString()))
    }

    fun listDeductions(month: String? = null, keyword: String? = null): List<Deduction> {
        val sql = StringBuilder(
            "SELECT id, record_date, category, amount, note FROM deductions")
        val args = mutableListOf<String>()
        val conds = mutableListOf<String>()
        if (!month.isNullOrEmpty()) {
            conds.add("record_date LIKE ?")
            args.add("$month%")
        }
        if (!keyword.isNullOrEmpty()) {
            conds.add("(note LIKE ? OR category LIKE ? OR record_date LIKE ?)")
            val kw = "%$keyword%"
            args += listOf(kw, kw, kw)
        }
        if (conds.isNotEmpty()) sql.append(" WHERE ").append(conds.joinToString(" AND "))
        sql.append(" ORDER BY record_date DESC, id DESC")
        val out = ArrayList<Deduction>()
        database.rawQuery(sql.toString(), args.toTypedArray()).use { c ->
            while (c.moveToNext()) out.add(
                Deduction(
                    id = c.getInt(0),
                    date = c.getString(1) ?: "",
                    category = c.getString(2) ?: "其他",
                    amount = c.getDouble(3),
                    note = c.getString(4) ?: "",
                )
            )
        }
        return out
    }

    fun allDeductions(): List<Deduction> = listDeductions(null)

    private fun dedCv(d: Deduction) = ContentValues().apply {
        put("record_date", d.date)
        put("category", d.category)
        put("amount", d.amount)
        put("note", d.note)
    }

    // ---------- 发薪记录 ----------

    fun getPayment(period: String): Payment? {
        database.rawQuery(
            "SELECT id, period, actual_amount, paid_date, note FROM payments WHERE period=?",
            arrayOf(period)
        ).use { c ->
            if (c.moveToFirst()) return paymentFromCursor(c)
        }
        return null
    }

    fun savePayment(p: Payment) {
        val cv = ContentValues().apply {
            put("period", p.period)
            put("actual_amount", p.actualAmount)
            put("paid_date", p.paidDate)
            put("note", p.note)
        }
        database.insertWithOnConflict(
            "payments", null, cv, SQLiteDatabase.CONFLICT_REPLACE)
    }

    fun listPeriods(): List<String> {
        val out = ArrayList<String>()
        database.rawQuery(
            "SELECT DISTINCT substr(record_date, 1, 7) AS p FROM work_records " +
                "UNION SELECT DISTINCT substr(record_date, 1, 7) FROM deductions " +
                "UNION SELECT period FROM payments ORDER BY p DESC", null
        ).use { c ->
            while (c.moveToNext()) {
                val p = c.getString(0)
                if (!p.isNullOrEmpty()) out.add(p)
            }
        }
        return out
    }

    private fun paymentFromCursor(c: android.database.Cursor) = Payment(
        id = c.getInt(0),
        period = c.getString(1) ?: "",
        actualAmount = c.getDouble(2),
        paidDate = c.getString(3) ?: "",
        note = c.getString(4) ?: "",
    )

    // ---------- 合并导入（与 Windows 端 merge_data 行为一致） ----------

    /** 合并导入：完全相同的记录去重、不同的追加；发薪按月份更新。返回统计文本。 */
    fun mergeData(
        settings: Map<String, String>,
        works: List<WorkRecord>,
        deductions: List<Deduction>,
        payments: List<Payment>,
    ): String {
        var addedWork = 0; var dupWork = 0
        var addedDed = 0; var dupDed = 0
        var payNew = 0; var payUpd = 0
        database.beginTransaction()
        try {
            if (settings.isNotEmpty()) saveSettingsLocked(settings)

            val existingW = HashSet<String>()
            database.rawQuery(WORK_SIG_QUERY, null).use { c ->
                while (c.moveToNext()) existingW.add(workSigRow(
                    c.getString(0), c.getString(1), c.getString(2), c.getString(3),
                    c.getDouble(4), c.getDouble(5), c.getDouble(6), c.getDouble(7),
                    c.getString(8), c.getString(9), c.getInt(10) != 0))
            }
            for (w in works) {
                val sig = workSig(w)
                if (sig in existingW) { dupWork++; continue }
                database.insert("work_records", null, workCv(w))
                existingW.add(sig)
                addedWork++
            }

            val existingD = HashSet<String>()
            database.rawQuery(
                "SELECT record_date, category, amount, note FROM deductions", null
            ).use { c ->
                while (c.moveToNext()) existingD.add(dedSig(
                    c.getString(0) ?: "", c.getString(1) ?: "",
                    c.getDouble(2), c.getString(3) ?: ""))
            }
            for (d in deductions) {
                val sig = dedSig(d.date, d.category, d.amount, d.note)
                if (sig in existingD) { dupDed++; continue }
                database.insert("deductions", null, dedCv(d))
                existingD.add(sig)
                addedDed++
            }

            for (p in payments) {
                if (p.period.isEmpty()) continue
                val cur = getPaymentLocked(p.period)
                if (cur == null) {
                    database.insert("payments", null, payCv(p))
                    payNew++
                } else if (cur.actualAmount != p.actualAmount ||
                    cur.paidDate != p.paidDate || cur.note != p.note) {
                    database.update("payments", payCv(p), "period=?", arrayOf(p.period))
                    payUpd++
                }
            }
            database.setTransactionSuccessful()
        } finally {
            database.endTransaction()
        }
        return "新增工作 $addedWork 条、相同 $dupWork 条；" +
            "新增扣款 $addedDed 条、相同 $dupDed 条；" +
            "发薪新增 $payNew 条、更新 $payUpd 条"
    }

    private fun saveSettingsLocked(data: Map<String, String>) {
        for ((key, value) in data) {
            val cv = ContentValues().apply {
                put("key", key)
                put("value", value)
            }
            database.insertWithOnConflict(
                "settings", null, cv, SQLiteDatabase.CONFLICT_REPLACE)
        }
    }

    private fun getPaymentLocked(period: String): Payment? {
        database.rawQuery(
            "SELECT id, period, actual_amount, paid_date, note FROM payments WHERE period=?",
            arrayOf(period)
        ).use { c ->
            if (c.moveToFirst()) return paymentFromCursor(c)
        }
        return null
    }

    private fun payCv(p: Payment) = ContentValues().apply {
        put("period", p.period)
        put("actual_amount", p.actualAmount)
        put("paid_date", p.paidDate)
        put("note", p.note)
    }

    // ---------- 去重签名（与 Windows 端 _norm_sig_value 算法一致） ----------

    private fun numSig(v: Double): String {
        // round(x, 2) 后去掉多余小数位，与 Python str(round(v, 2)) 输出一致
        val r = kotlin.math.round(v * 100) / 100
        return if (r == kotlin.math.floor(r)) {
            // 整数值输出一位小数（Python float str 行为：8.0 -> "8.0"）
            "${r.toInt()}.0"
        } else {
            r.toString()
        }
    }

    private fun workSig(
        date: String, type: String, startTime: String, endTime: String,
        hours: Double, units: Double, rate: Double, amount: Double,
        content: String, note: String, isHoliday: Boolean,
    ): String = listOf(
        date, type, startTime, endTime,
        numSig(hours), numSig(units), numSig(rate), numSig(amount),
        content, note, if (isHoliday) "1" else "0",
    ).joinToString("|")

    private fun workSig(w: WorkRecord): String = workSig(
        w.date, w.type, w.startTime, w.endTime,
        w.hours, w.units, w.rate, w.amount, w.content, w.note, w.isHoliday)

    private fun workSigRow(
        date: String?, type: String?, startTime: String?, endTime: String?,
        hours: Double, units: Double, rate: Double, amount: Double,
        content: String?, note: String?, isHoliday: Boolean,
    ): String = workSig(
        date ?: "", type ?: "", startTime ?: "", endTime ?: "",
        hours, units, rate, amount, content ?: "", note ?: "", isHoliday)

    private fun dedSig(date: String, category: String, amount: Double, note: String): String =
        listOf(date, category, numSig(amount), note).joinToString("|")

    private companion object {
        val WORK_SIG_QUERY =
            "SELECT record_date, record_type, start_time, end_time, hours, " +
                "units, rate, amount, content, note, is_holiday FROM work_records"
    }
}
