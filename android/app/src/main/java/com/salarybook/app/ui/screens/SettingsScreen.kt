package com.salarybook.app.ui.screens

import android.net.Uri
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.FileUpload
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Send
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.salarybook.app.data.SalaryDao
import com.salarybook.app.sync.Discovery
import com.salarybook.app.sync.LanClient
import com.salarybook.app.sync.SyncJson
import com.salarybook.app.sync.Xlsx
import com.salarybook.app.sync.XlsxSync
import com.salarybook.app.ui.components.LabeledField
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@Composable
fun SettingsScreen(dao: SalaryDao, modifier: Modifier = Modifier, onDataChanged: () -> Unit = {}) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var rules by remember { mutableStateOf(dao.getSettings()) }
    var deviceList by remember { mutableStateOf<List<Discovery.Device>>(emptyList()) }
    var syncStatus by remember { mutableStateOf("") }

    fun toast(msg: String) = Toast.makeText(context, msg, Toast.LENGTH_LONG).show()

    // 定时刷新已发现设备
    LaunchedEffect(Unit) {
        while (true) {
            deviceList = Discovery.deviceList()
            delay(1500)
        }
    }

    fun doSync(dev: Discovery.Device, direction: String) {
        scope.launch {
            syncStatus = if (direction == "pull") {
                try {
                    val json = withContext(Dispatchers.IO) { LanClient.pull(dev.host, dev.port) }
                    val msg = SyncJson.import(json, dao)
                    rules = dao.getSettings()
                    onDataChanged()
                    "✓ 从「${dev.name}」拉取成功：$msg"
                } catch (e: Exception) { "✗ 拉取失败：${e.message}" }
            } else {
                try {
                    val res = withContext(Dispatchers.IO) {
                        LanClient.push(dev.host, dev.port, SyncJson.export(dao))
                    }
                    "✓ 已推送到「${dev.name}」：$res"
                } catch (e: Exception) { "✗ 推送失败：${e.message}" }
            }
            toast(syncStatus)
        }
    }

    fun scan() {
        scope.launch {
            syncStatus = "正在扫描局域网设备…"
            deviceList = withContext(Dispatchers.IO) { Discovery.scan() }
            syncStatus = if (deviceList.isEmpty())
                "未发现设备：请确认对方软件已开启、端口服务已启动，且连同一 WiFi"
            else "发现 ${deviceList.size} 台设备"
            toast(syncStatus)
        }
    }

    var manualHost by remember { mutableStateOf("") }
    var manualPort by remember { mutableStateOf("18080") }

    // JSON 文件备份（微信互传 / 换机迁移）
    val exportLauncher = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/json")) { uri ->
        if (uri != null) {
            scope.launch {
                try {
                    val json = SyncJson.export(dao)
                    withContext(Dispatchers.IO) {
                        context.contentResolver.openOutputStream(uri)?.use { it.write(json.toByteArray(Charsets.UTF_8)) }
                    }
                    toast("已导出 JSON 备份")
                } catch (e: Exception) {
                    toast("导出失败：${e.message}")
                }
            }
        }
    }
    val importLauncher = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri: Uri? ->
        if (uri != null) {
            scope.launch {
                try {
                    val text = withContext(Dispatchers.IO) {
                        context.contentResolver.openInputStream(uri)?.use { it.readBytes().toString(Charsets.UTF_8) } ?: ""
                    }
                    val msg = SyncJson.import(text, dao)
                    rules = dao.getSettings()
                    onDataChanged()
                    toast("导入成功：$msg")
                } catch (e: Exception) {
                    toast("导入失败：${e.message}")
                }
            }
        }
    }

    // Excel 导出 / 导入
    val excelExportLauncher = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")) { uri ->
        if (uri != null) {
            scope.launch {
                try {
                    val sheets = withContext(Dispatchers.IO) { XlsxSync.exportSheets(dao, dao.getSettings()["company"] ?: "") }
                    withContext(Dispatchers.IO) {
                        context.contentResolver.openOutputStream(uri)?.use { out -> Xlsx.write(out, sheets) }
                    }
                    toast("已导出 Excel（工作/扣款/发薪 3 个工作表）")
                } catch (e: Exception) {
                    toast("导出失败：${e.message}")
                }
            }
        }
    }
    val excelImportLauncher = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri: Uri? ->
        if (uri != null) {
            scope.launch {
                try {
                    val sheets = withContext(Dispatchers.IO) {
                        context.contentResolver.openInputStream(uri)?.use { Xlsx.read(it) } ?: emptyList()
                    }
                    val msg = XlsxSync.importSheets(dao, sheets)
                    rules = dao.getSettings()
                    onDataChanged()
                    toast("Excel 导入成功：$msg")
                } catch (e: Exception) {
                    toast("导入失败：${e.message}")
                }
            }
        }
    }

    fun manualSync(direction: String) {
        val port = manualPort.trim().toIntOrNull()
        if (manualHost.isBlank() || port == null) {
            toast("请填写有效的 IP 和端口")
            return
        }
        scope.launch {
            syncStatus = if (direction == "pull") {
                try {
                    val json = withContext(Dispatchers.IO) { LanClient.pull(manualHost.trim(), port) }
                    val msg = SyncJson.import(json, dao)
                    rules = dao.getSettings()
                    onDataChanged()
                    "✓ 拉取成功：$msg"
                } catch (e: Exception) { "✗ 拉取失败：${e.message}" }
            } else {
                try {
                    val res = withContext(Dispatchers.IO) {
                        LanClient.push(manualHost.trim(), port, SyncJson.export(dao))
                    }
                    "✓ 推送成功：$res"
                } catch (e: Exception) { "✗ 推送失败：${e.message}" }
            }
            toast(syncStatus)
        }
    }

    Column(modifier.fillMaxSize().verticalScroll(rememberScrollState())) {
        Text("设置", style = MaterialTheme.typography.titleLarge, modifier = Modifier.padding(16.dp))

        // ---- 数据同步（自动发现设备） ----
        Card(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 8.dp)) {
            Column(Modifier.fillMaxWidth().padding(16.dp)) {
                Text("数据同步", style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.height(4.dp))
                Text("两端软件连同一 WiFi 时会自动互相发现，点设备旁的「拉取/推送」即可同步（类似 LocalSend）",
                    fontSize = 12.sp, color = Color(0xFF757575))
                Spacer(Modifier.height(6.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Button(onClick = { scan() }, shape = RoundedCornerShape(10.dp)) {
                        Icon(Icons.Default.Refresh, null, Modifier.size(16.dp)); Spacer(Modifier.width(4.dp)); Text("重新扫描")
                    }
                    Spacer(Modifier.width(10.dp))
                    Text("本机：${Discovery.deviceName()}", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                Spacer(Modifier.height(6.dp))
                if (syncStatus.isNotBlank()) {
                    Text(syncStatus, color = if (syncStatus.startsWith("✓") || syncStatus.startsWith("发现"))
                        Color(0xFF2E7D32) else Color(0xFFC62828), fontSize = 13.sp)
                    Spacer(Modifier.height(6.dp))
                }
                if (deviceList.isEmpty()) {
                    Text("未发现设备（等待中…）", color = Color(0xFF909090), fontSize = 13.sp)
                } else {
                    deviceList.forEach { dev ->
                        Card(
                            modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)),
                        ) {
                            Column(Modifier.fillMaxWidth().padding(10.dp)) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Column(Modifier.weight(1f)) {
                                        Text(dev.name, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                                        Text("${dev.host}:${dev.port}", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                    }
                                    Button(onClick = { doSync(dev, "pull") },
                                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF2E7D32)),
                                        modifier = Modifier.padding(end = 6.dp)) {
                                        Icon(Icons.Default.Download, null, Modifier.size(14.dp)); Spacer(Modifier.width(3.dp)); Text("拉取")
                                    }
                                    Button(onClick = { doSync(dev, "push") },
                                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF1976D2))) {
                                        Icon(Icons.Default.Send, null, Modifier.size(14.dp)); Spacer(Modifier.width(3.dp)); Text("推送")
                                    }
                                }
                            }
                        }
                    }
                }
                Spacer(Modifier.height(8.dp))
                HorizontalDivider()
                Spacer(Modifier.height(8.dp))
                Text("手动连接（备选，自动发现失败时用）", fontWeight = FontWeight.SemiBold, fontSize = 13.sp)
                Spacer(Modifier.height(6.dp))
                Row(Modifier.fillMaxWidth()) {
                    Box(Modifier.weight(1f)) { LabeledField("对方 IP", manualHost, { manualHost = it }) }
                    Spacer(Modifier.width(10.dp))
                    Box(Modifier.weight(1f)) { LabeledField("端口", manualPort, { manualPort = it }, keyboard = androidx.compose.ui.text.input.KeyboardType.Number) }
                }
                Spacer(Modifier.height(6.dp))
                Row(Modifier.fillMaxWidth()) {
                    Button(onClick = { manualSync("pull") }, modifier = Modifier.weight(1f),
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF2E7D32))) { Text("手动拉取") }
                    Spacer(Modifier.width(8.dp))
                    Button(onClick = { manualSync("push") }, modifier = Modifier.weight(1f),
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF1976D2))) { Text("手动推送") }
                }
                Spacer(Modifier.height(6.dp))
                Row(Modifier.fillMaxWidth()) {
                    OutlinedButton(onClick = { excelExportLauncher.launch("薪资记录_${java.text.SimpleDateFormat("yyyyMMdd_HHmm").format(java.util.Date())}.xlsx") },
                        modifier = Modifier.weight(1f)) { Icon(Icons.Default.FileUpload, null, Modifier.size(15.dp)); Spacer(Modifier.width(4.dp)); Text("导出 Excel") }
                    Spacer(Modifier.width(8.dp))
                    OutlinedButton(onClick = { excelImportLauncher.launch(arrayOf("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "*/*")) },
                        modifier = Modifier.weight(1f)) { Icon(Icons.Default.Download, null, Modifier.size(15.dp)); Spacer(Modifier.width(4.dp)); Text("导入 Excel") }
                }
                Spacer(Modifier.height(6.dp))
                Row(Modifier.fillMaxWidth()) {
                    OutlinedButton(onClick = { exportLauncher.launch("salary_backup_${java.text.SimpleDateFormat("yyyyMMdd_HHmm").format(java.util.Date())}.json") },
                        modifier = Modifier.weight(1f)) { Icon(Icons.Default.FileUpload, null, Modifier.size(15.dp)); Spacer(Modifier.width(4.dp)); Text("导出 JSON") }
                    Spacer(Modifier.width(8.dp))
                    OutlinedButton(onClick = { importLauncher.launch(arrayOf("application/json", "text/plain")) },
                        modifier = Modifier.weight(1f)) { Icon(Icons.Default.Download, null, Modifier.size(15.dp)); Spacer(Modifier.width(4.dp)); Text("导入 JSON") }
                }
            }
        }

        // ---- 工资规则 ----
        Card(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 8.dp)) {
            Column(Modifier.fillMaxWidth().padding(16.dp)) {
                Text("工资规则", style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.height(10.dp))
                var hRate by remember { mutableStateOf(rules["hourly_rate"] ?: "") }
                var dRate by remember { mutableStateOf(rules["daily_rate"] ?: "") }
                var mSalary by remember { mutableStateOf(rules["monthly_salary"] ?: "") }
                var pRate by remember { mutableStateOf(rules["piece_rate"] ?: "") }
                var oMult by remember { mutableStateOf(rules["overtime_multiplier"] ?: "1.5") }
                var hMult by remember { mutableStateOf(rules["holiday_multiplier"] ?: "3") }
                var payday by remember { mutableStateOf(rules["payday"] ?: "10") }
                var company by remember { mutableStateOf(rules["company"] ?: "") }
                Row(Modifier.fillMaxWidth()) {
                    Box(Modifier.weight(1f)) { LabeledField("时薪 (元/时)", hRate, { hRate = it }, keyboard = androidx.compose.ui.text.input.KeyboardType.Decimal) }
                    Spacer(Modifier.width(10.dp))
                    Box(Modifier.weight(1f)) { LabeledField("日薪 (元/天)", dRate, { dRate = it }, keyboard = androidx.compose.ui.text.input.KeyboardType.Decimal) }
                }
                Spacer(Modifier.height(8.dp))
                Row(Modifier.fillMaxWidth()) {
                    Box(Modifier.weight(1f)) { LabeledField("计件单价", pRate, { pRate = it }, keyboard = androidx.compose.ui.text.input.KeyboardType.Decimal) }
                    Spacer(Modifier.width(10.dp))
                    Box(Modifier.weight(1f)) { LabeledField("固定月薪", mSalary, { mSalary = it }, keyboard = androidx.compose.ui.text.input.KeyboardType.Decimal) }
                }
                Spacer(Modifier.height(8.dp))
                Row(Modifier.fillMaxWidth()) {
                    Box(Modifier.weight(1f)) { LabeledField("加班倍数", oMult, { oMult = it }, keyboard = androidx.compose.ui.text.input.KeyboardType.Decimal) }
                    Spacer(Modifier.width(10.dp))
                    Box(Modifier.weight(1f)) { LabeledField("节假日倍数", hMult, { hMult = it }, keyboard = androidx.compose.ui.text.input.KeyboardType.Decimal) }
                }
                Spacer(Modifier.height(8.dp))
                Row(Modifier.fillMaxWidth()) {
                    Box(Modifier.weight(1f)) { LabeledField("发薪日", payday, { payday = it }, keyboard = androidx.compose.ui.text.input.KeyboardType.Number) }
                    Spacer(Modifier.width(10.dp))
                    Box(Modifier.weight(1f)) { LabeledField("公司名称", company, { company = it }) }
                }
                Spacer(Modifier.height(12.dp))
                Button(onClick = {
                    dao.saveSettings(mapOf(
                        "hourly_rate" to hRate, "daily_rate" to dRate, "monthly_salary" to mSalary,
                        "piece_rate" to pRate, "overtime_multiplier" to oMult, "holiday_multiplier" to hMult,
                        "payday" to payday, "company" to company,
                    ))
                    rules = dao.getSettings()
                    onDataChanged()
                    toast("工资规则已保存")
                }, modifier = Modifier.fillMaxWidth().height(48.dp), shape = RoundedCornerShape(12.dp)) { Text("保存规则") }
            }
        }

        // ---- 帮助 ----
        Card(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 8.dp)) {
            Column(Modifier.fillMaxWidth().padding(16.dp)) {
                Text("使用提示", style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.height(8.dp))
                Text("· 记录支持计时/计件/加班/出勤四种类型\n· 加班勾选「节假日」按节假日倍数（默认3倍）计算\n· 月度对账：应发=收入-扣款，登记实发后自动显示差额\n· 与电脑同步：两端连同一 WiFi，电脑端「数据同步」启动同步服务，本页会自动发现并点设备同步\n· 数据保存在本机，导出 JSON 可备份/换机迁移", fontSize = 13.sp, lineHeight = 22.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        Spacer(Modifier.height(24.dp))
    }
}
