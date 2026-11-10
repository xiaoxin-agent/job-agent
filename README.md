# 🤖 Job Agent — AI Job Search Assistant

**English** | [中文](README.zh-CN.md)

An AI-powered, end-to-end job search management tool: job discovery, match analysis, resume optimization, cover letter generation, and application tracking.

## Features

### 🔍 Job Search & Import
- Extract job details from URLs such as Google Careers / LinkedIn / Indeed
- Batch search by keywords and location
- Automatic analysis of job requirements and skill match

### 📊 Match Analysis
- Automatically calculates a match percentage against your skill profile
- Skill gap analysis highlighting areas to improve
- Learning plan generation with recommended courses and resource links
- Learning calendar export (iCal), importable into Google Calendar

### 📝 Resume Management
- Upload / preview / download / delete resumes
- Link resumes to specific jobs
- Tailor a resume to a specific job posting (Tailor Resume)
- Resume PDF export
- Multi-language support: 中文 / English / Français

### ✉️ Cover Letters
- One-click generation of a targeted cover letter
- Save, view, and download

### 🎯 Application Tracking
- Review your application history
- Analyze application channels (email / company site / LinkedIn Easy Apply)
- Status board: Saved → Applied → Interviewing → Offer

### 🧠 Knowledge Quizzes
- Automatically generates quiz questions from your learning plan
- Multiple-choice plus free-response questions to verify learning

### 🌐 Multilingual UI
- Supports **中文 / English / Français**
- Switch via the URL parameter `?lang=zh-CN` or the dropdown in the top-right corner
- Automatic browser language detection (`Accept-Language` header)
- Every navigation link carries the language parameter, so switching pages does not lose your selection
- Adding a language only requires new entries in the `LANGUAGES` and `lang_labels` dictionaries

---

## Quick Start

### Requirements
- Python 3.8+
- No extra packages (standard library only)

### Run

```bash
cd /path/to/job-agent
python3 job_agent_web.py
```

The service listens on **http://localhost:9999** by default.

### Management Script

```bash
bash agent_ctl.sh start      # start
bash agent_ctl.sh stop       # stop
bash agent_ctl.sh restart    # restart
bash agent_ctl.sh status     # check status
bash agent_ctl.sh test       # run tests
bash agent_ctl.sh watchdog   # check / restart (suitable for cron)
```

### Watchdog (optional)

Add `watchdog.sh` to crontab to check every minute and restart on failure:

```cron
* * * * * /path/to/job-agent/watchdog.sh
```

---

## Configuring AI

AI chat features use the **DeepSeek API**.

API key resolution order (first match wins):

1. **Environment variable** `DEEPSEEK_API_KEY`
2. **Config file** `providers.deepseek.apiKey` in `~/.openclaw/agents/main/agent/models.json`

> ⚠️ **Note**: `agent_data/settings.json` is **not read by the code** (legacy from older docs, deprecated).

### Option 1: Environment variable

```bash
export DEEPSEEK_API_KEY="sk-you…here"
```

Suitable when starting the service manually from a terminal. **Note**: processes restarted automatically by cron / watchdog **do not inherit** variables `export`ed in your shell, so this approach is unreliable for unattended restarts.

### Option 2: Config file (recommended, restart-safe)

Add the following to `~/.openclaw/agents/main/agent/models.json`:

```json
{
  "providers": {
    "deepseek": {
      "apiKey": "sk-you…here"
    }
  }
}
```

> 🔒 This file lives **outside** the workspace repository and is never committed to Git.
> Never write the key into any file under `job-agent/`.

### Where AI Is Used

AI participates in generating and analyzing the following:

| Feature | Description |
|---------|-------------|
| Resume tailoring | Adjusts resume content to the job requirements |
| Cover letter generation | Writes a cover letter automatically |
| Skill gap analysis | Detects missing skills and scores them |
| Learning plan | Generates course recommendations and a learning path |
| Knowledge quiz | Builds a quiz from the learning plan |
| Job analysis | Fetches and parses job details from a URL |

---

## User Profile

The default profile (`agent_data/user_profile.json`) holds skills, years of experience, preferred locations, and more. Edit it on the `/profile` page or modify the JSON file directly.

Profile fields:

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

## Project Structure

```
job-agent/
├── agent_ctl.sh          # management script (start/stop/restart/status)
├── watchdog.sh           # watchdog script (for cron)
├── job_agent_web.py      # web server + frontend pages (~4790 lines)
├── job_agent_core.py     # core logic: search, matching, profile (~1840 lines)
├── job_agent_apply.py    # application analysis and management (~243 lines)
├── tests.py              # test suite (~1400 lines)
├── agent_data/           # runtime data (already in .gitignore)
│   ├── user_profile.json # user profile
│   ├── tracked_jobs.json # tracked jobs
│   └── resumes/          # resume files and associations
├── static/               # static assets (logo SVG, etc.)
└── sites/                # job site parsers
```

> The API key is not in the repository — see "Configuring AI" above.

---

## Internationalization

Steps to add a new language:

1. Add a language entry to the `LANGUAGES` dictionary in `job_agent_web.py`
2. Add the language option to the `lang_labels` dictionary in the same file
3. Restart the service; the dropdown in the top-right corner picks up the new language automatically

---

## License

MIT
