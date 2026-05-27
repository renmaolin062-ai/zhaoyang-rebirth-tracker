"""
生成晚间 RPG 结算页面。

运行：
python generate_night_dashboard.py
"""

from __future__ import annotations

from dashboard import save_night_dashboard


if __name__ == "__main__":
    path = save_night_dashboard()
    print(f"晚间结算页面已生成：{path}")
