"""
固定任务页面：周期性/重复任务的设置与管理。
双击编辑，支持每周/工作日/每月规则 + 日历预览双向联动。
"""
import tkinter as tk
from tkinter import ttk, messagebox
import datetime

from utils.i18n import t
from ui.single_task_tab import _pad_right

try:
    from tkcalendar import Calendar
    HAS_CALENDAR = True
except ImportError:
    HAS_CALENDAR = False

# unicode 转义写死星期名，避免 Windows GBK 环境下 i18n 列表取值的编码问题
_WDAY_ZH = ["一", "二", "三", "四", "五", "六", "日"]


def _rule_to_text(rule):
    """将规则转为可读文本"""
    rtype = rule.get("type", "")
    days = rule.get("days", [])
    if rtype == "weekly":
        names = [_WDAY_ZH[d] for d in days]
        return "每周" + "、".join(names)
    elif rtype == "workdays":
        return "每个工作日"
    elif rtype == "monthly":
        return "每月" + "、".join(str(d) for d in days) + " 号"
    elif rtype == "custom":
        return f"自定义 ({len(days)} 天)"
    return "未设置"


def _compute_rule_dates(rule, start, end):
    """根据规则计算匹配的日期集合（不含 custom_add/remove）"""
    rtype = rule.get("type", "")
    rdays = rule.get("days", [])
    matched = set()
    current = start
    while current <= end:
        ds = current.isoformat()
        if rtype == "weekly":
            if current.weekday() in rdays:
                matched.add(ds)
        elif rtype == "workdays":
            from utils.holidays import is_workday
            if is_workday(current):
                matched.add(ds)
        elif rtype == "monthly":
            if current.day in rdays:
                matched.add(ds)
        elif rtype == "custom":
            if ds in rdays:
                matched.add(ds)
        current += datetime.timedelta(days=1)
    return matched


