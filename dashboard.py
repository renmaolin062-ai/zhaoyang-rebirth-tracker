"""
每日监督表格核心逻辑。

这里负责生成：
1. daily_dashboard.html 静态监督表格
2. 本地网页打卡表格
3. 早晨和晚间推送内容

任务会根据日期、昨天完成率、连续打卡天数、AI学习断档情况自动变化。
"""

from __future__ import annotations

import html
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
PROGRESS_PATH = BASE_DIR / "progress.json"
TASK_POOL_PATH = BASE_DIR / "task_pool.json"
DASHBOARD_PATH = BASE_DIR / "daily_dashboard.html"
NIGHT_DASHBOARD_PATH = BASE_DIR / "night_dashboard.html"
LOCAL_TZ = timezone(timedelta(hours=8))


DEFAULT_TASK_POOL = {
    "manifestation_tasks": [
        "读身份声明：我不是被过去定义的人，我是正在重建能力、现金流和生活秩序的人。",
        "闭眼想象自己按时学习、完成项目、稳定赚钱，并一点点把钱还给父母。",
        "写下一句今日肯定语：显化不是空想，是我每天的行动。",
        "复盘一个已经变好的证据，提醒自己重塑正在发生。"
    ],
    "energy_tasks": [
        "喝温水、洗脸、开窗，让身体先醒过来。",
        "开合跳30个，再做5组深呼吸。",
        "晒太阳5分钟，站直，把今天的状态拉起来。",
        "整理桌面3分钟，只留下今天要用的东西。"
    ],
    "ai_learning_tasks": [
        "完成今天的Python主线学习，并写一个小例子。",
        "复习昨天的Python知识点，把不懂的地方问Codex。",
        "用Codex解释一个AI工具案例，并记录可模仿的步骤。",
        "做30分钟基础复习：变量、判断、循环、函数任选一个。"
    ],
    "wealth_rebuild_tasks": [
        "整理一个未来可以变现的小技能点。",
        "记录一个可执行的收入线索，不投钱，只观察和学习。",
        "优化一个作品、脚本、页面或内容选题。",
        "检查今天有没有冲动消费，把风险挡在门外。"
    ],
    "reading_tasks": [
        "阅读《终身成长》当前章节，并写一句触动自己的话。",
        "摘抄一个关于成长型思维的句子。",
        "把今天读到的内容和自己当前困境连接起来。",
        "用三句话复述今天阅读内容。"
    ],
    "evening_review_tasks": [
        "记录今天完成了什么，没完成什么，不批判，只看事实。",
        "写下今天最容易失控的时刻，以及下次怎么提前挡住。",
        "确认明天最重要的一件事。",
        "复盘今天的AI学习、阅读、财富行动和风险行为。"
    ]
}


def read_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    """读取 JSON；如果文件不存在或格式错误，就返回默认值。"""
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def write_json(path: Path, data: Dict[str, Any]) -> None:
    """保存 JSON。"""
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_task_pool() -> Dict[str, List[str]]:
    """读取任务池，缺字段时用默认任务补齐。"""
    pool = read_json(TASK_POOL_PATH, DEFAULT_TASK_POOL)
    for key, value in DEFAULT_TASK_POOL.items():
        if not isinstance(pool.get(key), list) or not pool[key]:
            pool[key] = value
    return pool


def pick_task(pool: Dict[str, List[str]], key: str, seed: int) -> str:
    """按日期和进度稳定选择任务，让每天内容不完全一样。"""
    tasks = pool.get(key, DEFAULT_TASK_POOL[key])
    return tasks[seed % len(tasks)]


def yesterday_text(today_text: str) -> str:
    """返回昨天日期。"""
    try:
        today = date.fromisoformat(today_text)
    except ValueError:
        today = date.today()
    return (today - timedelta(days=1)).isoformat()


def local_today_text() -> str:
    """返回北京时间日期，避免云端 UTC 把早晨推送算成前一天。"""
    return datetime.now(LOCAL_TZ).date().isoformat()


def plan_day_from_start(config: Dict[str, Any], today_text: str) -> int:
    """根据 START_DATE 自动计算今天是重塑计划第几天。"""
    try:
        start = date.fromisoformat(str(config.get("START_DATE", "2026-05-25")))
        current = date.fromisoformat(today_text)
    except ValueError:
        return 1
    return max((current - start).days + 1, 1)


def auto_python_day(config: Dict[str, Any], today_text: str) -> int:
    """Python 学习日自动随日期增长，也保留手动配置作为最低起点。"""
    configured_day = int(config.get("PYTHON_DAY", 1) or 1)
    return max(configured_day, plan_day_from_start(config, today_text))


def auto_book_chapter(config: Dict[str, Any], today_text: str) -> int:
    """阅读章节自动推进：默认每7天进入下一章。"""
    configured_chapter = int(config.get("BOOK_CHAPTER", 1) or 1)
    auto_chapter = (plan_day_from_start(config, today_text) - 1) // 7 + 1
    return max(configured_chapter, auto_chapter)


def get_all_task_ids() -> List[str]:
    """所有固定任务 ID。"""
    return [
        "morning_energy",
        "morning_manifestation",
        "morning_ai_learning",
        "morning_wealth_action",
        "morning_commute_prepare",
        "day_ai_case",
        "day_viral_video",
        "day_risk_check",
        "evening_codex_project",
        "evening_tk_analysis",
        "evening_reading",
        "evening_wealth_review",
        "evening_manifestation_energy",
        "evening_plan_and_catchup",
        "evening_checkin",
    ]


def default_task_status() -> Dict[str, Dict[str, Any]]:
    """给每个任务生成默认状态。"""
    return {task_id: {"done": False, "note": ""} for task_id in get_all_task_ids()}


def normalize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """兼容旧版 progress.json，并补齐新版任务状态。"""
    normalized = {
        "tasks": default_task_status(),
        "manifestation": bool(record.get("manifestation", False)),
        "energy": bool(record.get("energy", False)),
        "ai_learning": bool(record.get("ai_learning", False)),
        "reading": bool(record.get("reading", False)),
        "wealth_action": bool(record.get("wealth_action", False)),
        "no_risky_money_behavior": bool(record.get("no_risky_money_behavior", True)),
        "impulsive_spending": bool(record.get("impulsive_spending", False)),
        "mood_score": int(record.get("mood_score", 7) or 7),
        "income_today": float(record.get("income_today", 0) or 0),
        "note": str(record.get("note", "")),
    }

    old_tasks = record.get("tasks", {})
    if isinstance(old_tasks, dict):
        for task_id, status in old_tasks.items():
            if task_id in normalized["tasks"] and isinstance(status, dict):
                normalized["tasks"][task_id]["done"] = bool(status.get("done", False))
                normalized["tasks"][task_id]["note"] = str(status.get("note", ""))

    legacy_map = {
        "manifestation": ["morning_manifestation", "evening_manifestation_energy"],
        "energy": ["morning_energy"],
        "ai_learning": ["morning_ai_learning"],
        "reading": ["evening_reading"],
        "wealth_action": ["morning_wealth_action", "evening_wealth_review"],
        "no_risky_money_behavior": ["day_risk_check"],
    }
    for old_field, task_ids in legacy_map.items():
        if record.get(old_field) is True:
            for task_id in task_ids:
                normalized["tasks"][task_id]["done"] = True

    update_summary_fields(normalized)
    return normalized


def update_summary_fields(record: Dict[str, Any]) -> None:
    """根据逐项任务状态更新模块级字段，方便旧统计继续使用。"""
    tasks = record.get("tasks", {})

    def done(task_id: str) -> bool:
        return bool(tasks.get(task_id, {}).get("done", False))

    record["manifestation"] = done("morning_manifestation") and done("evening_manifestation_energy")
    record["energy"] = done("morning_energy")
    record["ai_learning"] = done("morning_ai_learning") or done("day_ai_case")
    record["reading"] = done("evening_reading")
    record["wealth_action"] = done("morning_wealth_action") and done("evening_wealth_review")
    record["no_risky_money_behavior"] = done("day_risk_check") and not bool(record.get("impulsive_spending", False))


