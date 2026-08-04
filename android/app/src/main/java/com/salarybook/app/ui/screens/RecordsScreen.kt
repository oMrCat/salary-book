package com.salarybook.app.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.background
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material.icons.filled.Login
import androidx.compose.material.icons.filled.Logout
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.salarybook.app.calc.computeWorkAmount
import com.salarybook.app.calc.currentMonth
import com.salarybook.app.calc.monthlySummary
import com.salarybook.app.calc.toDouble
import com.salarybook.app.calc.today
import com.salarybook.app.data.RECORD_TYPES
import com.salarybook.app.data.SalaryDao
import com.salarybook.app.data.WorkRecord
import com.salarybook.app.ui.components.ConfirmDialog
import com.salarybook.app.ui.components.EmptyHint
import com.salarybook.app.ui.components.LabeledField
import com.salarybook.app.ui.components.MoneyText
import com.salarybook.app.ui.components.TypeBadge
import com.salarybook.app.ui.components.fmtQty

@Composable
fun RecordsScreen(dao: SalaryDao, modifier: Modifier = Modifier, refreshSignal: Int = 0) {
    var works by remember { mutableStateOf<List<WorkRecord>>(emptyList()) }
    var month by remember { mutableStateOf(currentMonth()) }
    var keyword by remember { mutableStateOf("") }
    var refreshKey by remember { mutableIntStateOf(0) }
    var showEdit by remember { mutableStateOf(false) }
    var editing by remember { mutableStateOf<WorkRecord?>(null) }
    var deleting by remember { mutableStateOf<WorkRecord?>(null) }
    var clockInfo by remember { mutableStateOf("") }
    var showClockConfirm by remember { mutableStateOf(false) }

    fun reload() {
        val s = dao.getSettings()
        works = dao.listWork(month.takeIf { it.isNotBlank() }, keyword.trim().takeIf { it.isNotBlank() })
            .map { it.copy(amount = computeWorkAmount(it, s)) }
        if (s["clock_in_date"] == today() && s["clock_in_time"]?.isNotEmpty() == true) {
            clockInfo = "已上班打卡 ${s["clock_in_time"]}"
        } else {
            clockInfo = "未打卡"
        }
    }
    LaunchedEffect(month, keyword, refreshKey, refreshSignal) { reload() }

    val settings = remember { dao.getSettings() }
    val summary = remember(works) {
        monthlySummary(works, dao.listDeductions(month.takeIf { it.isNotBlank() }), dao.getPayment(month), month, settings)
    }

    Scaffold(
        modifier = modifier,
        floatingActionButton = {
            FloatingActionButton(onClick = {
                editing = null
                showEdit = true
            }) {
                Icon(Icons.Default.Add, contentDescription = "添加")
            }
        },
        topBar = {
            Column(Modifier.fillMaxWidth().background(MaterialTheme.colorScheme.primary)) {
                Text(
                    "工作记录",
                    color = MaterialTheme.colorScheme.onPrimary,
                    style = MaterialTheme.typography.titleLarge,
                    modifier = Modifier.padding(start = 16.dp, top = 8.dp, bottom = 4.dp),
                )
                Row(
                    Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 6.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    OutlinedTextField(
                        value = month,
                        onValueChange = { month = it },
                        label = { Text("月份 YYYY-MM") },
                        singleLine = true,
                        textStyle = LocalTextStyle.current.copy(fontSize = 13.sp),
                        modifier = Modifier.weight(1f),
                    )
                    Spacer(Modifier.width(6.dp))
                    OutlinedTextField(
                        value = keyword,
                        onValueChange = { keyword = it },
                        label = { Text("搜索") },
                        singleLine = true,
                        leadingIcon = { Icon(Icons.Default.Search, null, Modifier.size(18.dp)) },
                        textStyle = LocalTextStyle.current.copy(fontSize = 13.sp),
                        modifier = Modifier.weight(1.2f),
                    )
                }
            }
        },
    ) { pad ->
        Column(Modifier.padding(pad).fillMaxSize()) {
            // 打卡快捷栏
            Card(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 6.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer),
            ) {
                Row(
                    Modifier.fillMaxWidth().padding(12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(Modifier.weight(1f)) {
                        Text("快捷打卡", fontWeight = FontWeight.Bold, fontSize = 13.sp)
                        Text(clockInfo, fontSize = 12.sp, color = MaterialTheme.colorScheme.onSecondaryContainer)
                    }
                    Button(
                        onClick = {
                            dao.saveSettings(mapOf("clock_in_date" to today(), "clock_in_time" to java.text.SimpleDateFormat("HH:mm").format(java.util.Date())))
                            reload()
                        },
                        colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary),
                    ) { Icon(Icons.Default.Login, null, Modifier.size(16.dp)); Spacer(Modifier.width(4.dp)); Text("上班") }
                    Spacer(Modifier.width(8.dp))
                    Button(
                        onClick = { showClockConfirm = true },
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE65100)),
                    ) { Icon(Icons.Default.Logout, null, Modifier.size(16.dp)); Spacer(Modifier.width(4.dp)); Text("下班") }
                }
            }

            Card(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 4.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer),
            ) {
                Row(Modifier.fillMaxWidth().padding(12.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                    Column { Text("出勤 ${summary.workDays} 天", fontSize = 13.sp, fontWeight = FontWeight.Medium); Text("工时 ${summary.workHours}", fontSize = 12.sp, color = MaterialTheme.colorScheme.onPrimaryContainer) }
                    Column(horizontalAlignment = Alignment.End) { Text("收入", fontSize = 12.sp, color = MaterialTheme.colorScheme.onPrimaryContainer); MoneyText(summary.incomeTotal, MaterialTheme.colorScheme.onPrimaryContainer, 18) }
                    Column(horizontalAlignment = Alignment.End) { Text("应发", fontSize = 12.sp, color = MaterialTheme.colorScheme.onPrimaryContainer); MoneyText(summary.payable, MaterialTheme.colorScheme.primary, 18) }
                }
            }

            if (works.isEmpty()) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    EmptyHint("本月暂无记录，点右下角 + 添加")
                }
            } else {
                LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = 96.dp)) {
                    items(works, key = { it.id }) { w ->
                        WorkCard(
                            w = w,
                            onEdit = { editing = w; showEdit = true },
                            onDelete = { deleting = w },
                        )
                    }
                }
            }
        }
    }

    if (showClockConfirm) {
        ConfirmClockOut(dao) {
            showClockConfirm = false
            refreshKey++
        }
    }

    if (deleting != null) {
        ConfirmDialog(
            title = "删除记录",
            message = "确定删除 ${deleting!!.date} 的这条记录吗？",
            onConfirm = { dao.deleteWork(deleting!!.id); refreshKey++ },
            onDismiss = { deleting = null },
        )
    }

    if (showEdit) {
        WorkEditDialog(
            dao = dao,
            existing = editing,
            onDismiss = { showEdit = false },
            onSaved = { showEdit = false; refreshKey++ },
        )
    }
}

