# zhaoyang_rebirth_tracker

这是“赵皓阳一年重塑计划”的每日监督系统。

它会每天生成一张深色游戏化的 `REBIRTH RPG OS V2` 人生控制台，让你一眼看清：

- 08:00 起床后早晨要做什么
- 10:00 上班后白天只做哪些轻任务
- 19:00 下班后晚上如何推进项目、阅读和复盘
- 哪些任务完成了，哪些还没完成
- 10w还款目标、AI Academy、显化、阅读和 XP 连续打卡进度

AI Academy 会显示今天的课程老师。默认是 `吴恩达 Andrew Ng`，你可以在 `config.json` 里修改：

```json
"AI_COURSE_TEACHER": "吴恩达 Andrew Ng",
"AI_COURSE_NAME": "AI 与 Python 基础能力课"
```

## 1. 每天固定时间

- 07:30：自动推送 `REBIRTH RPG OS V2` 早晨人生控制台
- 08:00：起床
- 10:00：上班
- 19:00：下班
- 23:30：自动推送晚间RPG结算，并提醒打开结算面板

晚间提醒标题是：

```text
【强提醒】赵皓阳23:30晚间结算
```

如果当天任务还没完成，23:30 提醒里会显示：

```text
今天还没结束，先完成复盘，不要自责，只记录真实情况。
```

## 2. 安装依赖

进入项目目录：

```bash
cd zhaoyang_rebirth_tracker
```

安装依赖：

```bash
pip install -r requirements.txt
```

如果 `pip` 不可用，运行：

```bash
python -m pip install -r requirements.txt
```

## 3. 打开每日监督表格

运行：

```bash
python web_checkin.py
```

然后打开：

```text
http://127.0.0.1:5000
```

页面里会显示：

- 早晨任务表
- 白天轻任务表
- 晚上复盘表
- 财富进度条
- AI学习进度条
- 阅读进度条
- 连续打卡天数
- 今日完成率

你可以逐项勾选完成情况，填写备注、今日收入、情绪评分。提交后会写入 `progress.json`，同时刷新 `daily_dashboard.html`。

## 4. 查看静态监督表格

每天运行早晨推送或打开网页时，项目会生成：

```text
daily_dashboard.html
```

你可以直接双击打开这个文件查看当天表格。

## 5. 启动定时推送

运行：

```bash
python scheduler.py
```

它会按照 `config.json` 的时间自动运行：

```json
"MORNING_PUSH_TIME": "07:30",
"EVENING_PUSH_TIME": "23:30"
```

注意：这个窗口不能关闭，电脑睡眠时也不会运行。

## 6. 设置开机自启

推荐用 Windows 任务计划程序：

1. 打开 Windows 搜索，输入“任务计划程序”。
2. 点击“创建基本任务”。
3. 名称填写：`赵皓阳自动监督推送`。
4. 触发器选择：登录时。
5. 操作选择：启动程序。
6. 程序或脚本填写：

```text
python
```

7. 添加参数填写：

```text
scheduler.py
```

8. 起始于填写你的项目目录，例如：

```text
C:\Users\赵皓阳\Documents\New project 4\zhaoyang_rebirth_tracker
```

保存后，每次电脑登录时会自动启动定时推送。

## 7. 配置 PushPlus

1. 打开 https://www.pushplus.plus/
2. 微信扫码登录。
3. 找到你的 token。
4. 打开 `config.json`。
5. 填写：

```json
"PUSHPLUS_TOKEN": "这里换成你的token"
```

程序会优先使用 PushPlus 推送。

## 8. 配置 Server酱

Server酱 是第二备用通道。

1. 打开 https://sct.ftqq.com/
2. 微信扫码登录。
3. 绑定微信推送通道。
4. 找到 SendKey。
5. 打开 `config.json`。
6. 填写：

```json
"SERVERCHAN_ENABLED": true,
"SERVERCHAN_SENDKEY": "这里换成你的SendKey"
```

如果 PushPlus 失败，程序会自动尝试 Server酱。

## 9. 配置邮箱备用推送

邮箱是最后备用通道。PushPlus 和 Server酱 都失败时，程序会尝试发邮件。

打开 `config.json`，填写：

```json
"EMAIL_ENABLED": true,
"EMAIL_SMTP_HOST": "smtp.qq.com",
"EMAIL_SMTP_PORT": 465,
"EMAIL_USER": "你的邮箱@qq.com",
"EMAIL_PASSWORD": "你的邮箱SMTP授权码",
"EMAIL_TO": "接收提醒的邮箱@qq.com"
```

注意：`EMAIL_PASSWORD` 通常不是邮箱登录密码，而是邮箱设置里生成的 SMTP 授权码。

## 10. 手动推送

早晨 REBIRTH RPG OS V2 控制台：

```bash
python main.py morning
```

晚间复盘表格：

```bash
python main.py evening
```

23:30 晚间 RPG 结算页面：

```bash
python generate_night_dashboard.py
```

生成文件：

```text
night_dashboard.html
```

