"""
赵皓阳一年重塑计划 - 自动行动卡与推送脚本

这个文件负责：
1. 生成每天早上的行动卡
2. 保存每天的行动卡日志
3. 通过 PushPlus 推送到微信
4. 统计 progress.json 里的打卡进度
5. 可选：长期运行，按配置时间自动推送
"""

from __future__ import annotations

import argparse
import os
import json
import smtplib
import sys
import time
from datetime import date, datetime, timedelta, timezone
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, Tuple

from dashboard import (
    render_morning_push,
    render_morning_serverchan_push,
    render_night_push,
    save_daily_dashboard,
    save_night_dashboard,
)

try:
    import requests
except ImportError:
    requests = None

try:
    import schedule
except ImportError:
    schedule = None


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
PROGRESS_PATH = BASE_DIR / "progress.json"
LOGS_DIR = BASE_DIR / "logs"
LOCAL_TZ = timezone(timedelta(hours=8))


def make_console_utf8() -> None:
    """尽量让 Windows 控制台正确显示中文和表情。"""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass


make_console_utf8()


PYTHON_TASKS = {
    1: {
        "title": "安装环境与 print()",
        "detail": "任务：安装 Python，打开命令行，运行第一个 print('Hello, rebirth!')。",
    },
    2: {
        "title": "变量",
        "detail": "任务：学习变量，把姓名、目标金额、今日心情分别保存到变量里并打印出来。",
    },
    3: {
        "title": "input",
        "detail": "任务：学习 input()，写一个小程序，让用户输入今天收入并打印鼓励语。",
    },
    4: {
        "title": "if 判断",
        "detail": "任务：学习 if / else，判断今天是否完成 AI 学习，并输出不同提醒。",
    },
    5: {
        "title": "循环",
        "detail": "任务：学习 for 循环，连续打印 5 条今日肯定语。",
    },
}


def load_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    """读取 JSON 文件；如果文件不存在或内容损坏，给出清楚提示。"""
    if not path.exists():
        print(f"找不到文件：{path}")
        print("请确认项目文件完整，或重新创建这个文件。")
        return default

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"文件格式错误：{path}")
        print("请检查这个 JSON 文件里是否少了逗号、引号或大括号。")
        return default


def save_json(path: Path, data: Dict[str, Any]) -> None:
    """用漂亮的格式保存 JSON，方便小白直接打开查看。"""
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_config() -> Dict[str, Any]:
    """读取 config.json，并补齐缺失字段。"""
    default_config = {
        "PUSHPLUS_TOKEN": "",
        "TARGET_MONEY": 100000,
        "CURRENT_MONEY": 0,
        "BOOK_NAME": "终身成长",
        "BOOK_CHAPTER": 1,
        "PYTHON_DAY": 1,
        "AI_COURSE_TEACHER": "吴恩达 Andrew Ng",
        "AI_COURSE_NAME": "AI 与 Python 基础能力课",
        "START_DATE": "2026-05-25",
        "MORNING_PUSH_TIME": "07:30",
        "EVENING_PUSH_TIME": "23:30",
        "SERVERCHAN_ENABLED": False,
        "SERVERCHAN_SENDKEY": "",
        "EMAIL_ENABLED": False,
        "EMAIL_SMTP_HOST": "smtp.qq.com",
        "EMAIL_SMTP_PORT": 465,
        "EMAIL_USER": "",
        "EMAIL_PASSWORD": "",
        "EMAIL_TO": "",
    }
    config = load_json(CONFIG_PATH, default_config)

    for key, value in default_config.items():
        config.setdefault(key, value)

    # GitHub Actions 会把 Secrets 放进环境变量；这里优先使用环境变量，
    # 这样 token 不需要写死在仓库文件里。
    env_keys = [
        "SERVERCHAN_SENDKEY",
        "PUSHPLUS_TOKEN",
        "NIGHT_DASHBOARD_PUBLIC_URL",
        "MOBILE_REVIEW_PUBLIC_URL",
        "EMAIL_ENABLED",
        "EMAIL_SMTP_HOST",
        "EMAIL_SMTP_PORT",
        "EMAIL_USER",
        "EMAIL_PASSWORD",
        "EMAIL_TO",
    ]
    for key in env_keys:
        env_value = os.environ.get(key)
        if env_value not in (None, ""):
            config[key] = env_value

    if config.get("SERVERCHAN_SENDKEY"):
        config["SERVERCHAN_ENABLED"] = True

    return config


