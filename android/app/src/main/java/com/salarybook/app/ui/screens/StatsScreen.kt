package com.salarybook.app.ui.screens

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.salarybook.app.calc.annualSummary
import com.salarybook.app.calc.currentMonth
import com.salarybook.app.calc.trend
import com.salarybook.app.data.SalaryDao
import com.salarybook.app.ui.components.MoneyText
import kotlin.math.max

private data class DiffMonth(val month: String, val payable: Double, val actual: Double, val diff: Double)

@Composable
fun StatsScreen(dao: SalaryDao, modifier: Modifier = Modifier, refreshSignal: Int = 0) {
    var refreshKey by remember { mutableIntStateOf(0) }
    var chartType by remember { mutableStateOf("柱形图") }
    val settings = remember { dao.getSettings() }
    val works = remember(refreshKey, refreshSignal) { dao.allWorks() }
    val deductions = remember(refreshKey, refreshSignal) { dao.allDeductions() }
    val periods = remember(refreshKey, refreshSignal) { dao.listPeriods().reversed().takeLast(12) }
    val points = remember(refreshKey, refreshSignal, periods) { trend(periods, works, deductions, dao.listPeriods().mapNotNull { dao.getPayment(it) }, settings) }
    val year = currentMonth().take(4)
    val annual = remember(refreshKey, refreshSignal) { annualSummary(year, works, deductions, settings) }
    val diffMonths = remember(annual) {
        annual.byMonth.mapNotNull { (m, v) ->
            val pay = dao.getPayment(m)
            if (pay != null) {
                val diff = pay.actualAmount - v.third
                if (kotlin.math.abs(diff) >= 0.005) DiffMonth(m, v.third, pay.actualAmount, diff) else null
            } else null
        }
    }

    Column(modifier.fillMaxSize().verticalScroll(rememberScrollState())) {
        Text("统计图表", style = MaterialTheme.typography.titleLarge, modifier = Modifier.padding(16.dp))
        Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp), verticalAlignment = Alignment.CenterVertically) {
            Text("图表类型：", fontSize = 13.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            listOf("柱形图", "折线图", "饼图").forEach { t ->
                FilterChip(
                    selected = chartType == t,
                    onClick = { chartType = t },
                    label = { Text(t, fontSize = 12.sp) },
                    modifier = Modifier.padding(end = 6.dp),
                )
            }
        }
        Card(Modifier.fillMaxWidth().padding(12.dp).height(260.dp)) {
            ChartView(chartType, points, annual.incomeByType)
        }
        // 年度对账汇总
        val recon = remember(annual) {
            var pay = 0.0
            var act = 0.0
            annual.byMonth.forEach { (m, v) ->
                pay += v.third
                dao.getPayment(m)?.let { act += it.actualAmount }
            }
            Triple(pay, act, act - pay)
        }
        if (recon.first > 0) {
            val hasDiff = kotlin.math.abs(recon.third) >= 0.005
            Card(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 4.dp),
                colors = CardDefaults.cardColors(containerColor = if (hasDiff) MaterialTheme.colorScheme.errorContainer else MaterialTheme.colorScheme.primaryContainer)) {
                Row(Modifier.fillMaxWidth().padding(14.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                    Column {
                        Text("$year 年度对账汇总", fontSize = 12.sp, color = if (hasDiff) MaterialTheme.colorScheme.onErrorContainer else MaterialTheme.colorScheme.onPrimaryContainer, fontWeight = FontWeight.Bold)
                        Text("应发合计 ¥${"%.2f".format(recon.first)}   实发合计 ¥${"%.2f".format(recon.second)}",
                            fontSize = 13.sp, fontWeight = FontWeight.Bold,
                            color = if (hasDiff) MaterialTheme.colorScheme.onErrorContainer else MaterialTheme.colorScheme.onPrimaryContainer)
                    }
                    Text(
                        if (!hasDiff && recon.second > 0) "✓ 已对平" else if (recon.second == 0.0) "未登记实发" else "差额 ${if (recon.third >= 0) "+" else ""}¥${"%.2f".format(recon.third)}",
                        fontSize = 15.sp, fontWeight = FontWeight.Bold,
                        color = when {
                            recon.second == 0.0 -> Color(0xFF9E9E9E)
                            hasDiff -> Color(0xFFC62828)
                            else -> Color(0xFF2E7D32)
                        },
                    )
                }
            }
        }
        Text("本月快照（${currentMonth()}）", style = MaterialTheme.typography.titleSmall,
            modifier = Modifier.padding(horizontal = 16.dp))
        Row(Modifier.fillMaxWidth().padding(horizontal = 12.dp)) {
            StatChip("收入", currentMonthIncome(works, settings), Modifier.weight(1f))
            Spacer(Modifier.width(8.dp))
            StatChip("应发", currentMonthPayable(works, deductions, settings), Modifier.weight(1f))
        }
        Spacer(Modifier.height(12.dp))
        if (diffMonths.isNotEmpty()) {
            Row(Modifier.fillMaxWidth().padding(horizontal = 12.dp).background(MaterialTheme.colorScheme.errorContainer).padding(10.dp),
                verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.Warning, null, tint = Color(0xFFC62828), modifier = Modifier.size(18.dp))
                Spacer(Modifier.width(6.dp))
                Text("对账有差额：${diffMonths.joinToString("；") { "${it.month} 差 ¥${"%.2f".format(it.diff)}" }}",
                    color = MaterialTheme.colorScheme.onErrorContainer, fontSize = 12.sp, fontWeight = FontWeight.Bold)
            }
            Spacer(Modifier.height(6.dp))
        }
        Card(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 6.dp), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer)) {
            Column(Modifier.fillMaxWidth().padding(16.dp)) {
                Text("$year 年度汇总", fontWeight = FontWeight.Bold, fontSize = 15.sp)
                Spacer(Modifier.height(8.dp))
                Text("出勤 ${annual.workDays} 天 · 工时 ${annual.workHours} 小时", fontSize = 13.sp)
                Text("全年应发合计", fontSize = 13.sp, color = MaterialTheme.colorScheme.onPrimaryContainer)
                MoneyText(annual.payable, MaterialTheme.colorScheme.primary, 26)
                Text("收入 ¥${"%.2f".format(annual.incomeTotal)} − 扣款 ¥${"%.2f".format(annual.deductionTotal)}", fontSize = 12.sp, color = MaterialTheme.colorScheme.onPrimaryContainer)
                Spacer(Modifier.height(10.dp))
                Text("逐月汇总（含对账差额）：", fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                annual.byMonth.forEach { (m, v) ->
                    val pay = dao.getPayment(m)
                    val diff = pay?.let { it.actualAmount - v.third }
                    val hasDiff = diff != null && kotlin.math.abs(diff) >= 0.005
                    Row(Modifier.fillMaxWidth().padding(vertical = 2.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text(m, fontSize = 13.sp, fontWeight = if (hasDiff) FontWeight.Bold else FontWeight.Normal,
                            color = if (hasDiff) Color(0xFFC62828) else MaterialTheme.colorScheme.onPrimaryContainer)
                        Text(
                            if (pay == null) "应发 ¥${"%.2f".format(v.third)}"
                            else "应发 ¥${"%.2f".format(v.third)}   实发 ¥${"%.2f".format(pay.actualAmount)}   差额 ${if (diff!! >= 0) "+" else ""}¥${"%.2f".format(diff)}",
                            fontSize = 12.sp, fontWeight = if (hasDiff) FontWeight.Bold else FontWeight.Medium,
                            color = if (hasDiff) Color(0xFFC62828) else MaterialTheme.colorScheme.onPrimaryContainer,
                        )
                    }
                }
            }
        }
        Spacer(Modifier.height(24.dp))
    }
}