本地填写晚间结算：

```text
http://127.0.0.1:5000/night
```

这个页面不是工作日报，而是 RPG 战斗结算。它包含：

- 今日XP
- 今日完成任务数
- 主线 / 支线完成状态
- AI Academy复盘
- 显化复盘
- 阅读复盘
- 能力资产增长
- Boss战总结
- 情绪区
- 低能量模式

晚间推送顺序是：

1. Server酱
2. PushPlus备用
3. 邮箱备用

如果你想让手机点击消息后直接打开完整结算面板，需要把 `night_dashboard.html` 放到一个手机能访问的公网地址，然后在 `config.json` 填：

```json
"NIGHT_DASHBOARD_PUBLIC_URL": "https://你的网址/night_dashboard.html"
```

Server酱本身负责推送消息，不负责托管你电脑里的 HTML 文件。没有公网地址时，程序仍会生成本地 `night_dashboard.html`，并推送结算摘要。

查看统计：

```bash
python main.py stats
```

## 11. 每日内容为什么会变化

项目会读取 `task_pool.json`，并根据这些因素调整任务：

- 当前日期
- Python学习第几天
- 阅读第几章
- 昨天完成率
- 当前10w还款进度
- 连续打卡天数
- AI学习是否连续两天未完成

规则示例：

- 昨天完成率低于60%：今天降低难度。
- 连续打卡3天以上：今天稍微升级。
- AI学习连续2天未完成：今天只安排30分钟基础复习。

你可以直接编辑 `task_pool.json`，增加自己的任务文案。

## 12. 如何保证每天早上7:30收到提醒

请确认：

1. `python scheduler.py` 正在运行。
2. 电脑没有关机或睡眠。
3. `config.json` 里 `MORNING_PUSH_TIME` 是 `07:30`。
4. PushPlus、Server酱或邮箱至少有一个配置正确。
5. 网络可以访问对应推送服务。

最稳的做法：用 Windows 任务计划程序设置开机自启，并关闭电脑自动睡眠。

## 13. 电脑关机也能自动推送：GitHub Actions 云端定时

本项目已经内置 GitHub Actions 文件：

```text
.github/workflows/rebirth_scheduler.yml
```

它会在云端自动运行：

- 北京时间每天 07:30：执行 `python main.py morning`
- 北京时间每天 23:30：执行 `python main.py night`

GitHub Actions 使用 UTC 时间，所以配置里写的是：

- 北京时间 07:30 = UTC 23:30
- 北京时间 23:30 = UTC 15:30

### 第一步：把项目上传到 GitHub

1. 打开 https://github.com/
2. 登录账号。
3. 点击右上角 `+`。
4. 选择 `New repository`。
5. 仓库名可以填：

```text
zhaoyang_rebirth_tracker
```

6. 创建仓库。
7. 在电脑项目目录里运行：

```bash
git init
git add .
git commit -m "init rebirth rpg os"
git branch -M main
git remote add origin 你的GitHub仓库地址
git push -u origin main
```

如果你还不熟 Git，也可以先用 GitHub Desktop 上传整个文件夹。

### 第二步：添加 GitHub Secrets

不要把 token 直接写到公开仓库里。请放到 GitHub Secrets。

1. 打开你的 GitHub 仓库。
2. 点击 `Settings`。
3. 点击 `Secrets and variables`。
4. 点击 `Actions`。
5. 点击 `New repository secret`。
6. 添加这两个 secret：

```text
SERVERCHAN_SENDKEY
PUSHPLUS_TOKEN
```

值分别填写你的 Server酱 SendKey 和 PushPlus token。

可选：如果你已经有公网晚间结算页面，也可以添加：

```text
NIGHT_DASHBOARD_PUBLIC_URL
```

### 第三步：启用 Actions

1. 打开仓库顶部的 `Actions`。
2. 如果 GitHub 提示启用 workflow，点击启用。
3. 找到 `Rebirth RPG OS Scheduler`。

### 第四步：手动测试 workflow

1. 进入 `Actions`。
2. 点击 `Rebirth RPG OS Scheduler`。
3. 点击 `Run workflow`。
4. 选择：

```text
morning
```

或者：

```text
night
```

5. 点击绿色按钮运行。
6. 进入运行记录，看是否显示推送成功。

### 为什么电脑关机也能发送

因为 GitHub Actions 是 GitHub 云端服务器在运行：

- 不依赖你的电脑开机
- 不依赖本地 `scheduler.py`
- 不依赖本地浏览器
- 到时间后 GitHub 会自动执行 `python main.py morning` 或 `python main.py night`

只要 GitHub 仓库存在、Actions 开启、Secrets 配置正确，就能自动推送。

### 云端推送顺序

早晨任务卡：

1. Server酱
2. PushPlus
3. 邮箱

晚间结算：

1. Server酱
2. PushPlus
3. 邮箱

如果 Server酱成功，就会直接推送到微信；如果失败，会自动尝试 PushPlus；如果都失败，会在 Actions 日志里打印失败原因。
