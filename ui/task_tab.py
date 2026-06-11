"""
每日任务页面：添加、切换状态、编辑、删除任务和当日截止步骤
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import datetime

from ui.dialogs import EditDialog


class TaskTab(ttk.Frame):
    def __init__(self, parent, data_store, on_data_changed=None):
        super().__init__(parent)
        self.data_store = data_store
        self.on_data_changed = on_data_changed
        self.task_date = datetime.date.today()

        # 日期标签
        self.date_label = ttk.Label(self, text=f"日期: {self.task_date}")
        self.date_label.pack()

        # 任务列表
        self.listbox = tk.Listbox(self, height=10, cursor="hand2")
        self.listbox.pack(fill="both", expand=True)
        self.listbox.bind("<Button-1>", self._on_click)
        self.listbox.bind("<Double-Button-1>", self._on_edit)

        # 按钮
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="添加任务", command=self._add).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="删除任务", command=self._delete_selected).pack(side=tk.LEFT, padx=2)

        self.refresh()

    # ── 公开方法 ──────────────────────────────

    def refresh(self):
        """刷新列表，同时记录每行的来源信息以避免索引错位"""
        self.listbox.delete(0, tk.END)
        date_str = str(self.task_date)

        # _display_items: 每行一个元组，记录该行对应的真实数据位置
        #   ("task", date_str, task_index)
        #   ("step", project_name, real_step_index)
        self._display_items = []

        # 每日任务
        for i, task in enumerate(self.data_store.get_tasks(date_str)):
            status = "✓" if task["done"] else "✗"
            self.listbox.insert(tk.END, f"[{status}] {task['task']}")
            self._display_items.append(("task", date_str, i))

        # 长期项目中当日截止的步骤
        for proj_name, step in self.data_store.get_steps_due_on(date_str):
            proj = self.data_store.get_project(proj_name)
            if not proj:
                continue
            # 找到该 step 在项目中的真实索引
            step_list = proj["steps"]
            real_idx = None
            for si, s in enumerate(step_list):
                if s is step:  # 同一个字典对象
                    real_idx = si
                    break
            if real_idx is None:
                # fallback: 按 deadline 匹配
                for si, s in enumerate(step_list):
                    if s.get("deadline") == date_str and s["step"] == step["step"]:
                        real_idx = si
                        break
            if real_idx is None:
                continue

            status = "✓" if step.get("done") else "✗"
            self.listbox.insert(tk.END, f"[{status}] 【{proj_name}】{step['step']}")
            self._display_items.append(("step", proj_name, real_idx))

    # ── 内部交互 ──────────────────────────────

    def _notify(self):
        if self.on_data_changed:
            self.on_data_changed()

    def _add(self):
        text = simpledialog.askstring("新任务", "请输入任务内容:")
        if text:
            self.data_store.add_task(str(self.task_date), text)
            self.refresh()
            self._notify()

    def _delete_selected(self):
        """删除选中的任务或步骤"""
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning("提示", "请先点击选中一个条目")
            return
        index = sel[0]
        if index >= len(self._display_items):
            return
        item_type, key, data_idx = self._display_items[index]

        if item_type == "task":
            name = self.data_store.get_tasks(key)[data_idx]["task"]
        else:
            name = self.data_store.get_project(key)["steps"][data_idx]["step"]

        if not messagebox.askyesno("确认删除", f"确定要删除「{name}」吗？此操作不可恢复。"):
            return

        if item_type == "task":
            self.data_store.delete_task(key, data_idx)
        else:
            self.data_store.delete_step(key, data_idx)

        self.refresh()
        self._notify()

    def _on_click(self, event):
        index = self.listbox.nearest(event.y)
        if index < 0 or index >= len(self._display_items):
            return
        if event.x < 35:
            self._toggle_at(index)
        else:
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(index)

    def _toggle_at(self, index):
        item_type, key, data_idx = self._display_items[index]
        if item_type == "task":
            self.data_store.toggle_task(key, data_idx)
        else:
            self.data_store.toggle_step(key, data_idx)
            # 步骤状态变更后同步项目状态
            self.data_store.auto_check_project(key)
        self.refresh()
        self._notify()

    def _on_edit(self, event=None):
        index = self.listbox.nearest(event.y) if event else None
        if index is None or index < 0 or index >= len(self._display_items):
            return

        item_type, key, data_idx = self._display_items[index]

        if item_type == "task":
            task = self.data_store.get_tasks(key)[data_idx]
            dlg = EditDialog(self, "编辑任务", text=task["task"], show_delete=False)
            if dlg.result == "save":
                self.data_store.update_task(key, data_idx, dlg.text)
                self.refresh()
                self._notify()
        else:
            step = self.data_store.get_project(key)["steps"][data_idx]
            dlg = EditDialog(self, "编辑步骤", text=step["step"],
                             deadline=step.get("deadline", ""), has_deadline=True,
                             show_delete=False)
            if dlg.result == "save":
                self.data_store.update_step(key, data_idx, dlg.text, dlg.deadline)
                self.refresh()
                self._notify()