def task_completion_from_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """计算一条记录里的任务完成率。"""
    normalized = normalize_record(record)
    task_ids = get_all_task_ids()
    done_count = sum(1 for task_id in task_ids if normalized["tasks"][task_id]["done"])
    total = len(task_ids)
    return {
        "done_count": done_count,
        "total": total,
        "rate": round(done_count / total * 100) if total else 0,
    }


def calculate_streak(progress: Dict[str, Any], today_text: str) -> int:
    """计算连续打卡天数：当天有记录就算一天。"""
    try:
        current = date.fromisoformat(today_text)
    except ValueError:
        current = date.today()

    streak = 0
    while True:
        check_day = (current - timedelta(days=streak)).isoformat()
        if check_day not in progress:
            break
        streak += 1
    return streak


def ai_missed_two_days(progress: Dict[str, Any], today_text: str) -> bool:
    """判断 AI 学习是否连续两天没完成。"""
    try:
        current = date.fromisoformat(today_text)
    except ValueError:
        current = date.today()

    missed = 0
    for offset in (1, 2):
        day_text = (current - timedelta(days=offset)).isoformat()
        record = normalize_record(progress.get(day_text, {}))
        if not record.get("ai_learning", False):
            missed += 1
    return missed == 2


def percent(current: float, target: float) -> int:
    """计算进度百分比，最多显示 100。"""
    if target <= 0:
        return 0
    return max(0, min(round(current / target * 100), 100))


def get_dynamic_level(yesterday_rate: int, streak: int, ai_two_day_missed: bool) -> str:
    """根据昨天完成率、连续打卡和AI断档情况决定今天难度。"""
    if ai_two_day_missed:
        return "ai_recovery"
    if yesterday_rate < 60:
        return "lighter"
    if streak >= 3:
        return "upgrade"
    return "normal"


