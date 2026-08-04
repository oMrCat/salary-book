package com.salarybook.app.calc

import com.salarybook.app.data.Payment
import com.salarybook.app.data.WorkRecord
import java.util.Calendar

fun toDouble(v: Any?, default: Double = 0.0): Double = when (v) {
    is Number -> v.toDouble()
    is String -> v.trim().toDoubleOrNull() ?: default
    else -> default
}

fun diffHours(start: String, end: String): Double {
    fun parse(t: String): Long? {
        val parts = t.trim().split(":")
        if (parts.size < 2) return null
        val h = parts[0].toIntOrNull() ?: return null
        val m = parts[1].toIntOrNull() ?: return null
        return h * 3600L + m * 60L
    }
    val s = parse(start) ?: return 0.0
    val e = parse(end) ?: return 0.0
    var delta = (e - s) / 3600.0
    if (delta < 0) delta += 24
    return delta
}

fun computeWorkAmount(r: WorkRecord, settings: Map<String, String>): Double {
    var rate = toDouble(r.rate)
    if (rate <= 0) {
        rate = when (r.type) {
            "计时", "加班" -> toDouble(settings["hourly_rate"])
            "计件" -> toDouble(settings["piece_rate"])
            "按天", "出勤" -> toDouble(settings["daily_rate"])
            "按月" -> toDouble(settings["monthly_salary"])
            else -> 0.0
        }
    }
    when (r.type) {
        "计件" -> return (r.units * rate).round2()
        "按天", "出勤" -> {
            var days = r.hours
            if (days <= 0) days = 1.0
            return (days * rate).round2()
        }
        "按月" -> {
            var months = r.hours
            if (months <= 0) months = 1.0
            return (months * rate).round2()
        }
    }
    var hours = r.hours
    if (hours <= 0) hours = diffHours(r.startTime, r.endTime)
    if (r.type == "加班") {
        val mult = if (r.isHoliday)
            toDouble(settings["holiday_multiplier"], 3.0)
        else
            toDouble(settings["overtime_multiplier"], 1.5)
        hours *= mult
    } else if (r.isHoliday && r.type == "计时") {
        hours *= toDouble(settings["holiday_multiplier"], 3.0)
    }
    return (hours * rate).round2()
}

private fun Double.round2(): Double = kotlin.math.round(this * 100) / 100

data class MonthlySummary(
    val period: String,
    val works: List<WorkRecord>,
    val incomeTotal: Double,
    val incomeByType: Map<String, Double>,
    val deductionTotal: Double,
    val payable: Double,
    val payment: Payment?,
    val actual: Double?,
    val diff: Double?,
    val balanced: Boolean,
    val workDays: Int,
    val workHours: Double,
)

data class MonthPoint(
    val period: String,
    val income: Double,
    val payable: Double,
    val actual: Double,
    val diff: Double,
    val paid: Boolean,
)

data class AnnualSummary(
    val year: String,
    val incomeTotal: Double,
    val deductionTotal: Double,
    val payable: Double,
    val workDays: Int,
    val workHours: Double,
    val byMonth: Map<String, Triple<Double, Double, Double>>, // income, deduction, payable
    val incomeByType: Map<String, Double>,
)

fun monthAttendance(works: List<WorkRecord>): Pair<Int, Double> {
    val days = HashSet<String>()
    var hours = 0.0
    for (w in works) {
        if (w.type == "按月") continue
        days.add(w.date)
        var h = w.hours
        if (h <= 0 && w.startTime.isNotEmpty() && w.endTime.isNotEmpty()) {
            h = diffHours(w.startTime, w.endTime)
        }
        if (h > 0) hours += h
    }
    return days.size to kotlin.math.round(hours * 10) / 10
}

