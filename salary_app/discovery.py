# -*- coding: utf-8 -*-
"""局域网设备自动发现（LocalSend 风格）。

通过 UDP 广播在固定端口上周期发送 beacon，
收到 discover 请求则单播响应，从而维护在线设备列表。
设备之间通过 HTTP（见 lanserver.py）传输数据。
"""

import json
import random
import socket
import threading
import time

DISCOVERY_PORT = 20000
APP = "salary-book"


def primary_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def broadcast_addresses():
    """255.255.255.255 加子网广播地址，提高跨路由器可达性。"""
    addrs = ["255.255.255.255"]
    try:
        ip = primary_ip()
        if ip and ip.count(".") == 3:
            addrs.append(ip.rsplit(".", 1)[0] + ".255")
    except Exception:
        pass
    return addrs


def host_name():
    try:
        return socket.gethostname()
    except Exception:
        return "Windows 电脑"


class DiscoveryService:
    def __init__(self, name, port_getter):
        self.name = name
        self.device_id = "win-" + str(random.randint(100000, 999999))
        self.port_getter = port_getter
        self.enabled = True
        self.devices = {}
        self._sock = None
        self._thread = None
        self._stop = threading.Event()

    def start(self):
        if self._thread:
            return
        self._stop.clear()
        self.devices.clear()
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.bind(("", DISCOVERY_PORT))
        s.settimeout(0.5)
        self._sock = s
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
        self._thread = None

    @property
    def running(self):
        return self._thread is not None

    def _packet(self, cmd):
        return {
            "app": APP, "cmd": cmd, "name": self.name, "id": self.device_id,
            "host": primary_ip(), "port": self.port_getter() or 0,
        }

    def _send_broadcast(self, msg):
        if not self._sock:
            return
        payload = json.dumps(msg, ensure_ascii=False).encode("utf-8")
        for addr in broadcast_addresses():
            try:
                self._sock.sendto(payload, (addr, DISCOVERY_PORT))
            except Exception:
                pass

    def _send_unicast(self, host, msg):
        if not self._sock:
            return
        try:
            self._sock.sendto(
                json.dumps(msg, ensure_ascii=False).encode("utf-8"),
                (host, DISCOVERY_PORT))
        except Exception:
            pass

    def _loop(self):
        last = 0.0
        last_probe = 0.0
        while not self._stop.is_set():
            try:
                data, addr = self._sock.recvfrom(65535)
                try:
                    msg = json.loads(data.decode("utf-8"))
                except Exception:
                    msg = None
                if msg and msg.get("app") == APP and msg.get("id") != self.device_id:
                    self._handle(msg, addr)
            except socket.timeout:
                pass
            except OSError:
                break
            except Exception:
                pass
            now = time.time()
            if self.enabled and self.port_getter():
                if now - last > 3:
                    self._send_broadcast(self._packet("beacon"))
                    last = now
                if now - last_probe > 10:
                    self._probe_subnet()
                    last_probe = now

    def _probe_subnet(self):
        """向本机网段（/24）内各 IP 单播 discover，解决广播被路由器/AP 隔离的问题。"""
        ip = primary_ip()
        if ip.count(".") != 3:
            return
        prefix = ip.rsplit(".", 1)[0]
        payload = json.dumps(self._packet("discover"), ensure_ascii=False).encode("utf-8")
        for i in range(1, 255):
            if self._stop.is_set():
                return
            try:
                self._sock.sendto(payload, (f"{prefix}.{i}", DISCOVERY_PORT))
            except Exception:
                break

    def _handle(self, msg, addr):
        did = msg.get("id")
        if not did:
            return
        self.devices[did] = {
            "name": msg.get("name") or "未知设备",
            "host": msg.get("host") or addr[0],
            "port": msg.get("port") or 0,
            "id": did,
            "last": time.time(),
        }
        if msg.get("cmd") == "discover":
            self._send_unicast(self.devices[did]["host"], self._packet("response"))

    def scan(self, timeout=2.5):
        self.devices.clear()
        self._send_broadcast(self._packet("discover"))
        time.sleep(timeout)
        now = time.time()
        return [d for d in self.devices.values() if now - d["last"] < 60]

    def device_list(self):
        now = time.time()
        return [d for d in self.devices.values() if now - d["last"] < 60]
