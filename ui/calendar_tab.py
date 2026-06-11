"""
日历视图页面：彩色 DDL 标记 + 图例 + 日期详情面板
"""
import tkinter as tk
from tkinter import ttk
from tkcalendar import Calendar
import datetime


class CalendarTab(ttk.Frame):
    def __init__(self, parent, data_store):
        super().__init__(parent)
        self.data_store = data_store

        # 日历组件
        self.cal = Calendar(self, selectmode="day",
                            date_pattern="yyyy-mm-dd",
                            showweeknumbers=False)
        self.cal.pack(fill="both", expand=True, pady=(10, 0))
        self.cal.bind("<<CalendarSelected>>", self._on_date_select)

        # 事件颜色标记
        self.cal.tag_config("task_normal", background="#4D96FF", foreground="white")
        self.cal.tag_config("deadline_overdue", background="#FF4757", foreground="white")
        self.cal.tag_config("deadline_today", background="#FF6B6B", foreground="white")
        self.cal.tag_config("deadline_soon", background="#FFA502", foreground="white")
        self.cal.tag_config("deadline_week", background="#FFD93D", foreground="black")
        self.cal.tag_config("deadline_later", background="#6BCB77", foreground="white")

        # 图例
        legend_frame = ttk.LabelFrame(self, text="图例", padding=5)
        legend_frame.pack(fill="x", padx=10, pady=5)
        legends = [
            ("任务日", "#4D96FF"), ("逾期/今天到期", "#FF4757"),
            ("3天内到期", "#FFA502"), ("7天内到期", "#FFD93D"), ("更远到期", "#6BCB77"),
        ]
        for i, (text, color) in enumerate(legends):
            ttk.Label(legend_frame, text=f"  ● {text}  ", foreground=color,
                      font=("", 9, "bold")).grid(row=0, column=i, padx=3)

        # 日期详情面板
        detail_frame = ttk.LabelFrame(self, text="当日详情", padding=5)
        detail_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.detail_text = tk.Text(detail_frame, height=6, wrap=tk.WORD, font=("", 10))
        self.detail_text.pack(fill="both", expand=True)

        self.refresh()

    # ── 公开方法 ──────────────────────────────

    def refresh(self):
        """刷新日历上的事件标记（外部调用）"""
        self.cal.calevent_remove("all")
        today = datetime.date.today()

        # 有每日任务的日期 → 蓝色
        for date_str in self.data_store.get_all_task_dates():
            try:
                dt = datetime.date.fromisoformat(date_str)
                self.cal.calevent_create(dt, "有任务", tags=["task_normal"])
            except ValueError:
                continue

        # 项目步骤截止日期 → 按紧急程度分色
        for proj_name, step in self.data_store.get_all_step_deadlines():
            try:
                dl = datetime.date.fromisoformat(step["deadline"])
            except ValueError:
                continue

            desc = step["step"]
            if len(desc) > 15:
                desc = desc[:15] + "…"
            label = f"{proj_name}: {desc}"

            days_left = (dl - today).days
            if days_left < 0:
                tag = "deadline_overdue"
            elif days_left == 0:
                tag = "deadline_today"
            elif days_left <= 3:
                tag = "deadline_soon"
            elif days_left <= 7:
                tag = "deadline_week"
            else:
                tag = "deadline_later"

            self.cal.calevent_create(dl, label, tags=[tag])

    # ── 内部交互 ──────────────────────────────

    def _on_date_select(self, event=None):
        """点击某天时，在详情面板显示当天内容"""
        date_obj = self.cal.selection_get()
        date_str = str(date_obj)
        today = datetime.date.today()

        lines = [f"📅 {date_str}"]

        # 每日任务
        tasks = self.data_store.get_tasks(date_str)
        if tasks:
            lines.append("\n── 每日任务 ──")
            for t in tasks:
                status = "✓" if t["done"] else "✗"
                lines.append(f"  [{status}] {t['task']}")
        else:
            lines.append("\n── 每日任务 ──")
            lines.append("  (无)")

        # 项目步骤截止
        lines.append("\n── 项目步骤截止 ──")
        due_steps = self.data_store.get_steps_due_on(date_str)
        if due_steps:
            for proj_name, step in due_steps:
                status = "✓" if step.get("done") else "✗"
                days_left = (date_obj - today).days
                urgent = ""
                if not step.get("done") and days_left < 0:
                    urgent = " ⚠️已逾期"
                elif not step.get("done") and days_left == 0:
                    urgent = " 🔴今天到期"
                elif not step.get("done") and days_left <= 3:
                    urgent = f" 🟡仅剩{days_left}天"
                lines.append(f"  [{status}] [{proj_name}] {step['step']}{urgent}")
        else:
            lines.append("  (无)")

        self.detail_text.delete("1.0", tk.END)
        self.detail_text.insert("1.0", "\n".join(lines))