def get_task_sections(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """根据今日状态生成早晨、白天、晚间任务表。"""
    pool = load_task_pool()
    config = data["config"]
    seed = data["seed"]
    level = data["dynamic_level"]
    python_day = int(data["ai"]["day"])
    book_name = config.get("BOOK_NAME", "终身成长")
    book_chapter = int(data["reading"]["chapter"])

    ai_task = pick_task(pool, "ai_learning_tasks", seed + python_day)
    ai_duration = "40分钟"
    if level == "ai_recovery":
        ai_task = "AI学习连续两天没完成，今天只做30分钟基础复习：变量、判断、循环、函数任选一个。剩余时间整理笔记。"
        ai_duration = "30分钟"
    elif level == "lighter":
        ai_task = "昨天完成率偏低，今天降低难度：只完成一个最小Python练习，并把问题记下来。"
        ai_duration = "30分钟"
    elif level == "upgrade":
        ai_task = f"连续打卡不错，今天升级一点：完成Python第{python_day}天任务，并让Codex帮你改进一次。"

    wealth_task = pick_task(pool, "wealth_rebuild_tasks", seed + data["streak"])
    if data["money"]["percent"] < 10:
        wealth_task += " 当前还款进度还在起步，重点是积累能力和作品，不做高风险动作。"

    return [
        {
            "key": "morning",
            "title": "🌅 早晨启动",
            "summary": "08:00起床后完成，9:30前收束，10:00上班。",
            "tasks": [
                {
                    "id": "morning_energy",
                    "time": "08:00-08:10",
                    "module": "能量提升",
                    "task": pick_task(pool, "energy_tasks", seed),
                    "duration": "10分钟",
                },
                {
                    "id": "morning_manifestation",
                    "time": "08:10-08:20",
                    "module": "显化",
                    "task": pick_task(pool, "manifestation_tasks", seed + 1),
                    "duration": "10分钟",
                },
                {
                    "id": "morning_ai_learning",
                    "time": "08:20-09:00",
                    "module": "AI学习",
                    "task": ai_task,
                    "duration": ai_duration,
                },
                {
                    "id": "morning_wealth_action",
                    "time": "09:00-09:20",
                    "module": "财富重建",
                    "task": wealth_task,
                    "duration": "20分钟",
                },
                {
                    "id": "morning_commute_prepare",
                    "time": "09:20-09:30",
                    "module": "上班准备",
                    "task": "出门/上班准备：收拾物品，确认今天不借钱、不投资、不冲动消费。",
                    "duration": "10分钟",
                },
            ],
        },
        {
            "key": "daytime",
            "title": "☀️ 白天轻任务",
            "summary": "10:00上班后只安排轻任务，不放重学习，保护工作精力。",
            "tasks": [
                {
                    "id": "day_ai_case",
                    "time": "午休10分钟",
                    "module": "AI案例",
                    "task": "午休看10分钟AI案例，只记录一个可模仿点。",
                    "duration": "10分钟",
                },
                {
                    "id": "day_viral_video",
                    "time": "碎片时间",
                    "module": "内容系统",
                    "task": "记录一个爆款视频：标题、开头3秒、评论区需求。",
                    "duration": "10分钟",
                },
                {
                    "id": "day_risk_check",
                    "time": "下班前",
                    "module": "风险检查",
                    "task": "检查今天有没有借钱、投资、合伙、套现、陌生赚钱链接和超过100元非必需消费。",
                    "duration": "5分钟",
                },
            ],
        },
        {
            "key": "evening",
            "title": "🌙 晚间复盘",
            "summary": "19:00下班后进入深度重建时间，23:30推送复盘提醒。",
            "tasks": [
                {
                    "id": "evening_codex_project",
                    "time": "19:30-20:30",
                    "module": "Codex项目",
                    "task": "Codex项目推进：写、改或测试一个真实小功能。",
                    "duration": "60分钟",
                },
                {
                    "id": "evening_tk_analysis",
                    "time": "20:30-21:00",
                    "module": "内容系统",
                    "task": "AI视频/TK爆款分析：拆一条内容，记录选题、钩子、结构。",
                    "duration": "30分钟",
                },
                {
                    "id": "evening_reading",
                    "time": "21:00-21:40",
                    "module": "书籍阅读",
                    "task": f"{pick_task(pool, 'reading_tasks', seed + book_chapter)} 当前书籍：《{book_name}》第{book_chapter}章。",
                    "duration": "40分钟",
                },
                {
                    "id": "evening_wealth_review",
                    "time": "21:40-22:10",
                    "module": "财富重建",
                    "task": "财富重建复盘：今天做了什么收入相关小动作？有没有任何高风险行为？",
                    "duration": "30分钟",
                },
                {
                    "id": "evening_manifestation_energy",
                    "time": "22:10-22:40",
                    "module": "显化",
                    "task": "晚间显化 + 能量清理：承认今天的真实状态，把自责放下，把注意力收回来。",
                    "duration": "30分钟",
                },
                {
                    "id": "evening_plan_and_catchup",
                    "time": "22:40-23:20",
                    "module": "明日计划",
                    "task": "明日计划 + 自由补任务：先补最关键的一项，再写下明天最重要的一件事。",
                    "duration": "40分钟",
                },
                {
                    "id": "evening_checkin",
                    "time": "23:30",
                    "module": "复盘打卡",
                    "task": pick_task(pool, "evening_review_tasks", seed + 2),
                    "duration": "5分钟",
                },
            ],
        },
    ]


def section_rates(sections: List[Dict[str, Any]], record: Dict[str, Any]) -> Dict[str, int]:
    """计算每个任务区完成率。"""
    rates = {}
    for section in sections:
        tasks = section["tasks"]
        done_count = sum(1 for task in tasks if record["tasks"][task["id"]]["done"])
        rates[section["key"]] = round(done_count / len(tasks) * 100)
    return rates


def build_dashboard_data(today_text: str | None = None) -> Dict[str, Any]:
    """组装网页、静态HTML和推送都要用的数据。"""
    today_text = today_text or local_today_text()
    config = read_json(CONFIG_PATH, {})
    progress = read_json(PROGRESS_PATH, {})
    record = normalize_record(progress.get(today_text, {}))
    yesterday_record = progress.get(yesterday_text(today_text), {})
    yesterday_rate = task_completion_from_record(yesterday_record)["rate"] if yesterday_record else 0
    streak = calculate_streak(progress, today_text)

    target_money = float(config.get("TARGET_MONEY", 100000) or 100000)
    base_money = float(config.get("CURRENT_MONEY", 0) or 0)
    income_from_progress = sum(
        float(item.get("income_today", 0) or 0)
        for item in progress.values()
        if isinstance(item, dict)
    )
    current_money = base_money + income_from_progress
    plan_day = plan_day_from_start(config, today_text)
    python_day = auto_python_day(config, today_text)
    book_chapter = auto_book_chapter(config, today_text)

    data: Dict[str, Any] = {
        "today": today_text,
        "plan_day": plan_day,
        "seed": date.fromisoformat(today_text).toordinal(),
        "goal": "按8:00-9:30完成早晨启动，白天只做轻任务，晚上完成项目、阅读和复盘。",
        "config": config,
        "record": record,
        "streak": streak,
        "yesterday_rate": yesterday_rate,
        "dynamic_level": get_dynamic_level(
            yesterday_rate,
            streak,
            ai_missed_two_days(progress, today_text),
        ),
        "money": {
            "target": target_money,
            "current": current_money,
            "remaining": max(target_money - current_money, 0),
            "percent": percent(current_money, target_money),
        },
        "ai": {
            "day": python_day,
            "target": 365,
            "percent": percent(float(python_day), 365),
            "teacher": str(config.get("AI_COURSE_TEACHER", "吴恩达 Andrew Ng") or "吴恩达 Andrew Ng"),
            "course_name": str(config.get("AI_COURSE_NAME", "AI 与 Python 基础能力课") or "AI 与 Python 基础能力课"),
        },
        "reading": {
            "book": config.get("BOOK_NAME", "终身成长"),
            "chapter": book_chapter,
            "target": 12,
            "percent": percent(float(book_chapter), 12),
        },
    }
    data["sections"] = get_task_sections(data)
    completion = task_completion_from_record(record)
    completion["section_rates"] = section_rates(data["sections"], record)
    data["completion"] = completion
    return data


def task_label_map_for_day(day_text: str) -> Dict[str, str]:
    """返回某一天的任务 ID 到任务名称映射，用于历史记录展示。"""
    data = build_dashboard_data(day_text)
    labels: Dict[str, str] = {}
    for section in data["sections"]:
        for task in section["tasks"]:
            labels[task["id"]] = short_task_name(task)
    return labels


def summarize_history(records: List[Dict[str, Any]], days: int) -> Dict[str, Any]:
    """统计最近 N 天的成长数据。"""
    if not records:
        return {
            "days": days,
            "checkin_days": 0,
            "avg_rate": 0,
            "ai_done": 0,
            "reading_done": 0,
            "wealth_done": 0,
            "income": 0,
            "avg_mood": 0,
        }

    recent = records[-days:]
    checkin_days = len(recent)
    return {
        "days": days,
        "checkin_days": checkin_days,
        "avg_rate": round(sum(item["rate"] for item in recent) / checkin_days) if checkin_days else 0,
        "ai_done": sum(1 for item in recent if item["ai_learning"]),
        "reading_done": sum(1 for item in recent if item["reading"]),
        "wealth_done": sum(1 for item in recent if item["wealth_action"]),
        "income": round(sum(float(item["income_today"] or 0) for item in recent), 2),
        "avg_mood": round(sum(int(item["mood_score"] or 0) for item in recent) / checkin_days, 1) if checkin_days else 0,
    }


def build_growth_history_data(today_text: str | None = None) -> Dict[str, Any]:
    """构建成长记录页数据：不是只看今天，而是保留长期轨迹。"""
    today_text = today_text or local_today_text()
    progress = read_json(PROGRESS_PATH, {})
    records: List[Dict[str, Any]] = []

    for day_text in sorted(progress.keys()):
        raw_record = progress.get(day_text, {})
        if not isinstance(raw_record, dict):
            continue

        record = normalize_record(raw_record)
        completion = task_completion_from_record(record)
        labels = task_label_map_for_day(day_text)
        task_notes = []
        for task_id, status in record.get("tasks", {}).items():
            note = str(status.get("note", "")).strip() if isinstance(status, dict) else ""
            if note:
                task_notes.append(
                    {
                        "task": labels.get(task_id, task_id),
                        "note": note,
                    }
                )

        records.append(
            {
                "date": day_text,
                "done_count": completion["done_count"],
                "total": completion["total"],
                "rate": completion["rate"],
                "mood_score": record.get("mood_score", 7),
                "income_today": record.get("income_today", 0),
                "note": str(record.get("note", "")).strip(),
                "ai_learning": bool(record.get("ai_learning", False)),
                "reading": bool(record.get("reading", False)),
                "wealth_action": bool(record.get("wealth_action", False)),
                "no_risky_money_behavior": bool(record.get("no_risky_money_behavior", True)),
                "task_notes": task_notes,
            }
        )

    return {
        "today": today_text,
        "records": records,
        "total_days": len(records),
        "streak": calculate_streak(progress, today_text),
        "week": summarize_history(records, 7),
        "month": summarize_history(records, 30),
    }


def get_task_status(data: Dict[str, Any], task_id: str) -> Dict[str, Any]:
    """读取某个任务的完成状态。"""
    return data["record"]["tasks"].get(task_id, {"done": False, "note": ""})


def find_task(data: Dict[str, Any], task_id: str) -> Dict[str, str]:
    """按任务 ID 找任务。"""
    for section in data["sections"]:
        for task in section["tasks"]:
            if task["id"] == task_id:
                return task
    return {
        "id": task_id,
        "time": "",
        "module": "任务",
        "task": "未找到任务",
        "duration": "",
    }


def render_xp_bar(label: str, value: str, percent_value: int, extra_class: str = "") -> str:
    """生成发光进度条。"""
    return f"""
      <div class="rpg-meter {html.escape(extra_class)}">
        <div class="meter-head">
          <span>{html.escape(label)}</span>
          <strong>{html.escape(value)}</strong>
        </div>
        <div class="meter-track">
          <div class="meter-fill" style="--target: {percent_value}%; width: {percent_value}%"></div>
        </div>
      </div>
    """


def render_task_control(
    task: Dict[str, str],
    status: Dict[str, Any],
    editable: bool,
    card_class: str = "quest-card",
    reward: str = "+10 XP",
) -> str:
    """生成可点击的 RPG 任务卡。"""
    task_id = task["id"]
    checked = "checked" if status.get("done") else ""
    note = html.escape(str(status.get("note", "")))
    done_class = "is-done" if status.get("done") else ""

    if editable:
        checkbox = f'<input class="quest-check" id="{task_id}" type="checkbox" name="task_done_{task_id}" {checked}>'
        label_for = f'for="{task_id}"'
        note_input = f'<input class="note-input" name="task_note_{task_id}" value="{note}" placeholder="战斗备注">'
    else:
        checkbox = ""
        label_for = ""
        note_input = f'<div class="note-readonly">{note or "未记录"}</div>'

    return f"""
      <div class="quest-wrap {done_class}">
        {checkbox}
        <label {label_for} class="{html.escape(card_class)}">
          <span class="quest-icon">{module_icon(task["module"])}</span>
          <span class="quest-meta">
            <span class="quest-time">{html.escape(task["time"])}</span>
            <span class="quest-module">{html.escape(task["module"])}</span>
          </span>
          <strong>{html.escape(short_task_name(task))}</strong>
          <p>{html.escape(task["task"])}</p>
          <span class="reward-pill">{html.escape(reward)}</span>
          <span class="defeated">✔ 已击败Boss</span>
        </label>
        {note_input}
      </div>
    """


def module_icon(module: str) -> str:
    """给任务模块配图标。"""
    icons = {
        "能量提升": "⚡",
        "显化": "✦",
        "AI学习": "⌘",
        "财富重建": "◆",
        "上班准备": "◈",
        "AI案例": "🎓",
        "内容系统": "▶",
        "风险检查": "🛡",
        "Codex项目": "◇",
        "书籍阅读": "📖",
        "明日计划": "☽",
        "复盘打卡": "✓",
    }
    return icons.get(module, "✧")


def short_task_name(task: Dict[str, str]) -> str:
    """把任务名压短，适合卡片标题。"""
    task_id = task["id"]
    names = {
        "morning_energy": "能量启动",
        "morning_manifestation": "晨间显化",
        "morning_ai_learning": "AI Academy 主课",
        "morning_wealth_action": "财富小动作",
        "morning_commute_prepare": "上班准备",
        "day_ai_case": "AI案例观察",
        "day_viral_video": "爆款视频记录",
        "day_risk_check": "风险护盾",
        "evening_codex_project": "Codex项目推进",
        "evening_tk_analysis": "TK爆款分析",
        "evening_reading": "阅读成长",
        "evening_wealth_review": "财富复盘",
        "evening_manifestation_energy": "能量清理",
        "evening_plan_and_catchup": "明日计划",
        "evening_checkin": "复盘打卡",
    }
    return names.get(task_id, task["module"])


def render_role_panel(data: Dict[str, Any]) -> str:
    """角色状态卡。"""
    completion = data["completion"]
    level = max(1, data["streak"] + 1)
    energy = min(100, 62 + data["streak"] * 5 + completion["rate"] // 5)
    wealth_level = max(1, data["money"]["percent"] // 10 + 1)
    xp_value = f'{completion["done_count"] * 30} / {completion["total"] * 30} XP'

    return f"""
      <section class="glass-card role-panel">
        <div class="avatar-ring">
          <div class="avatar-core">赵</div>
        </div>
        <div class="role-copy">
          <span class="panel-kicker">REBIRTH RPG OS</span>
          <h1>赵皓阳</h1>
          <p>职业：AI重塑者 / 财富重建中 / 长期主义玩家</p>
        </div>
        <div class="role-stats">
          <div><span>Lv</span><strong>{level}</strong></div>
          <div><span>连续</span><strong>{data["streak"]}天</strong></div>
          <div><span>能量</span><strong>{energy}</strong></div>
          <div><span>财富阶级</span><strong>T{wealth_level}</strong></div>
        </div>
        {render_xp_bar("XP", xp_value, completion["rate"], "xp-glow")}
      </section>
    """


def render_main_quest(data: Dict[str, Any], editable: bool) -> str:
    """主线 Boss 任务。"""
    task = find_task(data, "morning_ai_learning")
    status = get_task_status(data, task["id"])
    return f"""
      <section class="glass-card boss-panel">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">MAIN QUEST</span>
            <h2>今日主线 Boss</h2>
          </div>
          <span class="boss-reward">奖励 +120 XP</span>
        </div>
        {render_task_control(task, status, editable, "boss-card", "+120 XP")}
      </section>
    """


def render_side_quests(data: Dict[str, Any], editable: bool) -> str:
    """支线任务网格。"""
    task_ids = [
        "morning_energy",
        "morning_commute_prepare",
        "day_ai_case",
        "day_viral_video",
        "day_risk_check",
    ]
    cards = [
        render_task_control(find_task(data, task_id), get_task_status(data, task_id), editable, "side-card", "+25 XP")
        for task_id in task_ids
    ]
    return f"""
      <section class="glass-card side-panel">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">SIDE QUESTS</span>
            <h2>支线任务</h2>
          </div>
          <span class="tiny-badge">轻任务 / 防断线</span>
        </div>
        <div class="quest-grid">{''.join(cards)}</div>
      </section>
    """


def render_manifestation_temple(data: Dict[str, Any], editable: bool) -> str:
    """显化修炼神殿。"""
    morning = find_task(data, "morning_manifestation")
    evening = find_task(data, "evening_manifestation_energy")
    return f"""
      <section class="glass-card temple-panel">
        <div class="temple-orb"></div>
        <span class="panel-kicker">MANIFESTATION TEMPLE</span>
        <h2>显化修炼</h2>
        <p class="identity-text">身份声明：正在从低谷里重建秩序的 AI 创造者。不是被过去定义的人，而是把行动写进现实的人。</p>
        <div class="vision-zone">
          <span>视觉化</span>
          <strong>稳定学习 → 写出项目 → 创造价值 → 一点点还给父母</strong>
        </div>
        <div class="affirmation-grid">
          <div>我不再用焦虑证明努力。</div>
          <div>我用每天的行动兑现显化。</div>
          <div>我的能力、作品和现金流正在重建。</div>
        </div>
        <div class="temple-actions">
          {render_task_control(morning, get_task_status(data, morning["id"]), editable, "ritual-card", "+30 XP")}
          {render_task_control(evening, get_task_status(data, evening["id"]), editable, "ritual-card", "+30 XP")}
        </div>
      </section>
    """


def render_ai_academy(data: Dict[str, Any], editable: bool) -> str:
    """AI Academy 面板。"""
    task = find_task(data, "morning_ai_learning")
    status = get_task_status(data, task["id"])
    ai = data["ai"]
    steps = ["课程", "认知", "实操", "输出"]
    flow = "".join(f'<div class="academy-step"><span>{index}</span><strong>{step}</strong></div>' for index, step in enumerate(steps, 1))
    return f"""
      <section class="glass-card academy-panel">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">AI ACADEMY</span>
            <h2>🎓 今日课程</h2>
          </div>
          <div class="teacher-avatar">AI</div>
        </div>
        <div class="course-card">
          <span>Python Day {ai["day"]}</span>
          <h3>{html.escape(short_task_name(task))}</h3>
          <p><strong>今日老师：</strong>{html.escape(ai["teacher"])}</p>
          <p><strong>课程名称：</strong>{html.escape(ai["course_name"])}</p>
          <p>{html.escape(task["task"])}</p>
          <small>{html.escape(task["time"])} / {html.escape(task["duration"])}</small>
        </div>
        <div class="academy-flow">{flow}</div>
        <div class="course-status {'is-done' if status.get('done') else ''}">
          <span>{'已完成课程' if status.get('done') else '等待挑战'}</span>
          <strong>{'+120 XP 已入账' if status.get('done') else '完成主线 Boss 后解锁输出'}</strong>
        </div>
      </section>
    """


def render_reading_tree(data: Dict[str, Any], editable: bool) -> str:
    """阅读成长树。"""
    task = find_task(data, "evening_reading")
    status = get_task_status(data, task["id"])
    chapter = data["reading"]["chapter"]
    levels = []
    for level in range(1, 5):
        unlocked = chapter >= level
        done = status.get("done") and level <= max(1, min(chapter, 4))
        class_name = "book-node"
        if unlocked:
            class_name += " unlocked"
        if done:
            class_name += " read"
        levels.append(
            f"""
            <div class="{class_name}">
              <span>Level {level}</span>
              <strong>{html.escape(data["reading"]["book"])}</strong>
              <small>{'已读节点' if done else ('已解锁' if unlocked else '未解锁')}</small>
            </div>
            """
        )

    return f"""
      <section class="glass-card reading-panel">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">GROWTH MAP</span>
            <h2>阅读成长树</h2>
          </div>
          <span class="tiny-badge">第 {chapter} 章</span>
        </div>
        {render_xp_bar("年度阅读进度", f'《{data["reading"]["book"]}》', data["reading"]["percent"], "reading-glow")}
        <div class="book-map">{''.join(levels)}</div>
        {render_task_control(task, status, editable, "reading-check-card", "+60 XP")}
      </section>
    """


def render_wealth_assets(data: Dict[str, Any], editable: bool) -> str:
    """财富资产系统。"""
    morning = find_task(data, "morning_wealth_action")
    evening = find_task(data, "evening_wealth_review")
    attributes = [
        ("Python", "+1", "skill"),
        ("Prompt", "+1", "mind"),
        ("阅读", "+1", "book"),
        ("AI认知", "+1", "ai"),
    ]
    attribute_cards = "".join(
        f'<div class="asset-stat {kind}"><span>{name}</span><strong>{value}</strong></div>'
        for name, value, kind in attributes
    )
    return f"""
      <section class="glass-card wealth-panel">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">ASSET GROWTH</span>
            <h2>财富资产</h2>
          </div>
          <span class="tiny-badge">成长型资产</span>
        </div>
        <p class="soft-copy">不把压力写成缺口，把今天能增长的资产写进系统。</p>
        <div class="asset-grid">{attribute_cards}</div>
        {render_xp_bar("还款进度", f'{data["money"]["current"]:.0f} / {data["money"]["target"]:.0f} 元', data["money"]["percent"], "wealth-glow")}
        <div class="wealth-actions">
          {render_task_control(morning, get_task_status(data, morning["id"]), editable, "asset-task-card", "+40 XP")}
          {render_task_control(evening, get_task_status(data, evening["id"]), editable, "asset-task-card", "+40 XP")}
        </div>
      </section>
    """


def render_settlement(data: Dict[str, Any], editable: bool) -> str:
    """晚间 RPG 结算面板。"""
    evening_ids = [
        "evening_codex_project",
        "evening_tk_analysis",
        "evening_plan_and_catchup",
        "evening_checkin",
    ]
    cards = [
        render_task_control(find_task(data, task_id), get_task_status(data, task_id), editable, "settle-card", "+45 XP")
        for task_id in evening_ids
    ]
    xp_today = data["completion"]["done_count"] * 30
    return f"""
      <section class="glass-card settlement-panel">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">BATTLE RESULT</span>
            <h2>今日结算</h2>
          </div>
          <span class="boss-reward">{xp_today} XP</span>
        </div>
        <div class="settlement-stats">
          <div><span>今日XP</span><strong>{xp_today}</strong></div>
          <div><span>任务完成</span><strong>{data["completion"]["done_count"]}/{data["completion"]["total"]}</strong></div>
          <div><span>能力增长</span><strong>+4</strong></div>
        </div>
        <div class="boss-summary">
          <span>Boss总结</span>
          <p>今天的胜利不是完美，而是如实记录、继续行动。</p>
        </div>
        <div class="settle-grid">{''.join(cards)}</div>
      </section>
    """


def render_dashboard_html(
    data: Dict[str, Any],
    editable: bool = False,
    saved: bool = False,
    css_href: str = "dashboard.css",
) -> str:
    """生成完整每日监督表格 HTML。"""
    record = data["record"]
    money = data["money"]
    ai = data["ai"]
    reading = data["reading"]
    completion = data["completion"]
    form_start = '<form method="post">' if editable else ""
    form_end = "</form>" if editable else ""
    saved_html = '<div class="notice">已保存今天的打卡记录。</div>' if saved else ""
    level_text = {
        "ai_recovery": "AI恢复日：今天先做基础复习，把断档接上。",
        "lighter": "轻量日：昨天完成率偏低，今天降低难度，先恢复节奏。",
        "upgrade": "升级日：连续打卡不错，今天稍微加一点强度。",
        "normal": "标准日：按计划推进，不求猛，只求稳。",
    }.get(data["dynamic_level"], "标准日：按计划推进。")

    extra_fields = ""
    if editable:
        impulsive_yes = "selected" if record.get("impulsive_spending") else ""
        impulsive_no = "" if record.get("impulsive_spending") else "selected"
        extra_fields = f"""
          <section class="task-card">
            <div class="section-title">
              <div>
                <h2>今日收尾记录</h2>
                <p>记录收入、情绪和风险，给明天留一条清楚的线索。</p>
              </div>
            </div>
            <div class="field-grid">
              <label>
                今日是否有冲动花钱
                <select name="impulsive_spending">
                  <option value="no" {impulsive_no}>没有</option>
                  <option value="yes" {impulsive_yes}>有</option>
                </select>
              </label>
              <label>
                今日收入
                <input type="number" step="0.01" min="0" name="income_today" value="{record.get('income_today', 0)}">
              </label>
              <label>
                情绪评分 1-10
                <input type="number" min="1" max="10" name="mood_score" value="{record.get('mood_score', 7)}">
              </label>
            </div>
            <label class="full-note">
              今日备注
              <textarea name="note" placeholder="今天最值得记录的一句话">{html.escape(str(record.get('note', '')))}</textarea>
            </label>
            <button class="submit-btn" type="submit">保存今日 RPG 进度</button>
          </section>
        """

    left_column = "\n".join(
        [
            render_role_panel(data),
            render_main_quest(data, editable),
            render_side_quests(data, editable),
            render_manifestation_temple(data, editable),
        ]
    )
    right_column = "\n".join(
        [
            render_ai_academy(data, editable),
            render_reading_tree(data, editable),
            render_wealth_assets(data, editable),
            render_settlement(data, editable),
        ]
    )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>赵皓阳 REBIRTH RPG OS</title>
  <link rel="stylesheet" href="{html.escape(css_href)}">
</head>
<body>
  <main class="os-shell">
    <section class="command-hero">
      <div class="hero-copy">
        <span class="system-pill">REBIRTH RPG OS / {html.escape(data["today"])}</span>
        <h1>人生升级控制台</h1>
        <p>{html.escape(data["goal"])}</p>
        <div class="timeline-strip">
          <span>08:00 起床</span>
          <span>10:00 上班</span>
          <span>19:00 下班</span>
          <span>23:30 结算</span>
          <a href="/history">成长记录</a>
          <a href="/night">晚间结算</a>
        </div>
      </div>
      <div class="hero-orbit">
        <span>今日完成率</span>
        <strong>{completion["rate"]}%</strong>
        <small>{completion["done_count"]} / {completion["total"]} QUESTS</small>
      </div>
    </section>

    <section class="system-status">
      <div class="status-chip">{html.escape(level_text)}</div>
      <div class="status-chip">昨天完成率 {data["yesterday_rate"]}%</div>
      <div class="status-chip">连续打卡 {data["streak"]} 天</div>
      <div class="status-chip">Python Day {data["ai"]["day"]}</div>
    </section>

    {saved_html}

    {form_start}
      <section class="dashboard-grid">
        <div class="dashboard-column left-rail">{left_column}</div>
        <div class="dashboard-column right-rail">{right_column}</div>
      </section>
      {extra_fields}
    {form_end}
  </main>
</body>
</html>
"""


def render_growth_history_html(
    data: Dict[str, Any],
    css_href: str = "dashboard.css",
) -> str:
    """生成成长记录页：展示每日记录、周复盘、月复盘。"""
    records = data["records"]
    recent_records = list(reversed(records[-30:]))
    week = data["week"]
    month = data["month"]

    def stat_card(label: str, value: str, tone: str = "") -> str:
        return f"""
          <div class="history-stat {html.escape(tone)}">
            <span>{html.escape(label)}</span>
            <strong>{html.escape(value)}</strong>
          </div>
        """

    def summary_block(title: str, summary: Dict[str, Any]) -> str:
        return f"""
          <section class="glass-card history-summary">
            <div class="panel-head">
              <div>
                <span class="panel-kicker">REVIEW</span>
                <h2>{html.escape(title)}</h2>
              </div>
              <span class="boss-reward">{summary["avg_rate"]}% AVG</span>
            </div>
            <div class="history-stat-grid">
              {stat_card("打卡天数", f'{summary["checkin_days"]} / {summary["days"]}')}
              {stat_card("AI完成", f'{summary["ai_done"]} 天', "cyan")}
              {stat_card("阅读完成", f'{summary["reading_done"]} 天', "green")}
              {stat_card("财富行动", f'{summary["wealth_done"]} 天', "gold")}
              {stat_card("累计收入", f'{summary["income"]} 元', "gold")}
              {stat_card("平均情绪", f'{summary["avg_mood"]} / 10', "purple")}
            </div>
          </section>
        """

    if recent_records:
        record_cards = []
        for item in recent_records:
            notes_html = ""
            if item["task_notes"]:
                notes_html = "".join(
                    f'<li><strong>{html.escape(note["task"])}</strong>：{html.escape(note["note"])}</li>'
                    for note in item["task_notes"][:4]
                )
                notes_html = f'<ul class="history-task-notes">{notes_html}</ul>'

            daily_note = html.escape(item["note"]) if item["note"] else "今天还没有写总备注。"
            record_cards.append(
                f"""
                <article class="history-day-card">
                  <div class="history-day-head">
                    <div>
                      <span>{html.escape(item["date"])}</span>
                      <h3>{item["rate"]}% CLEAR</h3>
                    </div>
                    <strong>{item["done_count"]} / {item["total"]}</strong>
                  </div>
                  <div class="history-tags">
                    <span class="{'is-on' if item['ai_learning'] else ''}">AI</span>
                    <span class="{'is-on' if item['reading'] else ''}">阅读</span>
                    <span class="{'is-on' if item['wealth_action'] else ''}">财富</span>
                    <span class="{'is-on' if item['no_risky_money_behavior'] else ''}">风险安全</span>
                  </div>
                  <div class="meter-track history-meter">
                    <div class="meter-fill" style="width:{item["rate"]}%"></div>
                  </div>
                  <div class="history-mini">
                    <span>情绪 {item["mood_score"]}/10</span>
                    <span>收入 {item["income_today"]} 元</span>
                  </div>
                  <p class="history-note">{daily_note}</p>
                  {notes_html}
                </article>
                """
            )
        records_html = "\n".join(record_cards)
    else:
        records_html = """
          <section class="glass-card history-empty">
            <h2>还没有成长记录</h2>
            <p>完成今天第一次打卡后，这里会自动出现你的成长轨迹。</p>
          </section>
        """

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>赵皓阳 REBIRTH 成长记录</title>
  <link rel="stylesheet" href="{html.escape(css_href)}">
</head>
<body>
  <main class="os-shell history-shell">
    <section class="command-hero history-hero">
      <div class="hero-copy">
        <span class="system-pill">REBIRTH ARCHIVE / {html.escape(data["today"])}</span>
        <h1>成长记录</h1>
        <p>这里不是重新开始。这里保存每天的行动证据，用来做一周复盘、一个月复盘，看见自己真的在变。</p>
        <div class="timeline-strip">
          <a href="/">今日打卡</a>
          <a href="/night">晚间结算</a>
        </div>
      </div>
      <div class="hero-orbit">
        <span>CHECK-IN DAYS</span>
        <strong>{data["total_days"]}</strong>
        <small>连续 {data["streak"]} 天</small>
      </div>
    </section>

    <section class="history-review-grid">
      {summary_block("最近7天复盘", week)}
      {summary_block("最近30天复盘", month)}
    </section>

    <section class="glass-card history-list-card">
      <div class="panel-head">
        <div>
          <span class="panel-kicker">DAILY ARCHIVE</span>
          <h2>每日成长轨迹</h2>
        </div>
        <span class="tiny-badge">最近30天</span>
      </div>
      <div class="history-list">
        {records_html}
      </div>
    </section>
  </main>
</body>
</html>
"""


def save_daily_dashboard(today_text: str | None = None) -> Path:
    """生成 daily_dashboard.html。"""
    data = build_dashboard_data(today_text)
    html_content = render_dashboard_html(data, editable=False, css_href="dashboard.css")
    DASHBOARD_PATH.write_text(html_content, encoding="utf-8")
    return DASHBOARD_PATH


def render_morning_rpg_push(today_text: str | None = None) -> str:
    """生成微信推送用 REBIRTH RPG OS V2 HTML。"""
    data = build_dashboard_data(today_text)
    main_task = find_task(data, "morning_ai_learning")
    energy_task = find_task(data, "morning_energy")
    wealth_task = find_task(data, "morning_wealth_action")
    reading_task = find_task(data, "evening_reading")
    level = max(1, data["streak"] + 1)
    current_xp = data["completion"]["done_count"] * 30
    target_xp = data["completion"]["total"] * 30
    money = data["money"]
    ai = data["ai"]
    reading = data["reading"]

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>REBIRTH RPG OS V2</title>
</head>
<body style="margin:0;padding:0;background:#060814;color:#eef3ff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans SC','Microsoft YaHei',Arial,sans-serif;">
  <div style="max-width:720px;margin:0 auto;padding:18px;background:linear-gradient(160deg,#070914 0%,#111936 48%,#160d2e 100%);">
    <div style="border:1px solid rgba(125,249,255,.22);border-radius:26px;padding:24px;background:linear-gradient(145deg,rgba(255,255,255,.10),rgba(255,255,255,.04));box-shadow:0 20px 60px rgba(0,0,0,.35);">
      <div style="display:inline-block;padding:7px 11px;border:1px solid rgba(125,249,255,.32);border-radius:999px;color:#7df9ff;background:rgba(125,249,255,.08);font-size:12px;font-weight:800;letter-spacing:.08em;">REBIRTH RPG OS V2</div>
      <h1 style="margin:16px 0 8px;font-size:34px;line-height:1.05;color:#fff;">赵皓阳 · 今日人生控制台</h1>
      <p style="margin:0;color:#96a2bf;line-height:1.7;">{html.escape(data["today"])}｜计划第 {data["plan_day"]} 天｜08:00 起床｜10:00 上班｜今天不是打卡，是升级。</p>
    </div>

    <div style="margin-top:14px;display:grid;gap:12px;">
      <div style="border:1px solid rgba(255,211,122,.38);border-radius:24px;padding:18px;background:linear-gradient(135deg,rgba(255,211,122,.14),rgba(255,255,255,.05));">
        <div style="color:#ffd37a;font-size:12px;font-weight:900;letter-spacing:.08em;">① MAIN QUEST</div>
        <h2 style="margin:8px 0 10px;color:#fff;font-size:24px;">今日主线任务</h2>
        <p style="margin:0 0 8px;color:#dbe5ff;line-height:1.65;"><b>主线目标：</b>{html.escape(short_task_name(main_task))}</p>
        <p style="margin:0 0 8px;color:#96a2bf;line-height:1.65;"><b>今日第一步：</b>{html.escape(main_task["task"])}</p>
        <div style="display:inline-block;margin-top:4px;padding:8px 12px;border-radius:999px;background:linear-gradient(135deg,#ffd37a,#ff9f43);color:#201605;font-weight:900;">预计XP +120</div>
      </div>

      <div style="border:1px solid rgba(125,249,255,.22);border-radius:24px;padding:18px;background:rgba(255,255,255,.055);">
        <div style="color:#7df9ff;font-size:12px;font-weight:900;letter-spacing:.08em;">② AI ACADEMY</div>
        <h2 style="margin:8px 0 10px;color:#fff;font-size:24px;">AI Academy</h2>
        <p style="margin:0 0 8px;color:#dbe5ff;line-height:1.65;"><b>今日老师：</b>{html.escape(ai["teacher"])}</p>
        <p style="margin:0 0 8px;color:#dbe5ff;line-height:1.65;"><b>今日课程：</b>{html.escape(ai["course_name"])}｜Python Day {ai["day"]}</p>
        <p style="margin:0 0 8px;color:#96a2bf;line-height:1.65;"><b>今日实操：</b>{html.escape(main_task["task"])}</p>
        <p style="margin:0;color:#63f3a6;line-height:1.65;"><b>课程→行动绑定：</b>学完立刻写一个小例子，并把问题交给 Codex 改进。</p>
      </div>

      <div style="border:1px solid rgba(169,121,255,.34);border-radius:24px;padding:18px;background:linear-gradient(135deg,rgba(111,75,255,.22),rgba(255,255,255,.05));">
        <div style="color:#cbb7ff;font-size:12px;font-weight:900;letter-spacing:.08em;">③ MANIFESTATION</div>
        <h2 style="margin:8px 0 12px;color:#fff;font-size:24px;">显化模块</h2>
        <div style="display:grid;gap:10px;">
          <div style="padding:14px;border-radius:18px;background:rgba(255,255,255,.08);font-size:20px;font-weight:800;color:#fff;">我正在创造1000w人生。</div>
          <div style="padding:14px;border-radius:18px;background:rgba(255,255,255,.08);font-size:20px;font-weight:800;color:#fff;">我会让父母开心。</div>
          <div style="padding:14px;border-radius:18px;background:rgba(255,255,255,.08);font-size:20px;font-weight:800;color:#fff;">我拥有财富、房子、E300L。</div>
        </div>
      </div>

      <div style="border:1px solid rgba(125,249,255,.20);border-radius:24px;padding:18px;background:rgba(255,255,255,.05);">
        <div style="color:#7df9ff;font-size:12px;font-weight:900;letter-spacing:.08em;">④ ENERGY</div>
        <h2 style="margin:8px 0 10px;color:#fff;font-size:24px;">能量提升</h2>
        <p style="margin:0;color:#dbe5ff;line-height:1.65;"><b>晨间启动动作：</b>{html.escape(energy_task["task"])}</p>
      </div>

      <div style="border:1px solid rgba(99,243,166,.24);border-radius:24px;padding:18px;background:rgba(99,243,166,.07);">
        <div style="color:#63f3a6;font-size:12px;font-weight:900;letter-spacing:.08em;">⑤ READING TREE</div>
        <h2 style="margin:8px 0 10px;color:#fff;font-size:24px;">阅读系统</h2>
        <p style="margin:0 0 8px;color:#dbe5ff;line-height:1.65;"><b>今日书籍：</b>《{html.escape(reading["book"])}》</p>
        <p style="margin:0;color:#96a2bf;line-height:1.65;"><b>今日章节：</b>第 {reading["chapter"]} 章｜{html.escape(reading_task["time"])}</p>
      </div>

      <div style="border:1px solid rgba(255,211,122,.24);border-radius:24px;padding:18px;background:rgba(255,211,122,.07);">
        <div style="color:#ffd37a;font-size:12px;font-weight:900;letter-spacing:.08em;">⑥ ASSET GROWTH</div>
        <h2 style="margin:8px 0 10px;color:#fff;font-size:24px;">财富重建</h2>
        <p style="margin:0 0 8px;color:#dbe5ff;line-height:1.65;"><b>今日赚钱动作：</b>{html.escape(wealth_task["task"])}</p>
        <p style="margin:0;color:#96a2bf;line-height:1.65;"><b>当前还款目标：</b>{money["current"]:.0f} / {money["target"]:.0f} 元</p>
      </div>

      <div style="border:1px solid rgba(125,249,255,.22);border-radius:24px;padding:18px;background:rgba(255,255,255,.055);">
        <div style="color:#7df9ff;font-size:12px;font-weight:900;letter-spacing:.08em;">⑦ XP SYSTEM</div>
        <h2 style="margin:8px 0 10px;color:#fff;font-size:24px;">XP系统</h2>
        <p style="margin:0 0 8px;color:#dbe5ff;line-height:1.65;"><b>等级：</b>Lv {level}</p>
        <p style="margin:0 0 10px;color:#dbe5ff;line-height:1.65;"><b>经验值：</b>{current_xp} / {target_xp} XP</p>
        <div style="height:12px;border-radius:999px;background:rgba(255,255,255,.08);overflow:hidden;">
          <div style="height:100%;width:{data["completion"]["rate"]}%;border-radius:999px;background:linear-gradient(90deg,#7df9ff,#a979ff,#ffd37a);"></div>
        </div>
        <p style="margin:10px 0 0;color:#96a2bf;line-height:1.65;"><b>连续天数：</b>{data["streak"]} 天</p>
      </div>
    </div>
  </div>
</body>
</html>"""


def render_morning_push(today_text: str | None = None) -> str:
    """早上推送默认使用 REBIRTH RPG OS V2 HTML。"""
    return render_morning_rpg_push(today_text)


def render_morning_serverchan_push(today_text: str | None = None) -> str:
    """生成 Server酱 微信里稳定显示的 REBIRTH RPG OS V2 文本卡片。"""
    data = build_dashboard_data(today_text)
    main_task = find_task(data, "morning_ai_learning")
    energy_task = find_task(data, "morning_energy")
    wealth_task = find_task(data, "morning_wealth_action")
    reading_task = find_task(data, "evening_reading")
    level = max(1, data["streak"] + 1)
    xp_today = data["completion"]["done_count"] * 30
    money = data["money"]
    ai = data["ai"]
    reading = data["reading"]

    return "\n\n".join(
        [
            "# REBIRTH RPG OS V2｜大怪升级人生控制台",
            "今天按 RPG 主线推进：打怪、拿 XP、升级。",
            f"日期：{data['today']}｜计划第 {data['plan_day']} 天｜Lv {level}｜连续 {data['streak']} 天｜今日XP {xp_today}",
            "## ① 今日主线任务",
            f"主线目标：{short_task_name(main_task)}",
            f"今日第一步：{main_task['task']}",
            "预计XP：+120",
            "## ② AI Academy",
            f"今日老师：{ai['teacher']}",
            f"今日课程：{ai['course_name']}｜Python Day {ai['day']}",
            f"今日实操：{main_task['task']}",
            "课程→行动绑定：学完立刻写一个小例子，并交给 Codex 改进。",
            "## ③ 显化模块",
            "我正在创造1000w人生。",
            "我会让父母开心。",
            "我拥有财富、房子、E300L。",
            "## ④ 能量提升",
            f"晨间启动动作：{energy_task['task']}",
            "## ⑤ 阅读系统",
            f"今日书籍：《{reading['book']}》",
            f"今日章节：第 {reading['chapter']} 章｜{reading_task['time']}",
            "## ⑥ 财富重建",
            f"今日赚钱动作：{wealth_task['task']}",
            f"当前还款目标：{money['current']:.0f} / {money['target']:.0f} 元",
            "## ⑦ XP系统",
            f"等级：Lv {level}",
            f"经验值：{xp_today} XP",
            "打开今天的手机消息，先完成第一步。大怪不是一天打完，是每天削一层血。",
        ]
    )


def get_night_review(record: Dict[str, Any]) -> Dict[str, Any]:
    """读取晚间结算字段，缺失时给默认值。"""
    review = record.get("night_review", {})
    if not isinstance(review, dict):
        review = {}
    return {
        "strongest_action": str(review.get("strongest_action", "")),
        "biggest_blocker": str(review.get("biggest_blocker", "")),
        "most_important_learning": str(review.get("most_important_learning", "")),
        "tomorrow_first_step": str(review.get("tomorrow_first_step", "")),
        "real_feeling": str(review.get("real_feeling", "")),
        "minimum_version_done": bool(review.get("minimum_version_done", False)),
        "self_thanks": str(review.get("self_thanks", "")),
        "reading_pages": str(review.get("reading_pages", "")),
        "reading_insight": str(review.get("reading_insight", "")),
        "ai_cognition": str(review.get("ai_cognition", "")),
        "ai_practice": str(review.get("ai_practice", "")),
        "ai_output": str(review.get("ai_output", "")),
    }


def done_text(done: bool) -> str:
    """把完成状态转成人话。"""
    return "已完成" if done else "未完成"


def render_result_stat(label: str, value: str, tone: str = "") -> str:
    """结算顶部数字卡。"""
    return f"""
      <div class="result-stat {html.escape(tone)}">
        <span>{html.escape(label)}</span>
        <strong>{html.escape(value)}</strong>
      </div>
    """


def render_result_line(label: str, value: str) -> str:
    """结算信息行。"""
    return f"""
      <div class="result-line">
        <span>{html.escape(label)}</span>
        <strong>{html.escape(value)}</strong>
      </div>
    """


def render_night_field(
    label: str,
    name: str,
    value: str,
    editable: bool,
    placeholder: str = "",
) -> str:
    """晚间结算文本字段。"""
    safe_value = html.escape(value)
    if editable:
        control = f'<textarea name="{html.escape(name)}" placeholder="{html.escape(placeholder)}">{safe_value}</textarea>'
    else:
        control = f'<p class="night-answer">{safe_value or "未记录"}</p>'
    return f"""
      <label class="night-field">
        <span>{html.escape(label)}</span>
        {control}
      </label>
    """


def render_night_dashboard_html(
    data: Dict[str, Any],
    editable: bool = False,
    saved: bool = False,
    css_href: str = "dashboard.css",
) -> str:
    """生成手机端晚间 RPG 战斗结算页面。"""
    record = data["record"]
    review = get_night_review(record)
    completion = data["completion"]
    level = max(1, data["streak"] + 1)
    xp_today = completion["done_count"] * 30
    mood_score = int(record.get("mood_score", 7) or 7)
    low_energy = mood_score <= 3

    main_done = bool(record["tasks"]["morning_ai_learning"]["done"])
    side_ids = ["morning_energy", "day_ai_case", "day_viral_video", "day_risk_check"]
    side_done = sum(1 for task_id in side_ids if record["tasks"][task_id]["done"])
    manifestation_done = record.get("manifestation", False)
    wealth_done = record.get("wealth_action", False)
    identity_done = bool(record["tasks"]["morning_manifestation"]["done"])

    ai_task = find_task(data, "morning_ai_learning")
    reading_task = find_task(data, "evening_reading")

    saved_html = '<div class="notice">今晚结算已保存。</div>' if saved else ""
    form_start = '<form method="post">' if editable else ""
    form_end = "</form>" if editable else ""

    mood_control = (
        f'<input type="number" min="1" max="10" name="mood_score" value="{mood_score}">'
        if editable
        else f'<p class="night-answer">{mood_score} / 10</p>'
    )
    minimum_checked = "checked" if review["minimum_version_done"] else ""
    minimum_control = (
        f'<label class="low-check"><input type="checkbox" name="minimum_version_done" {minimum_checked}> 今天完成最低版本了吗？</label>'
        if editable
        else f'<p class="night-answer">{done_text(review["minimum_version_done"])}</p>'
    )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>赵皓阳 REBIRTH RPG OS｜晚间结算</title>
  <link rel="stylesheet" href="{html.escape(css_href)}">
</head>
<body class="night-body">
  <main class="night-shell">
    <section class="night-hero">
      <span class="system-pill">NIGHT SETTLEMENT / 23:30</span>
      <h1>🌙 今日结算</h1>
      <p>{html.escape(data["today"])}｜打完今天这场怪，准备结算升级。</p>
      <div class="night-stats">
        {render_result_stat("等级", f"Lv {level}", "purple")}
        {render_result_stat("今日XP", str(xp_today), "gold")}
        {render_result_stat("连续天数", f'{data["streak"]}天', "cyan")}
      </div>
    </section>

    {saved_html}

    {form_start}
      <section class="night-grid">
        <section class="glass-card battle-card">
          <div class="panel-head">
            <div>
              <span class="panel-kicker">BATTLE RESULT</span>
              <h2>今日战果</h2>
            </div>
            <span class="boss-reward">{completion["rate"]}% CLEAR</span>
          </div>
          <div class="result-board">
            {render_result_line("今日获得XP", f"{xp_today} XP")}
            {render_result_line("今日完成任务数", f'{completion["done_count"]} / {completion["total"]}')}
            {render_result_line("今日主线", done_text(main_done))}
            {render_result_line("今日支线", f"{side_done} / {len(side_ids)}")}
          </div>
        </section>

        <section class="glass-card night-academy-card">
          <span class="panel-kicker">AI ACADEMY REVIEW</span>
          <h2>AI Academy复盘</h2>
          <div class="result-board">
            {render_result_line("今日老师", data["ai"]["teacher"])}
            {render_result_line("今日课程", short_task_name(ai_task))}
            {render_result_line("学习时间", ai_task["time"])}
          </div>
          {render_night_field("今日认知", "ai_cognition", review["ai_cognition"], editable, "今天对AI/Python多理解了什么？")}
          {render_night_field("今日实操", "ai_practice", review["ai_practice"], editable, "今天动手做了什么？")}
          {render_night_field("今日输出成果", "ai_output", review["ai_output"], editable, "产出了代码、笔记、想法还是作品？")}
        </section>

        <section class="glass-card manifestation-review-card">
          <span class="panel-kicker">MANIFESTATION REVIEW</span>
          <h2>显化复盘</h2>
          <div class="result-board">
            {render_result_line("今日视觉化", done_text(manifestation_done))}
            {render_result_line("财富愿景", done_text(wealth_done))}
            {render_result_line("身份声明", done_text(identity_done))}
          </div>
        </section>

        <section class="glass-card reading-review-card">
          <span class="panel-kicker">READING GROWTH</span>
          <h2>阅读复盘</h2>
          <div class="result-board">
            {render_result_line("今天读了什么", f'《{data["reading"]["book"]}》第{data["reading"]["chapter"]}章')}
            {render_result_line("阅读任务", short_task_name(reading_task))}
          </div>
          {render_night_field("页数", "reading_pages", review["reading_pages"], editable, "例如：12页")}
          {render_night_field("一句最重要认知", "reading_insight", review["reading_insight"], editable, "不用漂亮，真实即可。")}
        </section>

        <section class="glass-card asset-review-card">
          <span class="panel-kicker">ABILITY ASSETS</span>
          <h2>能力资产增长</h2>
          <div class="asset-grid">
            <div class="asset-stat"><span>Python</span><strong>+1</strong></div>
            <div class="asset-stat"><span>Prompt</span><strong>+1</strong></div>
            <div class="asset-stat"><span>AI认知</span><strong>+1</strong></div>
            <div class="asset-stat"><span>阅读</span><strong>+1</strong></div>
          </div>
        </section>

        <section class="glass-card boss-review-card">
          <span class="panel-kicker">BOSS SUMMARY</span>
          <h2>Boss战总结</h2>
          {render_night_field("今天最强动作", "strongest_action", review["strongest_action"], editable, "今天哪一个动作最像在升级？")}
          {render_night_field("今天最大卡点", "biggest_blocker", review["biggest_blocker"], editable, "卡在哪里，不解释，不自责。")}
          {render_night_field("今天学到的最重要东西", "most_important_learning", review["most_important_learning"], editable, "一句话就够。")}
          {render_night_field("明天第一步", "tomorrow_first_step", review["tomorrow_first_step"], editable, "明天起床后先做什么？")}
        </section>

        <section class="glass-card emotion-card">
          <span class="panel-kicker">REAL STATUS</span>
          <h2>情绪区</h2>
          <label class="night-field">
            <span>今日状态打分 1-10</span>
            {mood_control}
          </label>
          {render_night_field("今日一句真实感受", "real_feeling", review["real_feeling"], editable, "不要鸡汤。真实即可。")}
        </section>

        <section class="glass-card low-energy-card {'active' if low_energy else ''}">
          <span class="panel-kicker">LOW ENERGY MODE</span>
          <h2>低能量模式</h2>
          <p class="soft-copy">如果今天能量低，只做极简复盘也算结算成功。</p>
          {minimum_control}
          {render_night_field("今天最想感谢自己的1件事", "self_thanks", review["self_thanks"], editable, "哪怕很小也可以。")}
        </section>
      </section>

      {'<button class="submit-btn night-submit" type="submit">完成今晚结算</button>' if editable else ''}
    {form_end}
  </main>
</body>
</html>
"""


def save_night_dashboard(today_text: str | None = None) -> Path:
    """生成 night_dashboard.html。"""
    data = build_dashboard_data(today_text)
    html_content = render_night_dashboard_html(data, editable=False, css_href="dashboard.css")
    NIGHT_DASHBOARD_PATH.write_text(html_content, encoding="utf-8")
    return NIGHT_DASHBOARD_PATH


def render_night_push(today_text: str | None = None) -> str:
    """生成23:30手机推送摘要。"""
    data = build_dashboard_data(today_text)
    config = data["config"]
    completion = data["completion"]
    xp_today = completion["done_count"] * 30
    record = data["record"]
    review = get_night_review(record)
    summary = review["real_feeling"] or "今天打完怪，先结算，不自责。"
    public_url = str(config.get("NIGHT_DASHBOARD_PUBLIC_URL", "")).strip()
    if public_url:
        button = f"[【查看完整结算面板】]({public_url})"
    else:
        button = "【查看完整结算面板】请先配置 config.json 里的 NIGHT_DASHBOARD_PUBLIC_URL。"

    return "\n\n".join(
        [
            "# 🌙 赵皓阳 REBIRTH RPG OS｜23:30战斗结算",
            f"日期：{data['today']}",
            f"今日XP：{xp_today}",
            f"任务完成：{completion['done_count']} / {completion['total']}",
            f"一句总结：{summary}",
            button,
        ]
    )
