# -*- coding: utf-8 -*-
"""
文本映射字典：为语言切换预留。
当前仅维护中文（zh），英文（en）暂未翻译。
新增 UI 文本时先在这里定义，代码中引用 TEXT[key] 而非硬编码。
"""
from typing import Any

TEXTS: dict[str, dict[str, Any]] = {
    "zh": {
        # 标签页名称
        "tab_single_task": "单次任务",
        "tab_project": "长期项目",
        "tab_routine": "固定任务",
        "tab_calendar": "日历视图",
        "tab_stats": "数据统计",

        # 统称
        "schedules": "日程",

        # 单次任务页
        "today_tasks": "今日任务",
        "upcoming_tasks": "之后的任务",
        "add_task_today": "添加任务（今日）",
        "add_task_date": "添加任务（指定日期）",
        "today_deadline": "今天截止",
        "overdue_days": "已逾期 {} 天",
        "days_left": "还剩 {} 天",
        "no_deadline": "无截止日期",

        # 长期项目页
        "project_start": "起始时间",
        "project_no_start": "无起始日期",
        "add_project": "添加项目",
        "delete_project": "删除项目",
        "add_step": "添加步骤",
        "project_steps": "个步骤",

        # 固定任务页
        "add_routine": "添加固定任务",
        "edit_routine": "编辑固定任务",
        "delete_routine": "删除固定任务",
        "routine_name": "任务名称",
        "time_slot": "时间时段",
        "repeat_rule": "重复规则",
        "every_week": "每周",
        "every_workday": "每个工作日（周一至周五，避开法定节假日）",
        "every_month": "每月",
        "calendar_preview": "日历预览（未来 3 个月）",
        "save": "保存",
        "cancel": "取消",
        "weekdays_short": ["一", "二", "三", "四", "五", "六", "日"],
        "rule_weekly": "每周{}",
        "rule_workdays": "每个工作日",
        "rule_monthly": "每月 {} 号",

        # 通用
        "confirm_delete": "确认删除",
        "confirm_delete_msg": "确定要删除「{}」吗？此操作不可恢复。",
        "please_select": "请先选中一个条目",
        "content_required": "内容不能为空",
        "no_data_in_range": "所选范围内无日程记录",
        "edit": "编辑",
        "delete": "删除",
    },
    "en": {
        # Placeholder for future English translation
        "tab_single_task": "Single Tasks",
        "tab_project": "Projects",
        "tab_routine": "Routines",
        "tab_calendar": "Calendar",
        "tab_stats": "Statistics",
        "schedules": "Schedules",
        "today_tasks": "Today's Tasks",
        "upcoming_tasks": "Upcoming Tasks",
        "add_task_today": "Add Task (Today)",
        "add_task_date": "Add Task (Pick Date)",
        "today_deadline": "Due Today",
        "overdue_days": "{} days overdue",
        "days_left": "{} days left",
        "no_deadline": "No deadline",
        "project_start": "Start Date",
        "project_no_start": "No start date",
        "add_project": "Add Project",
        "delete_project": "Delete Project",
        "add_step": "Add Step",
        "project_steps": "steps",
        "add_routine": "Add Routine",
        "edit_routine": "Edit Routine",
        "delete_routine": "Delete Routine",
        "routine_name": "Name",
        "time_slot": "Time Slot",
        "repeat_rule": "Repeat Rule",
        "every_week": "Weekly",
        "every_workday": "Workdays (Mon-Fri, excl. holidays)",
        "every_month": "Monthly",
        "calendar_preview": "Calendar Preview (next 3 months)",
        "save": "Save",
        "cancel": "Cancel",
        "weekdays_short": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "rule_weekly": "Every {}",
        "rule_workdays": "Every workday",
        "rule_monthly": "Monthly on day {}",
        "confirm_delete": "Confirm Delete",
        "confirm_delete_msg": "Are you sure you want to delete \"{}\"? This cannot be undone.",
        "please_select": "Please select an item first",
        "content_required": "Content cannot be empty",
        "no_data_in_range": "No records in the selected range",
        "edit": "Edit",
        "delete": "Delete",
    },
}

# 当前语言（后续加切换功能时改为可配置）
_current_lang = "zh"


def t(key: str, *args) -> str:
    """获取当前语言的文本，支持格式化参数"""
    text = TEXTS.get(_current_lang, TEXTS["zh"]).get(key, key)
    if args:
        return str(text).format(*args)
    return str(text)


def set_language(lang: str):
    """切换语言（本期预留）"""
    global _current_lang
    if lang in TEXTS:
        _current_lang = lang
