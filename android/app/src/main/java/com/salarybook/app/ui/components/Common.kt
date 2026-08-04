package com.salarybook.app.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.text.DecimalFormat

private val moneyFmt = DecimalFormat("#,##0.00")

fun fmtMoney(v: Double): String = moneyFmt.format(v)

fun fmtQty(v: Double): String = if (v == v.toLong().toDouble()) v.toLong().toString() else v.toString()

@Composable
fun MoneyText(value: Double, color: Color = MaterialTheme.colorScheme.primary, size: Int = 20) {
    Text(
        text = "¥${fmtMoney(value)}",
        color = color,
        fontSize = size.sp,
        fontWeight = FontWeight.Bold,
    )
}

@Composable
fun SectionHeader(title: String) {
    Text(
        text = title,
        style = MaterialTheme.typography.titleMedium,
        modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
    )
}

@Composable
fun EmptyHint(text: String) {
    Column(
        modifier = Modifier.fillMaxWidth().padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Icon(Icons.Default.Warning, contentDescription = null, tint = Color(0xFFB0B0B0), modifier = Modifier.size(36.dp))
        Spacer(Modifier.height(8.dp))
        Text(text, color = Color(0xFF909090))
    }
}

@Composable
fun TypeBadge(type: String) {
    val color = when (type) {
        "计时" -> Color(0xFF1976D2)
        "计件" -> Color(0xFF7B1FA2)
        "加班" -> Color(0xFFE65100)
        "按天", "出勤" -> Color(0xFF2E7D32)
        "按月" -> Color(0xFF00838F)
        else -> Color(0xFF616161)
    }
    androidx.compose.foundation.layout.Box(
        modifier = Modifier
            .padding(vertical = 2.dp)
            .then(
                Modifier.padding(0.dp)
            ),
        contentAlignment = Alignment.Center,
    ) {
        Card(
            colors = CardDefaults.cardColors(containerColor = color.copy(alpha = 0.12f)),
        ) {
            Text(
                text = type,
                color = color,
                fontSize = 12.sp,
                fontWeight = FontWeight.SemiBold,
                modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp),
            )
        }
    }
}

@Composable
fun InfoRow(label: String, value: String) {
    Row(Modifier.fillMaxWidth().padding(vertical = 3.dp)) {
        Text(label, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.width(110.dp))
        Text(value, fontWeight = FontWeight.Medium)
    }
}

@Composable
fun ConfirmDialog(
    title: String,
    message: String,
    onConfirm: () -> Unit,
    onDismiss: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(title) },
        text = { Text(message) },
        confirmButton = {
            TextButton(onClick = { onConfirm(); onDismiss() }) { Text("确定", color = MaterialTheme.colorScheme.primary) }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("取消") }
        },
    )
}

@Composable
fun LabeledField(
    label: String,
    value: String,
    onValueChange: (String) -> Unit,
    modifier: Modifier = Modifier,
    placeholder: String = "",
    singleLine: Boolean = true,
    keyboard: androidx.compose.ui.text.input.KeyboardType = androidx.compose.ui.text.input.KeyboardType.Text,
) {
    Column(modifier.fillMaxWidth()) {
        Text(label, fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(2.dp))
        OutlinedTextField(
            value = value,
            onValueChange = onValueChange,
            modifier = Modifier.fillMaxWidth(),
            placeholder = { Text(placeholder, color = Color(0xFFB0B0B0)) },
            singleLine = singleLine,
            keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = keyboard),
            textStyle = androidx.compose.ui.text.TextStyle(fontSize = 14.sp),
        )
    }
}