private fun currentMonthIncome(works: List<com.salarybook.app.data.WorkRecord>, settings: Map<String, String>): Double {
    val m = currentMonth()
    return com.salarybook.app.calc.monthlySummary(
        works.filter { it.date.startsWith(m) }, emptyList(), null, m, settings,
    ).incomeTotal
}

private fun currentMonthPayable(works: List<com.salarybook.app.data.WorkRecord>, deductions: List<com.salarybook.app.data.Deduction>, settings: Map<String, String>): Double {
    val m = currentMonth()
    return com.salarybook.app.calc.monthlySummary(
        works.filter { it.date.startsWith(m) },
        deductions.filter { it.date.startsWith(m) },
        null, m, settings,
    ).payable
}

@Composable
private fun StatChip(label: String, value: Double, modifier: Modifier = Modifier) {
    Card(modifier, colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f))) {
        Column(Modifier.fillMaxWidth().padding(12.dp)) {
            Text(label, fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            MoneyText(value, MaterialTheme.colorScheme.primary, 18)
        }
    }
}

@Composable
private fun ChartView(
    chartType: String,
    points: List<com.salarybook.app.calc.MonthPoint>,
    byType: Map<String, Double>,
) {
    if (chartType == "饼图") {
        PieChart(points, byType)
    } else if (chartType == "折线图") {
        LineChart(points)
    } else {
        BarChart(points)
    }
}

