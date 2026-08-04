package com.salarybook.app.sync

import com.salarybook.app.data.SalaryDao
import java.io.InputStream
import java.io.OutputStream
import java.net.ServerSocket

/**
 * 极简 HTTP 服务器：让同一局域网的电脑可以拉取/推送本机数据。
 * 端点：GET/POST /api/ping、/api/data
 */
object MiniHttpServer {

    private var server: ServerSocket? = null
    private var thread: Thread? = null

    @Synchronized
    fun start(dao: SalaryDao): Int {
        stop()
        val ss = ServerSocket(0)
        server = ss
        thread = Thread {
            while (!ss.isClosed) {
                try {
                    val sock = ss.accept()
                    Thread {
                        try {
                            handle(sock, dao)
                        } catch (_: Exception) {
                        } finally {
                            try {
                                sock.close()
                            } catch (_: Exception) {
                            }
                        }
                    }.apply { isDaemon = true }.start()
                } catch (_: Exception) {
                    break
                }
            }
        }
        thread?.isDaemon = true
        thread?.start()
        return ss.localPort
    }

    @Synchronized
    fun stop() {
        try {
            server?.close()
        } catch (_: Exception) {
        }
        server = null
        thread = null
    }

    private fun handle(sock: java.net.Socket, dao: SalaryDao) {
        val input: InputStream = sock.getInputStream()
        val out: OutputStream = sock.getOutputStream()

        val requestLine = readLine(input) ?: return
        val parts = requestLine.split(" ")
        if (parts.size < 2) return
        val method = parts[0]
        val path = parts[1].substringBefore("?")

        var contentLength = 0
        while (true) {
            val line = readLine(input) ?: break
            if (line.isEmpty()) break
            if (line.startsWith("Content-Length:", ignoreCase = true)) {
                contentLength = line.substringAfter(':').trim().toIntOrNull() ?: 0
            }
        }
        val body = if (contentLength > 0) readN(input, contentLength) else ""

        fun respond(status: String, text: String) {
            val bytes = text.toByteArray(Charsets.UTF_8)
            val head = "HTTP/1.1 $status\r\n" +
                "Content-Type: application/json; charset=utf-8\r\n" +
                "Content-Length: ${bytes.size}\r\n" +
                "Connection: close\r\n\r\n"
            out.write(head.toByteArray(Charsets.UTF_8))
            out.write(bytes)
            out.flush()
        }

        when {
            method == "GET" && path == "/api/ping" ->
                respond("200 OK", "{\"ok\":true,\"app\":\"salary-book\",\"message\":\"连接成功\"}")
            method == "GET" && path == "/api/data" ->
                respond("200 OK", SyncJson.export(dao))
            method == "POST" && path == "/api/data" -> {
                try {
                    val msg = SyncJson.import(body, dao)
                    respond("200 OK", "{\"ok\":true,\"app\":\"salary-book\",\"imported\":\"$msg\"}")
                } catch (e: Exception) {
                    respond("400 Bad Request", "{\"ok\":false,\"error\":\"${e.message}\"}")
                }
            }
            else -> respond("404 Not Found", "{\"ok\":false,\"error\":\"not found\"}")
        }
    }

    private fun readLine(input: InputStream): String? {
        val sb = StringBuilder()
        while (true) {
            val b = input.read()
            if (b < 0) return if (sb.isEmpty()) null else sb.toString()
            if (b == '\n'.code) return sb.toString()
            if (b != '\r'.code) sb.append(b.toChar())
        }
    }

    private fun readN(input: InputStream, n: Int): String {
        val buf = ByteArray(n)
        var off = 0
        while (off < n) {
            val r = input.read(buf, off, n - off)
            if (r < 0) break
            off += r
        }
        return String(buf, 0, off, Charsets.UTF_8)
    }
}
