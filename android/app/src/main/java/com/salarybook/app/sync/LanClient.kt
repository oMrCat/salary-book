package com.salarybook.app.sync

import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL

object LanClient {

    fun ping(host: String, port: Int): String {
        val conn = open(host, port, "/api/ping", "GET")
        return readBody(conn)
    }

    fun pull(host: String, port: Int): String {
        val conn = open(host, port, "/api/data", "GET")
        return readBody(conn)
    }

    fun push(host: String, port: Int, json: String): String {
        val conn = open(host, port, "/api/data", "POST")
        conn.doOutput = true
        conn.setRequestProperty("Content-Type", "application/json; charset=utf-8")
        conn.outputStream.use { it.write(json.toByteArray(Charsets.UTF_8)) }
        return readBody(conn)
    }

    private fun open(host: String, port: Int, path: String, method: String): HttpURLConnection {
        val conn = URL("http://${host.trim()}:$port$path").openConnection() as HttpURLConnection
        conn.connectTimeout = 8000
        conn.readTimeout = 15000
        conn.requestMethod = method
        return conn
    }

    private fun readBody(conn: HttpURLConnection): String {
        val code = conn.responseCode
        val stream = if (code in 200..299) conn.inputStream else conn.errorStream
        val text = stream?.let {
            BufferedReader(InputStreamReader(it, Charsets.UTF_8)).use { r -> r.readText() }
        } ?: ""
        conn.disconnect()
        if (code !in 200..299) {
            throw IllegalStateException("HTTP $code：${text.take(200)}")
        }
        return text
    }
}
