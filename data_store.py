"""
数据层：负责所有 JSON 文件的读写和数据的增删改查。
UI 层不需要知道数据怎么存的，只管调用这里的方法。
"""
import json
import os
import datetime


class DataStore:
    def __init__(self, filepath="schedule_data.json"):
        self.filepath = filepath
        self.data = {"tasks": {}, "projects": {}}
        self.load()

    # ── 文件读写 ──────────────────────────────

    def load(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, "r", encoding="utf-8") as f:
                self.data = json.load(f)

    def save(self):
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    # ── 每日任务操作 ──────────────────────────

    def get_tasks(self, date_str):
        """返回指定日期的任务列表 [{task, done}, ...]"""
        return self.data["tasks"].get(date_str, [])

    def add_task(self, date_str, text):
        if date_str not in self.data["tasks"]:
            self.data["tasks"][date_str] = []
        self.data["tasks"][date_str].append({"task": text, "done": False})
        self.save()

    def toggle_task(self, date_str, index):
        tasks = self.data["tasks"].get(date_str, [])
        if 0 <= index < len(tasks):
            tasks[index]["done"] = not tasks[index]["done"]
            self.save()

    def update_task(self, date_str, index, new_text):
        tasks = self.data["tasks"].get(date_str, [])
        if 0 <= index < len(tasks):
            tasks[index]["task"] = new_text
            self.save()

    def delete_task(self, date_str, index):
        tasks = self.data["tasks"].get(date_str, [])
        if 0 <= index < len(tasks):
            del tasks[index]
            if not tasks:  # 当天没有任务了就清理空列表
                del self.data["tasks"][date_str]
            self.save()

    # ── 长期项目操作 ──────────────────────────

    def get_projects(self):
        """返回 {项目名: {steps: [...]}, ...}"""
        return self.data["projects"]

    def get_project(self, name):
        return self.data["projects"].get(name)

    def add_project(self, name):
        if name not in self.data["projects"]:
            self.data["projects"][name] = {"steps": []}
            self.save()

    def delete_project(self, name):
        if name in self.data["projects"]:
            del self.data["projects"][name]
            self.save()

    def add_step(self, project_name, text, deadline):
        proj = self.data["projects"].get(project_name)
        if proj is not None:
            proj["steps"].append({"step": text, "done": False, "deadline": deadline})
            self.save()

    def toggle_step(self, project_name, index):
        proj = self.data["projects"].get(project_name)
        if proj and 0 <= index < len(proj["steps"]):
            proj["steps"][index]["done"] = not proj["steps"][index]["done"]
            self.save()

    def update_step(self, project_name, index, text, deadline):
        proj = self.data["projects"].get(project_name)
        if proj and 0 <= index < len(proj["steps"]):
            proj["steps"][index]["step"] = text
            proj["steps"][index]["deadline"] = deadline
            self.save()

    def delete_step(self, project_name, index):
        proj = self.data["projects"].get(project_name)
        if proj and 0 <= index < len(proj["steps"]):
            del proj["steps"][index]
            self.save()

    # ── 日历相关查询 ──────────────────────────

    def get_all_task_dates(self):
        """返回所有有每日任务的日期集合"""
        return set(self.data["tasks"].keys())

    def get_all_step_deadlines(self):
        """返回所有未完成步骤的截止日期列表 [(项目名, 步骤dict), ...]"""
        result = []
        for proj_name, proj_data in self.data["projects"].items():
            for step in proj_data.get("steps", []):
                if step.get("deadline") and not step.get("done"):
                    result.append((proj_name, step))
        return result

    def get_steps_due_on(self, date_str):
        """返回截止日期为指定日期的步骤列表 [(项目名, 步骤dict), ...]"""
        result = []
        for proj_name, proj_data in self.data["projects"].items():
            for step in proj_data.get("steps", []):
                if step.get("deadline") == date_str:
                    result.append((proj_name, step))
        return result