fun monthlySummary(
    works: List<WorkRecord>,
    deductions: List<com.salarybook.app.data.Deduction>,
    payment: Payment?,
    period: String,
    settings: Map<String, String>,
): MonthlySummary {
    val amounts = works.associateWith { computeWorkAmount(it, settings) }
    var income = 0.0
    for (w in works) income += amounts[w] ?: 0.0
    income = kotlin.math.round(income * 100) / 100.0
    val dedTotal = kotlin.math.round(deductions.sumOf { it.amount } * 100) / 100.0
    val payable = kotlin.math.round((income - dedTotal) * 100) / 100.0

    val actual = payment?.actualAmount?.let { kotlin.math.round(it * 100) / 100.0 }
    val diff = if (actual != null) kotlin.math.round((actual - payable) * 100) / 100.0 else null
    val balanced = actual != null && (diff ?: 0.0) < 0.005 && (diff ?: 0.0) > -0.005

    val byType = HashMap<String, Double>()
    for (w in works) {
        val v = amounts[w] ?: 0.0
        byType[w.type] = (byType[w.type] ?: 0.0) + v
    }

    val (days, hours) = monthAttendance(works)
    return MonthlySummary(
        period = period,
        works = works,
        incomeTotal = income,
        incomeByType = byType,
        deductionTotal = dedTotal,
        payable = payable,
        payment = payment,
        actual = actual,
        diff = diff,
        balanced = balanced,
        workDays = days,
        workHours = hours,
    )
}

fun trend(periods: List<String>, allWorks: List<WorkRecord>, allDeductions: List<com.salarybook.app.data.Deduction>, allPayments: List<Payment>, settings: Map<String, String>): List<MonthPoint> {
    return periods.map { p ->
        val s = monthlySummary(
            allWorks.filter { it.date.startsWith(p) },
            allDeductions.filter { it.date.startsWith(p) },
            allPayments.find { it.period == p },
            p, settings,
        )
        MonthPoint(p, s.incomeTotal, s.payable, s.actual ?: 0.0, s.diff ?: 0.0, s.payment != null)
    }
}

fun annualSummary(year: String, allWorks: List<WorkRecord>, allDeductions: List<com.salarybook.app.data.Deduction>, settings: Map<String, String>): AnnualSummary {
    val works = allWorks.filter { it.date.startsWith(year) }
    val deductions = allDeductions.filter { it.date.startsWith(year) }
    var income = 0.0
    for (w in works) income += computeWorkAmount(w, settings)
    income = kotlin.math.round(income * 100) / 100.0
    val ded = kotlin.math.round(deductions.sumOf { it.amount } * 100) / 100.0
    val payable = kotlin.math.round((income - ded) * 100) / 100.0
    val (days, hours) = monthAttendance(works)

    val byMonth = sortedMapOf<String, Triple<Double, Double, Double>>()
    for (w in works) {
        val m = w.date.take(7)
        val (i, d, p) = byMonth[m] ?: Triple(0.0, 0.0, 0.0)
        byMonth[m] = Triple(i + computeWorkAmount(w, settings), d, p)
    }
    for (d in deductions) {
        val m = d.date.take(7)
        val (i, dd, p) = byMonth[m] ?: Triple(0.0, 0.0, 0.0)
        byMonth[m] = Triple(i, dd + d.amount, p)
    }
    byMonth.keys.forEach { m ->
        val (i, d, _) = byMonth[m]!!
        byMonth[m] = Triple(i, d, i - d)
    }
    val byType = HashMap<String, Double>()
    for (w in works) {
        val v = computeWorkAmount(w, settings)
        byType[w.type] = (byType[w.type] ?: 0.0) + v
    }
    return AnnualSummary(year, income, ded, payable, days, hours, byMonth, byType)
}

fun today(): String {
    val c = Calendar.getInstance()
    val y = c.get(Calendar.YEAR)
    val m = c.get(Calendar.MONTH) + 1
    val d = c.get(Calendar.DAY_OF_MONTH)
    return "%04d-%02d-%02d".format(y, m, d)
}

fun currentMonth(): String = today().take(7)
