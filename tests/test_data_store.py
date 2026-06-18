"""
测试数据层 DataStore：验证增删改查逻辑正确性。
每个测试用临时文件，不触碰真实数据。
"""
import os
import tempfile
import pytest

# 把项目根目录加入路径（因为 data_store.py 在根目录）
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_store import DataStore


@pytest.fixture
def store():
    """每个测试用例获得一个干净的 DataStore（临时文件）"""
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    ds = DataStore(path)
    yield ds
    # 测试结束清理临时文件
    os.remove(path)


class TestTaskOperations:
    """每日任务相关测试"""

    def test_add_and_get(self, store):
        store.add_task("2026-06-11", "写测试代码")
        tasks = store.get_tasks("2026-06-11")
        assert len(tasks) == 1
        assert tasks[0]["task"] == "写测试代码"
        assert tasks[0]["done"] is False

    def test_toggle_task(self, store):
        store.add_task("2026-06-11", "测试切换")
        store.toggle_task("2026-06-11", 0)
        assert store.get_tasks("2026-06-11")[0]["done"] is True
        # 再切回来
        store.toggle_task("2026-06-11", 0)
        assert store.get_tasks("2026-06-11")[0]["done"] is False

    def test_update_task(self, store):
        store.add_task("2026-06-11", "原内容")
        store.update_task("2026-06-11", 0, "新内容")
        assert store.get_tasks("2026-06-11")[0]["task"] == "新内容"

    def test_delete_task(self, store):
        store.add_task("2026-06-11", "待删除")
        store.delete_task("2026-06-11", 0)
        assert store.get_tasks("2026-06-11") == []

    def test_no_crash_on_bad_index(self, store):
        """边界情况：操作不存在的索引不应崩溃"""
        store.toggle_task("2099-01-01", 99)      # 日期不存在
        store.add_task("2026-06-11", "唯一任务")
        store.toggle_task("2026-06-11", 99)      # 索引越界
        store.delete_task("2026-06-11", 99)
        store.update_task("2026-06-11", 99, "xxx")
        # 不应抛出异常


class TestProjectOperations:
    """长期项目相关测试"""

    def test_add_and_get(self, store):
        store.add_project("学习 Python")
        assert "学习 Python" in store.get_projects()

    def test_delete_project(self, store):
        store.add_project("临时项目")
        store.delete_project("临时项目")
        assert "临时项目" not in store.get_projects()

    def test_add_steps_with_deadline(self, store):
        store.add_project("毕设")
        store.add_step("毕设", "写开题报告", "2026-06-15")
        store.add_step("毕设", "做实验", "2026-07-01")

        proj = store.get_project("毕设")
        assert len(proj["steps"]) == 2
        assert proj["steps"][0]["step"] == "写开题报告"
        assert proj["steps"][0]["deadline"] == "2026-06-15"

    def test_toggle_step(self, store):
        store.add_project("测试项目")
        store.add_step("测试项目", "步骤1", "2026-06-20")
        store.toggle_step("测试项目", 0)
        assert store.get_project("测试项目")["steps"][0]["done"] is True

    def test_delete_step(self, store):
        store.add_project("测试项目")
        store.add_step("测试项目", "删掉我", "")
        store.delete_step("测试项目", 0)
        assert len(store.get_project("测试项目")["steps"]) == 0

    def test_update_step(self, store):
        store.add_project("测试项目")
        store.add_step("测试项目", "旧标题", "2026-06-30")
        store.update_step("测试项目", 0, "新标题", "2026-07-15")
        s = store.get_project("测试项目")["steps"][0]
        assert s["step"] == "新标题"
        assert s["deadline"] == "2026-07-15"

    def test_toggle_project(self, store):
        store.add_project("测试项目")
        assert store.get_project_done("测试项目") is False
        store.toggle_project("测试项目")
        assert store.get_project_done("测试项目") is True
        store.toggle_project("测试项目")
        assert store.get_project_done("测试项目") is False

    def test_auto_check_all_steps_done(self, store):
        """所有步骤完成时自动标记项目完成"""
        store.add_project("P1")
        store.add_step("P1", "步骤1", "")
        store.add_step("P1", "步骤2", "")
        store.toggle_step("P1", 0)
        store.toggle_step("P1", 1)
        store.auto_check_project("P1")
        assert store.get_project_done("P1") is True

    def test_auto_check_not_all_done(self, store):
        """部分步骤完成时不自动标记"""
        store.add_project("P2")
        store.add_step("P2", "步骤1", "")
        store.add_step("P2", "步骤2", "")
        store.toggle_step("P2", 0)
        store.auto_check_project("P2")
        assert store.get_project_done("P2") is False

    def test_auto_check_undo_when_step_undone(self, store):
        """步骤被取消完成时，项目也自动变为未完成"""
        store.add_project("P3")
        store.add_step("P3", "步骤1", "")
        # 先全部完成
        store.toggle_step("P3", 0)
        store.auto_check_project("P3")
        assert store.get_project_done("P3") is True
        # 再把步骤改回未完成
        store.toggle_step("P3", 0)
        store.auto_check_project("P3")
        assert store.get_project_done("P3") is False


