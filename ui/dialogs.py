"""
通用弹窗：编辑/删除任务和步骤时使用。
替代 simpledialog.askstring，支持在编辑页直接删除。
"""
import tkinter as tk
from tkinter import ttk, messagebox
import datetime
from utils.i18n import t


class EditDialog:
    """编辑弹窗：编辑文本 + 可选截止日期 + 删除按钮"""

    def __init__(self, parent, title, text="", deadline="", has_deadline=False, show_delete=True):
        self.result = None  # "save", "delete", None(取消)
        self.text = text
        self.deadline = deadline

        self.top = tk.Toplevel(parent)
        self.top.title(title)
        self.top.resizable(False, False)
        self.top.transient(parent)
        self.top.grab_set()

        # 内容输入
        ttk.Label(self.top, text="内容:").grid(row=0, column=0, sticky="w", padx=10, pady=(10, 0))
        self.text_var = tk.StringVar(value=text)
        self.text_entry = ttk.Entry(self.top, textvariable=self.text_var, width=40)
        self.text_entry.grid(row=1, column=0, columnspan=2, padx=10, pady=(2, 5))
        self.text_entry.focus_set()

        # 任务/截止日期（合二为一，日历选择）
        if has_deadline:
            ttk.Label(self.top, text="任务/截止日期:").grid(row=2, column=0, sticky="w", padx=10)
            date_frame = ttk.Frame(self.top)
            date_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=(2, 5), sticky="w")
            self.dl_var = tk.StringVar(value=deadline)
            ttk.Entry(date_frame, textvariable=self.dl_var, width=15).pack(side=tk.LEFT, padx=(0, 5))
            ttk.Button(date_frame, text="📅", width=3,
                       command=self._pick_date).pack(side=tk.LEFT)

        # 按钮行
        btn_row = 4 if has_deadline else 2
        btn_frame = ttk.Frame(self.top)
        btn_frame.grid(row=btn_row, column=0, columnspan=2, pady=(10, 10), padx=10)

        ttk.Button(btn_frame, text="保存修改", command=self._save).pack(side=tk.LEFT, padx=3)
        if show_delete:
            ttk.Button(btn_frame, text="删除", command=self._delete).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="取消", command=self._cancel).pack(side=tk.LEFT, padx=3)

        # 居中
        self.top.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        x = parent.winfo_rootx() + (pw - self.top.winfo_width()) // 2
        y = parent.winfo_rooty() + (ph - self.top.winfo_height()) // 2
        self.top.geometry(f"+{x}+{y}")

        self.top.wait_window()

    def _save(self):
        self.text = self.text_var.get().strip()
        if hasattr(self, "dl_var"):
            self.deadline = self.dl_var.get().strip()
        if not self.text:
            messagebox.showwarning("提示", "内容不能为空", parent=self.top)
            return
        self.result = "save"
        self.top.destroy()

    def _delete(self):
        if messagebox.askyesno("确认删除", "确定要删除吗？此操作不可恢复。", parent=self.top):
            self.result = "delete"
            self.top.destroy()

    def _cancel(self):
        self.top.destroy()

    def _pick_date(self):
        """弹出日历日期选择器"""
        try:
            from tkcalendar import Calendar

            cal_win = tk.Toplevel(self.top)
            cal_win.title("选择日期")
            cal_win.resizable(False, False)
            cal_win.transient(self.top)
            cal_win.grab_set()

            cal = Calendar(cal_win, selectmode="day", date_pattern="yyyy-mm-dd")
            cal.pack(padx=10, pady=10)

            def set_date():
                self.dl_var.set(str(cal.selection_get()))
                cal_win.destroy()

            ttk.Button(cal_win, text="确定", command=set_date).pack(pady=(0, 10))

            cal_win.update_idletasks()
            x = self.top.winfo_rootx() + (self.top.winfo_width() - cal_win.winfo_width()) // 2
            y = self.top.winfo_rooty() + (self.top.winfo_height() - cal_win.winfo_height()) // 2
            cal_win.geometry(f"+{x}+{y}")
        except ImportError:
            messagebox.showinfo("提示", "请输入日期 YYYY-MM-DD 格式", parent=self.top)