@Composable
private fun WorkCard(w: WorkRecord, onEdit: () -> Unit, onDelete: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 4.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f)),
    ) {
        Row(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(w.date, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                    Spacer(Modifier.width(6.dp))
                    TypeBadge(w.type)
                    if (w.isHoliday) {
                        Text("节假日", fontSize = 10.sp, color = Color(0xFFE65100), fontWeight = FontWeight.Bold)
                    }
                }
                val detail = buildString {
                    if (w.content.isNotBlank()) { append(w.content); append("  ") }
                    if (w.startTime.isNotBlank() || w.endTime.isNotBlank()) append("${w.startTime}-${w.endTime}  ")
                    if (w.hours > 0) append("${fmtQty(w.hours)}${if (w.type == "出勤") "天" else "小时"}  ")
                    if (w.units > 0) append("${fmtQty(w.units)}件")
                }
                Text(detail.ifBlank { "—" }, fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Column(horizontalAlignment = Alignment.End) {
                MoneyText(w.amount, MaterialTheme.colorScheme.primary, 16)
                Row {
                    IconButton(onClick = onEdit, modifier = Modifier.size(28.dp)) { Icon(Icons.Default.Edit, "编辑", Modifier.size(16.dp), tint = Color(0xFF607D8B)) }
                    IconButton(onClick = onDelete, modifier = Modifier.size(28.dp)) { Icon(Icons.Default.Delete, "删除", Modifier.size(16.dp), tint = Color(0xFFC62828)) }
                }
            }
        }
    }
}

