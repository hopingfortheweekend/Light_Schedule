"""
日历视图页面：按优先度标记日期颜色 + 详情面板彩色文字。
多种日程在同一天时，以最紧急的状态为准；固定任务最低优先。
"""
import tkinter as tk
from tkinter import ttk
from tkcalendar import Calendar
import datetime
from utils.i18n import t


class CalendarTab(ttk.Frame):
    def __init__(self, parent, data_store):
        super().__init__(parent)
        self.data_store = data_store
        self.today = datetime.date.today()

        self.cal = Calendar(self, selectmode="day",
                            date_pattern="yyyy-mm-dd",
                            showweeknumbers=False)
        self.cal.pack(fill="both", expand=True, pady=(10, 0))
        self.cal.bind("<<CalendarSelected>>", self._on_date_select)

        # 颜色：按紧急度从高到低
        self.cal.tag_config("overdue", background="#FF4757", foreground="white")
        self.cal.tag_config("today_due", background="#FF6B6B", foreground="white")
        self.cal.tag_config("soon_3d", background="#FFA502", foreground="white")
        self.cal.tag_config("week_7d", background="#FFD93D", foreground="black")
        self.cal.tag_config("later", background="#6BCB77", foreground="white")
        self.cal.tag_config("routine", background="#9B59B6", foreground="white")

        # 图例
        legend_frame = ttk.LabelFrame(self, text="图例", padding=5)
        legend_frame.pack(fill="x", padx=10, pady=5)
        legends = [
            ("逾期/今天到期", "#FF4757"),
            ("3天内到期", "#FFA502"),
            ("7天内到期", "#FFD93D"),
            ("更远到期", "#6BCB77"),
            ("固定任务", "#9B59B6"),
        ]
        for i, (text, color) in enumerate(legends):
            ttk.Label(legend_frame, text=f"  ● {text}  ", foreground=color,
                      font=("", 9, "bold")).grid(row=0, column=i, padx=3)

        # 详情面板
        detail_frame = ttk.LabelFrame(self, text="当日详情", padding=5)
        detail_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.detail_text = tk.Text(detail_frame, height=7, wrap=tk.WORD, font=("", 10))
        self.detail_text.pack(fill="both", expand=True)

        # Text 颜色标签
        self.detail_text.tag_config("overdue", foreground="#FF4757")
        self.detail_text.tag_config("today_due", foreground="#FF6B6B")
        self.detail_text.tag_config("soon_3d", foreground="#FFA502")
        self.detail_text.tag_config("week_7d", foreground="#FFD93D")
        self.detail_text.tag_config("later", foreground="#6BCB77")
        self.detail_text.tag_config("routine", foreground="#9B59B6")
        self.detail_text.tag_config("done", foreground="#999999")
        self.detail_text.tag_config("normal", foreground="black")
        self.detail_text.tag_config("header", font=("", 10, "bold"))
        self.detail_text.tag_config("section", font=("", 9, "bold"), foreground="#555555")

        self.refresh()

    # ── 公开方法 ──────────────────────────────

    def refresh(self):
        self.cal.calevent_remove("all")

        # 对每个日期，收集所有事件的紧急度等级
        # 等级：0=overdue, 1=today, 2=soon3d, 3=week7d, 4=later, 5=routine
        date_priority = {}  # date_str → min_priority

        # 项目步骤截止日期
        for proj_name, step in self.data_store.get_all_step_deadlines():
            try:
                dl = datetime.date.fromisoformat(step["deadline"])
            except ValueError:
                continue
            days_left = (dl - self.today).days
            if days_left < 0:
                prio = 0
                tag = "overdue"
            elif days_left == 0:
                prio = 1
                tag = "today_due"
            elif days_left <= 3:
                prio = 2
                tag = "soon_3d"
            elif days_left <= 7:
                prio = 3
                tag = "week_7d"
            else:
                prio = 4
                tag = "later"

            ds = step["deadline"]
            if ds not in date_priority or prio < date_priority[ds]:
                date_priority[ds] = prio

        # 固定任务日期
        start = self.today.replace(day=1)
        end_month = self.today.month + 3
        end_year = self.today.year
        while end_month > 12:
            end_month -= 12
            end_year += 1
        if end_month == 12:
            end = datetime.date(end_year + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            end = datetime.date(end_year, end_month + 1, 1) - datetime.timedelta(days=1)

        routine_dates = self.data_store.get_routine_dates_all(start, end)
        for date_str in routine_dates:
            if date_str not in date_priority:
                date_priority[date_str] = 5  # routine

        # 统一绘制
        tag_map = {0: "overdue", 1: "today_due", 2: "soon_3d", 3: "week_7d", 4: "later", 5: "routine"}
        for ds, prio in date_priority.items():
            try:
                dt = datetime.date.fromisoformat(ds)
            except ValueError:
                continue
            tag = tag_map.get(prio, "routine")
            self.cal.calevent_create(dt, "", tags=[tag])

    # ── 点击详情 ──────────────────────────────

    def _on_date_select(self, event=None):
        date_obj = self.cal.selection_get()
        date_str = str(date_obj)

        self.detail_text.delete("1.0", tk.END)

        # 标题
        self.detail_text.insert(tk.END, f"📅 {date_str}\n", "header")

        # ── 单次任务 ──
        self.detail_text.insert(tk.END, "\n── 单次任务 ──\n", "section")
        tasks = self.data_store.get_tasks(date_str)
        if tasks:
            for t in tasks:
                status = "✓" if t.get("done") else "✗"
                tag = self._task_color_tag(t, date_str)
                self.detail_text.insert(tk.END, f"  [{status}] {t['task']}\n", tag)
        else:
            self.detail_text.insert(tk.END, "  (无)\n", "normal")

        # ── 项目步骤截止 ──
        self.detail_text.insert(tk.END, "\n── 项目步骤截止 ──\n", "section")
        due_steps = self.data_store.get_steps_due_on(date_str)
        if due_steps:
            for proj_name, step in due_steps:
                status = "✓" if step.get("done") else "✗"
                tag = self._step_color_tag(step)
                line = f"  [{status}] [{proj_name}] {step['step']}\n"
                self.detail_text.insert(tk.END, line, tag)
        else:
            self.detail_text.insert(tk.END, "  (无)\n", "normal")

        # ── 固定任务 ──
        self.detail_text.insert(tk.END, "\n── 固定任务 ──\n", "section")
        routine_info = self.data_store.get_routine_info(date_str)
        if routine_info:
            for rid, rname in routine_info:
                self.detail_text.insert(tk.END, f"  🔄 {rname}\n", "routine")
        else:
            self.detail_text.insert(tk.END, "  (无)\n", "normal")

    def _task_color_tag(self, task, fallback_date):
        """根据任务 deadline 返回对应颜色 tag"""
        dl = task.get("deadline", fallback_date)
        if task.get("done"):
            return "done"
        return self._deadline_tag(dl)

    def _step_color_tag(self, step):
        """根据步骤 deadline 和完成状态返回颜色 tag"""
        if step.get("done"):
            return "done"
        dl = step.get("deadline", "")
        if not dl:
            return "normal"
        return self._deadline_tag(dl)

    def _deadline_tag(self, dl_str):
        """根据 deadline 日期返回对应颜色 tag"""
        try:
            dl = datetime.date.fromisoformat(dl_str)
        except ValueError:
            return "normal"
        days = (dl - self.today).days
        if days < 0:
            return "overdue"
        elif days == 0:
            return "today_due"
        elif days <= 3:
            return "soon_3d"
        elif days <= 7:
            return "week_7d"
        else:
            return "later"
