# 🗂️ Jira Status Tracker → Excel (Linux)

Automatically logs your Jira ticket **status changes** and **comments** into a monthly Excel sheet every day at 8 PM using a cron job.

---

## 📁 Project Structure

```
JiraTracker/
 ├── jira_tracker.py         ← Main script
 ├── run_jira_tracker.sh     ← Linux runner (used by cron)
 ├── requirements.txt        ← Python dependencies
 └── README.md               ← This file
```

> After first run, these will also appear:
> - `jira_status_log.xlsx` — your Excel output
> - `jira_state.json` — internal state (do not delete)

---

## ✅ Step 1 — Move Project to Your Home Folder

Open terminal and move the folder:

```bash
mv ~/Downloads/JiraTracker ~/JiraTracker
```

---

## ✅ Step 2 — Open in VS Code

```bash
code ~/JiraTracker
```

Or: VS Code → File → Open Folder → select `JiraTracker`

---

## ✅ Step 3 — Install Dependencies

Open the **VS Code Terminal** (`Ctrl + ~`) and run:

```bash
pip3 install -r requirements.txt
```

---

## ✅ Step 4 — Get Your Jira API Token

1. Go to: https://id.atlassian.com/manage-profile/security/api-tokens
2. Click **"Create API token"**
3. Give it a name like `JiraTracker`
4. Copy the token

---

## ✅ Step 5 — Configure the Script

Open `jira_tracker.py` in VS Code and fill in your details:

```python
JIRA_CONFIG = {
    "base_url":  "https://your-company.atlassian.net",  # ← your Jira URL
    "email":     "you@yourcompany.com",                  # ← your login email
    "api_token": "paste-your-token-here",                # ← token from Step 4
    "project":   "PROJ",                                 # ← your project key (e.g. DEV, QA)
}
```

> 💡 Your project key is the prefix in ticket numbers — if your tickets are `DEV-101`, your key is `DEV`

---

## ✅ Step 6 — Test the Script

In the VS Code Terminal, run:

```bash
python3 jira_tracker.py
```

### Expected output:
```
[2026-03-05 20:00:01] Checking YOUR Jira tickets → Sheet: 'March-2026'
  Found 8 ticket(s) assigned to you.
  ✓ DEV-101: status: To Do → In Progress
  ✓ DEV-105: new comment
  → Saved 2 change(s) to 'jira_status_log.xlsx' → sheet 'March-2026'
```

Open `jira_status_log.xlsx` — you should see your changes logged! ✅

---

## ✅ Step 7 — Set Up Auto Run at 8 PM (Cron Job)

### 7a — Make the shell script executable

```bash
chmod +x ~/JiraTracker/run_jira_tracker.sh
```

### 7b — Open crontab

```bash
crontab -e
```

> First time? It will ask you to choose an editor — pick **nano** (easiest)

### 7c — Add this line at the bottom

```
0 20 * * * /home/YOUR_USERNAME/JiraTracker/run_jira_tracker.sh
```

> ⚠️ Replace `YOUR_USERNAME` with your actual Linux username.
> To find it, run: `whoami`

So if your username is `rahul`, it becomes:
```
0 20 * * * /home/rahul/JiraTracker/run_jira_tracker.sh
```

### 7d — Save and exit

If using nano: press `Ctrl + X` → `Y` → `Enter`

### 7e — Verify cron is set

```bash
crontab -l
```

You should see your line listed. ✅

---

## 📊 Excel Output Structure

One Excel file with a **new sheet every month**:

```
jira_status_log.xlsx
  ├── March-2026
  ├── April-2026
  └── May-2026 ...
```

### Columns logged:

| Column | Description |
|---|---|
| Ticket | Jira ticket number (e.g. DEV-101) |
| Summary | Ticket title |
| Old Status | Status before change |
| New Status | Status after change |
| Changed At | Date & time logged |
| Priority | High / Medium / Low |
| Latest Comment | Most recent comment |

### Row colors by status:
- 🔵 **Blue** → To Do
- 🟡 **Yellow** → In Progress
- 🟠 **Orange** → In Review
- 🟢 **Green** → Done / Closed
- 🔴 **Red** → Blocked

---

## ❓ Troubleshooting

| Problem | Fix |
|---|---|
| `python3: command not found` | Run: `sudo apt install python3` |
| `pip3: command not found` | Run: `sudo apt install python3-pip` |
| `401 Unauthorized` | Wrong email or API token in config |
| `400 Bad Request` | Wrong project key — check your Jira URL |
| Cron not running | Check cron service: `sudo systemctl status cron` |
| No Excel file created | No changes detected since last run (normal) |
| Want to check cron logs | Run: `grep CRON /var/log/syslog` |
