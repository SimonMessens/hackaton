"""actiTime Encoding Assistant — CLI entry point."""

import getpass
import sys
from datetime import date, timedelta
from pathlib import Path

from actitime import ActiTimeClient
from llm import match_activities
from validator import validate_llm_output, validate_weekly_total
from excel import generate_excel, read_proposed_excel

ACTITIME_URL = "https://actitime.synthetis.com"


def prompt_credentials() -> tuple[str, str, str]:
    """Ask the user for actiTime + GitHub credentials at runtime."""
    print("=" * 60)
    print("  actiTime Encoding Assistant")
    print("=" * 60)
    print()
    username = input("actiTime username: ").strip()
    password = getpass.getpass("actiTime password: ")
    github_token = getpass.getpass("GitHub PAT (for LLM): ")
    print()
    return username, password, github_token


def choose_date() -> str:
    """Let the user pick a date (default: today)."""
    today = date.today().isoformat()
    raw = input(f"Date to encode [YYYY-MM-DD, default={today}]: ").strip()
    if not raw:
        return today
    # Basic validation
    try:
        date.fromisoformat(raw)
    except ValueError:
        print(f"Invalid date format '{raw}', using today.")
        return today
    return raw


def get_week_bounds(target: str) -> tuple[str, str]:
    """Return (monday, sunday) for the week containing target date."""
    d = date.fromisoformat(target)
    monday = d - timedelta(days=d.weekday())
    sunday = monday + timedelta(days=6)
    return monday.isoformat(), sunday.isoformat()


def main():
    # ── Step 1: Credentials ───────────────────────────────────────
    username, password, github_token = prompt_credentials()

    client = ActiTimeClient(ACTITIME_URL, username, password)

    # ── Step 2: Authenticate ──────────────────────────────────────
    print("🔐 Authenticating with actiTime...")
    try:
        user = client.login()
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        sys.exit(1)
    print(f"✅ Logged in as {client.full_name} (ID: {client.user_id})")
    print()

    # ── Step 3: Choose date ───────────────────────────────────────
    target_date = choose_date()
    week_start, week_end = get_week_bounds(target_date)
    print(f"📅 Target date: {target_date}  (week: {week_start} → {week_end})")
    print()

    # ── Step 4: Fetch tasks ───────────────────────────────────────
    print("📋 Fetching open tasks from actiTime...")
    tasks = client.get_open_tasks()
    if not tasks:
        print("❌ No open tasks found. Check your actiTime assignments.")
        sys.exit(1)
    print(f"   Found {len(tasks)} open tasks.")

    tasks_lookup = {t["id"]: t for t in tasks}
    valid_task_ids = set(tasks_lookup.keys())

    # ── Step 5: Fetch existing time-track for the week ────────────
    print("⏱️  Fetching existing time-track for the week...")
    week_data = client.get_timetrack(week_start, week_end)

    existing_week_minutes = 0
    existing_day_records = []
    for day in week_data:
        day_total = sum(r.get("time", 0) for r in day.get("records", []))
        existing_week_minutes += day_total
        if day.get("date") == target_date:
            existing_day_records = day.get("records", [])

    print(f"   Week total so far: {existing_week_minutes} min ({existing_week_minutes/60:.1f}h)")
    print(f"   Already logged on {target_date}: {sum(r.get('time',0) for r in existing_day_records)} min")
    print()

    # ── Step 6: Get user's schedule for expected daily minutes ────
    try:
        schedule = client.get_schedule(target_date, target_date)
        expected_minutes = schedule[0] if schedule else 468
    except Exception:
        expected_minutes = 468  # fallback: 7h48
    print(f"📐 Expected work time for {target_date}: {expected_minutes} min ({expected_minutes/60:.1f}h)")
    print()

    # ── Step 7: Free-text input ───────────────────────────────────
    print("📝 Describe what you did today (free text, press Enter twice to finish):")
    lines = []
    while True:
        line = input()
        if line.strip() == "":
            if lines:
                break
            continue
        lines.append(line)
    free_text = "\n".join(lines)
    print()

    # ── Step 8: LLM matching ─────────────────────────────────────
    print("🤖 Calling LLM to match activities to tasks...")
    try:
        proposed = match_activities(
            github_token=github_token,
            free_text=free_text,
            tasks=tasks,
            expected_minutes=expected_minutes,
        )
    except Exception as e:
        print(f"❌ LLM call failed: {e}")
        sys.exit(1)

    print(f"   LLM proposed {len(proposed)} entries:")
    for p in proposed:
        print(f"     • {p.get('taskName', '?')} — {p.get('minutes', 0)} min — {p.get('comment', '')}")
    print()

    # ── Step 9: Validate ──────────────────────────────────────────
    print("🔍 Validating LLM output...")
    issues = validate_llm_output(proposed, valid_task_ids, expected_minutes)
    new_day_total = sum(e.get("minutes", 0) for e in proposed)
    issues += validate_weekly_total(existing_week_minutes, new_day_total)

    if issues:
        print("⚠️  Validation warnings:")
        for issue in issues:
            print(f"   - {issue}")
        print()
        cont = input("Continue anyway? [y/N]: ").strip().lower()
        if cont != "y":
            print("Aborted.")
            sys.exit(0)
    else:
        print("   ✅ All checks passed.")
    print()

    # ── Step 10: Generate Excel ───────────────────────────────────
    excel_path = Path(f"timetrack_{target_date}.xlsx")
    print(f"📊 Generating Excel file: {excel_path}")
    generate_excel(
        filepath=excel_path,
        target_date=target_date,
        existing_records=existing_day_records,
        proposed_entries=proposed,
        tasks_lookup=tasks_lookup,
    )
    print(f"   ✅ File created: {excel_path.resolve()}")
    print()

    # ── Step 11: Wait for user to review ──────────────────────────
    print("📂 Please open the Excel file, review the 'Proposed' sheet,")
    print("   adjust minutes or set Include? to 'N' for rows to skip.")
    print()
    input("Press Enter when you're done reviewing the file...")
    print()

    # ── Step 12: Read back & push ─────────────────────────────────
    print("📥 Reading back the validated Excel...")
    validated = read_proposed_excel(excel_path)

    if not validated:
        print("No entries to push (all excluded or empty). Done.")
        sys.exit(0)

    print(f"   {len(validated)} entries to push:")
    for v in validated:
        t = tasks_lookup.get(v["taskId"], {})
        print(f"     • [{v['taskId']}] {t.get('name', '?')} — {v['minutes']} min")
    print()

    confirm = input("🚀 Push these to actiTime? [y/N]: ").strip().lower()
    if confirm != "y":
        print("Aborted. Excel file preserved.")
        sys.exit(0)

    print("📤 Pushing to actiTime...")
    try:
        results = client.batch_patch_timetrack(validated, client.user_id, target_date)
        print(f"   ✅ Done! {len(validated)} entries pushed to actiTime.")
    except Exception as e:
        print(f"   ⚠️  Batch push failed, trying individual updates...")
        success = 0
        for v in validated:
            try:
                client.patch_timetrack(client.user_id, target_date, v["taskId"], v["minutes"], v.get("comment", ""))
                success += 1
            except Exception as ex:
                print(f"   ❌ Failed for task {v['taskId']}: {ex}")
        print(f"   ✅ Pushed {success}/{len(validated)} entries.")

    print()
    print("🎉 All done! Have a great day.")


if __name__ == "__main__":
    main()
