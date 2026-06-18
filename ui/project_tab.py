"""
长期项目页面：项目列表 + 项目详情弹窗（步骤管理）。
含起止时间、倒计时和过期外观。
"""
import tkinter as tk
from tkinter import ttk, messagebox
import datetime

from ui.dialogs import EditDialog
from ui.single_task_tab import _countdown_text, _pad_right
from utils.i18n import t


class ProjectTab(ttk.Frame):
    def __init__(self, parent, data_store, on_data_changed=None):
        super().__init__(parent)
        self.data_store = data_store
        self.on_data_changed = on_data_changed
        self._proj_names = []
        self.today = datetime.date.today()

        self.listbox = tk.Listbox(self, height=10, cursor="hand2", font=("", 10))
        self.listbox.pack(fill="both", expand=True)
        self.listbox.bind("<Button-1>", self._on_click)
        self.listbox.bind("<Double-Button-1>", self._open_project)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text=t("add_project"), command=self._add).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text=t("delete_project"), command=self._delete).pack(side=tk.LEFT, padx=2)

        self.refresh()

    def refresh(self):
        self.listbox.delete(0, tk.END)
        self._proj_names = list(self.data_store.get_projects().keys())
        for name in self._proj_names:
            proj = self.data_store.get_project(name)
            done = self.data_store.get_project_done(name)
            status = "✓" if done else "✗"
            start = self.data_store.get_project_start_date(name)
            end = self.data_store.get_project_end_date(name)
            step_count = len(proj["steps"])

            # 起止时间信息 → 放在最右
            date_info = ""
            if start and end:
                date_info = f"{start} ~ {end}"
            elif start:
                date_info = f"{start} 起"
            elif end:
                date_info = f"截止 {end}"

            content = f"{name} — {step_count} {t('project_steps')}"
            is_overdue = self._is_project_overdue(proj)

            prefix = "⚠️ " if is_overdue else ""
            line = _pad_right(f"[{status}] {prefix}{content}", date_info, 55)
            self.listbox.insert(tk.END, line)
            if is_overdue:
                self.listbox.itemconfig(tk.END, fg="#999999")

    def _is_project_overdue(self, proj):
        if proj.get("done"):
            return False
        steps = proj.get("steps", [])
        if not steps:
            return False
        all_overdue = True
        has_deadline = False
        for s in steps:
            dl = s.get("deadline", "")
            if dl:
                has_deadline = True
                try:
                    d = datetime.date.fromisoformat(dl)
                    if d >= self.today or s.get("done"):
                        all_overdue = False
                        break
                except ValueError:
                    pass
            else:
                all_overdue = False
        return has_deadline and all_overdue

    def _notify(self):
        if self.on_data_changed:
            self.on_data_changed()

    def _add(self):
        dlg = ProjectAddDialog(self)
        if dlg.result == "save":
            self.data_store.add_project(dlg.name, dlg.start_date, dlg.end_date)
            self.refresh()

    def _delete(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning("提示", t("please_select"))
            return
        index = sel[0]
        if index >= len(self._proj_names):
            return
        proj_name = self._proj_names[index]
        if messagebox.askyesno(t("confirm_delete"),
                               f"确定要删除项目「{proj_name}」及其所有步骤吗？此操作不可恢复。"):
            self.data_store.delete_project(proj_name)
            self.refresh()
            self._notify()

    def _on_click(self, event):
        index = self.listbox.nearest(event.y)
        if index < 0 or index >= len(self._proj_names):
            return
        if event.x < 35:
            self._toggle_project(index)
        else:
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(index)

    def _toggle_project(self, index):
        proj_name = self._proj_names[index]
        currently_done = self.data_store.get_project_done(proj_name)
        if not currently_done:
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


class ProjectAddDialog:
    """添加项目弹窗：名称 + 可选起止日期"""
    def __init__(self, parent):
        self.result = None
        self.name = ""
        self.start_date = ""
        self.end_date = ""

        self.top = tk.Toplevel(parent)
        self.top.title("添加项目")
        self.top.resizable(False, False)
        self.top.transient(parent)
        self.top.grab_set()

        ttk.Label(self.top, text="项目名称:").grid(row=0, column=0, sticky="w", padx=10, pady=(10, 0))
        self.name_var = tk.StringVar()
        ttk.Entry(self.top, textvariable=self.name_var, width=35).grid(row=1, column=0, padx=10, pady=(2, 5))

        ttk.Label(self.top, text="起始日期 (YYYY-MM-DD，可留空):").grid(row=2, column=0, sticky="w", padx=10)
        self.start_var = tk.StringVar()
        ttk.Entry(self.top, textvariable=self.start_var, width=20).grid(row=3, column=0, padx=10, pady=(2, 2))

        ttk.Label(self.top, text="截止日期 (YYYY-MM-DD，可留空):").grid(row=4, column=0, sticky="w", padx=10)
        self.end_var = tk.StringVar()
        ttk.Entry(self.top, textvariable=self.end_var, width=20).grid(row=5, column=0, padx=10, pady=(2, 10))

        btn_frame = ttk.Frame(self.top)
        btn_frame.grid(row=6, column=0, pady=(0, 10))
        ttk.Button(btn_frame, text="✓ 保存", command=self._save).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="取消", command=self._cancel).pack(side=tk.LEFT, padx=3)

        self.top.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        x = parent.winfo_rootx() + (pw - self.top.winfo_width()) // 2
        y = parent.winfo_rooty() + (ph - self.top.winfo_height()) // 2
        self.top.geometry(f"+{x}+{y}")

        self.top.focus_set()
        self.top.wait_window()

    def _save(self):
        self.name = self.name_var.get().strip()
        self.start_date = self.start_var.get().strip()
        self.end_date = self.end_var.get().strip()
        if not self.name:
            messagebox.showwarning("提示", t("content_required"), parent=self.top)
            return
        self.result = "save"
        self.top.destroy()

    def _cancel(self):
        self.top.destroy()