class TestCalendarQueries:
    """日历查询相关测试"""

    def test_all_task_dates(self, store):
        store.add_task("2026-06-01", "任务A")
        store.add_task("2026-06-05", "任务B")
        dates = store.get_all_task_dates()
        assert "2026-06-01" in dates
        assert "2026-06-05" in dates

    def test_step_deadlines_only_active(self, store):
        """只有未完成的步骤才出现在截止列表中"""
        store.add_project("P1")
        store.add_step("P1", "未完成步骤", "2026-06-20")
        store.add_step("P1", "已完成步骤", "2026-06-21")
        store.toggle_step("P1", 1)  # 标记第二个为完成

        deadlines = store.get_all_step_deadlines()
        # 只有一个未完成的
        assert len(deadlines) == 1
        assert deadlines[0][1]["step"] == "未完成步骤"

    def test_steps_due_on(self, store):
        store.add_project("P1")
        store.add_step("P1", "赶上这天", "2026-12-25")
        store.add_step("P1", "另一天", "2026-12-26")
        due = store.get_steps_due_on("2026-12-25")
        assert len(due) == 1
        assert due[0][1]["step"] == "赶上这天"


class TestTaskDeadline:
    """任务截止日期相关测试"""

    def test_add_task_with_deadline(self, store):
        store.add_task("2026-07-01", "有截止日期的任务", "2026-07-10")
        tasks = store.get_tasks("2026-07-01")
        assert tasks[0]["deadline"] == "2026-07-10"

    def test_add_task_without_deadline(self, store):
        store.add_task("2026-07-01", "无截止日期")
        tasks = store.get_tasks("2026-07-01")
        assert "deadline" not in tasks[0]

    def test_update_task_set_deadline(self, store):
        store.add_task("2026-07-01", "原任务")
        store.update_task("2026-07-01", 0, "新任务", "2026-07-15")
        assert store.get_tasks("2026-07-01")[0]["deadline"] == "2026-07-15"

    def test_update_task_remove_deadline(self, store):
        store.add_task("2026-07-01", "任务", "2026-07-10")
        store.update_task("2026-07-01", 0, "任务", "")
        assert "deadline" not in store.get_tasks("2026-07-01")[0]


class TestProjectDates:
    """项目起止日期相关测试"""

    def test_add_project_with_dates(self, store):
        store.add_project("毕设", "2026-03-01", "2026-06-30")
        assert store.get_project_start_date("毕设") == "2026-03-01"
        assert store.get_project_end_date("毕设") == "2026-06-30"

    def test_add_project_without_dates(self, store):
        store.add_project("无日期项目")
        assert store.get_project_start_date("无日期项目") == ""
        assert store.get_project_end_date("无日期项目") == ""

    def test_update_project_dates(self, store):
        store.add_project("测试项目")
        store.update_project_dates("测试项目", "2026-06-01", "2026-12-31")
        assert store.get_project_start_date("测试项目") == "2026-06-01"
        assert store.get_project_end_date("测试项目") == "2026-12-31"
        # 清空日期
        store.update_project_dates("测试项目", "", "")
        assert store.get_project_start_date("测试项目") == ""
        assert store.get_project_end_date("测试项目") == ""

    def test_only_start_date(self, store):
        store.add_project("P", "2026-01-01")
        assert store.get_project_start_date("P") == "2026-01-01"
        assert store.get_project_end_date("P") == ""


