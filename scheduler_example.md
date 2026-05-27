# 自动运行设置示例

这个文件提供三种设置方式。刚开始最推荐用 Windows 任务计划程序。

## 1. Windows 任务计划程序设置方法

适合：自己的电脑每天会开机，想早晚自动推送。

### 早晨行动卡

1. 打开 Windows 搜索，输入“任务计划程序”。
2. 点击右侧“创建基本任务”。
3. 名称填写：`赵皓阳早晨行动卡`。
4. 触发器选择：每天。
5. 时间填写：`07:30`。
6. 操作选择：启动程序。
7. 程序或脚本填写：

```text
python
```

8. 添加参数填写：

```text
main.py morning
```

9. 起始于填写项目目录，例如：

```text
C:\Users\赵皓阳\Documents\New project 4\zhaoyang_rebirth_tracker
```

10. 保存任务。

### 晚间复盘提醒

再创建一个任务：

- 名称：`赵皓阳晚间复盘提醒`
- 时间：`23:30`
- 程序或脚本：`python`
- 添加参数：`main.py evening`
- 起始于：项目目录

### 网页打卡系统

网页打卡需要你手动运行：

```bash
python web_checkin.py
```

然后打开：

```text
http://127.0.0.1:5000
```

如果想让网页也自动启动，可以再建一个任务：

- 名称：`赵皓阳网页打卡系统`
- 触发器：登录时
- 程序或脚本：`python`
- 添加参数：`web_checkin.py`
- 起始于：项目目录

## 2. GitHub Actions 每天自动推送方法

适合：想让云端每天自动推送，不依赖自己电脑。

注意：

- GitHub Actions 可以推送早晚提醒。
- GitHub Actions 不能打开你电脑上的本地网页打卡系统。
- 不要把 PushPlus token 直接写进公开仓库。

### 设置 token

1. 打开 GitHub 仓库。
2. 进入 `Settings`。
3. 进入 `Secrets and variables`。
4. 进入 `Actions`。
5. 新建 secret：

```text
PUSHPLUS_TOKEN
```

值填写你的 PushPlus token。

### 示例 workflow

在仓库中新建文件：

```text
.github/workflows/daily_push.yml
```

内容示例：

```yaml
name: Daily Rebirth Push

on:
  schedule:
    - cron: "30 23 * * *"
    - cron: "30 15 * * *"
  workflow_dispatch:

jobs:
  push:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Put PushPlus token into config
        run: |
          python - <<'PY'
          import json
          from pathlib import Path
          path = Path("config.json")
          data = json.loads(path.read_text(encoding="utf-8"))
          data["PUSHPLUS_TOKEN"] = "${{ secrets.PUSHPLUS_TOKEN }}"
          path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
          PY

      - name: Morning push
        if: github.event.schedule == '30 23 * * *'
        run: python main.py morning

      - name: Evening push
        if: github.event.schedule == '30 15 * * *'
        run: python main.py evening
```

这里使用的是 UTC 时间：

- 北京时间 07:30 = UTC 23:30
- 北京时间 23:30 = UTC 15:30

## 3. 本地长期运行方法

适合：电脑会一直开着，想用一个窗口长期负责早晚提醒。

先安装依赖：

```bash
pip install -r requirements.txt
```

然后运行：

```bash
python main.py scheduler
```

它会根据 `config.json` 里的时间自动推送：

```json
"MORNING_PUSH_TIME": "07:30",
"EVENING_PUSH_TIME": "23:30"
```

注意：

- 这个窗口不能关闭。
- 电脑睡眠时不会运行。
- 如果想稳定一些，建议使用 Windows 任务计划程序。
