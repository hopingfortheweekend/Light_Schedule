"""
长期项目页面：项目列表 + 项目详情弹窗（步骤管理）
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import datetime

from ui.dialogs import EditDialog


class ProjectTab(ttk.Frame):
    def __init__(self, parent, data_store, on_data_changed=None):
        super().__init__(parent)
        self.data_store = data_store
        self.on_data_changed = on_data_changed
        self._proj_names = []  # 与列表显示顺序一致的项目名

        # 项目列表
        self.listbox = tk.Listbox(self, height=10, cursor="hand2")
        self.listbox.pack(fill="both", expand=True)
        self.listbox.bind("<Button-1>", self._on_click)
        self.listbox.bind("<Double-Button-1>", self._open_project)

        # 按钮
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="添加项目", command=self._add).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="删除项目", command=self._delete).pack(side=tk.LEFT, padx=2)

        self.refresh()

    # ── 公开方法 ──────────────────────────────

    def refresh(self):
        self.listbox.delete(0, tk.END)
        self._proj_names = list(self.data_store.get_projects().keys())
        for name in self._proj_names:
            proj = self.data_store.get_project(name)
            done = self.data_store.get_project_done(name)
            status = "✓" if done else "✗"
            self.listbox.insert(tk.END, f"[{status}] {name} - {len(proj['steps'])} 步骤")

    # ── 内部交互 ──────────────────────────────

    def _notify(self):
        if self.on_data_changed:
            self.on_data_changed()

    def _add(self):
        name = simpledialog.askstring("新项目", "请输入项目名称:")
        if name:
            self.data_store.add_project(name)
            self.refresh()

    def _delete(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning("提示", "请先选中一个项目")
            return
        index = sel[0]
        if index >= len(self._proj_names):
            return
        proj_name = self._proj_names[index]
        if messagebox.askyesno("确认删除", f"确定要删除项目「{proj_name}」及其所有步骤吗？此操作不可恢复。"):
            self.data_store.delete_project(proj_name)
            self.refresh()
            self._notify()

    def _on_click(self, event):
        index = self.listbox.nearest(event.y)
        if index < 0 or index >= len(self._proj_names):
            return
        if event.x < 35:  # 状态标记区域
            self._toggle_project(index)
        else:
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(index)

    def _toggle_project(self, index):
        proj_name = self._proj_names[index]
        currently_done = self.data_store.get_project_done(proj_name)

        if not currently_done:
            # 要标记为完成 → 检查是否所有步骤都完成了
            proj = self.data_store.get_project(proj_name)
            steps = proj.get("steps", [])
            incomplete = [s["step"] for s in steps if not s.get("done")]
            if incomplete:
                msg = f"以下 {len(incomplete)} 个步骤尚未完成:\n\n"
                msg += "\n".join(f"  · {s}" for s in incomplete[:5])
                if len(incomplete) > 5:
                    msg += f"\n  ... 还有 {len(incomplete) - 5} 个"
                msg += "\n\n是否仍要标记项目为已完成？"
                if not messagebox.askyesno("确认操作", msg):
                    return

        self.data_store.toggle_project(proj_name)
        self.refresh()
        self._notify()

    def _open_project(self, event=None):
        if event:
            index = self.listbox.nearest(event.y)
            if index < 0 or index >= len(self._proj_names):
                return
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(index)
        else:
            sel = self.listbox.curselection()
            if not sel:
                return
            index = sel[0]

        proj_name = self._proj_names[index]
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
        self.top.geometry("480x380")

        self.listbox = tk.Listbox(self.top, height=10, cursor="hand2")
        self.listbox.pack(fill="both", expand=True)
        self.listbox.bind("<Button-1>", self._on_click)
        self.listbox.bind("<Double-Button-1>", self._on_edit)

        btn_frame = ttk.Frame(self.top)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="添加步骤", command=self._add).pack(side=tk.LEFT, padx=2)

        self.refresh()

    def refresh(self):
        self.listbox.delete(0, tk.END)
        proj = self.data_store.get_project(self.project_name)
        if not proj:
            return

        # 排序：有截止日期的在前（早→晚），无日期的在后
        def sort_key(item):
            _, step = item
            dl = step.get("deadline", "")
            if dl:
                try:
                    return (0, datetime.date.fromisoformat(dl))
                except ValueError:
                    return (1, datetime.date.max)
            return (1, datetime.date.max)

        # (数据索引, 步骤) → 排序 → 建立显示位置 → 数据位置映射
        indexed = list(enumerate(proj["steps"]))
        indexed.sort(key=sort_key)
        self._display_to_data = [data_idx for data_idx, _ in indexed]

        for _, step in indexed:
            status = "✓" if step["done"] else "✗"
            deadline = step["deadline"] if step["deadline"] else "无截止时间"
            self.listbox.insert(tk.END, f"[{status}] {step['step']} - 截止: {deadline}")

    def _real_index(self, display_index):
        """将显示索引转为数据中的真实索引"""
        if hasattr(self, "_display_to_data") and 0 <= display_index < len(self._display_to_data):
            return self._display_to_data[display_index]
        return display_index  # fallback

    def _notify(self):
        # 步骤变更后自动检查项目是否全部完成
        self.data_store.auto_check_project(self.project_name)
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

    def _toggle_at(self, display_index):
        real = self._real_index(display_index)
        self.data_store.toggle_step(self.project_name, real)
        self.refresh()
        self._notify()

    def _on_edit(self, event=None):
        display_index = self.listbox.nearest(event.y) if event else None
        if display_index is None or display_index < 0:
            return
        real = self._real_index(display_index)
        proj = self.data_store.get_project(self.project_name)
        if not proj or real >= len(proj["steps"]):
            return
        step = proj["steps"][real]
        dlg = EditDialog(self.top, "编辑/删除步骤", text=step["step"],
                         deadline=step.get("deadline", ""), has_deadline=True)
        if dlg.result == "save":
            self.data_store.update_step(self.project_name, real, dlg.text, dlg.deadline)
        elif dlg.result == "delete":
            self.data_store.delete_step(self.project_name, real)
        else:
            return
        self.refresh()
        self._notify()
