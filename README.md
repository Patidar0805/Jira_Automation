# 📊 Jira Activity Tracker → Excel

A lightweight Python automation tool that **automatically tracks your Jira ticket activity and logs it into a monthly Excel sheet** — no manual effort required.

---

## 🚀 What It Does

Every day at **8 PM (via cron job)**, the script connects to your Jira account and:

- ✅ Fetches all tickets **currently assigned to you** + tickets assigned to you **this month**
- ✅ Logs when a **ticket is assigned to you** (with the status at that exact time)
- ✅ Logs only **2 tracked status changes** while the ticket is assigned to you:
  - `To-Do → In Development`
  - `In Development → Code Review`
- ✅ Logs every **comment you added** on the ticket
- ✅ Each activity = **separate row** in Excel (no overwriting, no duplicates)
- ✅ Tickets are **grouped together** with a blank row separator between each group
- ✅ Groups sorted by **earliest activity date (newest first)**, rows within group sorted **ascending**
- ✅ Creates a **new sheet every month** (e.g. `March-2026`, `April-2026`)
- ✅ Creates an **empty sheet** on first run of the month even if no activity found
- ✅ Maintains a **Run Logs sheet** to track every script execution

---

## 📋 Excel Output

One Excel file with a new tab every month:

```
jira_status_log.xlsx
  ├── March-2026
  ├── April-2026
  ├── May-2026 ...
  └── Run Logs      ← script execution history
```

### Columns tracked per activity:

| Column | Description |
|---|---|
| **Ticket** | Jira ticket number (e.g. TSTD-123) |
| **Summary** | Ticket title |
| **Activity** | 👤 Ticket Assigned / 🔄 Status Changed / 💬 Comment Added |
| **Old Status** | Status before the change |
| **New Status** | Status after the change |
| **Comment** | Comment text (only for comment entries) |
| **Done At** | Date & time of the activity (IST) |
| **Updated By** | Name of person who made the change |
| **Priority** | Ticket priority (High / Medium / Low) |

### Row color coding (per ticket group):

| Color | Meaning |
|---|---|
| 🟣 Purple | Ticket assigned to you |
| 🟡 Yellow | To-Do → In Development |
| 🟠 Orange | In Development → Code Review |
| ⚪ Grey | Comment added |

> Each ticket group has its own soft background color to visually separate tickets from each other.

### Run Logs sheet:

| Column | Description |
|---|---|
| Run Date | Date the script ran |
| Run Time | Time the script ran |
| Tickets Found | Number of tickets fetched |
| Total Changes | Number of new entries logged |
| Activity Log | Line-by-line summary of all changes |

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
    "projects":  ["PROJ", "PROJ2"],   # add all your project keys
}
```

> 💡 Your project key is the prefix in ticket numbers — if tickets are `TSTD-101`, key is `TSTD`

### 5. Test it
```bash
python3 jira_tracker.py
```

### 6. Set up auto-run at 8 PM (Linux cron)
```bash
chmod +x run_jira_tracker.sh
crontab -e
```
Add this line (replace with your actual username):
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

> After first run, these will also appear:
> - `jira_status_log.xlsx` — Excel output file
> - `jira_state.json` — Internal state tracker (do not delete)

---

## 🔒 Security Note

Never commit your `api_token` to GitHub. Add this to your `.gitignore`:
```
jira_state.json
jira_status_log.xlsx
.env
```

---

## ❓ Troubleshooting

| Problem | Fix |
|---|---|
| `401 Unauthorized` | Wrong email or API token — regenerate at Jira |
| `400 Bad Request` | Wrong project key in config |
| No entries logged | No tracked transitions found this month |
| Cron not running | Check: `sudo systemctl status cron` |
| Wrong timestamps | Script uses IST (UTC+11:30 offset for your Jira instance) |

---

## 📄 License

Free to use and modify.
