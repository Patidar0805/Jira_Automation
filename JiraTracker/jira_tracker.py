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

# ─────────────────────────────────────────────
#  CONFIG — Fill in your details here
# ─────────────────────────────────────────────
JIRA_CONFIG = {
    "base_url":  "",   # e.g. https://mycompany.atlassian.net
    "email":     "",               # Your Jira login email
    "api_token": "",                  # https://id.atlassian.com/manage-profile/security/api-tokens
    "projects":   [],                            
# ─────────────────────────────────────────────
#  JIRA API
# ─────────────────────────────────────────────
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
    projects_jql = ", ".join(JIRA_CONFIG["projects"])
    jql = f"project in ({projects_jql}) AND assignee = \"{account_id}\" ORDER BY updated DESC"
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

# ─────────────────────────────────────────────
#  ASSIGNMENT WINDOWS
# ─────────────────────────────────────────────
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

# ─────────────────────────────────────────────
#  STATE
# ─────────────────────────────────────────────
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

# ─────────────────────────────────────────────
#  EXCEL
# ─────────────────────────────────────────────
HEADERS = ["Ticket", "Summary", "Activity", "Old Status", "New Status", "Comment", "Updated By", "Done At", "Priority"]

STATUS_COLORS = {
    "To Do":          "4A90D9",  # Bold Blue
    "In Progress":    "F5A623",  # Bold Orange
    "In Development": "E67E22",  # Dark Orange
    "Code Review":    "8E44AD",  # Bold Purple
    "In Review":      "9B59B6",  # Medium Purple
    "Done":           "27AE60",  # Bold Green
    "Closed":         "1E8449",  # Dark Green
    "Blocked":        "E74C3C",  # Bold Red
    "comment":        "95A5A6",  # Medium Grey
    "assigned":       "2980B9",  # Strong Blue
    "default":        "FFFFFF",  # White
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

def sort_sheet(ws):
    """Sort all data rows by Ticket (col 1) then Done At (col 8)."""
    data = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if any(cell is not None for cell in row):
            data.append(list(row))

    # Sort by ticket number then by date
    data.sort(key=lambda x: (str(x[0] or ""), str(x[7] or "")), reverse=True)

    # Clear existing data rows
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.value = None

    # Rewrite sorted rows with formatting
    for i, row_data in enumerate(data, start=2):
        color_key = "default"
        activity = row_data[2] or ""
        new_status = row_data[4] or ""
        if "Assigned" in activity:
            color_key = "assigned"
        elif "Comment" in activity:
            color_key = "comment"
        else:
            color_key = new_status

        fill_clr = STATUS_COLORS.get(color_key, STATUS_COLORS["default"])
        row_fill = PatternFill("solid", start_color=fill_clr)
        border   = Border(
            bottom=Side(style="thin", color="DDDDDD"),
            right=Side(style="thin",  color="DDDDDD")
        )
        for col, value in enumerate(row_data, start=1):
            cell = ws.cell(row=i, column=col, value=value)
            cell.font      = Font(name="Arial", size=10)
            cell.fill      = row_fill
            cell.alignment = Alignment(vertical="center", wrap_text=(col == 6))
            cell.border    = border
        ws.row_dimensions[i].height = 20

def update_run_log(wb, total_logged, log_entries):
    """Maintain a 'Run Logs' sheet with every script execution."""
    log_sheet_name = "Run Logs"
    if log_sheet_name in wb.sheetnames:
        wl = wb[log_sheet_name]
    else:
        wl = wb.create_sheet(title=log_sheet_name)
        # Header row
        log_headers = ["Run Date", "Run Time", "Tickets Found", "Total Changes", "Activity Log"]
        hfill = PatternFill("solid", start_color="1F4E79")
        hfont = Font(bold=True, color="FFFFFF", name="Arial", size=11)
        col_widths = [16, 12, 16, 16, 80]
        for i, (h, w) in enumerate(zip(log_headers, col_widths), start=1):
            cell = wl.cell(row=1, column=i, value=h)
            cell.font      = hfont
            cell.fill      = hfill
            cell.alignment = Alignment(horizontal="center", vertical="center")
            wl.column_dimensions[get_column_letter(i)].width = w
        wl.row_dimensions[1].height = 24
        wl.freeze_panes = "A2"

    now        = datetime.now()
    run_date   = now.strftime("%Y-%m-%d")
    run_time   = now.strftime("%H:%M:%S")
    tickets    = len(set(e.split(":")[0] for e in log_entries)) if log_entries else 0
    # Build activity log — each change on a new line inside the cell
    if log_entries:
        activity_text = "\n".join(log_entries)
    else:
        activity_text = "No new activity found."

    next_row = wl.max_row + 1
    # Alternate row background for readability
    bg_color = "F5F5F5" if next_row % 2 == 0 else "FFFFFF"
    row_fill = PatternFill("solid", start_color=bg_color)
    border   = Border(
        bottom=Side(style="thin", color="DDDDDD"),
        right=Side(style="thin",  color="DDDDDD")
    )

    row_data = [run_date, run_time, tickets, total_logged, activity_text]
    for col, value in enumerate(row_data, start=1):
        cell = wl.cell(row=next_row, column=col, value=value)
        cell.font      = Font(name="Arial", size=10)
        cell.fill      = row_fill
        cell.alignment = Alignment(vertical="top", wrap_text=(col == 5))
        cell.border    = border

    # Row height based on number of log lines
    line_count = len(log_entries) if log_entries else 1
    wl.row_dimensions[next_row].height = max(20, line_count * 15)


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
        dark_bg = ["4A90D9", "F5A623", "E67E22", "8E44AD", "9B59B6",
           "27AE60", "1E8449", "E74C3C", "95A5A6", "2980B9"]
        font_color = "FFFFFF" if fill_clr in dark_bg else "000000"
        cell.font = Font(name="Arial", size=10, color=font_color, bold=(col == 1))
        cell.fill      = row_fill
        cell.alignment = Alignment(vertical="center", wrap_text=(col == 6))
        cell.border    = border
    ws.row_dimensions[next_row].height = 20



# ─────────────────────────────────────────────
#  MAIN SYNC
# ─────────────────────────────────────────────
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
    log_entries  = []

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
                    log_entries.append(f"👤 {key}: Assigned by {updated_by} | Status: {status_at_assignment} | At: {done_at}")

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
                    log_entries.append(f"🔄 {key}: {old_status} → {new_status} by {updated_by} | At: {done_at}")

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
            log_entries.append(f"💬 {key}: Comment by {updated_by} | At: {done_at}")

        if key not in state:
            state[key] = {}
        state[key]["logged_ids"] = list(logged_ids)
  

    sheet_is_new = ws.max_row == 1
    if total_logged:
        sort_sheet(ws)
        update_run_log(wb, total_logged, log_entries)
        wb.save(OUTPUT_FILE)
        print(f"\n  → Saved {total_logged} new entries to '{OUTPUT_FILE}' → sheet '{sheet_name}'")
    elif sheet_is_new:
        sort_sheet(ws)
        update_run_log(wb, total_logged, log_entries)
        wb.save(OUTPUT_FILE)
        print(f"\n  → No activity found. Empty sheet '{sheet_name}' created in '{OUTPUT_FILE}'")
    else:
        update_run_log(wb, total_logged, log_entries)
        wb.save(OUTPUT_FILE)
        print("\n  → No new activity found.")

    save_state(state)

if __name__ == "__main__":
    sync()
