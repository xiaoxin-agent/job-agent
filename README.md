# 🤖 Job Agent — AI 求职助手

AI 驱动的求职全流程管理工具：职位搜索、匹配分析、简历优化、求职信生成、申请跟踪。

## 功能一览

### 🔍 职位搜索与采集
- 从 Google Careers / LinkedIn / Indeed 等 URL 抓取职位详情
- 基于关键词和地点批量搜索
- 自动分析职位要求与技能匹配度

### 📊 匹配度分析
- 根据用户技能画像自动计算匹配百分比
- 技能差距分析（Skill Gap），提示待提升方向
- 学习计划生成，含推荐课程和资料链接
- 学习日历导出（iCal 格式），可导入 Google Calendar

### 📝 简历管理
- 上传 / 预览 / 下载 / 删除简历
- 简历与职位关联
- 针对特定职位优化简历（Tailor Resume）
- 简历 PDF 导出
- 多语言支持：中文 / English / Français

### ✉️ 求职信
- 一键生成针对性求职信（Cover Letter）
- 保存、查看、下载

### 🎯 申请跟踪
- 查看历史申请记录
- 分析申请方式（邮箱 / 官网 / LinkedIn Easy Apply）
- 状态看板：Saved → Applied → Interviewing → Offer

### 🧠 知识测验
- 根据学习计划自动生成测验题目（Quiz）
- 选择题 + 问答题，检验学习成果

### 🌐 多语言界面
- 支持 **中文 / English / Français**
- URL 参数 `?lang=zh-CN` 或右上角下拉切换
- 浏览器语言自动检测（Accept-Language header）
- 所有页面导航链接携带语言参数，切换页面不丢失
- 拓展语言只需在 `LANGUAGES` 字典和 `lang_labels` 字典增添条目

---

## 快速开始

### 依赖
- Python 3.8+
- 无需额外包（纯标准库）

### 启动

```bash
cd /path/to/job-agent
python3 job_agent_web.py
```

服务默认运行在 **http://localhost:9999**

### 管理脚本

```bash
bash agent_ctl.sh start      # 启动
bash agent_ctl.sh stop       # 停止
bash agent_ctl.sh restart    # 重启
bash agent_ctl.sh status     # 查看状态
bash agent_ctl.sh test       # 运行测试
bash agent_ctl.sh watchdog   # 检查/重启（适用于 cron）
```

### 看门狗（可选）

把 `watchdog.sh` 加入 crontab 每分钟检查一次，崩溃自动重启：

```cron
* * * * * /path/to/job-agent/watchdog.sh
```

---

## 配置 AI

AI 对话功能使用 **DeepSeek API**。

### 方式一：环境变量（推荐）

```bash
export DEEPSEEK_API_KEY="sk-your-api-key-here"
```

### 方式二：配置文件

在 `agent_data/settings.json` 中配置：

```json
{
  "providers": {
    "deepseek": {
      "apiKey": "sk-your-api-key-here"
    }
  }
}
```

### 使用场景

AI 参与以下功能的生成与分析：

| 功能 | 说明 |
|------|------|
| 简历优化（Tailor） | 针对职位要求调整简历内容 |
| 求职信生成 | 自动撰写 Cover Letter |
| 技能差距分析 | 检测缺失技能并评分 |
| 学习计划 | 生成课程推荐和学习路线 |
| 知识测验 | 根据学习计划生成 Quiz |
| 职位分析 | 从 URL 抓取并解析职位详情 |

---

## 用户画像

默认画像（`agent_data/user_profile.json`）包含技能、经验年限、偏好地点等，可在页面 `/profile` 编辑，或直接修改 JSON 文件。

画像字段：

```json
{
  "name": "",
  "title": "Cloud/AI/Linux Engineer",
  "skills": {
    "Cloud": { "keywords": [...], "level": "expert", "years": 5 },
    "Linux": { "keywords": [...], "level": "expert", "years": 5 },
    ...
  },
  "experience_years": 5,
  "preferred_locations": ["Toronto", "Vancouver", ...],
  "salary_expectation": { "min": 130000, "max": 250000, "currency": "CAD" }
}
```

---

## 项目结构

```
job-agent/
├── agent_ctl.sh          # 管理脚本（start/stop/restart/status）
├── watchdog.sh           # 看门狗脚本（cron 用）
├── job_agent_web.py      # Web 服务器 + 前端页面（~4790 行）
├── job_agent_core.py     # 核心逻辑：搜索、匹配、画像（~1840 行）
├── job_agent_apply.py    # 申请分析与管理（~243 行）
├── tests.py              # 测试套件（~1400 行）
├── agent_data/           # 运行时数据
│   ├── user_profile.json # 用户画像
│   ├── tracked_jobs.json # 跟踪的职位
│   └── settings.json     # 设置（含 API Key）
├── static/               # 静态资源（logo SVG 等）
└── sites/                # 职位网站解析器
```

---

## 国际化

添加新语言步骤：

1. 在 `job_agent_web.py` 的 `LANGUAGES` 字典新增语言条目
2. 在相同文件的 `lang_labels` 字典添加语言选项
3. 重启服务，右上角下拉框自动出现新语言选项

---

## License

MIT