class RoutineTab(ttk.Frame):
    """固定任务标签页"""

    def __init__(self, parent, data_store, on_data_changed=None):
        super().__init__(parent)
        self.data_store = data_store
        self.on_data_changed = on_data_changed

        list_frame = ttk.LabelFrame(self, text="固定任务列表", padding=5)
        list_frame.pack(fill="both", expand=True, padx=5, pady=(5, 2))

        self.listbox = tk.Listbox(list_frame, height=5, cursor="hand2")
        self.listbox.pack(fill="both", expand=True)
        self.listbox.bind("<Double-Button-1>", self._on_edit)

        list_btn = ttk.Frame(list_frame)
        list_btn.pack(pady=(3, 0))
        ttk.Button(list_btn, text=t("add_routine"), command=self._open_add).pack(side=tk.LEFT, padx=2)
        ttk.Button(list_btn, text=t("delete"), command=self._delete).pack(side=tk.LEFT, padx=2)

        self.refresh()

    def refresh(self):
        self.listbox.delete(0, tk.END)
        self._routines = self.data_store.get_routines()
        for r in self._routines:
            rule_text = _rule_to_text(r.get("rule", {}))
            date_info = self._format_date_range(r)
            line = _pad_right(f"{r['name']} — {rule_text}", date_info)
            self.listbox.insert(tk.END, line)

    def _format_date_range(self, routine):
        """格式化起止时间显示"""
        sd = routine.get("start_date", "")
        ed = routine.get("end_date", "")
        if sd and ed:
            return f"📅 {sd}～{ed}"
        elif sd:
            return f"📅 {sd}～"
        elif ed:
            return f"📅 ～{ed}"
        return ""

    def _notify(self):
        if self.on_data_changed:
            self.on_data_changed()

    def _get_selected(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning("提示", t("please_select"))
            return None
        idx = sel[0]
        if idx >= len(self._routines):
            return None
        return self._routines[idx]

    def _open_add(self):
        RoutineEditDialog(self, self.data_store,
                          on_save=lambda: (self.refresh(), self._notify()))

    def _on_edit(self, event=None):
        routine = self._get_selected()
        if not routine:
            return
        RoutineEditDialog(self, self.data_store, routine=routine,
                          on_save=lambda: (self.refresh(), self._notify()))

    def _delete(self):
        routine = self._get_selected()
        if not routine:
            return
        if messagebox.askyesno(t("confirm_delete"),
                               t("confirm_delete_msg", routine["name"])):
            self.data_store.delete_routine(routine["id"])
            self.refresh()
            self._notify()


class RoutineEditDialog:
    """添加/编辑固定任务的弹窗"""

    def __init__(self, parent, data_store, routine=None, on_save=None):
        self.data_store = data_store
        self.routine = routine
        self.on_save = on_save
        self._custom_add = set(routine.get("custom_add", [])) if routine else set()
        self._custom_remove = set(routine.get("custom_remove", [])) if routine else set()

        is_edit = routine is not None
        self.top = tk.Toplevel(parent)
        self.top.title("编辑固定任务" if is_edit else "添加固定任务")
        self.top.resizable(False, False)
        self.top.transient(parent)
        self.top.grab_set()

        main = ttk.Frame(self.top, padding=10)
        main.pack(fill="both", expand=True)

        # ── 基本信息 ──
        ttk.Label(main, text="任务名称:").grid(row=0, column=0, sticky="w")
        self.name_var = tk.StringVar(value=routine["name"] if routine else "")
        ttk.Entry(main, textvariable=self.name_var, width=30).grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        # 起止时间
        ttk.Label(main, text="起止时间:").grid(row=1, column=0, sticky="w")
        date_frame = ttk.Frame(main)
        date_frame.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        self.start_var = tk.StringVar(value=routine.get("start_date", "") if routine else "")
        self.end_var = tk.StringVar(value=routine.get("end_date", "") if routine else "")
        ttk.Entry(date_frame, textvariable=self.start_var, width=12).pack(side=tk.LEFT)
        ttk.Label(date_frame, text=" ～ ").pack(side=tk.LEFT)
        ttk.Entry(date_frame, textvariable=self.end_var, width=12).pack(side=tk.LEFT)
        ttk.Label(date_frame, text="  可留空", foreground="gray").pack(side=tk.LEFT)

        ttk.Label(main, text="时间时段:").grid(row=2, column=0, sticky="w")
        slot_frame = ttk.Frame(main)
        slot_frame.grid(row=2, column=1, padx=5, pady=2, sticky="ew")
        self.slot_var = tk.StringVar(value=routine.get("time_slot", "") if routine else "")
        ttk.Entry(slot_frame, textvariable=self.slot_var, width=18).pack(side=tk.LEFT)
        ttk.Label(slot_frame, text="  如 08:00-09:00，可留空",
                  foreground="gray").pack(side=tk.LEFT)

        # ── 重复规则 ──
        ttk.Separator(main, orient="horizontal").grid(row=3, column=0, columnspan=2,
                                                       sticky="ew", pady=(10, 5))
        ttk.Label(main, text="重复规则:", font=("", 10, "bold")).grid(row=4, column=0,
                                                                        columnspan=2, sticky="w", pady=(0, 5))

        self.rule_type = tk.StringVar(value="weekly")
        if routine:
            self.rule_type.set(routine.get("rule", {}).get("type", "weekly"))

        # 三种规则 Radio 按钮
        radio_frame = ttk.Frame(main)
        radio_frame.grid(row=5, column=0, columnspan=2, sticky="w")

        ttk.Radiobutton(radio_frame, text="每周固定星期几", variable=self.rule_type,
                        value="weekly", command=self._on_rule_change).pack(anchor="w")
        ttk.Radiobutton(radio_frame, text="每个工作日（周一至五，避节假日）", variable=self.rule_type,
                        value="workdays", command=self._on_rule_change).pack(anchor="w")
        ttk.Radiobutton(radio_frame, text="每月固定日期", variable=self.rule_type,
                        value="monthly", command=self._on_rule_change).pack(anchor="w")

        # —— 每周子选项（两排：一~五 + 六日）——
        self.weekly_frame = ttk.Frame(main)
        self.weekly_frame.grid(row=6, column=0, columnspan=2, sticky="w", padx=(20, 0), pady=(5, 0))
        self.weekday_vars = []
        # 第一排：周一 ~ 周五
        row1 = ttk.Frame(self.weekly_frame)
        row1.pack(anchor="w")
        for i in range(0, 5):
            var = tk.BooleanVar(value=False)
            self.weekday_vars.append(var)
            ttk.Checkbutton(row1, text=f"周{_WDAY_ZH[i]}", variable=var).pack(side=tk.LEFT, padx=3)
        # 第二排：周六 ~ 周日
        row2 = ttk.Frame(self.weekly_frame)
        row2.pack(anchor="w", pady=(2, 0))
        for i in range(5, 7):
            var = tk.BooleanVar(value=False)
            self.weekday_vars.append(var)
            ttk.Checkbutton(row2, text=f"周{_WDAY_ZH[i]}", variable=var).pack(side=tk.LEFT, padx=3)

        # —— 每月子选项 ——
        self.monthly_frame = ttk.Frame(main)
        self.monthly_frame.grid(row=7, column=0, columnspan=2, sticky="w", padx=(20, 0), pady=(5, 0))
        ttk.Label(self.monthly_frame, text="每月").pack(side=tk.LEFT)
        self.month_day_var = tk.StringVar()
        ttk.Entry(self.monthly_frame, textvariable=self.month_day_var, width=5).pack(side=tk.LEFT, padx=3)
        ttk.Label(self.monthly_frame, text="号（多个用逗号分隔，如 1,15）",
                  foreground="gray").pack(side=tk.LEFT)

        # 初始化规则值
        if routine:
            rule = routine.get("rule", {})
            if rule.get("type") == "weekly":
                for d in rule.get("days", []):
                    if 0 <= d < 7:
                        self.weekday_vars[d].set(True)
            elif rule.get("type") == "monthly":
                self.month_day_var.set(",".join(str(d) for d in rule.get("days", [])))

        # —— 日历预览 ——
        ttk.Separator(main, orient="horizontal").grid(row=8, column=0, columnspan=2,
                                                       sticky="ew", pady=(10, 5))
        ttk.Label(main, text="日历预览（未来 3 个月，点击日期可增删）:",
                  font=("", 10, "bold")).grid(row=9, column=0, columnspan=2, sticky="w", pady=(0, 5))

        if HAS_CALENDAR:
            self.cal_frame = ttk.Frame(main)
            self.cal_frame.grid(row=10, column=0, columnspan=2, pady=2)

            self.cal = Calendar(self.cal_frame, selectmode="day",
                                date_pattern="yyyy-mm-dd", showweeknumbers=False)
            self.cal.pack()
            self.cal.bind("<<CalendarSelected>>", self._on_cal_click)

            self.cal.tag_config("rule_match", background="#6BCB77", foreground="white")
            self.cal.tag_config("custom_add", background="#4D96FF", foreground="white")
            self.cal.tag_config("custom_remove", background="#cccccc", foreground="#999999")

            # 图例
            leg = ttk.Frame(main)
            leg.grid(row=11, column=0, columnspan=2, pady=(3, 0))
            ttk.Label(leg, text="● 规则匹配", foreground="#6BCB77").pack(side=tk.LEFT, padx=4)
            ttk.Label(leg, text="● 手动追加", foreground="#4D96FF").pack(side=tk.LEFT, padx=4)
            ttk.Label(leg, text="○ 手动排除", foreground="#999999").pack(side=tk.LEFT, padx=4)
        else:
            ttk.Label(main, text="(需安装 tkcalendar)", foreground="gray").grid(
                row=10, column=0, columnspan=2)

        # —— 按钮 ——
        ttk.Separator(main, orient="horizontal").grid(row=12, column=0, columnspan=2,
                                                       sticky="ew", pady=(10, 5))
        btn = ttk.Frame(main)
        btn.grid(row=13, column=0, columnspan=2, pady=(0, 5))
        ttk.Button(btn, text="✓ 保存", command=self._save, width=12).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn, text="取消", command=self._cancel, width=8).pack(side=tk.LEFT, padx=3)

        self._on_rule_change()
        if HAS_CALENDAR:
            self._refresh_calendar()

        self.top.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        x = parent.winfo_rootx() + (pw - self.top.winfo_width()) // 2
        y = parent.winfo_rooty() + (ph - self.top.winfo_height()) // 2
        self.top.geometry(f"+{x}+{y}")

        self.top.wait_window()

    def _on_rule_change(self):
        """切换规则类型时显示/隐藏对应子选项"""
        rt = self.rule_type.get()
        if rt == "weekly":
            self.weekly_frame.grid()
        else:
            self.weekly_frame.grid_remove()
        if rt == "monthly":
            self.monthly_frame.grid()
        else:
            self.monthly_frame.grid_remove()
        if HAS_CALENDAR:
            self._refresh_calendar()

    def _build_rule(self):
        rt = self.rule_type.get()
        if rt == "weekly":
            days = [i for i, v in enumerate(self.weekday_vars) if v.get()]
            return {"type": "weekly", "days": days}
        elif rt == "workdays":
            return {"type": "workdays", "days": []}
        elif rt == "monthly":
            raw = self.month_day_var.get().strip()
            days = [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]
            return {"type": "monthly", "days": days}
        return {"type": "weekly", "days": []}

    def _get_date_range(self):
        today = datetime.date.today()
        start = today.replace(day=1)
        end_month = today.month + 3
        end_year = today.year
        while end_month > 12:
            end_month -= 12
            end_year += 1
        if end_month == 12:
            end = datetime.date(end_year + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            end = datetime.date(end_year, end_month + 1, 1) - datetime.timedelta(days=1)
        return start, end

    def _refresh_calendar(self):
        if not HAS_CALENDAR:
            return
        self.cal.calevent_remove("all")
        start, end = self._get_date_range()
        rule = self._build_rule()
        rule_dates = _compute_rule_dates(rule, start, end)

        current = start
        while current <= end:
            ds = current.isoformat()
            if ds in self._custom_remove:
                self.cal.calevent_create(current, "排除", tags=["custom_remove"])
            elif ds in self._custom_add:
                self.cal.calevent_create(current, "追加", tags=["custom_add"])
            elif ds in rule_dates:
                self.cal.calevent_create(current, "规则", tags=["rule_match"])
            current += datetime.timedelta(days=1)

    def _on_cal_click(self, event=None):
        if not HAS_CALENDAR:
            return
        ds = str(self.cal.selection_get())
        rule = self._build_rule()
        start, end = self._get_date_range()
        rule_dates = _compute_rule_dates(rule, start, end)

        if ds in self._custom_remove:
            self._custom_remove.discard(ds)
        elif ds in self._custom_add:
            self._custom_add.discard(ds)
        elif ds in rule_dates:
            self._custom_remove.add(ds)
        else:
            self._custom_add.add(ds)

        self._refresh_calendar()

    def _save(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("提示", "请输入任务名称", parent=self.top)
            return

        start_date = self.start_var.get().strip()
        end_date = self.end_var.get().strip()

        rule = self._build_rule()
        # 如果手动追加的日期远超规则匹配数，自动切为自定义模式
        if len(self._custom_add) > len(self._custom_remove) + 15:
            rule_dates = _compute_rule_dates(rule, *self._get_date_range())
            all_dates = sorted(rule_dates.union(self._custom_add) - self._custom_remove)
            rule = {"type": "custom", "days": all_dates}
            self._custom_add.clear()
            self._custom_remove.clear()

        custom_add = sorted(self._custom_add)
        custom_remove = sorted(self._custom_remove)

        if self.routine:
            self.data_store.update_routine(
                self.routine["id"], name=name, rule=rule,
                custom_add=custom_add, custom_remove=custom_remove,
                start_date=start_date, end_date=end_date)
        else:
            self.data_store.add_routine(name, rule, custom_add, custom_remove,
                                        start_date=start_date, end_date=end_date)

        if self.on_save:
            self.on_save()
        self.top.destroy()

    def _cancel(self):
        self.top.destroy()
