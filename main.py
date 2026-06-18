"""
轻简日程管理 — 入口文件
"""
import tkinter as tk
from tkinter import ttk

from data_store import DataStore
from ui.single_task_tab import SingleTaskTab
from ui.project_tab import ProjectTab
from ui.calendar_tab import CalendarTab
from ui.stats_tab import StatsTab
from utils.export import export_csv
from utils.i18n import t


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
        export_btn.lift()

        # —— 五个页面 ——
        self.single_task_tab = SingleTaskTab(self.notebook, self.data_store,
                                              on_data_changed=self._on_data_changed)
        self.notebook.add(self.single_task_tab, text=t("tab_single_task"))

        self.project_tab = ProjectTab(self.notebook, self.data_store,
                                       on_data_changed=self._on_data_changed)
        self.notebook.add(self.project_tab, text=t("tab_project"))

        # 固定任务页（延迟导入，避免循环依赖）
        from ui.routine_tab import RoutineTab
        self.routine_tab = RoutineTab(self.notebook, self.data_store,
                                       on_data_changed=self._on_data_changed)
        self.notebook.add(self.routine_tab, text=t("tab_routine"))

        self.calendar_tab = CalendarTab(self.notebook, self.data_store)
        self.notebook.add(self.calendar_tab, text=t("tab_calendar"))

        self.stats_tab = StatsTab(self.notebook, self.data_store)
        self.notebook.add(self.stats_tab, text=t("tab_stats"))

    def _on_data_changed(self):
        """数据变更时刷新日历和统计"""
        self.calendar_tab.refresh()
        self.stats_tab.refresh()


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("720x720")  # 稍大的默认窗口，方便看到三个任务区
    app = App(root)
    root.mainloop()