def get_today() -> str:
    """返回北京时间日期，例如：2026-05-25。"""
    return datetime.now(LOCAL_TZ).date().isoformat()


def get_current_stage(config: Dict[str, Any], today_text: str) -> str:
    """根据 START_DATE 粗略判断当前阶段。"""
    try:
        start = datetime.strptime(config["START_DATE"], "%Y-%m-%d").date()
        today_date = datetime.strptime(today_text, "%Y-%m-%d").date()
    except (KeyError, ValueError):
        return "起步阶段（请检查 config.json 里的 START_DATE）"

    day_number = max((today_date - start).days + 1, 1)

    if day_number <= 30:
        return f"第 {day_number} 天：基础重建期"
    if day_number <= 90:
        return f"第 {day_number} 天：能力积累期"
    if day_number <= 180:
        return f"第 {day_number} 天：作品与收入探索期"
    if day_number <= 365:
        return f"第 {day_number} 天：稳定变现与还款期"
    return f"第 {day_number} 天：长期复利期"


def get_python_task(day: int) -> Dict[str, str]:
    """根据 PYTHON_DAY 生成当天 Python 学习任务。"""
    if day in PYTHON_TASKS:
        return PYTHON_TASKS[day]

    extended_tasks = [
        "复习变量、input、if、循环，并写一个 20 行以内的小程序。",
        "学习列表 list，记录今天的 3 个行动。",
        "学习字典 dict，保存今日收入、心情分、阅读状态。",
        "学习函数 def，把重复代码整理成一个函数。",
        "做一个小项目：每日收入记录器。",
        "做一个小项目：读书打卡记录器。",
        "做一个小项目：复盘问题生成器。",
    ]
    task = extended_tasks[(day - 6) % len(extended_tasks)]
    return {
        "title": f"扩展练习 {day}",
        "detail": f"任务：{task}",
    }


def save_daily_log(today_text: str, content: str) -> Path:
    """把每天的行动卡保存到 logs/YYYY-MM-DD.md。"""
    LOGS_DIR.mkdir(exist_ok=True)
    log_path = LOGS_DIR / f"{today_text}.md"
    log_path.write_text(content, encoding="utf-8")
    return log_path


def send_pushplus(title: str, content: str) -> Tuple[bool, str]:
    """使用 PushPlus 推送 HTML 内容到微信。"""
    if requests is None:
        return False, "缺少 requests 依赖，请在项目目录运行：pip install -r requirements.txt"

    config = load_config()
    token = str(config.get("PUSHPLUS_TOKEN", "")).strip()

    if not token:
        return False, "PushPlus token 为空，请打开 config.json 填写 PUSHPLUS_TOKEN。"

    payload = {
        "token": token,
        "title": title,
        "content": content,
        "template": "html",
    }

    try:
        response = requests.post(
            "https://www.pushplus.plus/send",
            json=payload,
            timeout=15,
        )
    except requests.RequestException as error:
        return False, f"PushPlus 请求失败，请检查网络。错误信息：{error}"

    if response.status_code != 200:
        return False, f"PushPlus 返回异常状态码：{response.status_code}，返回内容：{response.text}"

    try:
        result = response.json()
    except ValueError:
        return False, f"PushPlus 返回内容不是 JSON：{response.text}"

    if result.get("code") == 200:
        return True, "PushPlus 推送成功。"

    return False, f"PushPlus 推送失败，请检查 token 是否正确。返回信息：{result}"


