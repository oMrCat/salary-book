# -*- coding: utf-8 -*-
"""局域网同步 HTTP 服务 + 客户端。

设备通过 UDP 广播自动发现（discovery.py），数据经 HTTP 传输。
接口：
  GET  /api/ping       连接测试
  GET  /api/data       拉取（对方 -> 本机），返回原始数据集 JSON
  POST /api/data       推送（本机 -> 对方），body 为数据集 JSON
"""

import json
import socket
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from . import sync

DEFAULT_PORT = 18080


def get_lan_ips():
    ips = set()
    try:
        ips.update(socket.gethostbyname_ex(socket.gethostname())[2])
    except Exception:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ips.add(s.getsockname()[0])
        s.close()
    except Exception:
        pass
    return sorted(ip for ip in ips if not ip.startswith("127."))


class _Handler(BaseHTTPRequestHandler):
    server_version = "SalarySync/1.0"

    def log_message(self, *args):
        pass

    def _send_bytes(self, body, status=200, content_type="application/json; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send(self, obj, status=200):
        self._send_bytes(json.dumps(obj, ensure_ascii=False).encode("utf-8"), status)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/ping":
            self._send({"ok": True, "app": sync.APP, "message": "连接成功"})
        elif path == "/api/data":
            try:
                self._send_bytes(sync.export_json(self.server.db).encode("utf-8"))
            except Exception as exc:
                self._send({"ok": False, "error": str(exc)}, 500)
        else:
            self._send({"ok": False, "error": "not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        if path != "/api/data":
            self._send({"ok": False, "error": "not found"}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length).decode("utf-8")
            payload = json.loads(raw)
            data = payload.get("data", payload) if isinstance(payload, dict) else payload
            result = sync.import_json(self.server.db, json.dumps(data, ensure_ascii=False))
            self._send({"ok": True, "imported": result})
        except Exception as exc:
            self._send({"ok": False, "error": str(exc)}, 400)


class SyncServer:
    def __init__(self, db, port=DEFAULT_PORT):
        self.db = db
        self.port = int(port)
        self.httpd = None
        self.thread = None
        self.last_result = "尚未同步"

    @property
    def running(self):
        return self.httpd is not None

    def start(self):
        if self.httpd:
            return
        self.httpd = ThreadingHTTPServer(("0.0.0.0", self.port), _Handler)
        self.httpd.daemon_threads = True
        self.httpd.db = self.db
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None
            self.thread = None


# ---------- HTTP 客户端（Windows 主动从对方设备拉取/推送） ----------

def http_get(host, port, path, timeout=10):
    with urllib.request.urlopen(f"http://{host}:{port}{path}", timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def http_post(host, port, path, body, timeout=15):
    req = urllib.request.Request(
        f"http://{host}:{port}{path}",
        data=body.encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def ping_device(host, port):
    return http_get(host, port, "/api/ping")


def pull_device(host, port):
    """从对方拉取数据集 JSON 文本。"""
    return http_get(host, port, "/api/data")


def push_device(host, port, json_text):
    """向对方推送数据集 JSON，返回对方结果文本。"""
    return http_post(host, port, "/api/data", json_text)
