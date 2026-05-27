"""
赵皓阳一年重塑计划 - 定时推送脚本

运行：
python scheduler.py

默认时间：
07:30 发送 REBIRTH RPG OS V2 早晨控制台
23:30 发送晚间RPG结算
"""

from __future__ import annotations

import time

try:
    import schedule
except ImportError:
    print("缺少 schedule 依赖，暂时无法启动定时推送。")
    print("请在项目目录运行：pip install -r requirements.txt")
    raise SystemExit(1)

from main import load_config, push_evening, push_morning


def main() -> None:
    config = load_config()
    morning_time = config.get("MORNING_PUSH_TIME", "07:30")
    evening_time = config.get("EVENING_PUSH_TIME", "23:30")

    schedule.every().day.at(morning_time).do(push_morning)
    schedule.every().day.at(evening_time).do(push_evening)

    print("定时推送已启动。")
    print(f"每天 {morning_time} 推送 REBIRTH RPG OS V2 早晨控制台。")
    print(f"每天 {evening_time} 推送晚间RPG结算。")
    print("请保持这个窗口不要关闭。按 Ctrl + C 可以停止。")

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
