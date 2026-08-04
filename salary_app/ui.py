# -*- coding: utf-8 -*-
"""tkinter 主界面：工作记录 / 工资规则 / 扣款记录 / 月度对账 / 统计图表 / 数据同步。

界面配色采用暖橙主题，全部使用 ttk 全局样式统一美化。
"""

import hashlib
import os
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

from . import calc, db as db_mod
from . import lanserver, sync as sync_mod

FONT = ("Microsoft YaHei UI", 10)
FONT_BOLD = ("Microsoft YaHei UI", 10, "bold")
FONT_SMALL = ("Microsoft YaHei UI", 9)
FONT_TITLE = ("Microsoft YaHei UI", 15, "bold")
HEAD_FONT = ("Microsoft YaHei UI", 10, "bold")
WEEK = ["一", "二", "三", "四", "五", "六", "日"]

PALETTE = {
    "primary": "#FF6B35",
    "primary_dark": "#E8551F",
    "primary_light": "#FFE3D6",
    "accent": "#2E9E44",
    "bg": "#FFF6F1",
    "panel": "#FFFFFF",
    "text": "#2B2320",
    "muted": "#8A7B73",
    "danger": "#C62828",
    "ok": "#2E7D32",
    "heading": "#5C453A",
}


def _today():
    return datetime.now().strftime("%Y-%m-%d")


def _today_cn():
    d = datetime.now()
    return f"{d.strftime('%Y-%m-%d')} 周{WEEK[d.weekday()]}"


