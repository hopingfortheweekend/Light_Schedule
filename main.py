"""
轻简日程管理 — 入口文件
"""
import tkinter as tk
from tkinter import ttk

from data_store import DataStore
from ui.task_tab import TaskTab
from ui.project_tab import ProjectTab
from ui.calendar_tab import CalendarTab
from ui.stats_tab import StatsTab
from utils.export import export_csv


class App:
    """主窗口：组装各页面"""
    def __init__(self, root):
        self.root = root
        self.root.title("轻简日程管理")

        # 数据层
        self.data_store = DataStore()

        # 标签页容器 + 导出按钮（叠在标签栏右侧）
        tab_row = ttk.Frame(root)
        tab_row.pack(fill="both", expand=True, padx=5, pady=(5, 0))

        self.notebook = ttk.Notebook(tab_row)
        self.notebook.pack(fill="both", expand=True)

        export_btn = ttk.Button(tab_row, text="📤 导出数据",
                                command=lambda: export_csv(self.data_store, root))
        export_btn.place(relx=1.0, x=-5, y=2, anchor="ne")
        export_btn.lift()  # 确保在 Notebook 上方可见

        # —— 四个页面 ——
        self.task_tab = TaskTab(self.notebook, self.data_store,
                                on_data_changed=self._on_data_changed)
        self.notebook.add(self.task_tab, text="每日任务")

        self.project_tab = ProjectTab(self.notebook, self.data_store,
                                      on_data_changed=self._on_data_changed)
        self.notebook.add(self.project_tab, text="长期项目")

        self.calendar_tab = CalendarTab(self.notebook, self.data_store)
        self.notebook.add(self.calendar_tab, text="日历视图")

        self.stats_tab = StatsTab(self.notebook, self.data_store)
        self.notebook.add(self.stats_tab, text="数据统计")

    def _on_data_changed(self):
        """数据变更时刷新日历和统计"""
        self.calendar_tab.refresh()
        self.stats_tab.refresh()


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
