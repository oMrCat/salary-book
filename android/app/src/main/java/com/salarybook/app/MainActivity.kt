package com.salarybook.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.salarybook.app.data.SalaryDao
import com.salarybook.app.data.SalaryDb
import com.salarybook.app.ui.App
import com.salarybook.app.ui.theme.SalaryTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        val dao = SalaryDao(SalaryDb(applicationContext))
        setContent {
            SalaryTheme {
                App(dao)
            }
        }
    }
}