def _hash_pwd(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _nice_max(value):
    """把 Y 轴最大值取整到好看的刻度（500/1000/2000/5000...）。"""
    if value <= 0:
        return 500
    for m in (500, 1000, 2000, 5000, 10000, 20000, 50000, 100000,
              200000, 500000, 1000000, 2000000, 5000000, 10000000):
        if value <= m:
            return m
    return ((value // 50000) + 1) * 50000


def setup_style(root):
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    bg = PALETTE["bg"]
    style.configure(".", font=FONT, background=bg, foreground=PALETTE["text"])

    style.configure("TNotebook", background=bg, borderwidth=0)
    style.configure("TNotebook.Tab", padding=(16, 9), font=FONT_BOLD,
                    background="#F5E3D8", foreground=PALETTE["heading"])
    style.map("TNotebook.Tab",
              background=[("selected", PALETTE["primary"])],
              foreground=[("selected", "#FFFFFF")])

    style.configure("Treeview", background="#FFFFFF", fieldbackground="#FFFFFF",
                    foreground=PALETTE["text"], rowheight=27, borderwidth=0,
                    font=FONT)
    style.configure("Treeview.Heading", font=("Microsoft YaHei UI", 10, "bold"),
                    background="#FBE9DE", foreground=PALETTE["heading"],
                    relief="flat", padding=(6, 6))
    style.map("Treeview",
              background=[("selected", "#FFD3C0")],
              foreground=[("selected", "#3A1F0E")])
    style.map("Treeview.Heading", background=[("active", "#F5D5C2")])

    style.configure("TButton", font=FONT, padding=(12, 6), background="#F5D5C2",
                    foreground=PALETTE["text"], bordercolor="#E8B89B", focuscolor="none")
    style.map("TButton", background=[("active", "#FFE0D0"), ("pressed", "#F0C3A8")])

    style.configure("Accent.TButton", font=FONT_BOLD, padding=(14, 7),
                    background=PALETTE["primary"], foreground="#FFFFFF",
                    bordercolor=PALETTE["primary_dark"])
    style.map("Accent.TButton", background=[("active", PALETTE["primary_dark"]),
                                            ("pressed", "#D94A14")])

    style.configure("Success.TButton", font=FONT_BOLD, padding=(12, 6),
                    background=PALETTE["ok"], foreground="#FFFFFF",
                    bordercolor=PALETTE["ok"])
    style.map("Success.TButton", background=[("active", "#237031")])

    style.configure("Danger.TButton", font=FONT, padding=(12, 6),
                    background="#FADBD8", foreground=PALETTE["danger"],
                    bordercolor="#E8B89B")
    style.map("Danger.TButton", background=[("active", "#F5C6C2")])

    style.configure("TLabel", font=FONT, background=bg, foreground=PALETTE["text"])
    style.configure("Title.TLabel", font=FONT_TITLE, background=bg,
                    foreground=PALETTE["heading"])
    style.configure("Sub.TLabel", font=FONT_SMALL, background=bg,
                    foreground=PALETTE["muted"])
    style.configure("Status.TLabel", font=FONT_BOLD, background=bg,
                    foreground=PALETTE["heading"])

    style.configure("TLabelframe", background=bg, bordercolor="#F0C9B4",
                    relief="solid", borderwidth=1, padding=(10, 6))
    style.configure("TLabelframe.Label", font=FONT_BOLD, background=bg,
                    foreground=PALETTE["heading"])

    style.configure("TEntry", fieldbackground="#FFFFFF", bordercolor="#E0C4B2",
                    insertcolor=PALETTE["primary"])
    style.configure("TCombobox", fieldbackground="#FFFFFF", bordercolor="#E0C4B2")
    style.configure("TCheckbutton", background=bg, font=FONT)
    style.map("TCheckbutton", background=[("active", bg)])

    style.configure("Horizontal.TProgressbar", background=PALETTE["primary"],
                    troughcolor="#F5E3D8", bordercolor="#F5E3D8")

    # 快捷样式供个别标签页使用
    style.configure("Info.TLabel", font=FONT, background=PALETTE["primary_light"],
                    foreground=PALETTE["heading"], padding=8)


class SalaryApp(tk.Tk):
    def __init__(self, database=None):
        super().__init__()
        self.db = database or db_mod.Database()
        self.sync_server = lanserver.SyncServer(self.db)
        self.title("薪资记录账本")
        self.geometry("1160x780")
        self.minsize(960, 640)
        self.configure(bg=PALETTE["bg"])
        setup_style(self)

        self._build_header()
        self._build_notebook()
        self._build_statusbar()

        self.refresh_status()
        if self.db.get_settings().get("password"):
            self._show_lock()

    # ---------- 顶部横幅 ----------
    def _build_header(self):
        header = tk.Frame(self, bg=PALETTE["primary"], height=64)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="薪资记录账本", bg=PALETTE["primary"],
                 fg="#FFFFFF", font=FONT_TITLE).pack(side="left", padx=18)
        tk.Label(header, text="记录每日辛苦 · 发工资时对账不糊涂",
                 bg=PALETTE["primary"], fg="#FFE3D6", font=FONT_SMALL
                 ).pack(side="left", padx=6, pady=(10, 0))
        self.header_status_var = tk.StringVar()
        tk.Label(header, textvariable=self.header_status_var, bg=PALETTE["primary"],
                 fg="#FFFFFF", font=FONT).pack(side="right", padx=18)

    # ---------- 标签页 ----------
    def _build_notebook(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(10, 0))
        self.tab_work = WorkTab(self.notebook, self)
        self.tab_rules = RulesTab(self.notebook, self)
        self.tab_deduct = DeductionTab(self.notebook, self)
        self.tab_reconcile = ReconcileTab(self.notebook, self)
        self.tab_stats = StatsTab(self.notebook, self)
        self.tab_sync = SyncTab(self.notebook, self)
        for tab, label in [
            (self.tab_work, "工作记录"), (self.tab_rules, "工资规则"),
            (self.tab_deduct, "扣款记录"), (self.tab_reconcile, "月度对账"),
            (self.tab_stats, "统计图表"), (self.tab_sync, "数据同步"),
        ]:
            self.notebook.add(tab, text=label)
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)

    def _build_statusbar(self):
        self.status_var = tk.StringVar()
        status = tk.Label(self, textvariable=self.status_var, bg="#3A2A20",
                          fg="#F5E3D8", anchor="w", font=FONT_SMALL, padx=12, pady=4)
        status.pack(fill="x", side="bottom")

    # ---------- 状态刷新 ----------
    def refresh_all(self):
        self.tab_work.refresh()
        self.tab_deduct.refresh()
        self.tab_reconcile.refresh()
        self.tab_stats.refresh()
        self.tab_sync.refresh()
        self.refresh_status()

    def refresh_status(self):
        period = _today()[:7]
        s = calc.monthly_summary(self.db, period)
        parts = [f"本月出勤 {s['work_days']} 天 / 工时 {s['work_hours']}",
                 f"应发 ¥{s['payable']:.2f}"]
        if s["actual"] is None:
            parts.append("工资未登记实发")
        else:
            parts.append(f"实发 ¥{s['actual']:.2f}" +
                         (" · 已对平" if s["balanced"] else " · 有差额"))
        self.status_var.set("  |  ".join(parts))
        if self.sync_server.running:
            ip = "、".join(lanserver.get_lan_ips()) or "本机"
            self.header_status_var.set(f"同步服务运行中  {ip}:{self.sync_server.port}")
        else:
            self.header_status_var.set(f"今日 {_today_cn()}")

    def _on_tab_change(self, _event=None):
        cur = self.notebook.select()
        if cur == str(self.tab_work):
            self.tab_work.refresh()
        elif cur == str(self.tab_deduct):
            self.tab_deduct.refresh()
        elif cur == str(self.tab_reconcile):
            self.tab_reconcile.refresh()
        elif cur == str(self.tab_stats):
            self.tab_stats.refresh()
        elif cur == str(self.tab_sync):
            self.tab_sync.refresh()
        self.refresh_status()

    # ---------- 密码锁 ----------
    def _show_lock(self):
        self.withdraw()
        lock = tk.Toplevel(self)
        lock.title("请输入启动密码")
        lock.geometry("340x170")
        lock.resizable(False, False)
        lock.configure(bg=PALETTE["bg"])
        lock.transient(self)
        tk.Label(lock, text="本软件已设置密码保护", font=FONT_BOLD,
                 bg=PALETTE["bg"], fg=PALETTE["heading"]).pack(pady=(18, 4))
        tk.Label(lock, text="工资数据已加密，输入密码进入", font=FONT_SMALL,
                 bg=PALETTE["bg"], fg=PALETTE["muted"]).pack()
        frame = tk.Frame(lock, bg=PALETTE["bg"])
        frame.pack(pady=10)
        tk.Label(frame, text="密码：", font=FONT, bg=PALETTE["bg"]).pack(side="left")
        var = tk.StringVar()
        entry = ttk.Entry(frame, textvariable=var, show="*", width=18)
        entry.pack(side="left", padx=(0, 8))

        def check(_ev=None):
            if _hash_pwd(var.get()) == self.db.get_settings().get("password"):
                lock.destroy()
                self.deiconify()
            else:
                messagebox.showerror("错误", "密码不正确", parent=lock)
                var.set("")
                entry.focus_set()

        def quit_app():
            self.destroy()

        btns = tk.Frame(lock, bg=PALETTE["bg"])
        btns.pack(pady=6)
        ttk.Button(btns, text="确定", style="Accent.TButton", command=check).pack(side="left", padx=4)
        ttk.Button(btns, text="退出", command=quit_app).pack(side="left", padx=4)
        entry.bind("<Return>", check)
        entry.focus_set()
        self.wait_window(lock)


class _BaseTab(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app


class WorkTab(_BaseTab):
    def __init__(self, master, app):
        super().__init__(master, app)
        self._build_clock()
        self._build_top()
        self._build_table()
        self._build_form()
        self._build_stats()
        self.refresh()

    def _build_clock(self):
        frame = ttk.LabelFrame(self, text="快捷打卡（自动按计时录入）")
        frame.pack(fill="x", padx=8, pady=(8, 0))
        row = ttk.Frame(frame)
        row.pack(fill="x", padx=6, pady=6)
        self.clock_var = tk.StringVar(value="未打卡")
        tk.Label(row, textvariable=self.clock_var, bg=PALETTE["panel"],
                 fg=PALETTE["primary_dark"], font=FONT_BOLD).pack(side="left", padx=(2, 12))
        ttk.Button(row, text="上班打卡", style="Accent.TButton", command=self._clock_in).pack(side="left", padx=2)
        ttk.Button(row, text="下班打卡", style="Success.TButton", command=self._clock_out).pack(side="left", padx=2)
        tk.Label(row, text="工作内容(可选)：", font=FONT, bg=PALETTE["panel"]).pack(side="left", padx=(14, 2))
        self.clock_content = tk.StringVar()
        ttk.Entry(row, textvariable=self.clock_content, width=28).pack(side="left")

    def _clock_in(self):
        now = datetime.now()
        self.app.db.save_settings({"clock_in_date": now.strftime("%Y-%m-%d"),
                                   "clock_in_time": now.strftime("%H:%M")})
        self.clock_var.set(f"已上班打卡：{now.strftime('%H:%M:%S')}")
        messagebox.showinfo("打卡", f"上班打卡成功：{now.strftime('%H:%M:%S')}")

    def _clock_out(self):
        s = self.app.db.get_settings()
        if s.get("clock_in_date") != _today() or not s.get("clock_in_time"):
            messagebox.showwarning("提示", "今天还没有上班打卡，请先点击「上班打卡」")
            return
        start = s["clock_in_time"]
        end = datetime.now().strftime("%H:%M")
        rec = {
            "record_date": _today(), "record_type": "计时",
            "start_time": start, "end_time": end, "hours": 0, "units": 0,
            "rate": 0, "content": self.clock_content.get().strip(), "note": "",
            "is_holiday": 0, "amount": 0,
        }
        rec["amount"] = calc.compute_work_amount(rec, s)
        self.app.db.add_work(rec)
        self.app.db.save_settings({"clock_in_date": "", "clock_in_time": ""})
        self.clock_var.set("未打卡")
        self.clock_content.set("")
        self.refresh()
        messagebox.showinfo("下班打卡", f"已记录 {start}-{end}，计 ¥{rec['amount']:.2f}")

    def _build_top(self):
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=8, pady=6)
        tk.Label(bar, text="月份筛选：", font=FONT, bg=PALETTE["bg"]).pack(side="left")
        self.filter_var = tk.StringVar(value=_today()[:7])
        ttk.Entry(bar, textvariable=self.filter_var, width=10).pack(side="left", padx=(4, 8))
        ttk.Button(bar, text="全部记录", command=self._clear_filter).pack(side="left", padx=2)
        ttk.Button(bar, text="刷新", command=self.refresh).pack(side="left", padx=2)
        tk.Label(bar, text="搜索：", font=FONT, bg=PALETTE["bg"]).pack(side="left", padx=(16, 2))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(bar, textvariable=self.search_var, width=16)
        search_entry.pack(side="left")
        search_entry.bind("<KeyRelease>", lambda _e: self.refresh())
        self.holiday_shortcut = tk.StringVar(value="本日节假日")
        ttk.Button(bar, text="标记本日为节假日加班", style="Accent.TButton",
                   command=self._add_holiday_shortcut).pack(side="right")

    def _add_holiday_shortcut(self):
        s = self.app.db.get_settings()
        rec = {
            "record_date": _today(), "record_type": "加班",
            "start_time": "00:00", "end_time": "00:00", "hours": 1, "units": 0,
            "rate": 0, "content": self.holiday_shortcut.get(), "note": "节假日",
            "is_holiday": 1, "amount": 0,
        }
        rec["amount"] = calc.compute_work_amount(rec, s)
        self.app.db.add_work(rec)
        self.refresh()

    def _clear_filter(self):
        self.filter_var.set("")
        self.search_var.set("")
        self.refresh()

    def _build_table(self):
        wrap = ttk.Frame(self)
        wrap.pack(fill="both", expand=True, padx=8, pady=4)
        cols = ("id", "record_date", "record_type", "start_time", "end_time",
                "hours", "units", "rate", "amount", "holiday", "content", "note")
        headers = ("ID", "日期", "类型", "开始", "结束", "时长/天", "件数",
                   "单价", "金额", "节假日", "工作内容", "备注")
        self.tree = ttk.Treeview(wrap, columns=cols, show="headings", selectmode="browse")
        widths = {"id": 44, "record_date": 86, "record_type": 56, "start_time": 56,
                  "end_time": 56, "hours": 64, "units": 52, "rate": 62,
                  "amount": 76, "holiday": 58, "content": 200, "note": 130}
        for c, h in zip(cols, headers):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=widths.get(c, 100), anchor="center")
        vs = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vs.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vs.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _build_form(self):
        form = ttk.LabelFrame(self, text="新增 / 编辑工作记录")
        form.pack(fill="x", padx=8, pady=4)
        self.edit_id = None

        row1 = ttk.Frame(form)
        row1.pack(fill="x", padx=6, pady=4)
        self.f_date = self._entry(row1, "日期(YYYY-MM-DD)：", 12, _today())
        self.f_type = tk.StringVar(value="计时")
        tk.Label(row1, text="类型：", font=FONT, bg=PALETTE["panel"]).pack(side="left", padx=(12, 2))
        self.type_combo = ttk.Combobox(row1, textvariable=self.f_type, values=db_mod.RECORD_TYPES,
                                       state="readonly", width=7)
        self.type_combo.pack(side="left")
        self.type_combo.bind("<<ComboboxSelected>>", self._update_qty_label)
        self.f_start = self._entry(row1, "开始(HH:MM)：", 8, "")
        self.f_end = self._entry(row1, "结束(HH:MM)：", 8, "")
        self.qty_label_var = tk.StringVar(value="时长(小时)：")
        tk.Label(row1, textvariable=self.qty_label_var, font=FONT, bg=PALETTE["panel"]).pack(side="left", padx=(12, 2))
        self.f_hours = tk.StringVar(value="")
        ttk.Entry(row1, textvariable=self.f_hours, width=8).pack(side="left")
        self.f_holiday = tk.BooleanVar(value=False)
        ttk.Checkbutton(row1, text="节假日", variable=self.f_holiday).pack(side="left", padx=(12, 2))

        row2 = ttk.Frame(form)
        row2.pack(fill="x", padx=6, pady=4)
        self.f_units = self._entry(row2, "件数：", 8, "")
        self.f_rate = self._entry(row2, "单价(留空用规则)：", 14, "")
        self.f_content = self._entry(row2, "工作内容：", 20, "")
        self.f_note = self._entry(row2, "备注：", 14, "")

        self.type_hint_var = tk.StringVar(value="金额 = 时长(小时) × 时薪")
        tk.Label(form, textvariable=self.type_hint_var, font=FONT_SMALL, bg=PALETTE["panel"],
                 fg="#0A6EB8", anchor="w").pack(fill="x", padx=6, pady=(0, 2))

        btns = ttk.Frame(form)
        btns.pack(fill="x", padx=6, pady=(0, 6))
        ttk.Button(btns, text="添加", style="Accent.TButton", command=self._add).pack(side="left", padx=2)
        ttk.Button(btns, text="保存修改", command=self._update).pack(side="left", padx=2)
        ttk.Button(btns, text="删除选中", style="Danger.TButton", command=self._delete).pack(side="left", padx=2)
        ttk.Button(btns, text="清空表单", command=self._clear_form).pack(side="left", padx=2)

    def _entry(self, parent, label, width, default=""):
        tk.Label(parent, text=label, font=FONT, bg=PALETTE["panel"]).pack(side="left", padx=(12, 2))
        var = tk.StringVar(value=default)
        ttk.Entry(parent, textvariable=var, width=width).pack(side="left")
        return var

    def _build_stats(self):
        self.stats_var = tk.StringVar()
        tk.Label(self, textvariable=self.stats_var, font=FONT_BOLD, bg=PALETTE["bg"],
                 fg="#0A6EB8").pack(fill="x", padx=8, pady=(0, 6))

    def _filter_period(self):
        return self.filter_var.get().strip() or None

    def refresh(self):
        settings = self.app.db.get_settings()
        rows = self.app.db.list_work(self._filter_period(),
                                     self.search_var.get().strip() or None)
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            # 金额按当前工资规则实时重算（规则改后无需重新录入）
            r["amount"] = calc.compute_work_amount(r, settings)
            self.tree.insert("", "end", values=(
                r["id"], r["record_date"], r["record_type"], r["start_time"],
                r["end_time"], r["hours"], r["units"], r["rate"], r["amount"],
                "是" if r["is_holiday"] else "", r["content"], r["note"],
            ))
        period = self._filter_period() or _today()[:7]
        s = calc.monthly_summary(self.app.db, period)
        self.stats_var.set(
            f"本月出勤 {s['work_days']} 天，总工时 {s['work_hours']} 小时，"
            f"收入合计 ¥{s['income_total']:.2f}，应发 ¥{s['payable']:.2f}"
            f"（{period}）")
        s = self.app.db.get_settings()
        if s.get("clock_in_date") == _today() and s.get("clock_in_time"):
            self.clock_var.set(f"已上班打卡：{s['clock_in_time']}")
        else:
            self.clock_var.set("未打卡")

    def _on_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        self.edit_id = vals[0]
        self.f_date.set(vals[1])
        rtype = vals[2]
        if rtype == "出勤":  # 兼容旧数据
            rtype = "按天"
        self.f_type.set(rtype)
        self.f_start.set(vals[3])
        self.f_end.set(vals[4])
        self.f_hours.set(self._fmt(vals[5]))
        self.f_units.set(self._fmt(vals[6]))
        self.f_rate.set(self._fmt(vals[7]))
        self.f_holiday.set(vals[9] == "是")
        self.f_content.set(vals[10])
        self.f_note.set(vals[11])
        self._update_qty_label()

    def _update_qty_label(self, _event=None):
        t = self.f_type.get()
        labels = {
            "计时": "时长(小时)：", "加班": "时长(小时)：",
            "计件": "件数：", "按天": "天数：", "出勤": "天数：",
            "按月": "月数：",
        }
        self.qty_label_var.set(labels.get(t, "时长/天："))
        hints = {
            "计时": "金额 = 时长(小时) × 时薪",
            "加班": "金额 = 时长(小时) × 时薪 × 加班倍数",
            "计件": "金额 = 件数 × 单价",
            "按天": "金额 = 天数 × 日薪（天数留空默认1天）",
            "按月": "金额 = 月数 × 固定月薪（月数留空默认1月）",
        }
        if hasattr(self, "type_hint_var"):
            self.type_hint_var.set(hints.get(t, ""))

    @staticmethod
    def _fmt(v):
        return "" if v in (None, "") else str(v)

    def _collect(self):
        rtype = self.f_type.get()
        if rtype == "出勤":  # 兼容旧数据
            rtype = "按天"
        rec = {
            "record_date": self.f_date.get().strip() or _today(),
            "record_type": rtype,
            "start_time": self.f_start.get().strip(),
            "end_time": self.f_end.get().strip(),
            "hours": calc.to_float(self.f_hours.get()),
            "units": calc.to_float(self.f_units.get()),
            "rate": calc.to_float(self.f_rate.get()),
            "content": self.f_content.get().strip(),
            "note": self.f_note.get().strip(),
            "is_holiday": 1 if self.f_holiday.get() else 0,
            "amount": 0,
        }
        rec["amount"] = calc.compute_work_amount(rec, self.app.db.get_settings())
        return rec

    def _add(self):
        self.app.db.add_work(self._collect())
        self._clear_form()
        self.refresh()

    def _update(self):
        if not self.edit_id:
            messagebox.showinfo("提示", "请先在表格中选中一条记录")
            return
        self.app.db.update_work(self.edit_id, self._collect())
        self._clear_form()
        self.refresh()

    def _delete(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先选中要删除的记录")
            return
        if messagebox.askyesno("确认", "确定删除选中的记录吗？"):
            self.app.db.delete_work(self.tree.item(sel[0], "values")[0])
            self.refresh()

    def _clear_form(self):
        self.edit_id = None
        self.f_date.set(_today())
        self.f_type.set("计时")
        self.f_start.set("")
        self.f_end.set("")
        self.f_hours.set("")
        self.f_units.set("")
        self.f_rate.set("")
        self.f_holiday.set(False)
        self.f_content.set("")
        self.f_note.set("")
        self._update_qty_label()


class RulesTab(_BaseTab):
    def __init__(self, master, app):
        super().__init__(master, app)
        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        ttk.Label(frame, text="工资规则设置", style="Title.TLabel").pack(anchor="w", pady=(0, 10))

        self.vars = {}
        fields = [
            ("hourly_rate", "时薪（元/小时）"),
            ("daily_rate", "日薪（元/天）"),
            ("monthly_salary", "固定月薪（元/月）"),
            ("piece_rate", "计件单价（元/件）"),
            ("overtime_multiplier", "加班费倍数（默认1.5）"),
            ("holiday_multiplier", "节假日加班倍数（默认3）"),
            ("payday", "每月发薪日（1-31）"),
            ("company", "公司名称"),
            ("remind_payday", "开启发薪日到账提醒（0关闭/1开启）"),
        ]
        grid = ttk.Frame(frame)
        grid.pack(fill="x")
        for i, (key, label) in enumerate(fields):
            tk.Label(grid, text=label, font=FONT, bg=PALETTE["bg"]).grid(
                row=i, column=0, sticky="w", pady=5, padx=(0, 12))
            var = tk.StringVar()
            ttk.Entry(grid, textvariable=var, width=26).grid(row=i, column=1, sticky="w")
            self.vars[key] = var
        ttk.Button(frame, text="保存规则", style="Accent.TButton", command=self._save).pack(anchor="w", pady=14)

        hint = (
            "计算说明：\n"
            "· 计时：时长(小时) × 时薪\n"
            "· 加班：时长(小时) × 时薪 × 加班倍数；勾选「节假日」× 节假日倍数（默认3倍）\n"
            "· 计件：件数 × 计件单价\n"
            "· 按天：天数 × 日薪（天数留空默认1天）\n"
            "· 按月：月数 × 固定月薪（月数留空默认1月，适合月薪族一键录入）\n"
            "· 某条记录若单独填了「单价」，优先使用记录内单价\n"
            "· 发薪日提醒：超过发薪日仍未登记实发，会在月度对账页提示"
        )
        ttk.Label(frame, text=hint, style="Sub.TLabel").pack(anchor="w", pady=(4, 0))
        self.load()

    def load(self):
        data = self.app.db.get_settings()
        for key, var in self.vars.items():
            var.set(data.get(key, ""))

    def _save(self):
        data = {k: v.get().strip() for k, v in self.vars.items()}
        self.app.db.save_settings(data)
        messagebox.showinfo("完成", "工资规则已保存")


class DeductionTab(_BaseTab):
    def __init__(self, master, app):
        super().__init__(master, app)
        self._build_top()
        self._build_table()
        self._build_form()
        self.refresh()

    def _build_top(self):
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=8, pady=(8, 4))
        tk.Label(bar, text="月份筛选：", font=FONT, bg=PALETTE["bg"]).pack(side="left")
        self.filter_var = tk.StringVar(value=_today()[:7])
        ttk.Entry(bar, textvariable=self.filter_var, width=10).pack(side="left", padx=(4, 8))
        ttk.Button(bar, text="全部记录", command=self._clear_filter).pack(side="left", padx=2)
        ttk.Button(bar, text="刷新", command=self.refresh).pack(side="left", padx=2)
        tk.Label(bar, text="搜索：", font=FONT, bg=PALETTE["bg"]).pack(side="left", padx=(16, 2))
        self.search_var = tk.StringVar()
        se = ttk.Entry(bar, textvariable=self.search_var, width=16)
        se.pack(side="left")
        se.bind("<KeyRelease>", lambda _e: self.refresh())

    def _clear_filter(self):
        self.filter_var.set("")
        self.search_var.set("")
        self.refresh()

    def _build_table(self):
        wrap = ttk.Frame(self)
        wrap.pack(fill="both", expand=True, padx=8, pady=4)
        cols = ("id", "record_date", "category", "amount", "note")
        headers = ("ID", "日期", "类别", "扣款金额", "备注")
        self.tree = ttk.Treeview(wrap, columns=cols, show="headings", selectmode="browse")
        widths = {"id": 60, "record_date": 120, "category": 90, "amount": 110, "note": 320}
        for c, h in zip(cols, headers):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=widths.get(c, 120), anchor="center")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _build_form(self):
        form = ttk.LabelFrame(self, text="新增 / 编辑扣款")
        form.pack(fill="x", padx=8, pady=4)
        self.edit_id = None
        row = ttk.Frame(form)
        row.pack(fill="x", padx=6, pady=6)
        self.f_date = self._entry(row, "日期：", 12, _today())
        self.f_cat = tk.StringVar(value="请假")
        tk.Label(row, text="类别：", font=FONT, bg=PALETTE["panel"]).pack(side="left", padx=(12, 2))
        ttk.Combobox(row, textvariable=self.f_cat, values=db_mod.DEDUCTION_CATEGORIES,
                     state="readonly", width=8).pack(side="left")
        self.f_amount = self._entry(row, "金额：", 10, "")
        self.f_note = self._entry(row, "备注：", 20, "")
        btns = ttk.Frame(form)
        btns.pack(fill="x", padx=6, pady=(0, 6))
        ttk.Button(btns, text="添加", style="Accent.TButton", command=self._add).pack(side="left", padx=2)
        ttk.Button(btns, text="保存修改", command=self._update).pack(side="left", padx=2)
        ttk.Button(btns, text="删除选中", style="Danger.TButton", command=self._delete).pack(side="left", padx=2)
        ttk.Button(btns, text="清空表单", command=self._clear_form).pack(side="left", padx=2)

    def _entry(self, parent, label, width, default=""):
        tk.Label(parent, text=label, font=FONT, bg=PALETTE["panel"]).pack(side="left", padx=(12, 2))
        var = tk.StringVar(value=default)
        ttk.Entry(parent, textvariable=var, width=width).pack(side="left")
        return var

    def _filter_period(self):
        return self.filter_var.get().strip() or None

    def refresh(self):
        rows = self.app.db.list_deductions(self._filter_period(),
                                           self.search_var.get().strip() or None)
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", values=(
                r["id"], r["record_date"], r["category"], r["amount"], r["note"],
            ))

    def _on_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        self.edit_id = vals[0]
        self.f_date.set(vals[1])
        self.f_cat.set(vals[2])
        self.f_amount.set(vals[3])
        self.f_note.set(vals[4])

    def _collect(self):
        return {
            "record_date": self.f_date.get().strip() or _today(),
            "category": self.f_cat.get(),
            "amount": calc.to_float(self.f_amount.get()),
            "note": self.f_note.get().strip(),
        }

    def _add(self):
        self.app.db.add_deduction(self._collect())
        self._clear_form()
        self.refresh()

    def _update(self):
        if not self.edit_id:
            messagebox.showinfo("提示", "请先在表格中选中一条记录")
            return
        self.app.db.update_deduction(self.edit_id, self._collect())
        self._clear_form()
        self.refresh()

    def _delete(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先选中要删除的记录")
            return
        if messagebox.askyesno("确认", "确定删除选中的扣款吗？"):
            self.app.db.delete_deduction(self.tree.item(sel[0], "values")[0])
            self.refresh()

    def _clear_form(self):
        self.edit_id = None
        self.f_date.set(_today())
        self.f_cat.set("请假")
        self.f_amount.set("")
        self.f_note.set("")


class ReconcileTab(_BaseTab):
    def __init__(self, master, app):
        super().__init__(master, app)
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=(8, 4))
        tk.Label(top, text="对账月份(YYYY-MM)：", font=FONT, bg=PALETTE["bg"]).pack(side="left")
        self.period_var = tk.StringVar(value=_today()[:7])
        ttk.Entry(top, textvariable=self.period_var, width=10).pack(side="left", padx=(4, 8))
        ttk.Button(top, text="生成汇总", style="Accent.TButton", command=self.refresh).pack(side="left", padx=2)
        ttk.Button(top, text="复制对账结果", command=self._copy_summary).pack(side="left", padx=6)
        ttk.Button(top, text="上一月", command=lambda: self._shift_month(-1)).pack(side="right", padx=2)
        ttk.Button(top, text="下一月", command=lambda: self._shift_month(1)).pack(side="right", padx=2)

        self.banner_var = tk.StringVar()
        self.banner = tk.Label(self, textvariable=self.banner_var, bg="#FDEBDD",
                               fg=PALETTE["danger"], font=FONT_BOLD, anchor="w", padx=10, pady=5)
        self.banner.pack(fill="x", padx=8)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=8, pady=4)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        left = ttk.LabelFrame(body, text="收入 / 扣款明细")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        self.tree = ttk.Treeview(
            left, columns=("date", "type", "detail", "amount"),
            show="headings", selectmode="browse", height=16,
        )
        for c, h, w, a in [
            ("date", "日期", 90, "center"),
            ("type", "类型", 72, "center"),
            ("detail", "明细", 210, "w"),
            ("amount", "金额", 82, "center"),
        ]:
            self.tree.heading(c, text=h)
            self.tree.column(c, width=w, anchor=a)
        self.tree.pack(fill="both", expand=True, padx=4, pady=4)

        right = ttk.LabelFrame(body, text="本月汇总")
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        self.summary_vars = {}
        rows_def = [
            ("days", "出勤天数", "0"),
            ("hours", "总工时(小时)", "0"),
            ("income", "收入合计", "0.00"),
            ("deduction", "扣款合计", "0.00"),
            ("payable", "应发工资", "0.00"),
            ("actual", "实发金额", "—"),
            ("diff", "差额（实发-应发）", "—"),
            ("status", "对账结果", "—"),
        ]
        grid = ttk.Frame(right)
        grid.pack(fill="x", padx=8, pady=8)
        for i, (key, label, _def) in enumerate(rows_def):
            tk.Label(grid, text=label, font=FONT, bg=PALETTE["panel"]).grid(
                row=i, column=0, sticky="w", pady=3)
            var = tk.StringVar(value=_def)
            lbl = tk.Label(grid, textvariable=var, font=("Microsoft YaHei UI", 12, "bold"),
                           bg=PALETTE["panel"])
            lbl.grid(row=i, column=1, sticky="e", padx=(16, 0), pady=3)
            self.summary_vars[key] = (var, lbl)

        comp = ttk.LabelFrame(right, text="应发构成（对账明细）")
        comp.pack(fill="x", padx=8, pady=(0, 8))
        self.composition_var = tk.StringVar(value="暂无数据")
        tk.Label(comp, textvariable=self.composition_var, font=FONT_SMALL, bg=PALETTE["panel"],
                 fg="#555", justify="left", anchor="w", wraplength=330).pack(fill="x", padx=6, pady=6)

        pay = ttk.LabelFrame(right, text="登记实发工资")
        pay.pack(fill="x", padx=8, pady=(0, 8))
        inner = ttk.Frame(pay)
        inner.pack(fill="x", padx=6, pady=6)
        tk.Label(inner, text="实发金额：", font=FONT, bg=PALETTE["panel"]).grid(row=0, column=0, sticky="w", pady=2)
        self.actual_var = tk.StringVar()
        ttk.Entry(inner, textvariable=self.actual_var, width=16).grid(row=0, column=1, sticky="w", pady=2)
        tk.Label(inner, text="实发日期：", font=FONT, bg=PALETTE["panel"]).grid(row=1, column=0, sticky="w", pady=2)
        self.paid_date_var = tk.StringVar(value=_today())
        ttk.Entry(inner, textvariable=self.paid_date_var, width=16).grid(row=1, column=1, sticky="w", pady=2)
        tk.Label(inner, text="备注：", font=FONT, bg=PALETTE["panel"]).grid(row=2, column=0, sticky="w", pady=2)
        self.pay_note_var = tk.StringVar()
        ttk.Entry(inner, textvariable=self.pay_note_var, width=24).grid(row=2, column=1, sticky="w", pady=2)
        btns = ttk.Frame(pay)
        btns.pack(fill="x", padx=6, pady=(0, 6))
        ttk.Button(btns, text="保存实发", style="Accent.TButton", command=self._save_actual).pack(side="left", padx=2)
        ttk.Button(btns, text="清空该月实发", style="Danger.TButton", command=self._clear_actual).pack(side="left", padx=2)

        quick = ttk.LabelFrame(right, text="快捷录入出勤（月薪族）")
        quick.pack(fill="x", padx=8, pady=(0, 8))
        qinner = ttk.Frame(quick)
        qinner.pack(fill="x", padx=6, pady=6)
        tk.Label(qinner, text="日期：", font=FONT, bg=PALETTE["panel"]).grid(row=0, column=0, sticky="w", pady=2)
        self.q_date_var = tk.StringVar(value=_today())
        ttk.Entry(qinner, textvariable=self.q_date_var, width=12).grid(row=0, column=1, sticky="w", pady=2)
        tk.Label(qinner, text="出勤天数：", font=FONT, bg=PALETTE["panel"]).grid(row=0, column=2, sticky="w", padx=(10, 0))
        self.q_days_var = tk.StringVar(value="22")
        ttk.Entry(qinner, textvariable=self.q_days_var, width=6).grid(row=0, column=3, sticky="w", pady=2)
        tk.Label(qinner, text="备注：", font=FONT, bg=PALETTE["panel"]).grid(row=1, column=0, sticky="w", pady=2)
        self.q_note_var = tk.StringVar(value="全月出勤")
        ttk.Entry(qinner, textvariable=self.q_note_var, width=24).grid(row=1, column=1, columnspan=3, sticky="w", pady=2)
        ttk.Button(quick, text="按日薪生成出勤记录", command=self._quick_attendance).pack(anchor="w", padx=6, pady=(0, 6))

        self.refresh()

    def _shift_month(self, step):
        try:
            y, m = map(int, self.period_var.get().split("-"))
        except ValueError:
            return
        total = y * 12 + (m - 1) + step
        y, m = divmod(total, 12)
        self.period_var.set(f"{y:04d}-{m + 1:02d}")
        self.refresh()

    def _quick_attendance(self):
        days = calc.to_float(self.q_days_var.get())
        if days <= 0:
            messagebox.showwarning("提示", "出勤天数必须大于 0")
            return
        rec = {
            "record_date": self.q_date_var.get().strip() or _today(),
            "record_type": "按天", "start_time": "", "end_time": "",
            "hours": days, "units": 0, "rate": 0,
            "content": "出勤", "note": self.q_note_var.get().strip(),
            "is_holiday": 0, "amount": 0,
        }
        rec["amount"] = calc.compute_work_amount(rec, self.app.db.get_settings())
        self.app.db.add_work(rec)
        self.q_note_var.set("")
        self.refresh()
        messagebox.showinfo("完成", f"已录入出勤 {days} 天，计 ¥{rec['amount']:.2f}")

    def _copy_summary(self):
        s = self.current_summary
        lines = [
            f"【{s['period']} 工资对账】",
            f"出勤 {s['work_days']} 天，工时 {s['work_hours']} 小时",
            f"收入合计 ¥{s['income_total']:.2f}",
            f"扣款合计 ¥{s['deduction_total']:.2f}",
            f"应发工资 ¥{s['payable']:.2f}",
        ]
        if s["actual"] is None:
            lines.append("实发金额 未登记")
        else:
            lines.append(f"实发金额 ¥{s['actual']:.2f}")
            lines.append(f"差额 ¥{s['diff']:.2f}")
            lines.append("对账结果 " + ("已对平" if s["balanced"] else "有差额，请核对"))
        text = "\n".join(lines)
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("已复制", "对账结果已复制到剪贴板，可直接粘贴分享")

    def refresh(self):
        period = self.period_var.get().strip()
        if len(period) != 7:
            messagebox.showwarning("提示", "月份格式应为 YYYY-MM")
            return
        summary = calc.monthly_summary(self.app.db, period)
        self.current_summary = summary
        self.tree.delete(*self.tree.get_children())
        for w in summary["works"]:
            detail = w["content"] or (w["start_time"] and f'{w["start_time"]}-{w["end_time"]}' or "")
            detail = detail or (f"{w['hours']}小时" if w["hours"] else f"{w['units']}件")
            tag = "holiday" if w["is_holiday"] else ""
            self.tree.insert("", "end", values=(
                w["record_date"], w["record_type"], detail, w["amount"],
            ), tags=(tag,) if tag else ())
        self.tree.tag_configure("holiday", foreground="#E67E22")
        if not summary["works"]:
            self.tree.insert("", "end", values=("", "", "本月暂无收入记录", ""))
        for d in summary["deductions"]:
            self.tree.insert("", "end", values=(
                d["record_date"], "扣款:" + d["category"], d["note"], -d["amount"],
            ))

        self.summary_vars["days"][0].set(str(summary["work_days"]))
        self.summary_vars["hours"][0].set(str(summary["work_hours"]))
        self.summary_vars["income"][0].set(f"{summary['income_total']:.2f}")
        self.summary_vars["deduction"][0].set(f"{summary['deduction_total']:.2f}")
        self.summary_vars["payable"][0].set(f"{summary['payable']:.2f}")
        if summary["actual"] is None:
            self.summary_vars["actual"][0].set("—")
            self.summary_vars["diff"][0].set("—")
            self.summary_vars["status"][0].set("未登记实发")
            self.summary_vars["status"][1].configure(fg="#7A6A62")
        else:
            self.summary_vars["actual"][0].set(f"{summary['actual']:.2f}")
            self.summary_vars["diff"][0].set(f"{summary['diff']:.2f}")
            if summary["balanced"]:
                self.summary_vars["status"][0].set("✓ 已对平")
                self.summary_vars["status"][1].configure(fg=PALETTE["ok"])
            else:
                self.summary_vars["status"][0].set("✗ 有差额，请核对")
                self.summary_vars["status"][1].configure(fg=PALETTE["danger"])

        payment = summary["payment"]
        self.actual_var.set("" if payment is None else payment["actual_amount"])
        self.paid_date_var.set("" if payment is None else (payment["paid_date"] or _today()))
        self.pay_note_var.set("" if payment is None else payment["note"])

        # 应发构成（标注具体项目）
        parts = []
        by_type = summary.get("income_by_type") or {}
        if not by_type and not summary["deductions"]:
            self.composition_var.set("本月暂无收入/扣款")
        else:
            type_parts = []
            for t in ("计时", "计件", "按天", "按月", "加班", "出勤"):
                v = by_type.get(t, 0)
                if v:
                    type_parts.append(f"{t} ¥{v:.2f}")
            if type_parts:
                parts.append(" + ".join(type_parts))
            if summary["deduction_total"]:
                parts.append(f"扣款 -¥{summary['deduction_total']:.2f}")
            text = "应发 ¥{:.2f} = ".format(summary["payable"]) + "，".join(parts)
            if summary["actual"] is not None and not summary["balanced"]:
                diff = summary["diff"] or 0
                sign = "+" if diff >= 0 else ""
                text += f"\n⚠ 实发 ¥{summary['actual']:.2f}，差额 {sign}¥{diff:.2f}，请核对各项目是否有漏记/错记"
            self.composition_var.set(text)

        self._update_banner(period, summary)

    def _update_banner(self, period, summary):
        s = self.app.db.get_settings()
        remind = s.get("remind_payday") in ("1", "", None)
        today = datetime.now()
        try:
            payday = int(float(s.get("payday") or 0))
        except (TypeError, ValueError):
            payday = 0
        if (remind and period == _today()[:7] and payday and
                today.day >= payday and summary["actual"] is None and
                (summary["works"] or summary["deductions"])):
            self.banner_var.set(f"⚠ 已到发薪日({payday}号)，本月工资尚未登记实发，请核对！")
            self.banner.configure(bg="#FDEBDD", fg=PALETTE["danger"])
        elif summary["actual"] is not None and not summary["balanced"] and summary["diff"] != 0:
            self.banner_var.set("⚠ 实发与应发不一致，请与公司确认是否有扣款漏记。")
            self.banner.configure(bg="#FDEBDD", fg=PALETTE["danger"])
        else:
            self.banner_var.set("")
            self.banner.configure(bg=PALETTE["bg"])

    def _save_actual(self):
        period = self.period_var.get().strip()
        actual = calc.to_float(self.actual_var.get())
        if actual < 0:
            messagebox.showwarning("提示", "实发金额不能为负数")
            return
        self.app.db.save_payment(period, actual,
                                 self.paid_date_var.get().strip() or _today(),
                                 self.pay_note_var.get().strip())
        self.refresh()
        self.app.refresh_status()

    def _clear_actual(self):
        period = self.period_var.get().strip()
        if messagebox.askyesno("确认", "确定清空该月的实发工资记录吗？"):
            self.app.db.delete_payment(period)
            self.refresh()
            self.app.refresh_status()