class TestRoutineOperations:
    """固定任务相关测试"""

    def test_add_and_list(self, store):
        rule = {"type": "weekly", "days": [0, 2, 4]}
        r = store.add_routine("晨读", rule)
        routines = store.get_routines()
        assert len(routines) == 1
        assert routines[0]["name"] == "晨读"
        assert routines[0]["rule"] == rule

    def test_update_routine(self, store):
        rule = {"type": "weekly", "days": [0]}
        r = store.add_routine("test", rule)
        store.update_routine(r["id"], name="改名")
        assert store.get_routines()[0]["name"] == "改名"

    def test_delete_routine(self, store):
        r = store.add_routine("test", {"type": "weekly", "days": [0]})
        assert store.delete_routine(r["id"]) is True
        assert len(store.get_routines()) == 0
        assert store.delete_routine("nonexistent") is False

    def test_routine_dates_weekly(self, store):
        """每周一三五 → 在范围内生成正确日期"""
        rule = {"type": "weekly", "days": [0, 2, 4]}  # Mon, Wed, Fri
        r = store.add_routine("隔天任务", rule)
        # 2026-06-15 (Mon) ~ 2026-06-21 (Sun) 应有 Mon(15), Wed(17), Fri(19)
        import datetime
        dates = store.get_routine_dates(r["id"],
                                        datetime.date(2026, 6, 15),
                                        datetime.date(2026, 6, 21))
        assert "2026-06-15" in dates  # Monday
        assert "2026-06-17" in dates  # Wednesday
        assert "2026-06-19" in dates  # Friday
        assert "2026-06-16" not in dates  # Tuesday

    def test_routine_dates_monthly(self, store):
        """每月 15 号 → 匹配正确"""
        rule = {"type": "monthly", "days": [15]}
        r = store.add_routine("月度复盘", rule)
        import datetime
        dates = store.get_routine_dates(r["id"],
                                        datetime.date(2026, 6, 1),
                                        datetime.date(2026, 7, 31))
        assert "2026-06-15" in dates
        assert "2026-07-15" in dates

    def test_routine_dates_with_custom(self, store):
        """custom_add 和 custom_remove 生效"""
        rule = {"type": "weekly", "days": [0]}  # 每周一
        r = store.add_routine("周一任务", rule,
                              custom_add=["2026-06-17"],    # 加个周三
                              custom_remove=["2026-06-22"])  # 去掉某个周一
        import datetime
        dates = store.get_routine_dates(r["id"],
                                        datetime.date(2026, 6, 15),
                                        datetime.date(2026, 6, 28))
        assert "2026-06-15" in dates   # Monday (rule)
        assert "2026-06-17" in dates   # added
        assert "2026-06-22" not in dates  # removed Monday
        assert "2026-06-16" not in dates  # Tuesday, no rule

    def test_routine_dates_all(self, store):
        """get_routine_dates_all 汇总所有固定任务"""
        store.add_routine("R1", {"type": "weekly", "days": [0]})
        store.add_routine("R2", {"type": "weekly", "days": [0]})
        import datetime
        all_dates = store.get_routine_dates_all(
            datetime.date(2026, 6, 15), datetime.date(2026, 6, 21))
        # 6/15 is Monday, both routines should match
        assert "2026-06-15" in all_dates
        assert len(all_dates["2026-06-15"]) == 2


class TestUpcomingQueries:
    """单次任务页"之后的任务"查询测试"""

    def test_upcoming_tasks(self, store):
        store.add_task("2026-06-20", "未来任务")
        store.add_task("2026-06-10", "过去任务")
        store.add_task("2026-06-15", "今天任务")
        upcoming = store.get_upcoming_tasks("2026-06-15")
        dates = [u[0] for u in upcoming]
        assert "2026-06-20" in dates
        assert "2026-06-10" not in dates
        assert "2026-06-15" not in dates  # 不含今天

    def test_upcoming_steps(self, store):
        store.add_project("P1")
        store.add_step("P1", "未来步骤", "2026-07-01")
        store.add_step("P1", "过去步骤", "2026-01-01")
        upcoming = store.get_upcoming_steps("2026-06-15")
        assert len(upcoming) == 1
        assert upcoming[0][1]["step"] == "未来步骤"


class TestHolidayUtils:
    """节假日工具测试"""

    def test_is_holiday(self, store):
        from utils.holidays import is_holiday, is_workday
        import datetime
        assert is_holiday(datetime.date(2026, 1, 1)) is True
        assert is_holiday(datetime.date(2026, 6, 15)) is False

    def test_is_workday(self, store):
        from utils.holidays import is_workday
        import datetime
        # 2026-06-15 is Monday, not a holiday
        assert is_workday(datetime.date(2026, 6, 15)) is True
        # 2026-06-20 is Saturday
        assert is_workday(datetime.date(2026, 6, 20)) is False
        # 2026-01-01 is a holiday (Thursday)
        assert is_workday(datetime.date(2026, 1, 1)) is False


class TestPersistence:
    """数据持久化测试"""

    def test_save_and_reload(self, store):
        store.add_task("2026-08-01", "持久化测试")
        store.add_project("重启项目")
        store.add_step("重启项目", "重启后还在", "2026-09-01")

        store2 = DataStore(store.filepath)
        assert store2.get_tasks("2026-08-01")[0]["task"] == "持久化测试"
        assert "重启项目" in store2.get_projects()

    def test_v03_data_migration(self, store):
        """旧数据（无 routines 键）加载时不崩溃，自动补齐"""
        import json
        # 写旧格式数据
        old_data = {"tasks": {"2026-06-15": [{"task": "旧任务", "done": False}]},
                     "projects": {}}
        with open(store.filepath, "w", encoding="utf-8") as f:
            json.dump(old_data, f)
        store2 = DataStore(store.filepath)
        assert "routines" in store2.data
        assert store2.data["routines"] == []
        assert store2.get_tasks("2026-06-15")[0]["task"] == "旧任务"
