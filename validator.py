"""Validation layer — checks LLM output for format, task existence, and duration coherence."""


def validate_llm_output(
    entries: list[dict],
    valid_task_ids: set[int],
    expected_minutes: int = 468,
    tolerance_minutes: int = 30,
) -> list[str]:
    """Validate the parsed LLM output.

    Returns a list of error/warning messages. Empty list = all good.
    """
    issues: list[str] = []

    if not isinstance(entries, list) or len(entries) == 0:
        issues.append("LLM returned an empty or non-list result.")
        return issues

    total_minutes = 0

    for i, entry in enumerate(entries):
        prefix = f"Entry #{i+1}"

        # ── Required fields ────────────────────────────────────────
        for field in ("taskId", "minutes"):
            if field not in entry:
                issues.append(f"{prefix}: missing required field '{field}'.")

        # ── taskId must exist ──────────────────────────────────────
        task_id = entry.get("taskId")
        if task_id is not None and task_id not in valid_task_ids:
            issues.append(f"{prefix}: taskId {task_id} does not exist in actiTime.")

        # ── minutes must be a positive multiple of 15 ─────────────
        minutes = entry.get("minutes", 0)
        if not isinstance(minutes, (int, float)):
            issues.append(f"{prefix}: 'minutes' is not a number.")
        else:
            minutes = int(minutes)
            if minutes <= 0:
                issues.append(f"{prefix}: 'minutes' must be > 0 (got {minutes}).")
            if minutes % 15 != 0:
                issues.append(f"{prefix}: 'minutes' ({minutes}) is not a multiple of 15.")
            total_minutes += minutes

    # ── Daily total check ──────────────────────────────────────────
    if abs(total_minutes - expected_minutes) > tolerance_minutes:
        issues.append(
            f"Total time = {total_minutes} min ({total_minutes/60:.1f}h). "
            f"Expected ~{expected_minutes} min ({expected_minutes/60:.1f}h) ± {tolerance_minutes} min."
        )

    return issues


def validate_weekly_total(
    existing_week_minutes: int,
    new_day_minutes: int,
    weekly_target: int = 2340,  # 39h * 60
    tolerance: int = 60,
) -> list[str]:
    """Check that existing week total + new day does not blow past 39h."""
    issues: list[str] = []
    projected = existing_week_minutes + new_day_minutes
    if projected > weekly_target + tolerance:
        issues.append(
            f"Weekly total would be {projected} min ({projected/60:.1f}h) — "
            f"exceeds target of {weekly_target/60:.1f}h by "
            f"{(projected - weekly_target)/60:.1f}h."
        )
    return issues
