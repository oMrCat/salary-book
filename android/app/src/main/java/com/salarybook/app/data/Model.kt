package com.salarybook.app.data

/** 工作记录实体（字段与 Windows 端 SQLite 表 work_records 一一对应）。 */
data class WorkRecord(
    val id: Int = 0,
    val date: String = "",
    val type: String = "计时",
    val startTime: String = "",
    val endTime: String = "",
    val hours: Double = 0.0,
    val units: Double = 0.0,
    val rate: Double = 0.0,
    val amount: Double = 0.0,
    val content: String = "",
    val note: String = "",
    val isHoliday: Boolean = false,
)

/** 扣款记录实体。 */
data class Deduction(
    val id: Int = 0,
    val date: String = "",
    val category: String = "其他",
    val amount: Double = 0.0,
    val note: String = "",
)

/** 发薪记录实体（period 形如 2026-08，唯一）。 */
data class Payment(
    val id: Int = 0,
    val period: String = "",
    val actualAmount: Double = 0.0,
    val paidDate: String = "",
    val note: String = "",
)

val RECORD_TYPES = listOf("计时", "计件", "按天", "按月", "加班") // 兼容旧数据里的"出勤"
val DEDUCTION_CATEGORIES = listOf("请假", "迟到", "社保", "公积金", "其他")