class StatsTab(_BaseTab):
    def __init__(self, master, app):
        super().__init__(master, app)
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(top, text="统计图表（近 12 个月）", style="Status.TLabel").pack(side="left")
        tk.Label(top, text="图表类型：", font=FONT, bg=PALETTE["bg"]).pack(side="left", padx=(16, 4))
        self.chart_var = tk.StringVar(value="柱形图")
        ttk.Combobox(top, textvariable=self.chart_var, state="readonly", width=8,
                     values=("柱形图", "折线图", "面积图", "饼图")).pack(side="left")
        self.chart_var.trace_add("write", lambda *a: self._draw(self._chart_data or []))
        ttk.Button(top, text="刷新", command=self.refresh).pack(side="left", padx=8)

        self.canvas = tk.Canvas(self, bg="#FFFFFF", height=360, highlightthickness=0)
        self.canvas.pack(fill="x", padx=8, pady=4)

        mid = ttk.Frame(self)
        mid.pack(fill="x", padx=8, pady=4)
        tk.Label(mid, text="年度汇总：", font=FONT, bg=PALETTE["bg"]).pack(side="left")
        self.year_var = tk.StringVar(value=_today()[:4])
        ttk.Entry(mid, textvariable=self.year_var, width=8).pack(side="left", padx=(4, 8))
        ttk.Button(mid, text="生成年度汇总", command=self._load_annual).pack(side="left", padx=2)
        ttk.Button(mid, text="导出年度报表(.xlsx)", command=lambda: self._export("xlsx")).pack(side="left", padx=6)
        ttk.Button(mid, text="导出年度报表(.csv)", command=lambda: self._export("csv")).pack(side="left", padx=2)

        self.annual_var = tk.StringVar()
        tk.Label(self, textvariable=self.annual_var, font=FONT_BOLD, bg=PALETTE["bg"],
                 fg="#0A6EB8").pack(fill="x", padx=8)
        self.recon_var = tk.StringVar()
        tk.Label(self, textvariable=self.recon_var, font=("Microsoft YaHei UI", 10, "bold"),
                 bg=PALETTE["primary_light"], fg=PALETTE["heading"], anchor="w", padx=8, pady=3
                 ).pack(fill="x", padx=8)
        self.diff_banner_var = tk.StringVar()
        tk.Label(self, textvariable=self.diff_banner_var, font=FONT_BOLD, bg="#FDEBDD",
                 fg=PALETTE["danger"], anchor="w", padx=8, pady=3).pack(fill="x", padx=8)

        wrap = ttk.Frame(self)
        wrap.pack(fill="both", expand=True, padx=8, pady=(4, 6))
        cols = ("month", "income", "deduction", "payable", "actual", "diff")
        headers = ("月份", "收入", "扣款", "应发", "实发", "差额")
        self.tree = ttk.Treeview(wrap, columns=cols, show="headings", height=8)
        widths = {"month": 90, "income": 120, "deduction": 100, "payable": 110,
                  "actual": 110, "diff": 120}
        for c, h in zip(cols, headers):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=widths.get(c, 100), anchor="center")
        self.tree.tag_configure("diff", foreground=PALETTE["danger"])
        self.tree.tag_configure("ok", foreground="#2E7D32")
        self.tree.pack(fill="both", expand=True)
        self.refresh()

    def refresh(self):
        periods = [p for p in reversed(self.app.db.list_periods())][-12:]
        self._chart_data = calc.trend(self.app.db, periods)
        self._draw(self._chart_data)
        self._load_annual()

    def _draw(self, data):
        self._chart_data = data
        ctype = self.chart_var.get()
        if ctype == "饼图":
            self._draw_pie()
        elif ctype == "折线图":
            self._draw_line(data)
        elif ctype == "面积图":
            self._draw_area(data)
        else:
            self._draw_bar(data)

    def _axes(self, maxv, n):
        c = self.canvas
        w = c.winfo_width() or 1080
        h = c.winfo_height() or 360
        pad_l, pad_r, pad_t, pad_b = 80, 20, 44, 50
        plot_w = w - pad_l - pad_r
        plot_h = h - pad_t - pad_b
        c.create_line(pad_l, pad_t, pad_l, pad_t + plot_h, fill="#CCCCCC")
        c.create_line(pad_l, pad_t + plot_h, pad_l + plot_w, pad_t + plot_h, fill="#CCCCCC")
        for tick in range(0, 5):
            y = pad_t + plot_h - plot_h * tick / 4
            val = maxv * tick / 4
            c.create_line(pad_l - 4, y, pad_l, y, fill="#CCCCCC")
            c.create_text(pad_l - 10, y, text=f"{val:,.0f}", anchor="e",
                          font=("Microsoft YaHei UI", 11, "bold"), fill="#5C453A")
        return pad_l, pad_r, pad_t, pad_b, plot_w, plot_h

    def _x_of(self, pad_l, slot, i, n):
        return pad_l + slot * i + slot / 2

    def _draw_bar(self, data):
        c = self.canvas
        c.delete("all")
        w = c.winfo_width() or 1080
        h = c.winfo_height() or 360
        if not data:
            c.create_text(w // 2, h // 2, text="暂无数据，请先记录工作", fill="#8A7B73")
            return
        raw_max = max([d["income"] for d in data] + [d["payable"] for d in data] +
                      [d.get("actual", 0) for d in data])
        maxv = _nice_max(raw_max or 1)
        pad_l, pad_r, pad_t, pad_b, plot_w, plot_h = self._axes(maxv, len(data))
        n = len(data)
        slot = plot_w / n
        bar_w = min(26, slot * 0.16)
        colors = [("income", "#1976D2"), ("payable", "#2E9E44"), ("actual", "#FF9800")]
        for i, d in enumerate(data):
            x0 = pad_l + slot * i + slot * 0.27
            for key, color in colors:
                if key == "actual" and not d.get("paid"):
                    continue
                val = d[key]
                y1 = pad_t + plot_h - plot_h * val / maxv
                c.create_rectangle(x0, y1, x0 + bar_w, pad_t + plot_h, fill=color, outline="")
                x0 += bar_w + 2
            c.create_text(self._x_of(pad_l, slot, i, n), pad_t + plot_h + 14,
                          text=d["period"][2:], anchor="n", font=("Microsoft YaHei UI", 10),
                          fill="#5C453A")
        self._mark_diff_points(data, pad_l, slot, n, pad_t)
        c.create_text(pad_l, 16, anchor="w", text="蓝=收入  绿=应发  橙=实发  红三角=有差额",
                      font=("Microsoft YaHei UI", 9), fill="#8A7B73")

    def _mark_diff_points(self, data, pad_l, slot, n, pad_t):
        c = self.canvas
        for i, d in enumerate(data):
            if d.get("paid") and abs(d.get("diff", 0)) >= 0.005:
                x = self._x_of(pad_l, slot, i, n)
                c.create_polygon(x - 7, pad_t + 2, x + 7, pad_t + 2, x, pad_t + 18,
                                 fill="#E53935", outline="#E53935")
                c.create_text(x, pad_t + 24, text=f"{d['diff']:+.0f}", anchor="n",
                              font=("Microsoft YaHei UI", 10, "bold"), fill="#E53935")

    def _draw_line(self, data):
        c = self.canvas
        c.delete("all")
        w = c.winfo_width() or 1080
        h = c.winfo_height() or 360
        if not data:
            c.create_text(w // 2, h // 2, text="暂无数据，请先记录工作", fill="#8A7B73")
            return
        raw_max = max([d["income"] for d in data] + [d["payable"] for d in data] +
                      [d.get("actual", 0) for d in data])
        maxv = _nice_max(raw_max or 1)
        pad_l, pad_r, pad_t, pad_b, plot_w, plot_h = self._axes(maxv, len(data))
        n = len(data)
        slot = plot_w / n
        series = [("income", "#1976D2"), ("payable", "#2E9E44"), ("actual", "#FF9800")]
        for key, color in series:
            if key == "actual" and not any(d.get("paid") for d in data):
                continue
            pts = []
            for i, d in enumerate(data):
                if key == "actual" and not d.get("paid"):
                    continue
                x = self._x_of(pad_l, slot, i, n)
                y = pad_t + plot_h - plot_h * d[key] / maxv
                pts.append((x, y))
                c.create_oval(x - 4, y - 4, x + 4, y + 4, fill=color, outline="")
            for i in range(1, len(pts)):
                c.create_line(pts[i - 1][0], pts[i - 1][1], pts[i][0], pts[i][1],
                              fill=color, width=3)
        for i, d in enumerate(data):
            c.create_text(self._x_of(pad_l, slot, i, n), pad_t + plot_h + 14,
                          text=d["period"][2:], anchor="n", font=("Microsoft YaHei UI", 10),
                          fill="#5C453A")
        self._mark_diff_points(data, pad_l, slot, n, pad_t)
        c.create_text(pad_l, 16, anchor="w", text="蓝=收入  绿=应发  橙=实发  红三角=有差额",
                      font=("Microsoft YaHei UI", 9), fill="#8A7B73")

    def _draw_area(self, data):
        c = self.canvas
        c.delete("all")
        w = c.winfo_width() or 1080
        h = c.winfo_height() or 360
        if not data:
            c.create_text(w // 2, h // 2, text="暂无数据，请先记录工作", fill="#8A7B73")
            return
        raw_max = max([d["income"] for d in data] + [d["payable"] for d in data] +
                      [d.get("actual", 0) for d in data])
        maxv = _nice_max(raw_max or 1)
        pad_l, pad_r, pad_t, pad_b, plot_w, plot_h = self._axes(maxv, len(data))
        n = len(data)
        slot = plot_w / n
        base = pad_t + plot_h
        series = [("income", "#1976D2"), ("payable", "#2E9E44")]
        for key, color in series:
            pts = []
            for i, d in enumerate(data):
                x = self._x_of(pad_l, slot, i, n)
                y = pad_t + plot_h - plot_h * d[key] / maxv
                pts.append((x, y))
            poly = [pts[0][0], base] + [p for pt in pts for p in pt] + [pts[-1][0], base]
            c.create_polygon(poly, fill=color, outline=color, stipple="gray50")
            for x, y in pts:
                c.create_oval(x - 4, y - 4, x + 4, y + 4, fill=color, outline="")
        for i, d in enumerate(data):
            c.create_text(self._x_of(pad_l, slot, i, n), pad_t + plot_h + 14,
                          text=d["period"][2:], anchor="n", font=("Microsoft YaHei UI", 10),
                          fill="#5C453A")
        self._mark_diff_points(data, pad_l, slot, n, pad_t)
        c.create_text(pad_l, 16, anchor="w", text="蓝=收入  绿=应发  红三角=有差额",
                      font=("Microsoft YaHei UI", 9), fill="#8A7B73")

    def _draw_pie(self):
        c = self.canvas
        c.delete("all")
        w = c.winfo_width() or 1080
        h = c.winfo_height() or 360
        ann = getattr(self, "current_annual", None)
        by_type = (ann or {}).get("income_by_type") or {}
        items = [(k, v) for k, v in by_type.items() if v > 0]
        if not items:
            c.create_text(w // 2, h // 2, text="暂无收入数据", fill="#8A7B73")
            return
        total = sum(v for _, v in items)
        legend_w = 320
        cx = (w - legend_w) // 2
        cy = h // 2 + 6
        r = min((w - legend_w) // 2 - 20, h // 2 - 34)
        r = max(r, 40)
        colors = ["#1976D2", "#2E9E44", "#FF9800", "#9C27B0", "#E53935", "#00ACC1"]
        start = 0.0
        for i, (k, v) in enumerate(items):
            extent = 360.0 * v / total
            c.create_arc(cx - r, cy - r, cx + r, cy + r,
                         start=start, extent=extent, fill=colors[i % len(colors)],
                         outline="#FFFFFF", width=2)
            start += extent
        lx = (w - legend_w) + 24
        ly = 30
        for i, (k, v) in enumerate(items):
            c.create_rectangle(lx, ly, lx + 15, ly + 15, fill=colors[i % len(colors)], outline="")
            c.create_text(lx + 24, ly + 8, anchor="w",
                          text=f"{k}  ¥{v:,.2f}  {v / total * 100:.1f}%",
                          font=("Microsoft YaHei UI", 11), fill="#333")
            ly += 30
        # 右侧下方：对账汇总（应发/实发/差额）
        ly += 12
        c.create_line(lx, ly - 6, w - 24, ly - 6, fill="#DDD")
        recon = getattr(self, "_pie_recon", None)
        if recon:
            pay, act, diff = recon
            c.create_text(lx, ly + 8, anchor="w", text=f"应发 ¥{pay:,.2f}",
                          font=("Microsoft YaHei UI", 11, "bold"), fill="#5C453A")
            ly += 28
            c.create_text(lx, ly + 8, anchor="w", text=f"实发 ¥{act:,.2f}",
                          font=("Microsoft YaHei UI", 11, "bold"), fill="#5C453A")
            ly += 28
            if act > 0:
                color = PALETTE["ok"] if abs(diff) < 0.005 else PALETTE["danger"]
                text = "✓ 已对平" if abs(diff) < 0.005 else f"差额 {'＋' if diff >= 0 else '－'}¥{abs(diff):,.2f}"
                c.create_text(lx, ly + 8, anchor="w", text=text,
                              font=("Microsoft YaHei UI", 13, "bold"), fill=color)
            else:
                c.create_text(lx, ly + 8, anchor="w", text="未登记实发",
                              font=("Microsoft YaHei UI", 11), fill="#8A7B73")
        c.create_text(w // 2, 16, text=f"收入构成（{ann['year']}年）", fill="#5C453A",
                      font=("Microsoft YaHei UI", 11, "bold"))
        # 饼图下方标注对账差额
        recon_txt = getattr(self, "_recon_pie_text", "")
        if recon_txt:
            c.create_text(w // 2, h - 10, text=recon_txt, fill=PALETTE["danger"],
                          font=("Microsoft YaHei UI", 10, "bold"))

    def _load_annual(self):
        year = self.year_var.get().strip()
        if len(year) != 4 or not year.isdigit():
            return
        ann = calc.annual_summary(self.app.db, year)
        self.current_annual = ann
        self.annual_var.set(
            f"{year} 年：出勤 {ann['work_days']} 天，工时 {ann['work_hours']} 小时，"
            f"收入 ¥{ann['income_total']:.2f}，扣款 ¥{ann['deduction_total']:.2f}，"
            f"应发合计 ¥{ann['payable']:.2f}")
        self.tree.delete(*self.tree.get_children())
        diff_months = []
        total_payable = 0.0
        total_actual = 0.0
        for m, v in ann["by_month"].items():
            pay = self.app.db.get_payment(m)
            if pay:
                actual = pay["actual_amount"]
                diff = round(actual - v["payable"], 2)
                total_payable += v["payable"]
                total_actual += actual
                tag = "diff" if abs(diff) >= 0.005 else "ok"
                self.tree.insert("", "end", values=(m, v["income"], v["deduction"],
                                                    v["payable"], actual, diff), tags=(tag,))
                if abs(diff) >= 0.005:
                    diff_months.append((m, v["payable"], actual, diff))
            else:
                self.tree.insert("", "end", values=(m, v["income"], v["deduction"],
                                                    v["payable"], "未登记", "—"))
        if not ann["by_month"]:
            self.tree.insert("", "end", values=(year, "本年暂无记录", "", "", "", ""))
            self.recon_var.set("")
        else:
            if total_actual > 0:
                diff_all = round(total_actual - total_payable, 2)
                sign = "＋" if diff_all >= 0 else "－"
                status = "已对平" if abs(diff_all) < 0.005 else f"差额 {sign}¥{abs(diff_all):.2f}"
                self.recon_var.set(
                    f"📋 年度对账汇总：应发合计 ¥{total_payable:.2f}　实发合计 ¥{total_actual:.2f}　{status}")
                self._recon_pie_text = (
                    f"对账：应发 ¥{total_payable:.2f}　实发 ¥{total_actual:.2f}　{status}"
                    if abs(diff_all) >= 0.005 else "")
                self._pie_recon = (total_payable, total_actual, diff_all)
            else:
                self.recon_var.set(f"📋 年度对账汇总：应发合计 ¥{total_payable:.2f}（尚未登记实发）")
                self._recon_pie_text = ""
                self._pie_recon = (total_payable, 0.0, 0.0)
        if diff_months:
            lines = "⚠ 对账有差额的月份："
            lines += "；".join(f"{m} 应发¥{a:.2f} 实发¥{b:.2f} 差额{'＋' if c >= 0 else '－'}¥{abs(c):.2f}"
                               for m, a, b, c in diff_months)
            self.diff_banner_var.set(lines)
        else:
            self.diff_banner_var.set("")

    def _export(self, fmt):
        if not hasattr(self, "current_annual"):
            return
        ann = self.current_annual
        path = filedialog.asksaveasfilename(
            title="选择保存位置",
            defaultextension=".xlsx" if fmt == "xlsx" else ".csv",
            initialfile=f"工资年度报表_{ann['year']}.{'xlsx' if fmt == 'xlsx' else 'csv'}",
            filetypes=[("Excel 文件", "*.xlsx")] if fmt == "xlsx" else [("CSV 文件", "*.csv")],
        )
        if not path:
            return
        try:
            settings = self.app.db.get_settings()
            if fmt == "xlsx":
                from . import excel
                excel.export_year(path, ann, settings.get("company", ""))
            else:
                from . import csvio
                csvio.export_year(path, ann, settings.get("company", ""))
            messagebox.showinfo("完成", f"已导出：\n{path}")
        except Exception as exc:
            messagebox.showerror("导出失败", str(exc))


class SyncTab(_BaseTab):
    def __init__(self, master, app):
        super().__init__(master, app)
        from . import discovery as discovery_mod
        self.discovery_mod = discovery_mod
        self.app.discovery = discovery_mod.DiscoveryService(
            name=discovery_mod.host_name(),
            port_getter=lambda: (self.app.sync_server.port if self.app.sync_server.running else 0),
        )
        self.device_items = {}
        self.build_lan()
        self.build_json()
        self.build_backup()
        self.build_password()
        self._poll_devices()

    # ---------- 局域网同步 ----------
    def build_lan(self):
        frame = ttk.LabelFrame(self, text="局域网同步（自动发现设备，需同一 WiFi）")
        frame.pack(fill="x", padx=10, pady=(10, 8))
        row1 = ttk.Frame(frame)
        row1.pack(fill="x", padx=6, pady=6)
        self.sync_state = tk.StringVar(value="同步服务未启动")
        self.sync_state_label = tk.Label(row1, textvariable=self.sync_state, font=FONT_BOLD, bg=PALETTE["panel"],
                                         fg="#7A6A62")
        self.sync_state_label.pack(side="left", padx=(2, 16))
        tk.Label(row1, text="端口：", font=FONT, bg=PALETTE["panel"]).pack(side="left")
        self.port_var = tk.StringVar(value=str(lanserver.DEFAULT_PORT))
        ttk.Entry(row1, textvariable=self.port_var, width=8).pack(side="left", padx=(2, 12))
        ttk.Button(row1, text="启动同步服务", style="Success.TButton", command=self._start).pack(side="left", padx=2)
        ttk.Button(row1, text="停止服务", style="Danger.TButton", command=self._stop).pack(side="left", padx=2)

        self.sync_info_var = tk.StringVar(value="")
        tk.Label(frame, textvariable=self.sync_info_var, font=FONT_SMALL, bg=PALETTE["panel"],
                 fg="#0A6EB8", justify="left").pack(fill="x", padx=6, pady=(0, 4))

        # 设备列表
        tk.Label(frame, text="已发现设备（两端软件都开着会自动出现在这里，点设备即可同步）：",
                 font=FONT_SMALL, bg=PALETTE["panel"], fg=PALETTE["muted"], anchor="w").pack(fill="x", padx=6)
        wrap = ttk.Frame(frame)
        wrap.pack(fill="x", padx=6, pady=(2, 4))
        self.device_tree = ttk.Treeview(wrap, columns=("name", "host", "port"),
                                        show="headings", height=4, selectmode="browse")
        for c, h, w in [("name", "设备名称", 200), ("host", "IP 地址", 160), ("port", "端口", 70)]:
            self.device_tree.heading(c, text=h)
            self.device_tree.column(c, width=w, anchor="center")
        self.device_tree.pack(side="left", fill="x", expand=True)

        row2 = ttk.Frame(frame)
        row2.pack(fill="x", padx=6, pady=(0, 6))
        ttk.Button(row2, text="重新扫描", command=self._scan).pack(side="left", padx=2)
        ttk.Button(row2, text="拉取(对方 → 本机)", style="Accent.TButton", command=self._do_pull).pack(side="left", padx=2)
        ttk.Button(row2, text="推送(本机 → 对方)", style="Success.TButton", command=self._do_push).pack(side="left", padx=2)
        ttk.Button(row2, text="手动连接", command=self._manual_connect).pack(side="left", padx=2)

        tk.Label(frame,
                 text="手机操作：打开 App → 设置 → 数据同步，会自动检测到本电脑；点设备旁「拉取/推送」即可。",
                 font=FONT_SMALL, bg=PALETTE["panel"], fg=PALETTE["muted"],
                 justify="left").pack(fill="x", padx=6, pady=(0, 6))

    # ---------- 服务启停 ----------
    def _start(self):
        try:
            port = int(self.port_var.get().strip() or lanserver.DEFAULT_PORT)
        except ValueError:
            messagebox.showwarning("提示", "端口需为数字")
            return
        if self.app.sync_server.running:
            self.app.sync_server.stop()
        server = lanserver.SyncServer(self.app.db, port)
        try:
            server.start()
        except OSError as exc:
            messagebox.showerror("启动失败", f"端口可能被占用：\n{exc}")
            return
        self.app.sync_server = server
        self.app.discovery.start()
        self._refresh_server_state()
        messagebox.showinfo("已启动",
                            f"同步服务已启动：{'、'.join(lanserver.get_lan_ips()) or '本机IP'}:{port}\n"
                            f"手机和电脑连同一 WiFi 后，打开手机 App 的数据同步页即可发现本电脑。")

    def _stop(self):
        self.app.sync_server.stop()
        self.app.discovery.stop()
        self._refresh_server_state()

    def _refresh_server_state(self):
        s = self.app.sync_server
        if s.running:
            ip = "、".join(lanserver.get_lan_ips()) or "本机"
            self.sync_state.set("● 同步服务运行中（正在广播，等待设备…）")
            self.sync_state_label.configure(fg=PALETTE["ok"])
            self.sync_info_var.set(f"本机地址：{ip}:{s.port}    设备名：{self.app.discovery.name}")
        else:
            self.sync_state.set("○ 同步服务未启动")
            self.sync_state_label.configure(fg="#7A6A62")
            self.sync_info_var.set("")

    # ---------- 设备列表 ----------
    def _poll_devices(self):
        try:
            if getattr(self.app, "discovery", None) and self.app.discovery.running:
                seen = set()
                for d in self.app.discovery.device_list():
                    seen.add(d["id"])
                    self._upsert_device(d)
                for did in list(self.device_items.keys()):
                    if did not in seen:
                        try:
                            self.device_tree.delete(self.device_items[did])
                        except Exception:
                            pass
                        del self.device_items[did]
            else:
                for did in list(self.device_items.keys()):
                    try:
                        self.device_tree.delete(self.device_items[did])
                    except Exception:
                        pass
                    del self.device_items[did]
        except Exception:
            pass
        try:
            self.after(1500, self._poll_devices)
        except Exception:
            pass

    def _upsert_device(self, d):
        iid = d["id"]
        vals = (d["name"], d["host"], d["port"])
        if iid in self.device_items:
            try:
                self.device_tree.item(self.device_items[iid], values=vals)
            except Exception:
                pass
        else:
            try:
                tree_iid = self.device_tree.insert("", "end", iid=iid, values=vals)
                self.device_items[iid] = tree_iid
            except Exception:
                pass

    def _scan(self):
        if not (self.app.sync_server.running and self.app.discovery.running):
            messagebox.showwarning("提示", "请先启动同步服务")
            return
        self._refresh_server_state()
        self.app.discovery.scan(2.5)
        for d in self.app.discovery.device_list():
            self._upsert_device(d)
        messagebox.showinfo("扫描完成", "已刷新设备列表，选中设备后点「拉取」或「推送」")

    def _selected_device(self):
        sel = self.device_tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先在设备列表中选择一台设备")
            return None
        vals = self.device_tree.item(sel[0], "values")
        return {"name": vals[0], "host": vals[1], "port": int(vals[2])}

    def _do_pull(self):
        dev = self._selected_device()
        if not dev:
            return
        if not messagebox.askyesno("确认拉取",
                                   f"将合并 {dev['name']}（{dev['host']}）的数据到本机：\n"
                                   "完全相同的记录自动去重，不同的记录追加。确定吗？"):
            return
        try:
            text = lanserver.pull_device(dev["host"], dev["port"])
            result = sync_mod.import_json(self.app.db, text)
            self.app.refresh_all()
            messagebox.showinfo("拉取成功", f"来自 {dev['name']}：\n{result}")
        except Exception as exc:
            messagebox.showerror("拉取失败", f"{dev['name']}：{exc}")

    def _do_push(self):
        dev = self._selected_device()
        if not dev:
            return
        if not messagebox.askyesno("确认推送",
                                   f"将本机数据合并到 {dev['name']}（{dev['host']}）：\n"
                                   "完全相同的记录自动去重，不同的记录追加。确定吗？"):
            return
        try:
            res = lanserver.push_device(dev["host"], dev["port"], sync_mod.export_json(self.app.db))
            messagebox.showinfo("推送成功", f"到 {dev['name']}：\n{res}")
        except Exception as exc:
            messagebox.showerror("推送失败", f"{dev['name']}：{exc}")

    # ---------- 手动连接（备选） ----------
    def _manual_connect(self):
        win = tk.Toplevel(self)
        win.title("手动连接设备")
        win.geometry("360x180")
        win.resizable(False, False)
        win.configure(bg=PALETTE["bg"])
        win.transient(self)
        tk.Label(win, text="手动输入对方地址（不自动发现时使用）", font=FONT_BOLD,
                 bg=PALETTE["bg"], fg=PALETTE["heading"]).pack(pady=(14, 8))
        f = tk.Frame(win, bg=PALETTE["bg"])
        f.pack()
        tk.Label(f, text="IP/域名：", font=FONT, bg=PALETTE["bg"]).grid(row=0, column=0, sticky="w", pady=4)
        host_var = tk.StringVar()
        ttk.Entry(f, textvariable=host_var, width=20).grid(row=0, column=1, pady=4)
        tk.Label(f, text="端口：", font=FONT, bg=PALETTE["bg"]).grid(row=1, column=0, sticky="w", pady=4)
        port_var = tk.StringVar(value=str(lanserver.DEFAULT_PORT))
        ttk.Entry(f, textvariable=port_var, width=20).grid(row=1, column=1, pady=4)

        def pull():
            try:
                text = lanserver.pull_device(host_var.get().strip(), int(port_var.get().strip()))
                result = sync_mod.import_json(self.app.db, text)
                self.app.refresh_all()
                messagebox.showinfo("拉取成功", result, parent=win)
            except Exception as exc:
                messagebox.showerror("拉取失败", str(exc), parent=win)

        def push():
            try:
                res = lanserver.push_device(host_var.get().strip(), int(port_var.get().strip()),
                                            sync_mod.export_json(self.app.db))
                messagebox.showinfo("推送成功", res, parent=win)
            except Exception as exc:
                messagebox.showerror("推送失败", str(exc), parent=win)

        btns = tk.Frame(win, bg=PALETTE["bg"])
        btns.pack(pady=10)
        ttk.Button(btns, text="拉取", style="Accent.TButton", command=pull).pack(side="left", padx=4)
        ttk.Button(btns, text="推送", style="Success.TButton", command=push).pack(side="left", padx=4)

    # ---------- JSON 文件备份 ----------
    def build_json(self):
        frame = ttk.LabelFrame(self, text="文件备份（Excel / JSON，可微信/QQ 发给手机，或换机迁移）")
        frame.pack(fill="x", padx=10, pady=(0, 8))
        btns = ttk.Frame(frame)
        btns.pack(fill="x", padx=6, pady=8)
        ttk.Button(btns, text="导出 Excel(.xlsx)", style="Accent.TButton", command=self._export_excel).pack(side="left", padx=2)
        ttk.Button(btns, text="导入 Excel", command=self._import_excel).pack(side="left", padx=2)
        ttk.Button(btns, text="导出 JSON", command=self._export_json).pack(side="left", padx=2)
        ttk.Button(btns, text="导入 JSON", command=self._import_json).pack(side="left", padx=2)
        tk.Label(btns, text="导入为智能合并：相同记录去重，不同记录追加。",
                 font=FONT_SMALL, bg=PALETTE["panel"], fg=PALETTE["muted"]).pack(side="left", padx=16)

    def _export_excel(self):
        path = filedialog.asksaveasfilename(
            title="导出全部数据到 Excel", defaultextension=".xlsx",
            initialfile=f"薪资记录全部数据_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            filetypes=[("Excel 文件", "*.xlsx")])
        if not path:
            return
        try:
            from . import excel
            excel.export_all(path, self.app.db, self.app.db.get_settings().get("company", ""))
            messagebox.showinfo("完成", f"已导出：\n{path}")
        except Exception as exc:
            messagebox.showerror("导出失败", str(exc))

    def _import_excel(self):
        path = filedialog.askopenfilename(title="选择 Excel 文件",
                                          filetypes=[("Excel 文件", "*.xlsx")])
        if not path:
            return
        if not messagebox.askyesno("确认",
                                   "将合并导入该 Excel 中的数据：完全相同的记录自动去重，不同的记录追加。确定继续吗？"):
            return
        try:
            from . import excel
            result = excel.import_excel(path, self.app.db)
            self.app.refresh_all()
            messagebox.showinfo("导入成功", f"导入结果：\n{result}")
        except Exception as exc:
            messagebox.showerror("导入失败", str(exc))

    def _export_json(self):
        path = filedialog.asksaveasfilename(
            title="导出 JSON 备份", defaultextension=".json",
            initialfile=f"工资数据备份_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
            filetypes=[("JSON 文件", "*.json")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(sync_mod.export_json(self.app.db))
            messagebox.showinfo("完成", f"已导出：\n{path}")
        except Exception as exc:
            messagebox.showerror("导出失败", str(exc))

    def _import_json(self):
        path = filedialog.askopenfilename(title="选择 JSON 备份",
                                          filetypes=[("JSON 文件", "*.json")])
        if not path:
            return
        if not messagebox.askyesno("确认",
                                   "将合并导入当前数据：完全相同的记录自动去重，不同的记录追加。确定继续吗？"):
            return
        try:
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
            result = sync_mod.import_json(self.app.db, text)
            self.app.refresh_all()
            messagebox.showinfo("导入成功", f"导入结果：{result}")
        except Exception as exc:
            messagebox.showerror("导入失败", str(exc))

    # ---------- 数据库备份 ----------
    def build_backup(self):
        frame = ttk.LabelFrame(self, text="数据库备份 / 恢复 / 全部导出")
        frame.pack(fill="x", padx=10, pady=(0, 8))
        btns = ttk.Frame(frame)
        btns.pack(fill="x", padx=6, pady=8)
        ttk.Button(btns, text="一键备份数据库", command=self._backup).pack(side="left", padx=2)
        ttk.Button(btns, text="从备份恢复", command=self._restore).pack(side="left", padx=2)
        ttk.Button(btns, text="导出全部数据 CSV", command=self._export_all).pack(side="left", padx=2)
        tk.Label(btns, text=f"数据文件：{self.app.db.db_path}",
                 font=FONT_SMALL, bg=PALETTE["panel"], fg=PALETTE["muted"]).pack(side="left", padx=16)

    def _backup(self):
        default = f"工资数据备份_{datetime.now().strftime('%Y%m%d_%H%M')}.db"
        path = filedialog.asksaveasfilename(
            title="选择备份保存位置", defaultextension=".db", initialfile=default,
            filetypes=[("数据库文件", "*.db")])
        if not path:
            return
        try:
            self.app.db.backup_to(path)
            messagebox.showinfo("完成", f"备份成功：\n{path}")
        except Exception as exc:
            messagebox.showerror("备份失败", str(exc))

    def _restore(self):
        path = filedialog.askopenfilename(title="选择备份文件", filetypes=[("数据库文件", "*.db")])
        if not path:
            return
        if not messagebox.askyesno("确认",
                                   "恢复将覆盖当前全部数据，确定继续吗？\n建议先做一次备份。"):
            return
        try:
            self.app.db.restore_from(path)
            self.app.refresh_all()
            self._refresh_pwd_state()
            messagebox.showinfo("完成", "恢复成功")
        except Exception as exc:
            messagebox.showerror("恢复失败", str(exc))

    def _export_all(self):
        path = filedialog.asksaveasfilename(
            title="选择保存位置", defaultextension=".csv", initialfile="工资全部数据.csv",
            filetypes=[("CSV 文件", "*.csv")])
        if not path:
            return
        try:
            from . import csvio
            csvio.export_all(path, self.app.db)
            messagebox.showinfo("完成", f"已导出：\n{path}")
        except Exception as exc:
            messagebox.showerror("导出失败", str(exc))

    # ---------- 密码 ----------
    def build_password(self):
        pwd = ttk.LabelFrame(self, text="启动密码保护（工资隐私）")
        pwd.pack(fill="x", padx=10, pady=(0, 10))
        inner = ttk.Frame(pwd)
        inner.pack(fill="x", padx=6, pady=8)
        self.pwd_state = tk.StringVar()
        tk.Label(inner, textvariable=self.pwd_state, font=FONT_BOLD, bg=PALETTE["panel"],
                 fg="#0A6EB8").grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 6))
        tk.Label(inner, text="当前密码：", font=FONT, bg=PALETTE["panel"]).grid(row=1, column=0, sticky="w")
        self.pwd_old = tk.StringVar()
        ttk.Entry(inner, textvariable=self.pwd_old, show="*", width=16).grid(row=1, column=1, sticky="w", padx=(0, 12))
        tk.Label(inner, text="新密码：", font=FONT, bg=PALETTE["panel"]).grid(row=1, column=2, sticky="w")
        self.pwd_new = tk.StringVar()
        ttk.Entry(inner, textvariable=self.pwd_new, show="*", width=16).grid(row=1, column=3, sticky="w")
        tk.Label(inner, text="确认新密码：", font=FONT, bg=PALETTE["panel"]).grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.pwd_new2 = tk.StringVar()
        ttk.Entry(inner, textvariable=self.pwd_new2, show="*", width=16).grid(row=2, column=1, sticky="w", padx=(0, 12), pady=(6, 0))
        ttk.Button(inner, text="设置/修改密码", command=self._set_pwd).grid(row=2, column=2, sticky="w", pady=(6, 0))
        ttk.Button(inner, text="清除密码", style="Danger.TButton", command=self._clear_pwd).grid(row=2, column=3, sticky="w", pady=(6, 0))
        self._refresh_pwd_state()

    def refresh(self):
        self._refresh_server_state()
        self._refresh_pwd_state()

    def _refresh_pwd_state(self):
        has = bool(self.app.db.get_settings().get("password"))
        self.pwd_state.set("当前状态：" + ("已开启密码保护" if has else "未开启密码保护"))

    def _set_pwd(self):
        s = self.app.db.get_settings()
        current = s.get("password")
        old = self.pwd_old.get()
        if current and _hash_pwd(old) != current:
            messagebox.showerror("错误", "当前密码不正确")
            return
        new = self.pwd_new.get()
        if not new:
            messagebox.showwarning("提示", "新密码不能为空")
            return
        if new != self.pwd_new2.get():
            messagebox.showwarning("提示", "两次输入的新密码不一致")
            return
        self.app.db.save_settings({"password": _hash_pwd(new)})
        self.pwd_old.set("")
        self.pwd_new.set("")
        self.pwd_new2.set("")
        self._refresh_pwd_state()
        messagebox.showinfo("完成", "密码已设置，下次启动需输入")

    def _clear_pwd(self):
        s = self.app.db.get_settings()
        current = s.get("password")
        if current and _hash_pwd(self.pwd_old.get()) != current:
            messagebox.showerror("错误", "当前密码不正确")
            return
        self.app.db.save_settings({"password": ""})
        self.pwd_old.set("")
        self._refresh_pwd_state()
        messagebox.showinfo("完成", "密码已清除")