private fun niceMax(v: Double): Float {
    if (v <= 0) return 500f
    val candidates = listOf(500, 1000, 2000, 5000, 10000, 20000, 50000, 100000,
        200000, 500000, 1000000, 2000000, 5000000, 10000000)
    for (m in candidates) if (v <= m) return m.toFloat()
    return (((v / 50000.0).toInt()) + 1) * 50000f
}

private fun shortAmount(v: Float): String =
    if (v >= 10000) "%.0fk".format(v / 1000f) else "%.0f".format(v)

@Composable
private fun BarChart(points: List<com.salarybook.app.calc.MonthPoint>) {
    val incomeColor = Color(0xFF1976D2)
    val payableColor = Color(0xFF2E9E44)
    val actualColor = Color(0xFFFF9800)
    val d = LocalDensity.current.density
    Canvas(Modifier.fillMaxSize().padding(4.dp)) {
        if (points.isEmpty()) return@Canvas
        val w = size.width
        val h = size.height
        val padL = 30f * d; val padR = 6f * d; val padB = 18f * d; val padT = 10f * d
        val plotW = w - padL - padR
        val plotH = h - padT - padB
        val rawMax = maxOf(
            points.maxOfOrNull { it.income } ?: 0.0,
            points.maxOfOrNull { it.payable } ?: 0.0,
            points.maxOfOrNull { if (it.paid) it.actual else 0.0 } ?: 0.0,
            1.0,
        )
        val maxV = niceMax(rawMax)
        val axisColor = Color(0xFFCCCCCC)
        drawLine(axisColor, Offset(padL, padT), Offset(padL, padT + plotH), strokeWidth = 1.5f)
        drawLine(axisColor, Offset(padL, padT + plotH), Offset(padL + plotW, padT + plotH), strokeWidth = 1.5f)
        val rightPaint = axisPaint(android.graphics.Paint.Align.RIGHT, 13f * d)
        val centerPaint = axisPaint(android.graphics.Paint.Align.CENTER, 11f * d)
        val leftPaint = axisPaint(android.graphics.Paint.Align.LEFT, 12f * d)
        for (i in 0..4) {
            val y = padT + plotH - plotH * i / 4f
            drawLine(axisColor, Offset(padL - 3f * d, y), Offset(padL, y), strokeWidth = 1f)
            drawContext.canvas.nativeCanvas.drawText(shortAmount(maxV * i / 4f), padL - 4f * d, y + 4f * d, rightPaint)
        }
        val n = points.size
        val slot = plotW / n
        val barW = (slot * 0.13f).coerceAtMost(10f * d)
        points.forEachIndexed { i, p ->
            var x0 = padL + slot * i + slot * 0.30f
            val bars = listOf(
                Triple(p.income.toFloat(), incomeColor, true),
                Triple(p.payable.toFloat(), payableColor, true),
                Triple(p.actual.toFloat(), actualColor, p.paid),
            )
            for ((v, color, show) in bars) {
                if (!show) continue
                val hh = (v / maxV) * plotH
                drawRect(color, Offset(x0, padT + plotH - hh), Size(barW, hh))
                x0 += barW + 1f * d
            }
            drawContext.canvas.nativeCanvas.drawText(p.period.take(7).substring(2), padL + slot * i + slot / 2f, padT + plotH + 12f * d, centerPaint)
        }
        drawDiffMarkers(points, padL, slot, padT, d)
        var lx = padL
        val sw = 6f * d
        fun legendItem(color: Color, label: String) {
            drawRect(color, Offset(lx, 3f * d), Size(sw, sw))
            drawContext.canvas.nativeCanvas.drawText(label, lx + sw + 3f * d, 7f * d + sw, leftPaint)
            lx += sw + 3f * d + label.length * 7f * d + 6f * d
        }
        legendItem(incomeColor, "收入")
        legendItem(payableColor, "应发")
        legendItem(actualColor, "实发")
        drawCircle(Color(0xFFE53935), radius = 2.5f * d, center = Offset(lx + 3f * d, 6f * d))
        drawContext.canvas.nativeCanvas.drawText("有差额", lx + 7f * d, 7f * d + sw, leftPaint)
    }
}

