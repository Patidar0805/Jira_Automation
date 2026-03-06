"""
Jira Status Tracker → Excel (Changelog Edition)
- Tracks ALL activity on tickets while assigned to YOU
- Each status change and comment = separate row in Excel
- Uses Jira Changelog API to capture every individual change
- Runs daily at 8 PM via cron, but logs everything that happened during the day
"""

import requests
import json
import os
from datetime import datetime, timezone, timedelta
from requests.auth import HTTPBasicAuth
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

#  CONFIG — Fill in your details here
JIRA_CONFIG = {
    "base_url":  "",   # e.g. https://mycompany.atlassian.net
    "email":     "",               # Your Jira login email
    "api_token": "",                  # https://id.atlassian.com/manage-profile/security/api-tokens
    "project":   "",                                 # Your Jira project key e.g. DEV, PROJ
}

OUTPUT_FILE = "jira_status_log.xlsx"
STATE_FILE  = "jira_state.json"


#  JIRA API
def auth():
    cfg = JIRA_CONFIG
    return HTTPBasicAuth(cfg["email"], cfg["api_token"])

def get_my_account_id():
    url = f"{JIRA_CONFIG['base_url']}/rest/api/3/myself"
    resp = requests.get(url, auth=auth())
    resp.raise_for_status()
    return resp.json()["accountId"]

def fetch_my_issues(account_id):
    url = f"{JIRA_CONFIG['base_url']}/rest/api/3/search/jql"
    jql = f"project = {JIRA_CONFIG['project']} AND assignee = \"{account_id}\" ORDER BY updated DESC"
    params = {
        "jql": jql,
        "fields": "summary,status,assignee,priority,comment",
        "maxResults": 200
    }
    resp = requests.get(url, auth=auth(), params=params)
    resp.raise_for_status()
    return resp.json().get("issues", [])

def fetch_changelog(issue_key):
    url = f"{JIRA_CONFIG['base_url']}/rest/api/3/issue/{issue_key}/changelog"
    all_entries = []
    start = 0
    while True:
        resp = requests.get(url, auth=auth(), params={"startAt": start, "maxResults": 100})
        resp.raise_for_status()
        data   = resp.json()
        values = data.get("values", [])
        all_entries.extend(values)
        if start + len(values) >= data.get("total", 0):
            break
        start += len(values)
    return all_entries

def fetch_comments(issue_key):
    url  = f"{JIRA_CONFIG['base_url']}/rest/api/3/issue/{issue_key}/comment"
    resp = requests.get(url, auth=auth(), params={"maxResults": 200})
    resp.raise_for_status()
    return resp.json().get("comments", [])

def extract_comment_text(body):
    if isinstance(body, str):
        return body
    text_parts = []
    for block in body.get("content", []):
        for inline in block.get("content", []):
            if inline.get("type") == "text":
                text_parts.append(inline.get("text", ""))
    return " ".join(text_parts).strip()


#  ASSIGNMENT WINDOWS
def get_my_assignment_windows(changelog, my_account_id):
    windows     = []
    assigned_at = None
    for entry in sorted(changelog, key=lambda x: x["created"]):
        for item in entry.get("items", []):
            if item["field"] == "assignee":
                to_id   = item.get("to")
                from_id = item.get("from")
                if to_id == my_account_id:
                    assigned_at = entry["created"]
                elif from_id == my_account_id and assigned_at:
                    windows.append((assigned_at, entry["created"]))
                    assigned_at = None
    if assigned_at:
        windows.append((assigned_at, None))
    return windows

def was_assigned_to_me(timestamp, windows):
    for (start, end) in windows:
        if end is None:
            if timestamp >= start:
                return True
        else:
            if start <= timestamp <= end:
                return True
    return False


#  STATE
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


#  EXCEL

HEADERS = ["Ticket", "Summary", "Activity", "Old Status", "New Status", "Comment", "Updated By", "Done At", "Priority"]

STATUS_COLORS = {
    "To Do":          "D0E8FF",
    "In Progress":    "FFF4CC",
    "In Development": "FFE8B0",
    "Code Review":    "FFD6CC",
    "In Review":      "FFD6CC",
    "Done":           "D4EDDA",
    "Closed":         "C8E6C9",
    "Blocked":        "FFD6D6",
    "comment":        "F0F0F0",
    "assigned":       "E8D5F5",   # ★ purple for ticket assigned to me
    "default":        "FFFFFF",
}

def get_month_sheet_name():
    return datetime.now().strftime("%B-%Y")

def style_header_row(ws):
    col_widths = [14, 38, 18, 18, 18, 45, 22, 22, 12]
    hfill = PatternFill("solid", start_color="1F4E79")
    hfont = Font(bold=True, color="FFFFFF", name="Arial", size=11)
    for i, (h, w) in enumerate(zip(HEADERS, col_widths), start=1):
        cell = ws.cell(row=1, column=i, value=h)
        cell.font      = hfont
        cell.fill      = hfill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[1].height = 24
    ws.freeze_panes = "A2"

def get_or_create_month_sheet(wb, sheet_name):
    if sheet_name in wb.sheetnames:
        return wb[sheet_name]
    ws = wb.create_sheet(title=sheet_name)
    style_header_row(ws)
    return ws

def load_or_create_workbook():
    if os.path.exists(OUTPUT_FILE):
        return load_workbook(OUTPUT_FILE)
    wb = Workbook()
    wb.remove(wb.active)
    return wb

