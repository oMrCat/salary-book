package com.salarybook.app.sync

import com.salarybook.app.data.Deduction
import com.salarybook.app.data.Payment
import com.salarybook.app.data.SalaryDao
import com.salarybook.app.data.WorkRecord
import org.json.JSONArray
import org.json.JSONObject

object SyncJson {

    const val APP = "salary-book"
    const val VERSION = 1

    fun export(dao: SalaryDao): String {
        val root = JSONObject()
        root.put("app", APP)
        root.put("version", VERSION)
        root.put("exported_at", exportTimestamp())

        val settings = JSONObject()
        dao.getSettings().forEach { (k, v) -> settings.put(k, v) }
        root.put("settings", settings)

        val works = JSONArray()
        dao.allWorks().forEach { w ->
            works.put(
                JSONObject()
                    .put("record_date", w.date)
                    .put("record_type", w.type)
                    .put("start_time", w.startTime)
                    .put("end_time", w.endTime)
                    .put("hours", w.hours)
                    .put("units", w.units)
                    .put("rate", w.rate)
                    .put("amount", w.amount)
                    .put("content", w.content)
                    .put("note", w.note)
                    .put("is_holiday", w.isHoliday)
            )
        }
        root.put("work_records", works)

        val deds = JSONArray()
        dao.allDeductions().forEach { d ->
            deds.put(
                JSONObject()
                    .put("record_date", d.date)
                    .put("category", d.category)
                    .put("amount", d.amount)
                    .put("note", d.note)
            )
        }
        root.put("deductions", deds)

        val pays = JSONArray()
        dao.listPeriods().forEach { p ->
            dao.getPayment(p)?.let { pay ->
                pays.put(
                    JSONObject()
                        .put("period", pay.period)
                        .put("actual_amount", pay.actualAmount)
                        .put("paid_date", pay.paidDate)
                        .put("note", pay.note)
                )
            }
        }
        root.put("payments", pays)
        return root.toString(2)
    }

    fun import(json: String, dao: SalaryDao): String {
        var root = JSONObject(json)
        // 兼容服务器包裹格式：{"ok":true,"app":"salary-book","data":{...}}
        val inner = root.optJSONObject("data")
        if (inner != null && inner.has("work_records")) {
            root = inner
        }
        if (root.optString("app") != APP) throw IllegalArgumentException("不是有效的工资对账数据文件")

        val settings = HashMap<String, String>()
        root.optJSONObject("settings")?.let { s ->
            s.keys().forEach { k -> settings[k] = s.optString(k) }
        }

        val works = ArrayList<WorkRecord>()
        root.optJSONArray("work_records")?.let { arr ->
            for (i in 0 until arr.length()) {
                val o = arr.getJSONObject(i)
                works.add(
                    WorkRecord(
                        date = o.optString("record_date"),
                        type = o.optString("record_type", "计时"),
                        startTime = o.optString("start_time"),
                        endTime = o.optString("end_time"),
                        hours = o.optDouble("hours", 0.0),
                        units = o.optDouble("units", 0.0),
                        rate = o.optDouble("rate", 0.0),
                        amount = o.optDouble("amount", 0.0),
                        content = o.optString("content"),
                        note = o.optString("note"),
                        isHoliday = o.optBoolean("is_holiday"),
                    )
                )
            }
        }

        val deds = ArrayList<Deduction>()
        root.optJSONArray("deductions")?.let { arr ->
            for (i in 0 until arr.length()) {
                val o = arr.getJSONObject(i)
                deds.add(
                    Deduction(
                        date = o.optString("record_date"),
                        category = o.optString("category", "其他"),
                        amount = o.optDouble("amount", 0.0),
                        note = o.optString("note"),
                    )
                )
            }
        }

        val pays = ArrayList<Payment>()
        root.optJSONArray("payments")?.let { arr ->
            for (i in 0 until arr.length()) {
                val o = arr.getJSONObject(i)
                pays.add(
                    Payment(
                        period = o.optString("period"),
                        actualAmount = o.optDouble("actual_amount", 0.0),
                        paidDate = o.optString("paid_date"),
                        note = o.optString("note"),
                    )
                )
            }
        }

        return dao.mergeData(settings, works, deds, pays)
    }

    private fun exportTimestamp(): String {
        val c = java.util.Calendar.getInstance()
        return "%04d-%02d-%02d %02d:%02d".format(
            c.get(java.util.Calendar.YEAR),
            c.get(java.util.Calendar.MONTH) + 1,
            c.get(java.util.Calendar.DAY_OF_MONTH),
            c.get(java.util.Calendar.HOUR_OF_DAY),
            c.get(java.util.Calendar.MINUTE),
        )
    }
}
