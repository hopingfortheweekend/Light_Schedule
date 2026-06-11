"""
轻简日程管理 — 入口文件
"""
import tkinter as tk
from tkinter import ttk

from data_store import DataStore
from ui.task_tab import TaskTab
from ui.project_tab import ProjectTab
from ui.calendar_tab import CalendarTab


class App:
    """主窗口：组装各页面"""
    def __init__(self, root):
        self.root = root
        self.root.title("轻简日程管理")

        # 数据层
        self.data_store = DataStore()

        # 标签页容器
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True)

        # —— 三个页面 ——
        # 日历页先创建，因为任务/项目变更时需要刷新它
        self.calendar_tab = CalendarTab(self.notebook, self.data_store)
        self.notebook.add(self.calendar_tab, text="日历视图")

        self.task_tab = TaskTab(self.notebook, self.data_store,
                                on_data_changed=self.calendar_tab.refresh)
        self.notebook.add(self.task_tab, text="每日任务")

        self.project_tab = ProjectTab(self.notebook, self.data_store,
                                      on_data_changed=self.calendar_tab.refresh)
        self.notebook.add(self.project_tab, text="长期项目")


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
