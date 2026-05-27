"""
赵皓阳一年重塑计划 - 本地网页打卡系统

运行方式：
python web_checkin.py

然后在浏览器打开：
http://127.0.0.1:5000
"""

from __future__ import annotations

import json
import sys
from datetime import date
from typing import Any, Dict

try:
    from flask import Flask, redirect, request, url_for
except ImportError:
    print("缺少 flask 依赖，暂时无法启动网页打卡系统。")
    print("请在项目目录运行：pip install -r requirements.txt")
    raise SystemExit(1)

from dashboard import (
    PROGRESS_PATH,
    build_dashboard_data,
    get_all_task_ids,
    get_night_review,
    normalize_record,
    render_dashboard_html,
    render_night_dashboard_html,
    save_daily_dashboard,
    save_night_dashboard,
    update_summary_fields,
    write_json,
)
from main import load_json


def make_console_utf8() -> None:
    """尽量让 Windows 控制台正确显示中文提示。"""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass


make_console_utf8()


app = Flask(__name__)


def today_text() -> str:
    """返回今天日期。"""
    return date.today().isoformat()


def parse_float(value: str | None, default: float = 0) -> float:
    """把网页表单里的数字转成 float；填错时用默认值。"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_int(value: str | None, default: int = 7) -> int:
    """把网页表单里的数字转成 int，并限制在 1-10。"""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(number, 10))


@app.route("/", methods=["GET", "POST"])
def index():
    today = today_text()
    progress = load_json(PROGRESS_PATH, {})

    if request.method == "POST":
        record = normalize_record(progress.get(today, {}))

        for task_id in get_all_task_ids():
            record["tasks"][task_id] = {
                "done": request.form.get(f"task_done_{task_id}") == "on",
                "note": request.form.get(f"task_note_{task_id}", "").strip(),
            }

        impulsive_spending = request.form.get("impulsive_spending") == "yes"
        record["impulsive_spending"] = impulsive_spending
        record["mood_score"] = parse_int(request.form.get("mood_score"), 7)
        record["income_today"] = parse_float(request.form.get("income_today"), 0)
        record["note"] = request.form.get("note", "").strip()
        update_summary_fields(record)

        progress[today] = record
        write_json(PROGRESS_PATH, progress)
        save_daily_dashboard(today)
        return redirect(url_for("index", saved="1"))

    data = build_dashboard_data(today)
    html = render_dashboard_html(
        data,
        editable=True,
        saved=request.args.get("saved") == "1",
        css_href="/dashboard.css",
    )
    return html


@app.route("/night", methods=["GET", "POST"])
def night():
    today = today_text()
    progress = load_json(PROGRESS_PATH, {})

    if request.method == "POST":
        record = normalize_record(progress.get(today, {}))
        review = get_night_review(record)
        review["strongest_action"] = request.form.get("strongest_action", "").strip()
        review["biggest_blocker"] = request.form.get("biggest_blocker", "").strip()
        review["most_important_learning"] = request.form.get("most_important_learning", "").strip()
        review["tomorrow_first_step"] = request.form.get("tomorrow_first_step", "").strip()
        review["real_feeling"] = request.form.get("real_feeling", "").strip()
        review["minimum_version_done"] = request.form.get("minimum_version_done") == "on"
        review["self_thanks"] = request.form.get("self_thanks", "").strip()
        review["reading_pages"] = request.form.get("reading_pages", "").strip()
        review["reading_insight"] = request.form.get("reading_insight", "").strip()
        review["ai_cognition"] = request.form.get("ai_cognition", "").strip()
        review["ai_practice"] = request.form.get("ai_practice", "").strip()
        review["ai_output"] = request.form.get("ai_output", "").strip()
        record["night_review"] = review
        record["mood_score"] = parse_int(request.form.get("mood_score"), record.get("mood_score", 7))

        progress[today] = record
        write_json(PROGRESS_PATH, progress)
        save_night_dashboard(today)
        return redirect(url_for("night", saved="1"))

    data = build_dashboard_data(today)
    html = render_night_dashboard_html(
        data,
        editable=True,
        saved=request.args.get("saved") == "1",
        css_href="/dashboard.css",
    )
    return html


@app.route("/dashboard.css")
def dashboard_css():
    css_path = PROGRESS_PATH.parent / "dashboard.css"
    return css_path.read_text(encoding="utf-8"), 200, {"Content-Type": "text/css; charset=utf-8"}


if __name__ == "__main__":
    if not PROGRESS_PATH.exists():
        PROGRESS_PATH.write_text(json.dumps({}, ensure_ascii=False), encoding="utf-8")

    save_daily_dashboard(today_text())
    save_night_dashboard(today_text())
    print("本地网页每日监督表格已启动。")
    print("请打开：http://127.0.0.1:5000")
    print("晚间结算：http://127.0.0.1:5000/night")
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