private fun androidx.compose.ui.graphics.drawscope.DrawScope.drawDiffMarkers(
    points: List<com.salarybook.app.calc.MonthPoint>,
    padL: Float,
    slot: Float,
    padT: Float,
    d: Float,
) {
    points.forEachIndexed { i, p ->
        if (p.paid && kotlin.math.abs(p.diff) >= 0.005) {
            val cx = padL + slot * i + slot / 2f
            drawCircle(Color(0xFFE53935), radius = 2.5f * d, center = Offset(cx, padT + 5f * d))
        }
    }
}

@Composable
private fun LineChart(points: List<com.salarybook.app.calc.MonthPoint>) {
    val incomeColor = Color(0xFF1976D2)
    val payableColor = Color(0xFF2E9E44)
    val actualColor = Color(0xFFFF9800)
    val d = LocalDensity.current.density
    Canvas(Modifier.fillMaxSize().padding(4.dp)) {
        if (points.isEmpty()) return@Canvas
        val w = size.width
        val h = size.height
        val padL = 30f * d; val padR = 6f * d; val padB = 18f * d; val padT = 10f * d
        val plotW = w - padL - padR
        val plotH = h - padT - padB
        val rawMax = maxOf(
            points.maxOfOrNull { it.income } ?: 0.0,
            points.maxOfOrNull { it.payable } ?: 0.0,
            points.maxOfOrNull { if (it.paid) it.actual else 0.0 } ?: 0.0,
            1.0,
        )
        val maxV = niceMax(rawMax)
        val axisColor = Color(0xFFCCCCCC)
        drawLine(axisColor, Offset(padL, padT), Offset(padL, padT + plotH), strokeWidth = 1.5f)
        drawLine(axisColor, Offset(padL, padT + plotH), Offset(padL + plotW, padT + plotH), strokeWidth = 1.5f)
        val rightPaint = axisPaint(android.graphics.Paint.Align.RIGHT, 13f * d)
        val centerPaint = axisPaint(android.graphics.Paint.Align.CENTER, 11f * d)
        val leftPaint = axisPaint(android.graphics.Paint.Align.LEFT, 12f * d)
        for (i in 0..4) {
            val y = padT + plotH - plotH * i / 4f
            drawLine(axisColor, Offset(padL - 3f * d, y), Offset(padL, y), strokeWidth = 1f)
            drawContext.canvas.nativeCanvas.drawText(shortAmount(maxV * i / 4f), padL - 4f * d, y + 4f * d, rightPaint)
        }
        val n = points.size
        val slot = plotW / n
        val series = listOf(
            Triple("income", incomeColor, true) to { p: com.salarybook.app.calc.MonthPoint -> p.income.toFloat() },
            Triple("payable", payableColor, true) to { p -> p.payable.toFloat() },
            Triple("actual", actualColor, points.any { it.paid }) to { p -> p.actual.toFloat() },
        )
        for ((meta, getter) in series) {
            val (key, color, anyShow) = meta
            if (!anyShow) continue
            val pts = ArrayList<Offset>()
            points.forEachIndexed { i, p ->
                if (key == "actual" && !p.paid) return@forEachIndexed
                val x = padL + slot * i + slot / 2f
                val v = getter(p)
                val y = padT + plotH - (v / maxV) * plotH
                pts.add(Offset(x, y))
                drawCircle(color, radius = 2f * d, center = Offset(x, y))
            }
            for (i in 1 until pts.size) {
                drawLine(color, pts[i - 1], pts[i], strokeWidth = 2.5f)
            }
        }
        points.forEachIndexed { i, p ->
            drawContext.canvas.nativeCanvas.drawText(p.period.take(7).substring(2), padL + slot * i + slot / 2f, padT + plotH + 12f * d, centerPaint)
        }
        drawDiffMarkers(points, padL, slot, padT, d)
        var lx = padL
        val sw = 6f * d
        fun legendItem(color: Color, label: String) {
            drawRect(color, Offset(lx, 3f * d), Size(sw, sw))
            drawContext.canvas.nativeCanvas.drawText(label, lx + sw + 3f * d, 7f * d + sw, leftPaint)
            lx += sw + 3f * d + label.length * 7f * d + 6f * d
        }
        legendItem(incomeColor, "收入")
        legendItem(payableColor, "应发")
        legendItem(actualColor, "实发")
        drawCircle(Color(0xFFE53935), radius = 2.5f * d, center = Offset(lx + 3f * d, 6f * d))
        drawContext.canvas.nativeCanvas.drawText("有差额", lx + 7f * d, 7f * d + sw, leftPaint)
    }
}

