package com.salarybook.app.ui.screens

import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.salarybook.app.calc.currentMonth
import com.salarybook.app.calc.monthlySummary
import com.salarybook.app.calc.toDouble
import com.salarybook.app.calc.today
import com.salarybook.app.data.Payment
import com.salarybook.app.data.SalaryDao
import com.salarybook.app.ui.components.LabeledField
import com.salarybook.app.ui.components.MoneyText
import com.salarybook.app.ui.components.TypeBadge
import kotlin.math.abs

@Composable
fun ReconcileScreen(dao: SalaryDao, modifier: Modifier = Modifier, refreshSignal: Int = 0) {
    var period by remember { mutableStateOf(currentMonth()) }
    var refreshKey by remember { mutableIntStateOf(0) }
    var showActual by remember { mutableStateOf(false) }
    var actualInput by remember { mutableStateOf("") }
    val context = LocalContext.current
    val clipboard = LocalClipboardManager.current

    val settings = remember { dao.getSettings() }
    val works = remember(period, refreshKey, refreshSignal) { dao.listWork(period) }
    val deductions = remember(period, refreshKey, refreshSignal) { dao.listDeductions(period) }
    val payment = remember(period, refreshKey, refreshSignal) { dao.getPayment(period) }
    val summary = remember(period, works, deductions, payment) {
        monthlySummary(works, deductions, payment, period, settings)
    }

    Scaffold(
        modifier = modifier,
        topBar = {
            Column(Modifier.fillMaxWidth().background(MaterialTheme.colorScheme.primary)) {
                Text("月度对账", color = MaterialTheme.colorScheme.onPrimary, style = MaterialTheme.typography.titleLarge,
                    modifier = Modifier.padding(start = 16.dp, top = 8.dp, bottom = 4.dp))
                Row(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 6.dp), verticalAlignment = Alignment.CenterVertically) {
                    OutlinedTextField(value = period, onValueChange = { period = it }, label = { Text("月份 YYYY-MM") },
                        singleLine = true, textStyle = LocalTextStyle.current.copy(fontSize = 13.sp), modifier = Modifier.weight(1f))
                    Spacer(Modifier.width(6.dp))
                    Button(onClick = { refreshKey++ }) { Text("汇总") }
                    Spacer(Modifier.width(6.dp))
                    Button(onClick = {
                        val text = buildString {
                            append("【$period 工资对账】\n")
                            append("出勤 ${summary.workDays} 天，工时 ${summary.workHours} 小时\n")
                            append("收入合计 ¥${"%.2f".format(summary.incomeTotal)}\n")
                            append("扣款合计 ¥${"%.2f".format(summary.deductionTotal)}\n")
                            append("应发工资 ¥${"%.2f".format(summary.payable)}\n")
                            if (summary.actual == null) append("实发金额 未登记")
                            else {
                                append("实发金额 ¥${"%.2f".format(summary.actual)}\n")
                                append("差额 ¥${"%.2f".format(summary.diff)}\n")
                                append("对账结果 ${if (summary.balanced) "已对平" else "有差额，请核对"}")
                            }
                        }
                        clipboard.setText(AnnotatedString(text))
                        Toast.makeText(context, "对账结果已复制", Toast.LENGTH_SHORT).show()
                    }) { Icon(Icons.Default.ContentCopy, null, Modifier.size(16.dp)); Spacer(Modifier.width(4.dp)); Text("复制") }
                }
            }
        },
    ) { pad ->
        Column(Modifier.padding(pad).fillMaxSize()) {
            if (summary.actual == null && summary.works.isNotEmpty() || (summary.actual != null && !summary.balanced)) {
                val msg = when {
                    summary.actual == null -> "本月工资尚未登记实发，请登记后核对"
                    else -> "实发与应发不一致，请核对"
                }
                Row(Modifier.fillMaxWidth().background(MaterialTheme.colorScheme.errorContainer).padding(12.dp),
                    verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.Warning, null, tint = MaterialTheme.colorScheme.error)
                    Spacer(Modifier.width(8.dp))
                    Text(msg, color = MaterialTheme.colorScheme.onErrorContainer, fontWeight = FontWeight.SemiBold, fontSize = 13.sp)
                }
            }

            // 汇总卡片
            Card(Modifier.fillMaxWidth().padding(12.dp), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer)) {
                Column(Modifier.fillMaxWidth().padding(16.dp)) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Column(horizontalAlignment = Alignment.Start) {
                            Text("应发工资", color = MaterialTheme.colorScheme.onPrimaryContainer, fontSize = 13.sp)
                            MoneyText(summary.payable, MaterialTheme.colorScheme.onPrimaryContainer, 30)
                        }
                        Column(horizontalAlignment = Alignment.End) {
                            Text("收入 / 扣款", color = MaterialTheme.colorScheme.onPrimaryContainer, fontSize = 12.sp)
                            Text("¥${"%.2f".format(summary.incomeTotal)} / -¥${"%.2f".format(summary.deductionTotal)}", color = MaterialTheme.colorScheme.onPrimaryContainer, fontSize = 13.sp, fontWeight = FontWeight.Medium)
                        }
                    }
                    Spacer(Modifier.height(10.dp))
                    HorizontalDivider(color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.2f))
                    Spacer(Modifier.height(10.dp))
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Column { Text("出勤", fontSize = 12.sp, color = MaterialTheme.colorScheme.onPrimaryContainer); Text("${summary.workDays} 天", fontSize = 15.sp, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onPrimaryContainer) }
                        Column { Text("工时", fontSize = 12.sp, color = MaterialTheme.colorScheme.onPrimaryContainer); Text("${summary.workHours} 小时", fontSize = 15.sp, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onPrimaryContainer) }
                        Column { Text("实发", fontSize = 12.sp, color = MaterialTheme.colorScheme.onPrimaryContainer); Text(summary.actual?.let { "¥%.2f".format(it) } ?: "未登记", fontSize = 15.sp, fontWeight = FontWeight.Bold, color = if (summary.actual == null) Color(0xFF9E9E9E) else MaterialTheme.colorScheme.onPrimaryContainer) }
                        Column { Text("差额", fontSize = 12.sp, color = MaterialTheme.colorScheme.onPrimaryContainer); Text(summary.diff?.let { (if (it >= 0) "+" else "") + "¥%.2f".format(it) } ?: "—", fontSize = 15.sp, fontWeight = FontWeight.Bold, color = if (summary.balanced) Color(0xFF2E7D32) else if (summary.diff != null) Color(0xFFC62828) else MaterialTheme.colorScheme.onPrimaryContainer) }
                    }
                    Spacer(Modifier.height(10.dp))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        if (summary.actual != null) {
                            Icon(if (summary.balanced) Icons.Default.CheckCircle else Icons.Default.Warning,
                                null, tint = if (summary.balanced) Color(0xFF2E7D32) else Color(0xFFC62828), modifier = Modifier.size(18.dp))
                            Spacer(Modifier.width(6.dp))
                            Text(if (summary.balanced) "✓ 已对平" else "✗ 有差额，请核对",
                                color = if (summary.balanced) Color(0xFF2E7D32) else Color(0xFFC62828), fontWeight = FontWeight.Bold)
                        } else {
                            Text("未登记实发", color = Color(0xFF757575), fontWeight = FontWeight.Medium)
                        }
                    }
                    Spacer(Modifier.height(10.dp))
                    HorizontalDivider(color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.2f))
                    Spacer(Modifier.height(8.dp))
                    // 应发构成（标注具体项目）
                    val byType = summary.incomeByType
                    if (byType.isNotEmpty() || summary.deductionTotal > 0) {
                        val typeParts = buildString {
                            for (t in listOf("计时", "计件", "按天", "按月", "加班", "出勤")) {
                                val v = byType[t] ?: 0.0
                                if (v > 0) { if (isNotEmpty()) append(" + "); append("$t ¥%.2f".format(v)) }
                            }
                        }
                        Text("应发 ¥${"%.2f".format(summary.payable)} = $typeParts" +
                                if (summary.deductionTotal > 0) "，扣款 -¥${"%.2f".format(summary.deductionTotal)}" else "",
                            fontSize = 12.sp, color = MaterialTheme.colorScheme.onPrimaryContainer)
                        if (summary.actual != null && !summary.balanced) {
                            val d = summary.diff ?: 0.0
                            Text("⚠ 实发 ¥${"%.2f".format(summary.actual)}，差额 ${if (d >= 0) "+" else ""}¥${"%.2f".format(d)}，请核对各项目是否有漏记/错记",
                                fontSize = 12.sp, fontWeight = FontWeight.Bold, color = Color(0xFFC62828))
                        }
                    }
                }
            }

            if (summary.works.isEmpty() && deductions.isEmpty()) {
                Column(Modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally) {
                    Spacer(Modifier.height(40.dp))
                    Text("本月暂无记录", color = Color(0xFF909090))
                }
            } else {
                LazyColumn(Modifier.fillMaxWidth().weight(1f), contentPadding = PaddingValues(bottom = 12.dp)) {
                    item { Text("收入 / 扣款明细", style = MaterialTheme.typography.titleSmall, modifier = Modifier.padding(horizontal = 16.dp, vertical = 6.dp)) }
                    items(summary.works, key = { it.id }) { w ->
                        Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                            TypeBadge(w.type)
                            Spacer(Modifier.width(8.dp))
                            Column(Modifier.weight(1f)) {
                                Text(w.date, fontSize = 13.sp)
                                val detail = buildString {
                                    if (w.content.isNotBlank()) append(w.content)
                                    if (w.startTime.isNotBlank()) { if (isNotEmpty()) append("  "); append("${w.startTime}-${w.endTime}") }
                                }
                                if (detail.isNotBlank()) Text(detail, fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                            MoneyText(w.amount, MaterialTheme.colorScheme.primary, 15)
                        }
                    }
                    items(deductions, key = { it.id }) { d ->
                        Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                            Text("扣款·${d.category}", fontSize = 12.sp, color = MaterialTheme.colorScheme.error, modifier = Modifier.width(90.dp))
                            Text(d.note, fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.weight(1f))
                            MoneyText(-d.amount, MaterialTheme.colorScheme.error, 15)
                        }
                    }
                }
            }

            Button(
                onClick = {
                    actualInput = summary.actual?.let { "%.2f".format(it) } ?: ""
                    showActual = true
                },
                modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp).height(52.dp),
                shape = RoundedCornerShape(14.dp),
            ) { Text(if (summary.actual == null) "登记实发工资" else "修改实发工资", fontSize = 16.sp, fontWeight = FontWeight.Bold) }
        }
    }

    if (showActual) {
        val pay = summary.payment
        AlertDialog(
            onDismissRequest = { showActual = false },
            title = { Text(if (pay == null) "登记实发" else "修改实发") },
            text = {
                Column {
                    LabeledField("实发金额", actualInput, { actualInput = it }, keyboard = androidx.compose.ui.text.input.KeyboardType.Decimal)
                    Spacer(Modifier.height(8.dp))
                    LabeledField("实发日期", payment?.paidDate ?: "", { }, placeholder = today())
                }
            },
            confirmButton = {
                TextButton(onClick = {
                    val amount = toDouble(actualInput)
                    if (amount < 0) {
                        Toast.makeText(context, "金额不能为负", Toast.LENGTH_SHORT).show()
                    } else {
                        dao.savePayment(Payment(period = period, actualAmount = amount, paidDate = today()))
                        showActual = false
                        refreshKey++
                    }
                }) { Text("保存") }
            },
            dismissButton = { TextButton(onClick = { showActual = false }) { Text("取消") } },
        )
    }
}
