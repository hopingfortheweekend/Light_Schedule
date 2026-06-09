import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from tkcalendar import Calendar
import datetime
import json
import os

DATA_FILE = "schedule_data.json"

class ScheduleApp:
    def __init__(self, root):
        self.root = root
        self.root.title("轻简日程管理")
        self.data = {"tasks": {}, "projects": {}}
        self.load_data()

        # Notebook (tab 控件)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True)

        # 每日任务页
        self.task_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.task_frame, text="每日任务")

        self.task_date = datetime.date.today()
        self.task_label = ttk.Label(self.task_frame, text=f"日期: {self.task_date}")
        self.task_label.pack()

        self.task_listbox = tk.Listbox(self.task_frame, height=10, cursor="hand2")
        self.task_listbox.pack(fill="both", expand=True)
        self.task_listbox.bind("<Button-1>", self.on_task_click)
        self.task_listbox.bind("<Double-Button-1>", self.edit_task)

        btn_frame = ttk.Frame(self.task_frame)
        btn_frame.pack(pady=5)
        self.add_task_button = ttk.Button(btn_frame, text="添加任务", command=self.add_task)
        self.add_task_button.pack(side=tk.LEFT, padx=2)
        self.mark_done_button = ttk.Button(btn_frame, text="切换完成状态", command=self.toggle_task_done)
        self.mark_done_button.pack(side=tk.LEFT, padx=2)

        self.load_tasks()

        # 项目页
        self.project_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.project_frame, text="长期项目")

        self.project_listbox = tk.Listbox(self.project_frame, height=10)
        self.project_listbox.pack(fill="both", expand=True)

        self.add_project_button = ttk.Button(self.project_frame, text="添加项目", command=self.add_project)
        self.add_project_button.pack(pady=5)

        self.view_project_button = ttk.Button(self.project_frame, text="查看项目详情", command=self.view_project)
        self.view_project_button.pack(pady=5)

        self.load_projects()

        # 日历页
        self.calendar_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.calendar_frame, text="日历视图")

        # 日历组件
        self.cal = Calendar(self.calendar_frame, selectmode="day",
                            date_pattern="yyyy-mm-dd",
                            showweeknumbers=False)
        self.cal.pack(fill="both", expand=True, pady=(10, 0))
        self.cal.bind("<<CalendarSelected>>", self.on_calendar_select)

        # 日历事件颜色标记
        # 每日任务：蓝色系
        self.cal.tag_config("task_normal", background="#4D96FF", foreground="white")
        # 项目步骤：按紧急程度 — 红色(逾期/今天)、橙色(3天内)、黄色(7天内)、绿色(更远)
        self.cal.tag_config("deadline_overdue", background="#FF4757", foreground="white")
        self.cal.tag_config("deadline_today", background="#FF6B6B", foreground="white")
        self.cal.tag_config("deadline_soon", background="#FFA502", foreground="white")
        self.cal.tag_config("deadline_week", background="#FFD93D", foreground="black")
        self.cal.tag_config("deadline_later", background="#6BCB77", foreground="white")

        # 图例
        legend_frame = ttk.LabelFrame(self.calendar_frame, text="图例", padding=5)
        legend_frame.pack(fill="x", padx=10, pady=5)
        legends = [
            ("任务日", "#4D96FF"), ("逾期/今天到期", "#FF4757"),
            ("3天内到期", "#FFA502"), ("7天内到期", "#FFD93D"), ("更远到期", "#6BCB77"),
        ]
        for i, (text, color) in enumerate(legends):
            lbl = ttk.Label(legend_frame, text=f"  ● {text}  ", foreground=color,
                           font=("", 9, "bold"))
            lbl.grid(row=0, column=i, padx=3)

        # 日期详情面板
        detail_frame = ttk.LabelFrame(self.calendar_frame, text="当日详情", padding=5)
        detail_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.detail_text = tk.Text(detail_frame, height=6, wrap=tk.WORD, font=("", 10))
        self.detail_text.pack(fill="both", expand=True)

        self.refresh_calendar_events()

    def add_task(self):
        task = simpledialog.askstring("新任务", "请输入任务内容:")
        if task:
            date_str = str(self.task_date)
            if date_str not in self.data["tasks"]:
                self.data["tasks"][date_str] = []
            self.data["tasks"][date_str].append({"task": task, "done": False})
            self.save_data()
            self.load_tasks()
            self.refresh_calendar_events()

    def on_task_click(self, event):
        """点击任务列表：若点在状态标记区域则切换完成状态，否则选中"""
        index = self.task_listbox.nearest(event.y)
        if index < 0:
            return
        if event.x < 35:  # 状态标记 [✓]/[✗] 区域
            self._toggle_task(index)
        else:
            self.task_listbox.selection_clear(0, tk.END)
            self.task_listbox.selection_set(index)

    def _toggle_task(self, index):
        """切换指定任务的完成状态"""
        date_str = str(self.task_date)
        if date_str not in self.data["tasks"] or index >= len(self.data["tasks"][date_str]):
            return
        current = self.data["tasks"][date_str][index]["done"]
        self.data["tasks"][date_str][index]["done"] = not current
        self.save_data()
        self.load_tasks()
        self.refresh_calendar_events()

    def toggle_task_done(self):
        """按钮：切换选中任务的完成状态"""
        selection = self.task_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先点击选中一个任务")
            return
        self._toggle_task(selection[0])

    def edit_task(self, event=None):
        """双击编辑任务内容"""
        index = self.task_listbox.nearest(event.y) if event else None
        if index is None or index < 0:
            return
        date_str = str(self.task_date)
        if date_str not in self.data["tasks"] or index >= len(self.data["tasks"][date_str]):
            return
        task = self.data["tasks"][date_str][index]
        new_text = simpledialog.askstring("编辑任务", "修改任务内容:", initialvalue=task["task"])
        if new_text and new_text != task["task"]:
            task["task"] = new_text
            self.save_data()
            self.load_tasks()

    def load_tasks(self):
        self.task_listbox.delete(0, tk.END)
        date_str = str(self.task_date)
        if date_str in self.data["tasks"]:
            for task in self.data["tasks"][date_str]:
                status = "✓" if task["done"] else "✗"
                self.task_listbox.insert(tk.END, f"[{status}] {task['task']}")

    def add_project(self):
        project_name = simpledialog.askstring("新项目", "请输入项目名称:")
        if project_name:
            self.data["projects"][project_name] = {"steps": []}
            self.save_data()
            self.load_projects()

    def view_project(self):
        selection = self.project_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请选择一个项目")
            return
        index = selection[0]
        project_name = list(self.data["projects"].keys())[index]
        ProjectWindow(self.root, project_name, self.data["projects"][project_name],
                      self.save_data, self.load_projects, self.refresh_calendar_events)

    def load_projects(self):
        self.project_listbox.delete(0, tk.END)
        for project, detail in self.data["projects"].items():
            self.project_listbox.insert(tk.END, f"{project} - {len(detail['steps'])} 步骤")

    def refresh_calendar_events(self):
        """扫描所有任务和项目步骤的截止日期，在日历上标记彩色事件"""
        self.cal.calevent_remove("all")

        today = datetime.date.today()

        # 标记每日任务日期
        for date_str in self.data.get("tasks", {}):
            try:
                dt = datetime.date.fromisoformat(date_str)
                self.cal.calevent_create(dt, "有任务", tags=["task_normal"])
            except ValueError:
                continue

        # 标记项目步骤的截止日期
        for proj_name, proj_data in self.data.get("projects", {}).items():
            for step in proj_data.get("steps", []):
                deadline_str = step.get("deadline", "")
                if not deadline_str or step.get("done"):
                    continue
                try:
                    dl = datetime.date.fromisoformat(deadline_str)
                except ValueError:
                    continue

                step_desc = step["step"]
                if len(step_desc) > 15:
                    step_desc = step_desc[:15] + "…"
                label = f"{proj_name}: {step_desc}"

                # 按紧急程度分颜色
                days_left = (dl - today).days
                if days_left < 0:
                    tag = "deadline_overdue"
                elif days_left == 0:
                    tag = "deadline_today"
                elif days_left <= 3:
                    tag = "deadline_soon"
                elif days_left <= 7:
                    tag = "deadline_week"
                else:
                    tag = "deadline_later"

                self.cal.calevent_create(dl, label, tags=[tag])

    def on_calendar_select(self, event=None):
        """点击日历某天时，在详情面板显示当天的任务和截止步骤"""
        date_obj = self.cal.selection_get()
        date_str = str(date_obj)
        today = datetime.date.today()

        lines = [f"📅 {date_str}"]

        # 每日任务
        tasks = self.data.get("tasks", {}).get(date_str, [])
        if tasks:
            lines.append("\n── 每日任务 ──")
            for t in tasks:
                status = "✓" if t["done"] else "✗"
                lines.append(f"  [{status}] {t['task']}")
        else:
            lines.append("\n── 每日任务 ──")
            lines.append("  (无)")

        # 项目步骤截止
        lines.append("\n── 项目步骤截止 ──")
        found_step = False
        for proj_name, proj_data in self.data.get("projects", {}).items():
            for step in proj_data.get("steps", []):
                if step.get("deadline") == date_str:
                    status = "✓" if step.get("done") else "✗"
                    days_left = (date_obj - today).days
                    urgent = ""
                    if not step.get("done") and days_left < 0:
                        urgent = " ⚠️已逾期"
                    elif not step.get("done") and days_left == 0:
                        urgent = " 🔴今天到期"
                    elif not step.get("done") and days_left <= 3:
                        urgent = f" 🟡仅剩{days_left}天"
                    lines.append(f"  [{status}] [{proj_name}] {step['step']}{urgent}")
                    found_step = True
        if not found_step:
            lines.append("  (无)")

        self.detail_text.delete("1.0", tk.END)
        self.detail_text.insert("1.0", "\n".join(lines))

    def save_data(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def load_data(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                self.data = json.load(f)


class ProjectWindow:
    def __init__(self, master, project_name, project_data, save_callback, refresh_callback, cal_refresh_callback):
        self.top = tk.Toplevel(master)
        self.top.title(f"项目: {project_name}")
        self.project_data = project_data
        self.save_callback = save_callback
        self.refresh_callback = refresh_callback
        self.cal_refresh_callback = cal_refresh_callback

        self.step_listbox = tk.Listbox(self.top, height=10, cursor="hand2")
        self.step_listbox.pack(fill="both", expand=True)
        self.step_listbox.bind("<Button-1>", self.on_step_click)
        self.step_listbox.bind("<Double-Button-1>", self.edit_step)

        btn_frame = ttk.Frame(self.top)
        btn_frame.pack(pady=5)
        self.add_step_button = ttk.Button(btn_frame, text="添加步骤", command=self.add_step)
        self.add_step_button.pack(side=tk.LEFT, padx=2)
        self.mark_step_done_button = ttk.Button(btn_frame, text="切换完成状态", command=self.toggle_step_done)
        self.mark_step_done_button.pack(side=tk.LEFT, padx=2)

        self.load_steps()

    def add_step(self):
        step = simpledialog.askstring("新步骤", "请输入步骤内容:")
        deadline = simpledialog.askstring("截止时间", "请输入截止日期 (YYYY-MM-DD)，可留空:")
        if step:
            self.project_data["steps"].append({"step": step, "done": False, "deadline": deadline})
            self.save_callback()
            self.load_steps()
            self.refresh_callback()
            self.cal_refresh_callback()

    def on_step_click(self, event):
        """点击步骤列表：若点在状态标记区域则切换完成状态，否则选中"""
        index = self.step_listbox.nearest(event.y)
        if index < 0:
            return
        if event.x < 35:  # 状态标记 [✓]/[✗] 区域
            self._toggle_step(index)
        else:
            self.step_listbox.selection_clear(0, tk.END)
            self.step_listbox.selection_set(index)

    def _toggle_step(self, index):
        """切换指定步骤的完成状态"""
        if index >= len(self.project_data["steps"]):
            return
        current = self.project_data["steps"][index]["done"]
        self.project_data["steps"][index]["done"] = not current
        self.save_callback()
        self.load_steps()
        self.cal_refresh_callback()

    def toggle_step_done(self):
        """按钮：切换选中步骤的完成状态"""
        selection = self.step_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先点击选中一个步骤")
            return
        self._toggle_step(selection[0])

    def edit_step(self, event=None):
        """双击编辑步骤内容和截止日期"""
        index = self.step_listbox.nearest(event.y) if event else None
        if index is None or index < 0 or index >= len(self.project_data["steps"]):
            return
        step = self.project_data["steps"][index]
        new_text = simpledialog.askstring("编辑步骤", "修改步骤内容:", initialvalue=step["step"])
        if new_text is not None and new_text != step["step"]:
            step["step"] = new_text
        new_deadline = simpledialog.askstring("编辑截止时间", "修改截止日期 (YYYY-MM-DD)，可留空:", initialvalue=step.get("deadline", ""))
        if new_deadline is not None and new_deadline != step.get("deadline", ""):
            step["deadline"] = new_deadline
        if new_text is not None or new_deadline is not None:
            self.save_callback()
            self.load_steps()
            self.cal_refresh_callback()
            self.refresh_callback()

    def load_steps(self):
        self.step_listbox.delete(0, tk.END)
        for step in self.project_data["steps"]:
            status = "✓" if step["done"] else "✗"
            deadline = step["deadline"] if step["deadline"] else "无截止时间"
            self.step_listbox.insert(tk.END, f"[{status}] {step['step']} - 截止: {deadline}")


if __name__ == "__main__":
    root = tk.Tk()
    app = ScheduleApp(root)
    root.mainloop()