def send_serverchan(title: str, content: str) -> Tuple[bool, str]:
    """使用 Server酱 推送内容到微信。"""
    if requests is None:
        return False, "缺少 requests 依赖，请在项目目录运行：pip install -r requirements.txt"

    config = load_config()
    enabled = bool(config.get("SERVERCHAN_ENABLED", False))
    sendkey = str(config.get("SERVERCHAN_SENDKEY", "")).strip()

    if not enabled:
        return False, "Server酱 未启用，请把 config.json 里的 SERVERCHAN_ENABLED 改为 true。"

    if not sendkey:
        return False, "Server酱 sendkey 为空，请打开 config.json 填写 SERVERCHAN_SENDKEY。"

    api_url = f"https://sctapi.ftqq.com/{sendkey}.send"
    payload = {
        "title": title,
        "desp": content,
    }

    try:
        response = requests.post(api_url, data=payload, timeout=15)
    except requests.RequestException as error:
        return False, f"Server酱 请求失败，请检查网络。错误信息：{error}"

    if response.status_code != 200:
        return False, f"Server酱 返回异常状态码：{response.status_code}，返回内容：{response.text}"

    try:
        result = response.json()
    except ValueError:
        return False, f"Server酱 返回内容不是 JSON：{response.text}"

    if result.get("code") in (0, 200):
        return True, "Server酱 推送成功。"

    return False, f"Server酱 推送失败，请检查 sendkey 是否正确。返回信息：{result}"


def send_email(title: str, content: str) -> Tuple[bool, str]:
    """使用邮箱作为最后备用推送通道。"""
    config = load_config()
    enabled = bool(config.get("EMAIL_ENABLED", False))

    if not enabled:
        return False, "邮箱推送未启用，请把 config.json 里的 EMAIL_ENABLED 改为 true。"

    smtp_host = str(config.get("EMAIL_SMTP_HOST", "")).strip()
    smtp_port = int(config.get("EMAIL_SMTP_PORT", 465) or 465)
    email_user = str(config.get("EMAIL_USER", "")).strip()
    email_password = str(config.get("EMAIL_PASSWORD", "")).strip()
    email_to = str(config.get("EMAIL_TO", "")).strip()

    missing = []
    if not smtp_host:
        missing.append("EMAIL_SMTP_HOST")
    if not email_user:
        missing.append("EMAIL_USER")
    if not email_password:
        missing.append("EMAIL_PASSWORD")
    if not email_to:
        missing.append("EMAIL_TO")
    if missing:
        return False, f"邮箱配置不完整，请检查 config.json：{', '.join(missing)}"

    message = MIMEText(content, "plain", "utf-8")
    message["Subject"] = title
    message["From"] = email_user
    message["To"] = email_to

    try:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20) as server:
            server.login(email_user, email_password)
            server.sendmail(email_user, [email_to], message.as_string())
    except Exception as error:
        return False, f"邮箱推送失败，请检查邮箱SMTP配置或网络。错误信息：{error}"

    return True, "邮箱推送成功。"


def send_notification(title: str, content: str, serverchan_content: str | None = None) -> bool:
    """统一推送入口：Server酱优先，失败后尝试 PushPlus，再失败就尝试邮箱。"""
    serverchan_ok, serverchan_message = send_serverchan(title, serverchan_content or content)
    print(serverchan_message)
    if serverchan_ok:
        return True

    print("Server酱失败，正在尝试备用通道：PushPlus。")
    pushplus_ok, pushplus_message = send_pushplus(title, content)
    print(pushplus_message)
    if pushplus_ok:
        return True

    print("正在尝试最后备用通道：邮箱。")
    email_ok, email_message = send_email(title, content)
    print(email_message)
    if email_ok:
        return True

    print("三个推送通道都失败了。日志已经保存，你可以稍后重试。")
    print(f"Server酱 失败原因：{serverchan_message}")
    print(f"PushPlus 失败原因：{pushplus_message}")
    print(f"邮箱失败原因：{email_message}")
    return False


def send_night_notification(title: str, content: str) -> bool:
    """晚间结算推送：Server酱优先，PushPlus备用，邮箱兜底。"""
    serverchan_ok, serverchan_message = send_serverchan(title, content)
    print(serverchan_message)
    if serverchan_ok:
        return True

    print("Server酱失败，正在尝试备用通道：PushPlus。")
    pushplus_ok, pushplus_message = send_pushplus(title, content)
    print(pushplus_message)
    if pushplus_ok:
        return True

    print("PushPlus失败，正在尝试最后备用通道：邮箱。")
    email_ok, email_message = send_email(title, content)
    print(email_message)
    if email_ok:
        return True

    print("三个推送通道都失败了。晚间结算页面已经保存，你可以稍后重试。")
    print(f"Server酱失败原因：{serverchan_message}")
    print(f"PushPlus失败原因：{pushplus_message}")
    print(f"邮箱失败原因：{email_message}")
    return False


