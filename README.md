# 📊 Jira Activity Tracker → Excel

A lightweight Python automation tool that **automatically tracks your Jira ticket activity and logs it into a monthly Excel sheet** — no manual effort required.

---

## 🚀 What It Does

Every day at **8 PM (via cron job)**, the script connects to your Jira account and:

- ✅ Fetches all tickets **currently assigned to you**
- ✅ Logs when a **ticket is assigned to you** (with status at that time)
- ✅ Logs every **status change** made while the ticket is assigned to you
- ✅ Logs every **comment you added** on the ticket
- ✅ Each activity = **separate row** in Excel (no overwriting, no duplicates)
- ✅ Creates a **new sheet every month** (e.g. `March-2026`, `April-2026`)
- ✅ Creates an **empty sheet** on first run of the month even if no activity found

---

## 📋 Excel Output

One Excel file with a new tab every month:

```
jira_status_log.xlsx
  ├── March-2026
  ├── April-2026
  └── May-2026 ...
```

### Columns tracked per activity:

| Column | Description |
|---|---|
| **Ticket** | Jira ticket number (e.g. TSTD-123) |
| **Summary** | Ticket title |
| **Activity** | 👤 Ticket Assigned / 🔄 Status Changed / 💬 Comment Added |
| **Old Status** | Status before the change |
| **New Status** | Status after the change |
| **Comment** | Comment text (if activity is a comment) |
| **Updated By** | Name of person who made the change |
| **Done At** | Date & time of the activity (IST) |
| **Priority** | Ticket priority (High / Medium / Low) |

### Row color coding:
| Color | Status |
|---|---|
| 🟣 Purple | Ticket assigned to you |
| 🔵 Blue | To Do |
| 🟡 Yellow | In Progress / In Development |
| 🟠 Orange | Code Review / In Review |
| 🟢 Green | Done / Closed |
| 🔴 Red | Blocked |
| ⚪ Grey | Comment added |

---

## 🛠️ Tech Stack

- **Python 3**
- **Jira REST API v3** (Changelog + Comments endpoints)
- **openpyxl** — Excel generation and formatting
- **requests** — HTTP calls to Jira
- **cron** — Linux task scheduler for auto-run at 8 PM

---

## ⚙️ Setup

### 1. Clone the repo
```bash
git clone https://github.com/your-username/JiraTracker.git
cd JiraTracker
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Get your Jira API Token
Go to: https://id.atlassian.com/manage-profile/security/api-tokens → Create token

### 4. Configure the script
Edit `jira_tracker.py` and fill in your details:
```python
JIRA_CONFIG = {
    "base_url":  "https://your-company.atlassian.net",
    "email":     "you@yourcompany.com",
    "api_token": "your-api-token-here",
    "project":   "PROJ",
}
```

### 5. Test it
```bash
python3 jira_tracker.py
```

### 6. Set up auto-run at 8 PM (Linux cron)
```bash
chmod +x run_jira_tracker.sh
crontab -e
```
Add this line:
```
0 20 * * * /home/your-username/JiraTracker/run_jira_tracker.sh
```

---

## 📁 Project Structure

```
JiraTracker/
 ├── jira_tracker.py         ← Main script
 ├── run_jira_tracker.sh     ← Cron runner (Linux)
 ├── requirements.txt        ← Python dependencies
 └── README.md               ← Documentation
```

> After first run:
> - `jira_status_log.xlsx` — Excel output file
> - `jira_state.json` — Internal state tracker (do not delete)

---

## 🔒 Security Note

Never commit your `api_token` to GitHub. Use a `.env` file or environment variables for production use. Add this to your `.gitignore`:
```
jira_state.json
jira_status_log.xlsx
.env
```

---

## 📄 License

MIT License — free to use and modify.
