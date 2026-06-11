"""
每日任务页面：添加、切换状态、编辑、删除今日任务
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import datetime


class TaskTab(ttk.Frame):
    def __init__(self, parent, data_store, on_data_changed=None):
        super().__init__(parent)
        self.data_store = data_store
        self.on_data_changed = on_data_changed  # 数据变更时回调（通知日历刷新）
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
        ttk.Button(btn_frame, text="切换完成状态", command=self._toggle_selected).pack(side=tk.LEFT, padx=2)

        self.refresh()

    # ── 公开方法 ──────────────────────────────

    def refresh(self):
        """刷新列表，并从 data_store 拉当日截止步骤一并显示"""
        self.listbox.delete(0, tk.END)
        date_str = str(self.task_date)

        # 每日任务
        for task in self.data_store.get_tasks(date_str):
            status = "✓" if task["done"] else "✗"
            self.listbox.insert(tk.END, f"[{status}] {task['task']}")

        # 长期项目中当日截止的步骤（加粗标记来源项目）
        for proj_name, step in self.data_store.get_steps_due_on(date_str):
            status = "✓" if step.get("done") else "✗"
            self.listbox.insert(tk.END, f"[{status}] 【{proj_name}】{step['step']}")

    # ── 内部交互 ──────────────────────────────

    def _notify(self):
        """通知外部数据已变更"""
        if self.on_data_changed:
            self.on_data_changed()

    def _add(self):
        text = simpledialog.askstring("新任务", "请输入任务内容:")
        if text:
            self.data_store.add_task(str(self.task_date), text)
            self.refresh()
            self._notify()

    def _on_click(self, event):
        index = self.listbox.nearest(event.y)
        if index < 0:
            return
        if event.x < 35:  # 状态标记区域
            self._toggle_at(index)
        else:
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(index)

    def _toggle_at(self, index):
        """切换指定行的完成状态（需要考虑是任务还是步骤）"""
        date_str = str(self.task_date)
        tasks = self.data_store.get_tasks(date_str)
        due_steps = self.data_store.get_steps_due_on(date_str)

        if index < len(tasks):
            # 是每日任务
            self.data_store.toggle_task(date_str, index)
        else:
            # 是长期项目步骤
            step_index = index - len(tasks)
            proj_name, _ = due_steps[step_index]
            # 找到该步骤在项目中的实际索引
            proj = self.data_store.get_project(proj_name)
            if proj:
                for i, s in enumerate(proj["steps"]):
                    if s.get("deadline") == date_str:
                        # 找到了——但可能有多个同日期步骤，需要计数
                        matching = [j for j, st in enumerate(proj["steps"])
                                   if st.get("deadline") == date_str]
                        if step_index < len(matching):
                            self.data_store.toggle_step(proj_name, matching[step_index])
                        break
        self.refresh()
        self._notify()

    def _toggle_selected(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning("提示", "请先点击选中一个条目")
            return
        self._toggle_at(sel[0])

    def _on_edit(self, event=None):
        """双击编辑：任务内容 或 步骤内容+截止日期"""
        index = self.listbox.nearest(event.y) if event else None
        if index is None or index < 0:
            return

        date_str = str(self.task_date)
        tasks = self.data_store.get_tasks(date_str)
        due_steps = self.data_store.get_steps_due_on(date_str)

        if index < len(tasks):
            # 编辑每日任务
            task = tasks[index]
            new_text = simpledialog.askstring("编辑任务", "修改任务内容:", initialvalue=task["task"])
            if new_text and new_text != task["task"]:
                self.data_store.update_task(date_str, index, new_text)
                self.refresh()
                self._notify()
        else:
            # 编辑项目步骤
            step_index = index - len(tasks)
            if step_index < len(due_steps):
                proj_name, step = due_steps[step_index]
                proj = self.data_store.get_project(proj_name)
                if proj:
                    # 找到该步骤在项目中的实际索引
                    matching_indices = [j for j, st in enumerate(proj["steps"])
                                       if st.get("deadline") == date_str]
                    if step_index < len(matching_indices):
                        real_index = matching_indices[step_index]
                        s = proj["steps"][real_index]
                        new_text = simpledialog.askstring("编辑步骤", "修改步骤内容:", initialvalue=s["step"])
                        if new_text is not None and new_text != s["step"]:
                            s["step"] = new_text
                        new_dl = simpledialog.askstring("编辑截止时间", "修改截止日期 (YYYY-MM-DD):",
                                                        initialvalue=s.get("deadline", ""))
                        if new_dl is not None and new_dl != s.get("deadline", ""):
                            s["deadline"] = new_dl
                        if new_text is not None or new_dl is not None:
                            self.data_store.save()
                            self.refresh()
                            self._notify()
