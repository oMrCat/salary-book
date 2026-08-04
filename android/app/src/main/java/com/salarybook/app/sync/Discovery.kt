package com.salarybook.app.sync

import android.os.Build
import org.json.JSONObject
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.Socket
import java.net.SocketTimeoutException

object Discovery {

    const val PORT = 20000
    private const val APP = "salary-book"

    data class Device(
        val id: String,
        val name: String,
        val host: String,
        val port: Int,
        val lastSeen: Long,
    )

    val devices = LinkedHashMap<String, Device>()

    private var socket: DatagramSocket? = null
    private var thread: Thread? = null
    private var running = false
    private val deviceId = "and-" + (100000..999999).random()
    private var httpPort = 0

    fun start() {
        if (running) return
        running = true
        try {
            val s = DatagramSocket(null)
            s.reuseAddress = true
            s.broadcast = true
            s.bind(InetSocketAddress(PORT))
            s.soTimeout = 500
            socket = s
        } catch (e: Exception) {
            socket = null
        }
        thread = Thread {
            var lastBeacon = 0L
            var lastProbe = 0L
            while (running) {
                val s = socket
                if (s != null) {
                    try {
                        val buf = ByteArray(65535)
                        val p = DatagramPacket(buf, buf.size)
                        s.receive(p)
                        val text = String(p.data, 0, p.length, Charsets.UTF_8)
                        handle(JSONObject(text), p.address.hostAddress ?: "")
                    } catch (e: SocketTimeoutException) {
                    } catch (e: Exception) {
                    }
                }
                val now = System.currentTimeMillis()
                if (now - lastBeacon > 3000) {
                    sendBeacon()
                    lastBeacon = now
                }
                if (now - lastProbe > 12000) {
                    probeSubnet()
                    lastProbe = now
                }
            }
        }
        thread?.isDaemon = true
        thread?.start()
    }

    fun stop() {
        running = false
        try {
            socket?.close()
        } catch (_: Exception) {
        }
        socket = null
        thread = null
    }

    fun setHttpPort(port: Int) {
        httpPort = port
    }

    fun httpPort(): Int = httpPort

    fun deviceName(): String = Build.MODEL

    private fun packet(cmd: String): JSONObject = JSONObject()
        .put("app", APP)
        .put("cmd", cmd)
        .put("name", deviceName())
        .put("id", deviceId)
        .put("host", localIp())
        .put("port", httpPort)

    private fun sendBroadcast(msg: JSONObject) {
        try {
            val s = socket ?: return
            val bytes = msg.toString().toByteArray(Charsets.UTF_8)
            val targets = HashSet<String>()
            targets.add("255.255.255.255")
            val ip = localIp()
            if (ip.count { it == '.' } == 3) {
                targets.add(ip.substringBeforeLast('.') + ".255")
            }
            for (t in targets) {
                try {
                    s.send(DatagramPacket(bytes, bytes.size, InetAddress.getByName(t), PORT))
                } catch (_: Exception) {
                }
            }
        } catch (_: Exception) {
        }
    }

    private fun sendUnicast(host: String, msg: JSONObject) {
        try {
            val s = socket ?: return
            val bytes = msg.toString().toByteArray(Charsets.UTF_8)
            s.send(DatagramPacket(bytes, bytes.size, InetAddress.getByName(host), PORT))
        } catch (_: Exception) {
        }
    }

    private fun sendBeacon() {
        if (httpPort > 0) sendBroadcast(packet("beacon"))
    }

    private fun probeSubnet() {
        val ip = localIp()
        if (ip.count { it == '.' } != 3) return
        val prefix = ip.substringBeforeLast('.')
        val msg = packet("discover")
        try {
            val s = socket ?: return
            val bytes = msg.toString().toByteArray(Charsets.UTF_8)
            for (i in 1..254) {
                if (!running) return
                try {
                    s.send(DatagramPacket(bytes, bytes.size, InetAddress.getByName("$prefix.$i"), PORT))
                } catch (_: Exception) {
                }
            }
        } catch (_: Exception) {
        }
    }

    private fun handle(msg: JSONObject, srcHost: String) {
        if (msg.optString("app") != APP) return
        val id = msg.optString("id")
        if (id.isEmpty() || id == deviceId) return
        val host = msg.optString("host").ifEmpty { srcHost }
        val port = msg.optInt("port", 0)
        val now = System.currentTimeMillis()
        devices[id] = Device(id, msg.optString("name", "未知设备"), host, port, now)
        if (msg.optString("cmd") == "discover") {
            sendUnicast(host, packet("response"))
        }
    }

    fun scan(timeoutMs: Long = 2500): List<Device> {
        devices.clear()
        sendBroadcast(packet("discover"))
        probeSubnet()
        val end = System.currentTimeMillis() + timeoutMs
        while (System.currentTimeMillis() < end) {
            try {
                Thread.sleep(50)
            } catch (_: Exception) {
            }
        }
        val now = System.currentTimeMillis()
        return devices.values.filter { now - it.lastSeen < 60000 }.toList()
    }

    fun deviceList(): List<Device> {
        val now = System.currentTimeMillis()
        return devices.values.filter { now - it.lastSeen < 60000 }.toList()
    }

    fun localIp(): String {
        return try {
            val s = Socket()
            s.connect(InetSocketAddress("8.8.8.8", 80), 2000)
            val ip = s.localAddress.hostAddress ?: ""
            s.close()
            ip
        } catch (e: Exception) {
            ""
        }
    }
}
