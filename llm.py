"""LLM integration — calls GitHub Models to match free-text activities to actiTime tasks."""

import json
from openai import OpenAI


def build_task_list_prompt(tasks: list[dict]) -> str:
    """Format the task list into a readable string for the LLM context."""
    lines = []
    for t in tasks:
        customer = t.get("customerName", "?")
        project = t.get("projectName", "?")
        name = t.get("name", "?")
        tid = t.get("id", "?")
        lines.append(f"  - ID:{tid}  |  {customer} > {project} > {name}")
    return "\n".join(lines)


SYSTEM_PROMPT = """\
You are a time-tracking assistant. The user will describe what they did during a workday.
You must map each activity to one of the available actiTime tasks and estimate a duration in minutes.

Rules:
- Only use task IDs from the provided list. NEVER invent a task ID.
- Durations must be in minutes and must be multiples of 15.
- The total should be close to {expected_minutes} minutes for the day (± 30 min is acceptable).
- If an activity does not clearly match any task, pick the closest match and add a note in the comment.
- Return ONLY a valid JSON array, no markdown, no explanation.

JSON format:
[
  {{ "taskId": <int>, "taskName": "<string>", "minutes": <int>, "comment": "<string>" }},
  ...
]
"""


def match_activities(
    github_token: str,
    free_text: str,
    tasks: list[dict],
    expected_minutes: int = 468,
    model: str = "gpt-4o",
) -> list[dict]:
    """Call the LLM to map the user's free-text description to actiTime tasks.

    Returns a list of dicts: [{ taskId, taskName, minutes, comment }]
    """
    client = OpenAI(
        base_url="https://models.inference.ai.azure.com",
        api_key=github_token,
    )

    task_list_str = build_task_list_prompt(tasks)

    system_msg = SYSTEM_PROMPT.format(expected_minutes=expected_minutes)

    user_msg = f"""Here are the available actiTime tasks:
{task_list_str}

The user described their day as follows:
\"{free_text}\"

Map each activity to a task and estimate durations. Return ONLY a JSON array."""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.2,
    )

    raw = response.choices[0].message.content.strip()

    # Strip markdown code fences if the LLM wraps them
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3].strip()

    return json.loads(raw)