def append_row(ws, row_data, color_key="default"):
    next_row = ws.max_row + 1
    fill_clr = STATUS_COLORS.get(color_key, STATUS_COLORS["default"])
    row_fill = PatternFill("solid", start_color=fill_clr)
    border   = Border(
        bottom=Side(style="thin", color="DDDDDD"),
        right=Side(style="thin",  color="DDDDDD")
    )
    for col, value in enumerate(row_data, start=1):
        cell = ws.cell(row=next_row, column=col, value=value)
        cell.font      = Font(name="Arial", size=10)
        cell.fill      = row_fill
        cell.alignment = Alignment(vertical="center", wrap_text=(col == 6))
        cell.border    = border
    ws.row_dimensions[next_row].height = 20


#  MAIN SYNC
def sync():
    now        = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet_name = get_month_sheet_name()
    print(f"\n[{now}] Syncing YOUR Jira activity → Sheet: '{sheet_name}'")

    state        = load_state()
    wb           = load_or_create_workbook()
    ws           = get_or_create_month_sheet(wb, sheet_name)
    my_id        = get_my_account_id()
    issues       = fetch_my_issues(my_id)
    total_logged = 0

    print(f"  Found {len(issues)} ticket(s) assigned to you.")

    for issue in issues:
        key      = issue["key"]
        fields   = issue["fields"]
        summary  = fields.get("summary", "")
        priority = (fields.get("priority") or {}).get("name", "")

        logged_ids = set(state.get(key, {}).get("logged_ids", []))
        changelog  = fetch_changelog(key)
        windows    = get_my_assignment_windows(changelog, my_id)

        if not windows:
            windows = [("1970-01-01T00:00:00.000+0000", None)]

        # ── ASSIGNMENT + STATUS CHANGES ─────────────
        for entry in changelog:
            entry_id   = entry["id"]
            timestamp  = entry["created"]
            updated_by = entry.get("author", {}).get("displayName", "Unknown")

            if entry_id in logged_ids:
                continue

            for item in entry.get("items", []):

                # ★ Log when ticket was assigned to me (any status)
                if item["field"] == "assignee" and item.get("to") == my_id:
                    utc_time = datetime.strptime(timestamp[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
                    done_at = (utc_time + timedelta(hours=11, minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
                    # Find the status AT THE TIME of assignment from changelog history
                    status_at_assignment = "—"
                    for prev_entry in sorted(changelog, key=lambda x: x["created"]):
                        if prev_entry["created"] > timestamp:
                            break
                        for prev_item in prev_entry.get("items", []):
                            if prev_item["field"] == "status":
                                status_at_assignment = prev_item.get("toString", "—")
                    # If no prior status change found, use the fromString of first status change
                    if status_at_assignment == "—":
                        for prev_entry in sorted(changelog, key=lambda x: x["created"]):
                            for prev_item in prev_entry.get("items", []):
                                if prev_item["field"] == "status":
                                    status_at_assignment = prev_item.get("fromString", "—")
                                    break
                            if status_at_assignment != "—":
                                break

                    row = [
                        key, summary,
                        "👤 Ticket Assigned to Me",
                        "—", status_at_assignment,
                        "",
                        updated_by,
                        done_at, priority
                    ]
                    append_row(ws, row, color_key="assigned")
                    logged_ids.add(entry_id)
                    total_logged += 1
                    print(f"  ✓ {key}: assigned to me by {updated_by} at {done_at} (status: {status_at_assignment})")

                # ★ Log status changes while assigned to me
                elif item["field"] == "status" and was_assigned_to_me(timestamp, windows):
                    old_status = item.get("fromString", "—")
                    new_status = item.get("toString", "—")
                    utc_time = datetime.strptime(timestamp[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
                    done_at = (utc_time + timedelta(hours=11, minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
                    row = [
                        key, summary,
                        "🔄 Status Changed",
                        old_status, new_status,
                        "",
                        updated_by,
                        done_at, priority
                    ]
                    append_row(ws, row, color_key=new_status)
                    logged_ids.add(entry_id)
                    total_logged += 1
                    print(f"  ✓ {key}: {old_status} → {new_status} by {updated_by} at {done_at}")

        # ── COMMENTS ────────────────────────────────
        comments = fetch_comments(key)
        for comment in comments:
            comment_id = comment["id"]
            timestamp  = comment["created"]
            author_id  = comment.get("author", {}).get("accountId", "")
            # ★ Get the name of person who added the comment
            updated_by = comment.get("author", {}).get("displayName", "Unknown")

            if comment_id in logged_ids:
                continue
            if author_id != my_id:
                continue
            if not was_assigned_to_me(timestamp, windows):
                continue

            text    = extract_comment_text(comment.get("body", {}))
            utc_time = datetime.strptime(timestamp[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
            done_at = (utc_time + timedelta(hours=11, minutes=30)).strftime("%Y-%m-%d %H:%M:%S")

            row = [
                key, summary,
                "💬 Comment Added",
                "", "",
                text,
                updated_by,   # ★ who added the comment
                done_at, priority
            ]
            append_row(ws, row, color_key="comment")
            logged_ids.add(comment_id)
            total_logged += 1
            print(f"  ✓ {key}: comment by {updated_by} at {done_at}")

        if key not in state:
            state[key] = {}
        state[key]["logged_ids"] = list(logged_ids)

    sheet_is_new = ws.max_row == 1
    if total_logged:
        wb.save(OUTPUT_FILE)
        print(f"\n  → Saved {total_logged} new entries to '{OUTPUT_FILE}' → sheet '{sheet_name}'")
    elif sheet_is_new:
        wb.save(OUTPUT_FILE)
        print(f"\n  → No activity found. Empty sheet '{sheet_name}' created in '{OUTPUT_FILE}'")
    else:
        print("\n  → No new activity found.")

    save_state(state)

if __name__ == "__main__":
    sync()
