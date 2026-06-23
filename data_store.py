"""
数据层：负责所有 JSON 文件的读写和数据的增删改查。
UI 层不需要知道数据怎么存的，只管调用这里的方法。
"""
import json
import os
import sys
import datetime
import uuid

from utils.logger import logger
from utils.holidays import is_workday


def _get_data_dir():
    """返回用户数据目录（Windows: %APPDATA%\\LightSchedule）。
    开发模式 (python main.py) 和 exe 模式共用同一份数据，不受代码位置影响。
    """
    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
    return os.path.join(appdata, "LightSchedule")


def _get_legacy_data_paths():
    """返回旧版可能存放数据的位置（用于迁移）"""
    paths = []
    # exe 同目录（旧版 frozen 模式）
    if getattr(sys, "frozen", False):
        paths.append(os.path.join(os.path.dirname(sys.executable), "schedule_data.json"))
    # 当前工作目录（旧版开发模式）
    paths.append(os.path.join(os.getcwd(), "schedule_data.json"))
    return paths


class DataStore:
    def __init__(self, filepath=None):
        # 确保数据目录存在
        data_dir = _get_data_dir()
        os.makedirs(data_dir, exist_ok=True)

        if filepath is None:
            filepath = os.path.join(data_dir, "schedule_data.json")
        self.filepath = filepath
        self.data = {"tasks": {}, "projects": {}, "routines": []}
        self.load()

    # ── 文件读写 ──────────────────────────────

    def load(self):
        if os.path.exists(self.filepath):
            # 已有数据：直接加载
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
                if "routines" not in self.data:
                    self.data["routines"] = []
                logger.info("数据加载成功: %s", self.filepath)
                return
            except (json.JSONDecodeError, IOError) as e:
                logger.error("数据文件损坏或无法读取: %s", e)
                self.data = {"tasks": {}, "projects": {}, "routines": []}
                return

        # 没有数据文件：先尝试从旧位置迁移
        for legacy_path in _get_legacy_data_paths():
            if os.path.exists(legacy_path):
                try:
                    import shutil
                    shutil.copy(legacy_path, self.filepath)
                    with open(self.filepath, "r", encoding="utf-8") as f:
                        self.data = json.load(f)
                    if "routines" not in self.data:
                        self.data["routines"] = []
                    logger.info("数据已从旧位置迁移: %s → %s", legacy_path, self.filepath)
                    return
                except (IOError, json.JSONDecodeError) as e:
                    logger.warning("旧数据迁移失败: %s", e)

        # 仍然没有：从示例数据复制
        sample_paths = []
        # 打包内的 sample
        bundled = self._get_bundled_data_path()
        if bundled and os.path.exists(bundled):
            sample_paths.append(bundled)
        # 项目根目录的 .sample.json
        if not getattr(sys, "frozen", False):
            cwd_sample = os.path.join(os.getcwd(), "schedule_data.sample.json")
            if os.path.exists(cwd_sample):
                sample_paths.append(cwd_sample)

        for sample_path in sample_paths:
            try:
                import shutil
                shutil.copy(sample_path, self.filepath)
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
                if "routines" not in self.data:
                    self.data["routines"] = []
                logger.info("已从示例数据初始化: %s", self.filepath)
                return
            except (IOError, json.JSONDecodeError) as e:
                logger.warning("示例数据复制失败: %s", e)

        # 实在没有数据，从空开始
        self.data = {"tasks": {}, "projects": {}, "routines": []}

    @staticmethod
    def _get_bundled_data_path():
        """返回 PyInstaller 打包内的 schedule_data.json 路径"""
        if getattr(sys, "frozen", False):
            return os.path.join(sys._MEIPASS, "schedule_data.json")
        return None

    def save(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except IOError as e:
            logger.error("数据保存失败: %s", e)

    # ── 每日任务操作 ──────────────────────────

    def get_tasks(self, date_str):
        """返回指定日期的任务列表 [{task, done, deadline?}, ...]"""
        return self.data["tasks"].get(date_str, [])

    def add_task(self, date_str, text, deadline=""):
        """添加任务，可选截止日期"""
        if date_str not in self.data["tasks"]:
            self.data["tasks"][date_str] = []
        entry = {"task": text, "done": False}
        if deadline:
            entry["deadline"] = deadline
        self.data["tasks"][date_str].append(entry)
        self.save()

    def toggle_task(self, date_str, index):
        tasks = self.data["tasks"].get(date_str, [])
        if 0 <= index < len(tasks):
            tasks[index]["done"] = not tasks[index]["done"]
            self.save()

    def update_task(self, date_str, index, new_text, deadline=None):
        """更新任务内容，可选截止日期。deadline=None 表示不修改"""
        tasks = self.data["tasks"].get(date_str, [])
        if 0 <= index < len(tasks):
            tasks[index]["task"] = new_text
            if deadline is not None:
                if deadline:
                    tasks[index]["deadline"] = deadline
                elif "deadline" in tasks[index]:
                    del tasks[index]["deadline"]
            self.save()

    def delete_task(self, date_str, index):
        tasks = self.data["tasks"].get(date_str, [])
        if 0 <= index < len(tasks):
            del tasks[index]
            if not tasks:
                del self.data["tasks"][date_str]
            self.save()

    # ── 长期项目操作 ──────────────────────────

    def get_projects(self):
        """返回 {项目名: {steps: [...], done: bool, start_date?: str}, ...}"""
        return self.data["projects"]

    def get_project(self, name):
        return self.data["projects"].get(name)

    def add_project(self, name, start_date="", end_date=""):
        """添加项目，可选起始日期和截止日期"""
        if name not in self.data["projects"]:
            entry = {"steps": [], "done": False}
            if start_date:
                entry["start_date"] = start_date
            if end_date:
                entry["end_date"] = end_date
            self.data["projects"][name] = entry
            self.save()

    def update_project_dates(self, name, start_date, end_date):
        """更新项目起止日期。传空字符串表示删除该字段"""
        proj = self.data["projects"].get(name)
        if proj:
            if start_date:
                proj["start_date"] = start_date
            elif "start_date" in proj:
                del proj["start_date"]
            if end_date:
                proj["end_date"] = end_date
            elif "end_date" in proj:
                del proj["end_date"]
            self.save()

    def get_project_start_date(self, name):
        """获取项目起始日期，无则返回空字符串"""
        proj = self.data["projects"].get(name)
        return proj.get("start_date", "") if proj else ""

    def get_project_end_date(self, name):
        """获取项目截止日期，无则返回空字符串"""
        proj = self.data["projects"].get(name)
        return proj.get("end_date", "") if proj else ""

    def delete_project(self, name):
        if name in self.data["projects"]:
            del self.data["projects"][name]

    def toggle_project(self, name):
        """切换项目的完成状态"""
        proj = self.data["projects"].get(name)
        if proj:
            proj["done"] = not proj.get("done", False)
            self.save()

    def auto_check_project(self, name):
        """步骤变更后自动同步项目状态：
        - 所有步骤都完成 → 项目标记为完成
        - 有步骤未完成 → 项目标记为未完成
        """
        proj = self.data["projects"].get(name)
        if not proj:
            return
        steps = proj.get("steps", [])
        if not steps:
            return
        all_done = all(s.get("done") for s in steps)
        if all_done and not proj.get("done"):
            proj["done"] = True
            self.save()
        elif not all_done and proj.get("done"):
            proj["done"] = False
            self.save()

    def get_project_done(self, name):
        """获取项目的完成状态（兼容旧数据无 done 字段）"""
        proj = self.data["projects"].get(name)
        return proj.get("done", False) if proj else False

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

    # ── 固定任务操作 ──────────────────────────

    def get_routines(self):
        """返回所有固定任务列表"""
        return self.data.get("routines", [])

    def add_routine(self, name, rule, custom_add=None, custom_remove=None,
                    start_date="", end_date=""):
        """添加固定任务。
        rule: {"type": "weekly"|"workdays"|"monthly", "days": [...]}
        start_date / end_date 可选，留空表示不限起止时间。
        """
        routine = {
            "id": uuid.uuid4().hex[:8],
            "name": name,
            "rule": rule,
            "custom_add": custom_add or [],
            "custom_remove": custom_remove or [],
            "created_at": datetime.date.today().isoformat(),
        }
        if start_date:
            routine["start_date"] = start_date
        if end_date:
            routine["end_date"] = end_date
        self.data.setdefault("routines", []).append(routine)
        self.save()
        return routine

    def update_routine(self, rid, name=None, rule=None, custom_add=None, custom_remove=None,
                      start_date=None, end_date=None):
        """更新固定任务。start_date/end_date 传 None 表示不修改，传空字符串表示删除字段。"""
        for r in self.data.get("routines", []):
            if r["id"] == rid:
                if name is not None:
                    r["name"] = name
                if rule is not None:
                    r["rule"] = rule
                if custom_add is not None:
                    r["custom_add"] = custom_add
                if custom_remove is not None:
                    r["custom_remove"] = custom_remove
                if start_date is not None:
                    if start_date:
                        r["start_date"] = start_date
                    elif "start_date" in r:
                        del r["start_date"]
                if end_date is not None:
                    if end_date:
                        r["end_date"] = end_date
                    elif "end_date" in r:
                        del r["end_date"]
                self.save()
                return True
        return False

    def delete_routine(self, rid):
        """删除固定任务"""
        routines = self.data.get("routines", [])
        for i, r in enumerate(routines):
            if r["id"] == rid:
                del routines[i]
                self.save()
                return True
        return False

    def get_routine_dates(self, rid, start, end):
        """返回某个固定任务在 [start, end] 范围内的日期列表。
        计算逻辑：规则匹配的日期 ∪ custom_add − custom_remove
        """
        routine = None
        for r in self.data.get("routines", []):
            if r["id"] == rid:
                routine = r
                break
        if not routine:
            return []

        return self._compute_routine_dates(routine, start, end)

    def get_routine_dates_all(self, start, end):
        """返回所有固定任务在 [start, end] 范围内的日期，
        格式: {date_str: [routine_name, ...]}"""
        from collections import defaultdict
        result = defaultdict(list)
        for r in self.data.get("routines", []):
            dates = self._compute_routine_dates(r, start, end)
            for d in dates:
                result[d].append(r["name"])
        return dict(result)

    def _compute_routine_dates(self, routine, start, end):
        """计算单个 routine 在范围内的日期集合。
        考虑 routine 自身的 start_date / end_date 约束。
        """
        rule = routine.get("rule", {})
        rtype = rule.get("type", "")
        rdays = rule.get("days", [])
        custom_add = set(routine.get("custom_add", []))
        custom_remove = set(routine.get("custom_remove", []))

        # 用 routine 自身的起止时间收紧范围
        rs = routine.get("start_date", "")
        re = routine.get("end_date", "")
        if rs:
            try:
                rs_d = datetime.date.fromisoformat(rs)
                if rs_d > start:
                    start = rs_d
            except ValueError:
                pass
        if re:
            try:
                re_d = datetime.date.fromisoformat(re)
                if re_d < end:
                    end = re_d
            except ValueError:
                pass
        if start > end:
            return []

        matched = set()

        current = start
        while current <= end:
            ds = current.isoformat()
            if rtype == "weekly":
                if current.weekday() in rdays:
                    matched.add(ds)
            elif rtype == "workdays":
                if is_workday(current):
                    matched.add(ds)
            elif rtype == "monthly":
                if current.day in rdays:
                    matched.add(ds)
            elif rtype == "custom":
                if ds in rdays:  # custom 模式下 days 存日期字符串列表
                    matched.add(ds)
            current += datetime.timedelta(days=1)

        # 合并手动增删
        result = matched.union(custom_add) - custom_remove
        # 裁剪到原始请求的 [start, end]
        # (start 可能已被 rs 收紧，需要保留原始 start 用于返回值裁剪)
        return sorted(d for d in result if d >= start.isoformat() and d <= end.isoformat())

    def get_routine_info(self, date_str):
        """返回指定日期上所有固定任务的信息列表 [(routine_id, routine_name), ...]"""
        result = []
        try:
            d = datetime.date.fromisoformat(date_str)
        except ValueError:
            return result
        for r in self.data.get("routines", []):
            dates = self._compute_routine_dates(r, d, d)
            if dates:
                result.append((r["id"], r["name"]))
        return result

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

    # ── 单次任务页（之后/过去区域）用到的查询 ──────

    def get_past_tasks(self, before_date_str):
        """返回 before_date 之前的所有任务，格式 [(date_str, task_dict), ...]，按日期降序（最近在前）"""
        result = []
        try:
            before = datetime.date.fromisoformat(before_date_str)
        except ValueError:
            return result
        for date_str, t_list in self.data["tasks"].items():
            try:
                d = datetime.date.fromisoformat(date_str)
            except ValueError:
                continue
            if d < before:
                for t in t_list:
                    result.append((date_str, t))
        result.sort(key=lambda x: x[0], reverse=True)
        return result

    def get_upcoming_tasks(self, after_date_str):
        """返回 after_date 之后的所有任务，格式 [(date_str, task_dict), ...]，按日期排序"""
        result = []
        try:
            after = datetime.date.fromisoformat(after_date_str)
        except ValueError:
            return result
        for date_str, t_list in self.data["tasks"].items():
            try:
                d = datetime.date.fromisoformat(date_str)
            except ValueError:
                continue
            if d > after:
                for t in t_list:
                    result.append((date_str, t))
        result.sort(key=lambda x: x[0])
        return result

    def get_upcoming_steps(self, after_date_str):
        """返回 deadline > after_date 的未完成步骤，
        格式 [(项目名, step_dict), ...]，按截止日期排序"""
        result = []
        try:
            after = datetime.date.fromisoformat(after_date_str)
        except ValueError:
            return result
        for proj_name, proj_data in self.data["projects"].items():
            for step in proj_data.get("steps", []):
                dl = step.get("deadline", "")
                if not dl:
                    continue
                try:
                    d = datetime.date.fromisoformat(dl)
                except ValueError:
                    continue
                if d > after and not step.get("done"):
                    result.append((proj_name, step))
        result.sort(key=lambda x: x[1].get("deadline", ""))
        return result