@Composable
private fun PieChart(points: List<com.salarybook.app.calc.MonthPoint>, byType: Map<String, Double>) {
    val colors = listOf(Color(0xFF1976D2), Color(0xFF2E9E44), Color(0xFFFF9800), Color(0xFF9C27B0), Color(0xFFE53935), Color(0xFF00ACC1))
    val d = LocalDensity.current.density
    Canvas(Modifier.fillMaxSize().padding(4.dp)) {
        val items = byType.filterValues { it > 0 }.toList()
        val w = size.width
        val h = size.height
        val legendW = 120f * d
        val leftPaint = axisPaint(android.graphics.Paint.Align.LEFT, 12f * d)
        if (items.isEmpty()) {
            drawContext.canvas.nativeCanvas.drawText("暂无收入数据", w / 2f, h / 2f, leftPaint)
            return@Canvas
        }
        val total = items.sumOf { it.second }
        val cx = (w - legendW) / 2f
        val cy = h / 2f + 4f * d
        val r = minOf((w - legendW) / 2f - 10f * d, h / 2f - 16f * d)
        var start = 0.0
        items.forEachIndexed { i, (_, v) ->
            val sweep = 360.0 * v / total
            drawArc(
                color = colors[i % colors.size],
                startAngle = start.toFloat(),
                sweepAngle = sweep.toFloat(),
                useCenter = true,
                topLeft = Offset(cx - r, cy - r),
                size = Size(r * 2, r * 2),
            )
            start += sweep
        }
        // 右侧：收入构成图例 + 对账汇总
        val lx = (w - legendW) + 8f * d
        var ly = 8f * d
        val titlePaint = axisPaint(android.graphics.Paint.Align.LEFT, 14f * d).apply { isFakeBoldText = true }
        drawContext.canvas.nativeCanvas.drawText("收入构成", lx, ly, titlePaint)
        ly += 12f * d
        items.forEachIndexed { i, (k, v) ->
            drawRect(colors[i % colors.size], Offset(lx, ly - 5f * d), Size(6f * d, 6f * d))
            drawContext.canvas.nativeCanvas.drawText(
                "$k ¥" + "%.2f".format(v) + "  " + "%.1f".format(v / total * 100) + "%",
                lx + 9f * d, ly, leftPaint)
            ly += 12f * d
        }
        val totalPayable = points.filter { it.paid }.sumOf { it.payable }
        val totalActual = points.filter { it.paid }.sumOf { it.actual }
        val diffAll = totalActual - totalPayable
        ly += 5f * d
        drawContext.canvas.nativeCanvas.drawText("应发 ¥" + "%.2f".format(totalPayable), lx, ly, leftPaint)
        ly += 12f * d
        drawContext.canvas.nativeCanvas.drawText("实发 ¥" + "%.2f".format(totalActual), lx, ly, leftPaint)
        ly += 12f * d
        if (totalActual > 0) {
            val diffText = if (kotlin.math.abs(diffAll) < 0.005) "✓ 已对平"
            else "差额 ${if (diffAll >= 0) "+" else ""}¥${"%.2f".format(diffAll)}"
            val p = axisPaint(android.graphics.Paint.Align.LEFT, 15f * d).apply {
                color = if (kotlin.math.abs(diffAll) < 0.005) android.graphics.Color.rgb(46, 125, 50) else android.graphics.Color.rgb(198, 40, 40)
                isFakeBoldText = true
            }
            drawContext.canvas.nativeCanvas.drawText(diffText, lx, ly, p)
        } else {
            drawContext.canvas.nativeCanvas.drawText("未登记实发", lx, ly, leftPaint)
        }
    }
}

private fun axisPaint(align: android.graphics.Paint.Align, size: Float): android.graphics.Paint =
    android.graphics.Paint().apply {
        color = android.graphics.Color.GRAY
        textSize = size
        textAlign = align
    }
