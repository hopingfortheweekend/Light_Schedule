"""
长期项目页面：项目列表 + 项目详情弹窗（步骤管理）
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import datetime


class ProjectTab(ttk.Frame):
    def __init__(self, parent, data_store, on_data_changed=None):
        super().__init__(parent)
        self.data_store = data_store
        self.on_data_changed = on_data_changed

        # 项目列表
        self.listbox = tk.Listbox(self, height=10, cursor="hand2")
        self.listbox.pack(fill="both", expand=True)
        self.listbox.bind("<Double-Button-1>", self._open_project)

        # 按钮
        ttk.Button(self, text="添加项目", command=self._add).pack(pady=5)

        self.refresh()

    # ── 公开方法 ──────────────────────────────

    def refresh(self):
        self.listbox.delete(0, tk.END)
        for name, detail in self.data_store.get_projects().items():
            self.listbox.insert(tk.END, f"{name} - {len(detail['steps'])} 步骤")

    # ── 内部交互 ──────────────────────────────

    def _notify(self):
        if self.on_data_changed:
            self.on_data_changed()

    def _add(self):
        name = simpledialog.askstring("新项目", "请输入项目名称:")
        if name:
            self.data_store.add_project(name)
            self.refresh()

    def _open_project(self, event=None):
        if event:
            index = self.listbox.nearest(event.y)
            if index < 0:
                return
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(index)
        else:
            sel = self.listbox.curselection()
            if not sel:
                return
            index = sel[0]

        proj_name = list(self.data_store.get_projects().keys())[index]
        ProjectWindow(self, proj_name, self.data_store,
                      on_done=lambda: (self.refresh(), self._notify()))


class ProjectWindow:
    """项目详情弹窗：管理步骤"""
    def __init__(self, parent, project_name, data_store, on_done=None):
        self.data_store = data_store
        self.project_name = project_name
        self.on_done = on_done

        self.top = tk.Toplevel(parent)
        self.top.title(f"项目: {project_name}")

        self.listbox = tk.Listbox(self.top, height=10, cursor="hand2")
        self.listbox.pack(fill="both", expand=True)
        self.listbox.bind("<Button-1>", self._on_click)
        self.listbox.bind("<Double-Button-1>", self._on_edit)

        btn_frame = ttk.Frame(self.top)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="添加步骤", command=self._add).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="切换完成状态", command=self._toggle_selected).pack(side=tk.LEFT, padx=2)

        self.refresh()

    def refresh(self):
        self.listbox.delete(0, tk.END)
        proj = self.data_store.get_project(self.project_name)
        if not proj:
            return

        # 按截止时间排序
        def sort_key(step):
            dl = step.get("deadline", "")
            if dl:
                try:
                    return (0, datetime.date.fromisoformat(dl))
                except ValueError:
                    return (1, datetime.date.max)
            return (1, datetime.date.max)

        for step in sorted(proj["steps"], key=sort_key):
            status = "✓" if step["done"] else "✗"
            deadline = step["deadline"] if step["deadline"] else "无截止时间"
            self.listbox.insert(tk.END, f"[{status}] {step['step']} - 截止: {deadline}")

    def _notify(self):
        if self.on_done:
            self.on_done()

    def _add(self):
        text = simpledialog.askstring("新步骤", "请输入步骤内容:")
        if not text:
            return
        deadline = simpledialog.askstring("截止时间", "请输入截止日期 (YYYY-MM-DD)，可留空:")
        self.data_store.add_step(self.project_name, text, deadline)
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
        self.data_store.toggle_step(self.project_name, index)
        self.refresh()
        self._notify()

    def _toggle_selected(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning("提示", "请先点击选中一个步骤")
            return
        self._toggle_at(sel[0])

    def _on_edit(self, event=None):
        index = self.listbox.nearest(event.y) if event else None
        if index is None or index < 0:
            return
        proj = self.data_store.get_project(self.project_name)
        if not proj or index >= len(proj["steps"]):
            return
        step = proj["steps"][index]
        new_text = simpledialog.askstring("编辑步骤", "修改步骤内容:", initialvalue=step["step"])
        if new_text is not None and new_text != step["step"]:
            step["step"] = new_text
        new_dl = simpledialog.askstring("编辑截止时间", "修改截止日期 (YYYY-MM-DD)，可留空:",
                                        initialvalue=step.get("deadline", ""))
        if new_dl is not None and new_dl != step.get("deadline", ""):
            step["deadline"] = new_dl
        if new_text is not None or new_dl is not None:
            self.data_store.save()
            self.refresh()
            self._notify()