def push_morning() -> None:
    """生成并推送早晨行动卡。"""
    today_text = get_today()
    card = render_morning_push(today_text)
    serverchan_card = render_morning_serverchan_push(today_text)
    log_path = save_daily_log(today_text, card)
    dashboard_path = save_daily_dashboard(today_text)
    print(f"REBIRTH RPG OS V2 已保存：{log_path}")
    print(f"每日 RPG 控制台已生成：{dashboard_path}")
    print("推送版本：REBIRTH RPG OS V2｜大怪升级人生控制台")
    send_notification("【强提醒】REBIRTH RPG OS V2｜赵皓阳大怪升级", card, serverchan_card)


def push_evening() -> None:
    """生成并推送23:30晚间RPG结算。"""
    today_text = get_today()
    review = render_night_push(today_text)
    save_daily_dashboard(today_text)
    night_path = save_night_dashboard(today_text)
    print(f"晚间结算页面已生成：{night_path}")
    send_night_notification("【强提醒】赵皓阳23:30晚间结算", review)


def push_night() -> None:
    """GitHub Actions 和本地都可以调用的晚间结算入口。"""
    push_evening()


def calculate_stats() -> Dict[str, Any]:
    """统计 progress.json 中的打卡数据。"""
    config = load_config()
    progress = load_json(PROGRESS_PATH, {})

    total_days = len(progress)
    today_date = datetime.now(LOCAL_TZ).date()
    streak = 0

    while True:
        check_date = (today_date - timedelta(days=streak)).isoformat()
        if check_date not in progress:
            break
        streak += 1

    def completion_rate(field_name: str) -> float:
        if total_days == 0:
            return 0.0
        done_days = sum(1 for item in progress.values() if item.get(field_name) is True)
        return round(done_days / total_days * 100, 2)

    income_from_progress = sum(
        float(item.get("income_today", 0) or 0)
        for item in progress.values()
    )
    current_money = float(config.get("CURRENT_MONEY", 0) or 0) + income_from_progress
    target_money = float(config.get("TARGET_MONEY", 100000) or 100000)

    return {
        "已执行天数": total_days,
        "连续打卡天数": streak,
        "AI学习完成率": f"{completion_rate('ai_learning')}%",
        "阅读完成率": f"{completion_rate('reading')}%",
        "财富行动完成率": f"{completion_rate('wealth_action')}%",
        "当前赚了多少钱": round(current_money, 2),
        "距离10w还差多少钱": round(max(target_money - current_money, 0), 2),
    }


def print_stats() -> None:
    """在命令行打印统计结果。"""
    stats = calculate_stats()
    print("赵皓阳一年重塑计划 - 当前统计")
    for key, value in stats.items():
        print(f"{key}：{value}")


def run_scheduler_forever() -> None:
    """本地长期运行：到了配置时间自动推送。"""
    if schedule is None:
        print("缺少 schedule 依赖，暂时无法启动本地长期运行。")
        print("请在项目目录运行：pip install -r requirements.txt")
        return

    config = load_config()
    morning_time = config.get("MORNING_PUSH_TIME", "07:30")
    evening_time = config.get("EVENING_PUSH_TIME", "23:30")

    schedule.every().day.at(morning_time).do(push_morning)
    schedule.every().day.at(evening_time).do(push_evening)

    print(f"已启动自动推送：早晨 {morning_time}，晚上 {evening_time}")
    print("请保持这个窗口不要关闭。按 Ctrl + C 可以停止。")

    while True:
        schedule.run_pending()
        time.sleep(30)


def main() -> None:
    parser = argparse.ArgumentParser(description="赵皓阳一年重塑计划自动化工具")
    parser.add_argument(
        "action",
        nargs="?",
        default="morning",
        choices=["morning", "evening", "night", "stats", "scheduler"],
        help="morning=早晨行动卡，night=晚间结算，evening=night别名，stats=查看统计，scheduler=本地长期运行",
    )
    args = parser.parse_args()

    if args.action == "morning":
        push_morning()
    elif args.action == "evening":
        push_evening()
    elif args.action == "night":
        push_night()
    elif args.action == "stats":
        print_stats()
    elif args.action == "scheduler":
        run_scheduler_forever()


if __name__ == "__main__":
    main()
