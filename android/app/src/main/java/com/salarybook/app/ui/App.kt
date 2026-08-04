package com.salarybook.app.ui

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountBalanceWallet
import androidx.compose.material.icons.filled.BarChart
import androidx.compose.material.icons.filled.Book
import androidx.compose.material.icons.filled.MoneyOff
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.sp
import com.salarybook.app.data.SalaryDao
import com.salarybook.app.sync.Discovery
import com.salarybook.app.sync.MiniHttpServer
import com.salarybook.app.ui.screens.DeductionsScreen
import com.salarybook.app.ui.screens.RecordsScreen
import com.salarybook.app.ui.screens.ReconcileScreen
import com.salarybook.app.ui.screens.SettingsScreen
import com.salarybook.app.ui.screens.StatsScreen

private data class TabItem(val label: String, val icon: ImageVector)

private val tabs = listOf(
    TabItem("记录", Icons.Default.Book),
    TabItem("扣款", Icons.Default.MoneyOff),
    TabItem("对账", Icons.Default.AccountBalanceWallet),
    TabItem("统计", Icons.Default.BarChart),
    TabItem("设置", Icons.Default.Settings),
)

@Composable
fun App(dao: SalaryDao) {
    var selected by rememberSaveable { mutableIntStateOf(0) }
    var appKey by remember { mutableIntStateOf(0) }

    // 局域网发现 + 迷你 HTTP 服务：应用打开期间持续广播，电脑可发现并同步本机
    DisposableEffect(dao) {
        val port = MiniHttpServer.start(dao)
        Discovery.setHttpPort(port)
        Discovery.start()
        onDispose {
            Discovery.stop()
            MiniHttpServer.stop()
        }
    }

    Scaffold(
        bottomBar = {
            NavigationBar {
                tabs.forEachIndexed { i, tab ->
                    NavigationBarItem(
                        selected = selected == i,
                        onClick = { selected = i },
                        icon = { Icon(tab.icon, null) },
                        label = { Text(tab.label, fontSize = 11.sp) },
                    )
                }
            }
        },
    ) { pad ->
        when (selected) {
            0 -> RecordsScreen(dao, Modifier.padding(pad), refreshSignal = appKey)
            1 -> DeductionsScreen(dao, Modifier.padding(pad), refreshSignal = appKey)
            2 -> ReconcileScreen(dao, Modifier.padding(pad), refreshSignal = appKey)
            3 -> StatsScreen(dao, Modifier.padding(pad), refreshSignal = appKey)
            4 -> SettingsScreen(dao, Modifier.padding(pad), onDataChanged = { appKey++ })
        }
    }
}
