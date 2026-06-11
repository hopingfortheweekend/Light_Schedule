"""
通用弹窗：编辑/删除任务和步骤时使用。
替代 simpledialog.askstring，支持在编辑页直接删除。
"""
import tkinter as tk
from tkinter import ttk, messagebox


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

        # 截止日期（仅步骤需要）
        if has_deadline:
            ttk.Label(self.top, text="截止日期 (YYYY-MM-DD):").grid(row=2, column=0, sticky="w", padx=10)
            self.dl_var = tk.StringVar(value=deadline)
            self.dl_entry = ttk.Entry(self.top, textvariable=self.dl_var, width=20)
            self.dl_entry.grid(row=3, column=0, columnspan=2, padx=10, pady=(2, 5))

        # 按钮行
        btn_frame = ttk.Frame(self.top)
        btn_frame.grid(row=4 if has_deadline else 2, column=0, columnspan=2,
                       pady=(10, 10), padx=10)

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


class ConfirmDelete:
    """确认删除弹窗（用于删除项目等顶层操作）"""
    @staticmethod
    def ask(parent, title, message):
        return messagebox.askyesno(title, message, parent=parent)
