const MERIT_ITEMS = [
  ["filial_peace", "孝顺父母 / 让父母安心"],
  ["ai_learning", "完成AI学习"],
  ["main_quest", "完成主线任务"],
  ["controlled_spending", "控制冲动消费"],
  ["reading_growth", "阅读成长"],
  ["energy_exercise", "运动 / 能量提升"],
  ["gentle_speech", "说话温和"],
  ["help_others", "帮助别人"],
  ["review_improve", "复盘改过"],
];

const FAULT_ITEMS = [
  ["delay_escape", "拖延逃避"],
  ["impulsive_spending", "冲动消费"],
  ["quick_comeback", "想快速翻盘"],
  ["emotional_outburst", "情绪失控"],
  ["impatient_parents", "对父母不耐烦"],
  ["stay_up_late", "熬夜伤身"],
  ["money_link", "点开赚钱诱惑链接"],
  ["complain_fate", "怨天尤人"],
  ["miss_minimum", "没有完成最低版本"],
];

function todayInBeijing() {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day}`;
}

function githubConfig() {
  return {
    token: process.env.PROGRESS_GITHUB_TOKEN || process.env.GH_TOKEN || "",
    repo: process.env.PROGRESS_REPO || process.env.GITHUB_REPO || "",
    branch: process.env.PROGRESS_BRANCH || "main",
    filePath: process.env.PROGRESS_FILE || "progress.json",
  };
}

function emptyMeritTable() {
  return {
    merits: Object.fromEntries(MERIT_ITEMS.map(([id]) => [id, false])),
    faults: Object.fromEntries(FAULT_ITEMS.map(([id]) => [id, false])),
    improvement_needed: "",
    tomorrow_fix: "",
  };
}

function normalizeRecord(record = {}) {
  const meritTable = emptyMeritTable();
  const rawMerits = record.merit_table?.merits || {};
  const rawFaults = record.merit_table?.faults || {};

  for (const [id] of MERIT_ITEMS) meritTable.merits[id] = Boolean(rawMerits[id]);
  for (const [id] of FAULT_ITEMS) meritTable.faults[id] = Boolean(rawFaults[id]);
  meritTable.improvement_needed = String(record.merit_table?.improvement_needed || "");
  meritTable.tomorrow_fix = String(record.merit_table?.tomorrow_fix || "");

  return {
    ...record,
    mood_score: Number(record.mood_score || 7),
    income_today: Number(record.income_today || 0),
    night_review: {
      ai_cognition: "",
      ai_practice: "",
      ai_output: "",
      reading_pages: "",
      reading_insight: "",
      strongest_action: "",
      biggest_blocker: "",
      most_important_learning: "",
      tomorrow_first_step: "",
      real_feeling: "",
      minimum_version_done: false,
      self_thanks: "",
      ...(record.night_review || {}),
    },
    merit_table: meritTable,
  };
}

function meritStats(record) {
  const table = normalizeRecord(record).merit_table;
  const meritCount = Object.values(table.merits).filter(Boolean).length;
  const faultCount = Object.values(table.faults).filter(Boolean).length;
  return { merit_count: meritCount, fault_count: faultCount, net: meritCount - faultCount };
}

function cumulativeMerit(progress) {
  return Object.values(progress || {}).reduce((total, record) => {
    if (!record || typeof record !== "object") return total;
    return total + meritStats(record).net;
  }, 0);
}

function completionStats(record) {
  const tasks = record.tasks || {};
  const values = Object.values(tasks);
  const total = values.length || 15;
  const done = values.filter((task) => task && task.done).length;
  const merit = meritStats(record);
  return {
    done_count: done,
    total,
    rate: total ? Math.round((done / total) * 100) : 0,
    xp_today: done * 30 + (merit.net > 0 ? 20 : 0),
    merit_xp_bonus: merit.net > 0 ? 20 : 0,
  };
}

async function readProgress() {
  const cfg = githubConfig();
  if (!cfg.token || !cfg.repo) {
    throw new Error("缺少 Vercel 环境变量：PROGRESS_GITHUB_TOKEN 和 PROGRESS_REPO");
  }

  const url = `https://api.github.com/repos/${cfg.repo}/contents/${cfg.filePath}?ref=${cfg.branch}`;
  const response = await fetch(url, {
    headers: {
      Authorization: `Bearer ${cfg.token}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "rebirth-rpg-os",
    },
  });

  if (response.status === 404) return { progress: {}, sha: null, cfg };
  if (!response.ok) throw new Error(`读取 progress.json 失败：GitHub ${response.status}`);

  const file = await response.json();
  const content = Buffer.from(String(file.content || "").replace(/\n/g, ""), "base64").toString("utf8");
  return { progress: content.trim() ? JSON.parse(content) : {}, sha: file.sha, cfg };
}

async function writeProgress(progress, sha, cfg, dateText) {
  const url = `https://api.github.com/repos/${cfg.repo}/contents/${cfg.filePath}`;
  const body = {
    message: `Cloud mobile review ${dateText}`,
    branch: cfg.branch,
    content: Buffer.from(JSON.stringify(progress, null, 2), "utf8").toString("base64"),
  };
  if (sha) body.sha = sha;

  const response = await fetch(url, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${cfg.token}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "Content-Type": "application/json",
      "User-Agent": "rebirth-rpg-os",
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`写入 progress.json 失败：GitHub ${response.status} ${text}`);
  }
  return response.json();
}

function updateRecord(record, input) {
  const next = normalizeRecord(record);
  const review = next.night_review;
  const fields = [
    "ai_cognition", "ai_practice", "ai_output", "reading_pages", "reading_insight",
    "strongest_action", "biggest_blocker", "most_important_learning", "tomorrow_first_step",
    "real_feeling", "self_thanks",
  ];
  for (const field of fields) review[field] = String(input[field] || "").trim();
  review.minimum_version_done = Boolean(input.minimum_version_done);
  next.mood_score = Math.max(1, Math.min(10, Number(input.mood_score || 7)));

  const table = emptyMeritTable();
  const merits = input.merits || {};
  const faults = input.faults || {};
  for (const [id] of MERIT_ITEMS) table.merits[id] = Boolean(merits[id]);
  for (const [id] of FAULT_ITEMS) table.faults[id] = Boolean(faults[id]);
  table.improvement_needed = String(input.improvement_needed || "").trim();
  table.tomorrow_fix = String(input.tomorrow_fix || "").trim();
  next.merit_table = table;
  return next;
}

export default async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");

  try {
    const dateText = todayInBeijing();
    const { progress, sha, cfg } = await readProgress();

    if (req.method === "GET") {
      const record = normalizeRecord(progress[dateText] || {});
      const merit = meritStats(record);
      return res.status(200).json({
        ok: true,
        date: dateText,
        record,
        merit: { ...merit, cumulative_net: cumulativeMerit(progress), xp_bonus: merit.net > 0 ? 20 : 0 },
        completion: completionStats(record),
        meritItems: MERIT_ITEMS,
        faultItems: FAULT_ITEMS,
      });
    }

    if (req.method === "POST") {
      const record = updateRecord(progress[dateText] || {}, req.body || {});
      progress[dateText] = record;
      await writeProgress(progress, sha, cfg, dateText);
      const merit = meritStats(record);
      return res.status(200).json({
        ok: true,
        date: dateText,
        record,
        merit: { ...merit, cumulative_net: cumulativeMerit(progress), xp_bonus: merit.net > 0 ? 20 : 0 },
        completion: completionStats(record),
      });
    }

    res.setHeader("Allow", "GET, POST");
    return res.status(405).json({ ok: false, error: "Method not allowed" });
  } catch (error) {
    return res.status(500).json({ ok: false, error: error instanceof Error ? error.message : String(error) });
  }
}
