package com.salarybook.app.data

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper

/** 默认设置（键与 Windows 端 settings 表一致）。 */
val DEFAULT_SETTINGS: Map<String, String> = mapOf(
    "hourly_rate" to "0",
    "daily_rate" to "0",
    "monthly_salary" to "0",
    "piece_rate" to "0",
    "overtime_multiplier" to "1.5",
    "holiday_multiplier" to "3",
    "payday" to "10",
    "company" to "",
    "password" to "",
    "remind_payday" to "1",
)

/**
 * SQLite 数据层：表结构与 Windows 端 salary_app/db.py 完全一致，
 * 保证两端 JSON 同步 / Excel 导入互相兼容。
 */
class SalaryDb(context: Context) :
    SQLiteOpenHelper(context, "salary.db", null, DB_VERSION) {

    init {
        // onCreate 回调运行在 framework 事务内，不能在里面执行 PRAGMA journal_mode，
        // WAL 必须从这里开启。
        setWriteAheadLoggingEnabled(true)
    }

    companion object {
        const val DB_VERSION = 1
    }

    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        db.execSQL("""
            CREATE TABLE IF NOT EXISTS work_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_date TEXT NOT NULL,
                record_type TEXT NOT NULL,
                start_time TEXT DEFAULT '',
                end_time TEXT DEFAULT '',
                hours REAL DEFAULT 0,
                units REAL DEFAULT 0,
                rate REAL DEFAULT 0,
                amount REAL DEFAULT 0,
                content TEXT DEFAULT '',
                note TEXT DEFAULT '',
                is_holiday INTEGER DEFAULT 0
            )
        """)
        db.execSQL("""
            CREATE TABLE IF NOT EXISTS deductions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_date TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL DEFAULT 0,
                note TEXT DEFAULT ''
            )
        """)
        db.execSQL("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period TEXT NOT NULL,
                actual_amount REAL DEFAULT 0,
                paid_date TEXT DEFAULT '',
                note TEXT DEFAULT '',
                UNIQUE(period)
            )
        """)
        seedSettings(db)
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        // v1 起步，暂无迁移
    }

    override fun onDowngrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        // 允许降级（表结构不变）
    }

    fun seedSettings(db: SQLiteDatabase = writableDatabase) {
        for ((key, value) in DEFAULT_SETTINGS) {
            val cv = ContentValues().apply {
                put("key", key)
                put("value", value)
            }
            db.insertWithOnConflict("settings", null, cv, SQLiteDatabase.CONFLICT_IGNORE)
        }
    }
}
