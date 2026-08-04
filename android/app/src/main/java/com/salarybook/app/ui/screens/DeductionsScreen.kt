package com.salarybook.app.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.background
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.salarybook.app.calc.currentMonth
import com.salarybook.app.calc.toDouble
import com.salarybook.app.calc.today
import com.salarybook.app.data.DEDUCTION_CATEGORIES
import com.salarybook.app.data.Deduction
import com.salarybook.app.data.SalaryDao
import com.salarybook.app.ui.components.ConfirmDialog
import com.salarybook.app.ui.components.EmptyHint
import com.salarybook.app.ui.components.LabeledField
import com.salarybook.app.ui.components.MoneyText

@Composable
fun DeductionsScreen(dao: SalaryDao, modifier: Modifier = Modifier, refreshSignal: Int = 0) {
    var items by remember { mutableStateOf<List<Deduction>>(emptyList()) }
    var month by remember { mutableStateOf(currentMonth()) }
    var keyword by remember { mutableStateOf("") }
    var refreshKey by remember { mutableIntStateOf(0) }
    var showEdit by remember { mutableStateOf(false) }
    var editing by remember { mutableStateOf<Deduction?>(null) }
    var deleting by remember { mutableStateOf<Deduction?>(null) }

    val total = items.sumOf { it.amount }

    LaunchedEffect(month, keyword, refreshKey, refreshSignal) {
        items = dao.listDeductions(month.takeIf { it.isNotBlank() }, keyword.trim().takeIf { it.isNotBlank() })
    }

    Scaffold(
        modifier = modifier,
        floatingActionButton = {
            FloatingActionButton(onClick = { editing = null; showEdit = true }) { Icon(Icons.Default.Add, "添加") }
        },
        topBar = {
            Column(Modifier.fillMaxWidth().background(MaterialTheme.colorScheme.primary)) {
                Text("扣款记录", color = MaterialTheme.colorScheme.onPrimary, style = MaterialTheme.typography.titleLarge,
                    modifier = Modifier.padding(start = 16.dp, top = 8.dp, bottom = 4.dp))
                Row(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 6.dp)) {
                    OutlinedTextField(value = month, onValueChange = { month = it }, label = { Text("月份") },
                        singleLine = true, textStyle = LocalTextStyle.current.copy(fontSize = 13.sp), modifier = Modifier.weight(1f))
                    Spacer(Modifier.width(6.dp))
                    OutlinedTextField(value = keyword, onValueChange = { keyword = it }, label = { Text("搜索") },
                        singleLine = true, leadingIcon = { Icon(Icons.Default.Search, null, Modifier.size(18.dp)) },
                        textStyle = LocalTextStyle.current.copy(fontSize = 13.sp), modifier = Modifier.weight(1.2f))
                }
            }
        },
    ) { pad ->
        Column(Modifier.padding(pad).fillMaxSize()) {
            Card(Modifier.fillMaxWidth().padding(12.dp), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer)) {
                Row(Modifier.fillMaxWidth().padding(12.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                    Text("本月扣款合计", fontSize = 14.sp, color = MaterialTheme.colorScheme.onErrorContainer)
                    MoneyText(total, MaterialTheme.colorScheme.error, 20)
                }
            }
            if (items.isEmpty()) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { EmptyHint("暂无扣款记录") }
            } else {
                LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = 96.dp)) {
                    items(items, key = { it.id }) { d ->
                        Card(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 4.dp),
                            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f))) {
                            Row(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
                                Column(Modifier.weight(1f)) {
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Text(d.date, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                                        Spacer(Modifier.width(8.dp))
                                        Text(d.category, fontSize = 12.sp, color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold)
                                    }
                                    if (d.note.isNotBlank()) Text(d.note, fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                }
                                MoneyText(-d.amount, MaterialTheme.colorScheme.error, 16)
                                IconButton(onClick = { editing = d; showEdit = true }, modifier = Modifier.size(28.dp)) { Icon(Icons.Default.Edit, "编辑", Modifier.size(16.dp), tint = Color(0xFF607D8B)) }
                                IconButton(onClick = { deleting = d }, modifier = Modifier.size(28.dp)) { Icon(Icons.Default.Delete, "删除", Modifier.size(16.dp), tint = Color(0xFFC62828)) }
                            }
                        }
                    }
                }
            }
        }
    }

    deleting?.let { d ->
        ConfirmDialog(title = "删除扣款", message = "确定删除 ${d.date} 的扣款（${d.category}）吗？",
            onConfirm = { dao.deleteDeduction(d.id); refreshKey++ }, onDismiss = { deleting = null })
    }
    if (showEdit) {
        DeductionEditDialog(dao, editing, { showEdit = false }) { showEdit = false; refreshKey++ }
    }
}

@Composable
private fun DeductionEditDialog(dao: SalaryDao, existing: Deduction?, onDismiss: () -> Unit, onSaved: () -> Unit) {
    var date by remember { mutableStateOf(existing?.date ?: today()) }
    var cat by remember { mutableStateOf(existing?.category ?: "请假") }
    var amount by remember { mutableStateOf(if (existing != null) existing.amount.toString() else "") }
    var note by remember { mutableStateOf(existing?.note ?: "") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(if (existing == null) "新增扣款" else "编辑扣款") },
        text = {
            Column {
                LabeledField("日期 (YYYY-MM-DD)", date, { date = it })
                Spacer(Modifier.height(8.dp))
                Text("类别", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Row(Modifier.fillMaxWidth()) {
                    DEDUCTION_CATEGORIES.take(3).forEach { c ->
                        FilterChip(selected = cat == c, onClick = { cat = c }, label = { Text(c, fontSize = 12.sp) }, modifier = Modifier.padding(end = 6.dp))
                    }
                }
                Row(Modifier.fillMaxWidth().padding(top = 4.dp)) {
                    DEDUCTION_CATEGORIES.drop(3).forEach { c ->
                        FilterChip(selected = cat == c, onClick = { cat = c }, label = { Text(c, fontSize = 12.sp) }, modifier = Modifier.padding(end = 6.dp))
                    }
                }
                Spacer(Modifier.height(8.dp))
                LabeledField("扣款金额", amount, { amount = it }, keyboard = androidx.compose.ui.text.input.KeyboardType.Decimal)
                Spacer(Modifier.height(8.dp))
                LabeledField("备注", note, { note = it })
            }
        },
        confirmButton = {
            TextButton(onClick = {
                val d = Deduction(id = existing?.id ?: 0, date = date.trim().ifEmpty { today() }, category = cat,
                    amount = toDouble(amount), note = note.trim())
                if (existing == null) dao.insertDeduction(d) else dao.updateDeduction(d)
                onSaved()
            }) { Text("保存") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("取消") } },
    )
}