@Composable
private fun ConfirmClockOut(dao: SalaryDao, onDone: () -> Unit) {
    val s = dao.getSettings()
    AlertDialog(
        onDismissRequest = onDone,
        title = { Text("下班打卡") },
        text = {
            if (s["clock_in_date"] != today() || s["clock_in_time"].isNullOrEmpty()) {
                Text("今天还没有上班打卡，无法下班打卡")
            } else {
                val start = s["clock_in_time"]!!
                val end = java.text.SimpleDateFormat("HH:mm").format(java.util.Date())
                val rec = WorkRecord(
                    date = today(), type = "计时", startTime = start, endTime = end,
                    rate = toDouble(dao.getSettings()["hourly_rate"]),
                )
                val amount = computeWorkAmount(rec, dao.getSettings())
                Text("将记录 ${start}-${end} 的计时工作，金额约 ¥${"%.2f".format(amount)}。确定打卡？")
            }
        },
        confirmButton = {
            if (s["clock_in_date"] == today() && !s["clock_in_time"].isNullOrEmpty()) {
                TextButton(onClick = {
                    val start = s["clock_in_time"]!!
                    val end = java.text.SimpleDateFormat("HH:mm").format(java.util.Date())
                    val rec = WorkRecord(
                        date = today(), type = "计时", startTime = start, endTime = end,
                        rate = toDouble(dao.getSettings()["hourly_rate"]),
                    )
                    val amount = computeWorkAmount(rec, dao.getSettings())
                    dao.insertWork(rec.copy(amount = amount))
                    dao.saveSettings(mapOf("clock_in_date" to "", "clock_in_time" to ""))
                    onDone()
                }) { Text("打卡") }
            }
        },
        dismissButton = { TextButton(onClick = onDone) { Text("取消") } },
    )
}

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
private fun WorkEditDialog(dao: SalaryDao, existing: WorkRecord?, onDismiss: () -> Unit, onSaved: () -> Unit) {
    var date by remember { mutableStateOf(existing?.date ?: today()) }
    var type by remember { mutableStateOf(if (existing?.type == "出勤") "按天" else (existing?.type ?: "计时")) }
    var start by remember { mutableStateOf(existing?.startTime ?: "") }
    var end by remember { mutableStateOf(existing?.endTime ?: "") }
    var hours by remember { mutableStateOf(if (existing != null && existing.hours > 0) existing.hours.toString() else "") }
    var units by remember { mutableStateOf(if (existing != null && existing.units > 0) existing.units.toString() else "") }
    var rate by remember { mutableStateOf(if (existing != null && existing.rate > 0) existing.rate.toString() else "") }
    var content by remember { mutableStateOf(existing?.content ?: "") }
    var note by remember { mutableStateOf(existing?.note ?: "") }
    var holiday by remember { mutableStateOf(existing?.isHoliday ?: false) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(if (existing == null) "新增工作记录" else "编辑工作记录") },
        text = {
            Column(Modifier.verticalScroll(rememberScrollState())) {
                LabeledField("日期 (YYYY-MM-DD)", date, { date = it })
                Spacer(Modifier.height(8.dp))
                Text("类型", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                FlowRow {
                    RECORD_TYPES.forEach { t ->
                        FilterChip(
                            selected = type == t,
                            onClick = { type = t },
                            label = { Text(t, fontSize = 12.sp) },
                            modifier = Modifier.padding(end = 6.dp, bottom = 4.dp),
                        )
                    }
                }
                val qtyLabel = when (type) {
                    "计时", "加班" -> "时长(小时)"
                    "计件" -> "件数"
                    "按天" -> "天数"
                    "按月" -> "月数"
                    else -> "时长"
                }
                val typeHint = when (type) {
                    "计时" -> "金额 = 时长(小时) × 时薪"
                    "加班" -> "金额 = 时长(小时) × 时薪 × 加班倍数"
                    "计件" -> "金额 = 件数 × 计件单价"
                    "按天" -> "金额 = 天数 × 日薪（留空默认1天）"
                    "按月" -> "金额 = 月数 × 固定月薪（留空默认1月）"
                    else -> ""
                }
                Spacer(Modifier.height(6.dp))
                Text(typeHint, fontSize = 12.sp, color = Color(0xFF1976D2), fontWeight = FontWeight.Medium)
                Row(Modifier.fillMaxWidth()) {
                    Box(Modifier.weight(1f)) { LabeledField("开始 HH:MM", start, { start = it }) }
                    Spacer(Modifier.width(8.dp))
                    Box(Modifier.weight(1f)) { LabeledField("结束 HH:MM", end, { end = it }) }
                }
                Spacer(Modifier.height(8.dp))
                Row(Modifier.fillMaxWidth()) {
                    Box(Modifier.weight(1f)) { LabeledField(qtyLabel, hours, { hours = it }, keyboard = androidx.compose.ui.text.input.KeyboardType.Decimal) }
                    Spacer(Modifier.width(8.dp))
                    if (type != "按月") {
                        Box(Modifier.weight(1f)) { LabeledField("件数", units, { units = it }, keyboard = androidx.compose.ui.text.input.KeyboardType.Decimal) }
                    } else {
                        Box(Modifier.weight(1f)) { Spacer(Modifier.height(1.dp)) }
                    }
                }
                Spacer(Modifier.height(8.dp))
                LabeledField("单价（留空用规则）", rate, { rate = it }, keyboard = androidx.compose.ui.text.input.KeyboardType.Decimal)
                Spacer(Modifier.height(8.dp))
                LabeledField("工作内容", content, { content = it })
                Spacer(Modifier.height(8.dp))
                LabeledField("备注", note, { note = it })
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Checkbox(checked = holiday, onCheckedChange = { holiday = it })
                    Text("节假日（加班按节假日倍数计算）", fontSize = 13.sp)
                }
            }
        },
        confirmButton = {
            TextButton(onClick = {
                val rec = WorkRecord(
                    id = existing?.id ?: 0,
                    date = date.trim().ifEmpty { today() },
                    type = type,
                    startTime = start.trim(),
                    endTime = end.trim(),
                    hours = toDouble(hours),
                    units = toDouble(units),
                    rate = toDouble(rate),
                    content = content.trim(),
                    note = note.trim(),
                    isHoliday = holiday,
                )
                val amount = computeWorkAmount(rec, dao.getSettings())
                val finalRec = rec.copy(amount = amount)
                if (existing == null) dao.insertWork(finalRec) else dao.updateWork(finalRec)
                onSaved()
            }) { Text("保存") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("取消") } },
    )
}
