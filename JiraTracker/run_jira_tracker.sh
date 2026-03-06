#!/bin/bash
# ─────────────────────────────────────────────
# Jira Tracker - Linux Runner
# Used by cron to auto-run at 8 PM daily
# ─────────────────────────────────────────────

# Update this path to where you saved this project
cd /home/{path}/JiraTracker

# Run the script
python3 jira_tracker.py

# Optional: save logs to file (uncomment below)
# python3 jira_tracker.py >> /home/$(whoami)/JiraTracker/run_log.txt 2>&1