class ProjectWindow:
    """项目详情弹窗：管理步骤，显示起止时间"""
    def __init__(self, parent, project_name, data_store, on_done=None):
        self.data_store = data_store
        self.project_name = project_name
        self.on_done = on_done
        self.today = datetime.date.today()

        self.top = tk.Toplevel(parent)
        self.top.title(f"项目: {project_name}")
        self.top.geometry("550x450")

        # 项目信息栏 — 起止时间
        info = ttk.Frame(self.top)
        info.pack(fill="x", padx=10, pady=(8, 2))

        self.info_label = ttk.Label(info, text="")
        self.info_label.pack(side=tk.LEFT)
        ttk.Button(info, text="编辑起止时间", command=self._edit_dates).pack(side=tk.RIGHT)
        self._update_info_label()

        self.listbox = tk.Listbox(self.top, height=10, cursor="hand2", font=("", 10))
        self.listbox.pack(fill="both", expand=True, padx=10)
        self.listbox.bind("<Button-1>", self._on_click)
        self.listbox.bind("<Double-Button-1>", self._on_edit)

        btn_frame = ttk.Frame(self.top)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text=t("add_step"), command=self._add).pack(side=tk.LEFT, padx=2)

        self.refresh()

    def _update_info_label(self):
        start = self.data_store.get_project_start_date(self.project_name)
        end = self.data_store.get_project_end_date(self.project_name)
        if start and end:
            self.info_label.config(text=f"⏱ {start} ~ {end}")
        elif start:
            self.info_label.config(text=f"⏱ {start} 起")
        elif end:
            self.info_label.config(text=f"⏱ 截止 {end}")
        else:
            self.info_label.config(text="未设置起止时间")

    def _edit_dates(self):
        start = self.data_store.get_project_start_date(self.project_name)
        end = self.data_store.get_project_end_date(self.project_name)

        dlg = tk.Toplevel(self.top)
        dlg.title("编辑起止时间")
        dlg.resizable(False, False)
        dlg.transient(self.top)
        dlg.grab_set()

        ttk.Label(dlg, text="起始日期 (YYYY-MM-DD):").grid(row=0, column=0, sticky="w", padx=10, pady=(10, 0))
        sv = tk.StringVar(value=start)
        ttk.Entry(dlg, textvariable=sv, width=20).grid(row=0, column=1, padx=10, pady=(10, 0))

        ttk.Label(dlg, text="截止日期 (YYYY-MM-DD):").grid(row=1, column=0, sticky="w", padx=10, pady=(5, 0))
        ev = tk.StringVar(value=end)
        ttk.Entry(dlg, textvariable=ev, width=20).grid(row=1, column=1, padx=10, pady=(5, 0))

        def save():
            self.data_store.update_project_dates(self.project_name,
                                                  sv.get().strip(), ev.get().strip())
            self._update_info_label()
            if self.on_done:
                self.on_done()
            dlg.destroy()

        btn = ttk.Frame(dlg)
        btn.grid(row=2, column=0, columnspan=2, pady=(10, 10))
        ttk.Button(btn, text="✓ 保存", command=save).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn, text="取消", command=dlg.destroy).pack(side=tk.LEFT, padx=3)

        dlg.update_idletasks()
        x = self.top.winfo_rootx() + (self.top.winfo_width() - dlg.winfo_width()) // 2
        y = self.top.winfo_rooty() + (self.top.winfo_height() - dlg.winfo_height()) // 2
        dlg.geometry(f"+{x}+{y}")

    def refresh(self):
        self.listbox.delete(0, tk.END)
        proj = self.data_store.get_project(self.project_name)
        if not proj:
            return

        def sort_key(item):
            _, step = item
            dl = step.get("deadline", "")
            if dl:
                try:
                    return (0, datetime.date.fromisoformat(dl))
                except ValueError:
                    return (1, datetime.date.max)
            return (1, datetime.date.max)

        indexed = list(enumerate(proj["steps"]))
        indexed.sort(key=sort_key)
        self._display_to_data = [data_idx for data_idx, _ in indexed]

        for _, step in indexed:
            status = "✓" if step["done"] else "✗"
            dl = step.get("deadline", "")
            ctd, is_overdue = _countdown_text(dl, self.today) if dl else ("", False)
            prefix = "⚠️ " if is_overdue else ""
            content = f"{prefix}{step['step']}"
            deadline_display = dl if dl else ""

            line = _pad_right(f"[{status}] {content}", f"{deadline_display}{ctd}", 50)
            self.listbox.insert(tk.END, line)
            if is_overdue:
                self.listbox.itemconfig(tk.END, fg="#999999")

        self._update_info_label()

    def _real_index(self, display_index):
        if hasattr(self, "_display_to_data") and 0 <= display_index < len(self._display_to_data):
            return self._display_to_data[display_index]
        return display_index

    def _notify(self):
        self.data_store.auto_check_project(self.project_name)
        if self.on_done:
            self.on_done()

    def _add(self):
        dlg = EditDialog(self.top, "添加步骤", has_deadline=True, show_delete=False)
        if dlg.result == "save" and dlg.text:
            self.data_store.add_step(self.project_name, dlg.text, dlg.deadline)
            self.refresh()
            self._notify()

    def _on_click(self, event):
        index = self.listbox.nearest(event.y)
        if index < 0:
            return
        if event.x < 35:
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
                         deadline=step.get("deadline", ""), has_deadline=True,
                         show_delete=True)
        if dlg.result == "save":
            self.data_store.update_step(self.project_name, real, dlg.text, dlg.deadline)
        elif dlg.result == "delete":
            self.data_store.delete_step(self.project_name, real)
        else:
            return
        self.refresh()
        self._notify()
