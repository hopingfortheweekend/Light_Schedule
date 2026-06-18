"""
单次任务页面：今日任务（上区）+ 之后任务（下区），含倒计时和过期外观。
支持添加任意日期的单次任务，以及当日截止的长期项目步骤。
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import datetime

from ui.dialogs import EditDialog, TaskDialog
from utils.i18n import t


def _countdown_text(deadline_str, today=None):
    """根据截止日期生成倒计时文本。返回 (text, is_overdue)。
    deadline_str 为空时返回 ('', False)。"""
    if not deadline_str:
        return "", False
    try:
        dl = datetime.date.fromisoformat(deadline_str)
    except ValueError:
        return "", False
    if today is None:
        today = datetime.date.today()
    days = (dl - today).days
    if days < 0:
        return f"⚠️ {t('overdue_days', -days)}", True
    elif days == 0:
        return f"🔴 {t('today_deadline')}", False
    else:
        return f"⏰ {t('days_left', days)}", False


def _pad_right(left_text, right_text, total_width=55):
    """将 left_text 和 right_text 分别置于一行左右两侧。
    left_text 靠左，right_text 靠右，中间用空格填充到约 total_width 字符宽。"""
    if not right_text:
        return left_text
    # 估算中英文混合宽度：CJK 字符约等于 2 个 ASCII 字符宽
    def _width(s):
        w = 0
        for ch in s:
            if '一' <= ch <= '鿿' or '　' <= ch <= '〿' or '＀' <= ch <= '￯':
                w += 2
            else:
                w += 1
        return w
    left_w = _width(left_text)
    right_w = _width(right_text)
    padding = max(2, total_width - left_w - right_w)
    return left_text + " " * padding + right_text


class SingleTaskTab(ttk.Frame):
    def __init__(self, parent, data_store, on_data_changed=None):
        super().__init__(parent)
        self.data_store = data_store
        self.on_data_changed = on_data_changed
        self.task_date = datetime.date.today()
        self.today = datetime.date.today()

        # ── 上半区：今日任务 ──
        today_frame = ttk.LabelFrame(self, text=f"📅 {t('today_tasks')} ({self.today})", padding=5)
        today_frame.pack(fill="both", expand=True, padx=5, pady=(5, 2))

        self.today_listbox = tk.Listbox(today_frame, height=6, cursor="hand2")
        self.today_listbox.pack(fill="both", expand=True)
        self.today_listbox.bind("<Button-1>", self._on_today_click)
        self.today_listbox.bind("<Double-Button-1>", self._on_today_edit)

        today_btn = ttk.Frame(today_frame)
        today_btn.pack(pady=(3, 0))
        ttk.Button(today_btn, text=t("add_task_today"), command=self._add_today).pack(side=tk.LEFT, padx=2)
        ttk.Button(today_btn, text=t("delete"), command=lambda: self._delete_selected(self.today_listbox, self._today_items)).pack(side=tk.LEFT, padx=2)

        # ── 下半区：之后的任务 ──
        upcoming_frame = ttk.LabelFrame(self, text=f"📆 {t('upcoming_tasks')}", padding=5)
        upcoming_frame.pack(fill="both", expand=True, padx=5, pady=(2, 5))

        self.upcoming_listbox = tk.Listbox(upcoming_frame, height=6, cursor="hand2")
        self.upcoming_listbox.pack(fill="both", expand=True)
        self.upcoming_listbox.bind("<Button-1>", self._on_upcoming_click)
        self.upcoming_listbox.bind("<Double-Button-1>", self._on_upcoming_edit)

        up_btn = ttk.Frame(upcoming_frame)
        up_btn.pack(pady=(3, 0))
        ttk.Button(up_btn, text=t("add_task_date"), command=self._add_upcoming).pack(side=tk.LEFT, padx=2)
        ttk.Button(up_btn, text=t("delete"), command=lambda: self._delete_selected(self.upcoming_listbox, self._upcoming_items)).pack(side=tk.LEFT, padx=2)

        # ── 下半区：过去的任务 ──
        past_frame = ttk.LabelFrame(self, text=f"📂 过去的任务", padding=5)
        past_frame.pack(fill="both", expand=True, padx=5, pady=(2, 5))

        self.past_listbox = tk.Listbox(past_frame, height=6, cursor="hand2")
        self.past_listbox.pack(fill="both", expand=True)
        self.past_listbox.bind("<Button-1>", self._on_past_click)
        self.past_listbox.bind("<Double-Button-1>", self._on_past_edit)

        past_btn = ttk.Frame(past_frame)
        past_btn.pack(pady=(3, 0))
        ttk.Button(past_btn, text=t("delete"), command=lambda: self._delete_selected(self.past_listbox, self._past_items)).pack(side=tk.LEFT, padx=2)

        self.refresh()

    # ── 公开方法 ──────────────────────────────

    def refresh(self):
        """刷新三个列表"""
        self._refresh_today()
        self._refresh_upcoming()
        self._refresh_past()

    def _refresh_today(self):
        self.today_listbox.delete(0, tk.END)
        date_str = str(self.today)
        self._today_items = []

        for i, task in enumerate(self.data_store.get_tasks(date_str)):
            status = "✓" if task.get("done") else "✗"
            deadline = task.get("deadline", date_str)
            ctd, is_overdue = _countdown_text(deadline, self.today)
            prefix = "⚠️ " if is_overdue else ""
            line = _pad_right(f"[{status}] {prefix}{task['task']}", ctd)
            self.today_listbox.insert(tk.END, line)
            if is_overdue:
                self.today_listbox.itemconfig(tk.END, fg="#999999")
            self._today_items.append(("task", date_str, i))

        for proj_name, step in self.data_store.get_steps_due_on(date_str):
            proj = self.data_store.get_project(proj_name)
            if not proj:
                continue
            real_idx = self._find_step_index(proj, step, date_str)
            if real_idx is None:
                continue
            status = "✓" if step.get("done") else "✗"
            dl = step.get("deadline", "")
            ctd, is_overdue = _countdown_text(dl, self.today)
            prefix = "⚠️ " if is_overdue else ""
            line = _pad_right(f"[{status}] {prefix}【{proj_name}】{step['step']}", ctd)
            self.today_listbox.insert(tk.END, line)
            if is_overdue:
                self.today_listbox.itemconfig(tk.END, fg="#999999")
            self._today_items.append(("step", proj_name, real_idx))

    def _refresh_upcoming(self):
        self.upcoming_listbox.delete(0, tk.END)
        today_str = str(self.today)
        self._upcoming_items = []

        for date_str, task in self.data_store.get_upcoming_tasks(today_str):
            status = "✓" if task.get("done") else "✗"
            dl = task.get("deadline", date_str)
            ctd, is_overdue = _countdown_text(dl, self.today)
            prefix = "⚠️ " if is_overdue else ""
            try:
                d = datetime.date.fromisoformat(date_str)
                date_prefix = f"{d.month}/{d.day} "
            except ValueError:
                date_prefix = ""
            line = _pad_right(f"{date_prefix}[{status}] {prefix}{task['task']}", ctd)
            self.upcoming_listbox.insert(tk.END, line)
            if is_overdue:
                self.upcoming_listbox.itemconfig(tk.END, fg="#999999")
            tlist = self.data_store.get_tasks(date_str)
            idx = next((i for i, t in enumerate(tlist) if t is task), 0)
            self._upcoming_items.append(("task", date_str, idx))

        for proj_name, step in self.data_store.get_upcoming_steps(today_str):
            proj = self.data_store.get_project(proj_name)
            if not proj:
                continue
            dl = step.get("deadline", "")
            real_idx = self._find_step_index(proj, step, dl)
            if real_idx is None:
                continue
            status = "✓" if step.get("done") else "✗"
            ctd, is_overdue = _countdown_text(dl, self.today)
            prefix = "⚠️ " if is_overdue else ""
            try:
                d = datetime.date.fromisoformat(dl)
                date_prefix = f"{d.month}/{d.day} "
            except ValueError:
                date_prefix = ""
            line = _pad_right(f"{date_prefix}[{status}] {prefix}【{proj_name}】{step['step']}", ctd)
            self.upcoming_listbox.insert(tk.END, line)
            if is_overdue:
                self.upcoming_listbox.itemconfig(tk.END, fg="#999999")
            self._upcoming_items.append(("step", proj_name, real_idx))

    def _refresh_past(self):
        self.past_listbox.delete(0, tk.END)
        today_str = str(self.today)
        self._past_items = []

        for date_str, task in self.data_store.get_past_tasks(today_str):
            status = "✓" if task.get("done") else "✗"
            dl = task.get("deadline", date_str)
            ctd, is_overdue = _countdown_text(dl, self.today)
            prefix = "⚠️ " if is_overdue else ""
            try:
                d = datetime.date.fromisoformat(date_str)
                date_prefix = f"{d.month}/{d.day} "
            except ValueError:
                date_prefix = ""
            line = _pad_right(f"{date_prefix}[{status}] {prefix}{task['task']}", ctd)
            self.past_listbox.insert(tk.END, line)
            if is_overdue:
                self.past_listbox.itemconfig(tk.END, fg="#999999")
            tlist = self.data_store.get_tasks(date_str)
            idx = next((i for i, t in enumerate(tlist) if t is task), 0)
            self._past_items.append(("task", date_str, idx))

    @staticmethod
    def _find_step_index(proj, step, fallback_date):
        """根据对象引用或 deadline 匹配找到步骤在项目中的真实索引"""
        step_list = proj["steps"]
        for i, s in enumerate(step_list):
            if s is step:
                return i
        # fallback
        for i, s in enumerate(step_list):
            if s.get("deadline") == fallback_date and s["step"] == step["step"]:
                return i
        return None

    # ── 添加任务 ──────────────────────────────

    def _add_today(self):
        dlg = TaskDialog(self, "添加今日任务", default_date=str(self.today),
                         show_deadline=False)
        if dlg.result == "save":
            self.data_store.add_task(str(self.today), dlg.text)
            self.refresh()
            self._notify()

    def _add_upcoming(self):
        dlg = TaskDialog(self, "添加任务", default_date="", show_date_picker=True)
        if dlg.result == "save" and dlg.task_date:
            self.data_store.add_task(dlg.task_date, dlg.text, dlg.deadline)
            self.refresh()
            self._notify()

    # ── 删除 ──────────────────────────────────

    def _delete_selected(self, listbox, items):
        sel = listbox.curselection()
        if not sel:
            messagebox.showwarning(t("please_select"), t("please_select"))
            return
        index = sel[0]
        if index >= len(items):
            return
        entry = items[index]
        item_type, key, data_idx = entry[0], entry[1], entry[2]

        if item_type == "task":
            name = self.data_store.get_tasks(key)[data_idx]["task"]
        else:
            name = self.data_store.get_project(key)["steps"][data_idx]["step"]

        if not messagebox.askyesno(t("confirm_delete"), t("confirm_delete_msg", name)):
            return

        if item_type == "task":
            self.data_store.delete_task(key, data_idx)
        else:
            self.data_store.delete_step(key, data_idx)
            self.data_store.auto_check_project(key)

        self.refresh()
        self._notify()

    # ── 点击交互 ──────────────────────────────

    def _on_today_click(self, event):
        self._on_list_click(event, self.today_listbox, self._today_items)

    def _on_upcoming_click(self, event):
        self._on_list_click(event, self.upcoming_listbox, self._upcoming_items)

    def _on_past_click(self, event):
        self._on_list_click(event, self.past_listbox, self._past_items)

    def _on_list_click(self, event, listbox, items):
        index = listbox.nearest(event.y)
        if index < 0 or index >= len(items):
            return
        if event.x < 35:
            self._toggle_at(items, index)
        else:
            listbox.selection_clear(0, tk.END)
            listbox.selection_set(index)

    def _toggle_at(self, items, index):
        entry = items[index]
        item_type, key, data_idx = entry[0], entry[1], entry[2]
        if item_type == "task":
            self.data_store.toggle_task(key, data_idx)
        else:
            self.data_store.toggle_step(key, data_idx)
            self.data_store.auto_check_project(key)
        self.refresh()
        self._notify()

    # ── 编辑 ──────────────────────────────────

    def _on_today_edit(self, event=None):
        self._do_edit(event, self.today_listbox, self._today_items)

    def _on_upcoming_edit(self, event=None):
        self._do_edit(event, self.upcoming_listbox, self._upcoming_items)

    def _on_past_edit(self, event=None):
        self._do_edit(event, self.past_listbox, self._past_items)

    def _do_edit(self, event, listbox, items):
        index = listbox.nearest(event.y) if event else None
        if index is None or index < 0 or index >= len(items):
            return

        entry = items[index]
        item_type, key, data_idx = entry[0], entry[1], entry[2]

        if item_type == "task":
            task = self.data_store.get_tasks(key)[data_idx]
            dlg = EditDialog(self, "编辑任务", text=task["task"],
                             deadline=task.get("deadline", ""), has_deadline=True,
                             show_delete=False)
            if dlg.result == "save":
                self.data_store.update_task(key, data_idx, dlg.text, dlg.deadline)
                self.refresh()
                self._notify()
        else:
            step = self.data_store.get_project(key)["steps"][data_idx]
            dlg = EditDialog(self, "编辑步骤", text=step["step"],
                             deadline=step.get("deadline", ""), has_deadline=True,
                             show_delete=False)
            if dlg.result == "save":
                self.data_store.update_step(key, data_idx, dlg.text, dlg.deadline)
                self.data_store.auto_check_project(key)
                self.refresh()
                self._notify()

    def _notify(self):
        if self.on_data_changed:
            self.on_data_changed()