class TaskDialog:
    """添加单次任务弹窗：任务内容 + 可选日期选择器（任务/截止日期合一）"""

    def __init__(self, parent, title, default_date="", show_date_picker=False,
                 show_deadline=True):
        self.result = None
        self.text = ""
        self.deadline = ""
        self.task_date = default_date

        self.top = tk.Toplevel(parent)
        self.top.title(title)
        self.top.resizable(False, False)
        self.top.transient(parent)
        self.top.grab_set()

        row = 0

        # 任务内容
        ttk.Label(self.top, text="任务内容:").grid(row=row, column=0, sticky="w", padx=10, pady=(10, 0))
        row += 1
        self.text_var = tk.StringVar()
        self.text_entry = ttk.Entry(self.top, textvariable=self.text_var, width=40)
        self.text_entry.grid(row=row, column=0, columnspan=2, padx=10, pady=(2, 5))
        self.text_entry.focus_set()
        row += 1

        # 日期选择器（给"之后的任务"用）：任务日期即截止日期，合二为一
        if show_date_picker:
            ttk.Label(self.top, text="任务/截止日期:").grid(row=row, column=0, sticky="w", padx=10)
            row += 1
            date_frame = ttk.Frame(self.top)
            date_frame.grid(row=row, column=0, columnspan=2, padx=10, pady=(2, 5))

            self.date_var = tk.StringVar(value=default_date or str(datetime.date.today()))
            ttk.Entry(date_frame, textvariable=self.date_var, width=15).pack(side=tk.LEFT, padx=(0, 5))

            ttk.Button(date_frame, text="📅", width=3,
                       command=self._pick_date).pack(side=tk.LEFT)
            row += 1

        # 按钮
        btn_frame = ttk.Frame(self.top)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=(10, 10), padx=10)
        ttk.Button(btn_frame, text="保存", command=self._save).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="取消", command=self._cancel).pack(side=tk.LEFT, padx=3)

        self.top.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        x = parent.winfo_rootx() + (pw - self.top.winfo_width()) // 2
        y = parent.winfo_rooty() + (ph - self.top.winfo_height()) // 2
        self.top.geometry(f"+{x}+{y}")

        self.top.wait_window()

    def _pick_date(self):
        """弹出日历日期选择器"""
        try:
            from tkcalendar import Calendar

            cal_win = tk.Toplevel(self.top)
            cal_win.title("选择日期")
            cal_win.resizable(False, False)
            cal_win.transient(self.top)
            cal_win.grab_set()

            cal = Calendar(cal_win, selectmode="day", date_pattern="yyyy-mm-dd")
            cal.pack(padx=10, pady=10)

            def set_date():
                self.date_var.set(str(cal.selection_get()))
                cal_win.destroy()

            ttk.Button(cal_win, text="确定", command=set_date).pack(pady=(0, 10))

            cal_win.update_idletasks()
            x = self.top.winfo_rootx() + (self.top.winfo_width() - cal_win.winfo_width()) // 2
            y = self.top.winfo_rooty() + (self.top.winfo_height() - cal_win.winfo_height()) // 2
            cal_win.geometry(f"+{x}+{y}")
        except ImportError:
            messagebox.showinfo("提示", "请输入日期 YYYY-MM-DD 格式", parent=self.top)

    def _save(self):
        self.text = self.text_var.get().strip()
        if not self.text:
            messagebox.showwarning("提示", "内容不能为空", parent=self.top)
            return
        if hasattr(self, "date_var"):
            self.task_date = self.date_var.get().strip()
            # 验证日期格式
            if self.task_date:
                try:
                    datetime.date.fromisoformat(self.task_date)
                except ValueError:
                    messagebox.showwarning("格式错误", "日期格式应为 YYYY-MM-DD", parent=self.top)
                    return
            # 任务日期即为截止日期，合二为一
            self.deadline = self.task_date
        self.result = "save"
        self.top.destroy()

    def _cancel(self):
        self.top.destroy()


class ConfirmDelete:
    """确认删除弹窗（用于删除项目等顶层操作）"""
    @staticmethod
    def ask(parent, title, message):
        return messagebox.askyesno(title, message, parent=parent)
