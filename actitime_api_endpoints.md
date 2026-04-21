# actiTime API — Endpoints Reference for the Assistant

**Base URL:** `https://actitime.synthetis.com/api/v1/`  
**Auth:** Basic Authentication on every request (`Authorization: Basic <base64(login:password)>`)

---

## 1. Authentication & Identity

### `GET /users/me`
**Why:** First call made at startup. Verifies that the credentials entered by the user are valid and retrieves the user's numeric `id`, which is required as a parameter in almost every subsequent call.

**Returns:** `id`, `username`, `fullName`, `email`, `active`

**Used when:** User logs in at the start of the session.

```
GET /users/me
→ { "id": 42, "username": "simon.messens", "fullName": "Simon Messens", ... }
```

---

## 2. User Schedule

### `GET /users/{uid}/schedule?dateFrom=YYYY-MM-DD&dateTo=YYYY-MM-DD`
**Why:** Retrieves the user's expected working time (in minutes) per day over a date range. Used to validate that the total time proposed by the LLM is coherent with the user's contract (e.g. 39h/week = 468 min/day average over 5 days).

**Returns:** Array of scheduled minutes per day, aligned to `dateFrom`.

**Used when:** Validating LLM output — warn if total daily time significantly deviates from the schedule.

```
GET /users/42/schedule?dateFrom=2026-04-21&dateTo=2026-04-27
→ { "schedule": [480, 480, 480, 480, 480, 0, 0] }  ← Mon–Sun in minutes
```

---

## 3. Tasks

### `GET /tasks?status=open&limit=1000&includeReferenced=projects,customers`
**Why:** Retrieves all open tasks that the user has access to (their Work Assignments). This list is the **"menu"** given to the LLM — it can only suggest tasks that exist here. Without this list, the LLM would hallucinate task names and IDs.

**Key filters used:**
| Parameter | Value | Reason |
|---|---|---|
| `status` | `open` | Only log time on open tasks |
| `limit` | `1000` | Get everything in one call |
| `includeReferenced` | `projects,customers` | Enrich task names with project/customer context for better LLM matching |

**Returns per task:** `id`, `name`, `projectName`, `customerName`, `typeOfWorkName`, `status`

**Used when:** Building the context payload sent to the LLM.

```
GET /tasks?status=open&limit=1000&includeReferenced=projects,customers
→ {
    "items": [
      { "id": 95,  "name": "Sprint planning",   "projectName": "Agile Dev", "customerName": "Acme Corp" },
      { "id": 116, "name": "Client meeting",    "projectName": "Support",   "customerName": "Beta Ltd"  },
      { "id": 135, "name": "Code review",       "projectName": "Agile Dev", "customerName": "Acme Corp" },
      ...
    ]
  }
```

---

## 4. Existing Time-Track (Read)

### `GET /timetrack?userIds={uid}&dateFrom=YYYY-MM-DD&dateTo=YYYY-MM-DD`
**Why:** Reads the time already logged by the user for a given period. Used for two purposes:
1. **Display in the Excel file** — Sheet 1 shows what is already recorded so the user has full context before validating.
2. **Avoid double-entry** — If time is already logged for a task on a given day, the assistant can warn or overwrite intentionally.

**Key parameters:**
| Parameter | Value | Reason |
|---|---|---|
| `userIds` | `{uid}` | Only fetch the current user's data |
| `dateFrom` | Start of current week/month | Relevant history window |
| `dateTo` | Target date | Up to and including the day being encoded |
| `includeReferenced` | `tasks,projects,customers` | Enrich records for readable Excel output |

**Used when:** Generating the Excel file.

```
GET /timetrack?userIds=42&dateFrom=2026-04-01&dateTo=2026-04-21&includeReferenced=tasks
→ {
    "data": [
      { "date": "2026-04-20", "userId": 42, "records": [
          { "taskId": 95,  "time": 120, "comment": "planning session" },
          { "taskId": 135, "time": 240 }
      ]},
      ...
    ]
  }
```

### `GET /timetrack/{userId}/{date}/{taskId}`
**Why:** Read a single specific time-track record. Useful to check if an entry already exists before deciding whether to create or update it.

**Used when:** Pre-flight check before writing, or for debugging a specific record.

```
GET /timetrack/42/2026-04-21/95
→ { "taskId": 95, "time": 120, "comment": "planning" }
```

---

## 5. Write Time-Track

### `PATCH /timetrack/{userId}/{date}/{taskId}`
**Why:** The **only write endpoint for time entries**. Creates a new entry if none exists, or replaces the existing one. This is called once per task per day after the user validates the Excel file.

**Body:**
```json
{ "time": 120, "comment": "Sprint planning with team" }
```

**Important rules:**
- `time` is in **minutes**
- Setting `time: 0` **deletes** the record
- `date` format: `YYYY-MM-DD` (or `"today"`)
- `userId` can be the numeric ID or the username string

**Used when:** Pushing the validated Excel data back to actiTime.

```
PATCH /timetrack/42/2026-04-21/95
Body: { "time": 120, "comment": "Sprint planning" }
→ { "taskId": 95, "time": 120, "comment": "Sprint planning" }
```

---

## 6. Batch Write (Optimization)

### `POST /batch`
**Why:** Sends up to **100 operations in a single HTTP call**. Instead of making one `PATCH` per task (e.g. 5–8 calls for a full day), the entire day's time entries are pushed atomically. Operations are independent — a failure on one does not cancel the others.

**Used when:** Final push step after user confirms the Excel. Replaces individual `PATCH /timetrack/...` calls.

```
POST /batch
Body: [
  { "method": "PATCH", "relativeUrl": "/timetrack/42/2026-04-21/95",  "body": { "time": 120, "comment": "Sprint planning" } },
  { "method": "PATCH", "relativeUrl": "/timetrack/42/2026-04-21/116", "body": { "time": 60,  "comment": "Client call"     } },
  { "method": "PATCH", "relativeUrl": "/timetrack/42/2026-04-21/135", "body": { "time": 180, "comment": "Code review"     } }
]
→ [ { "status": 200, ... }, { "status": 200, ... }, { "status": 200, ... } ]
```

---

## Summary Table

| Step | Endpoint | Method | Purpose |
|---|---|---|---|
| Login | `/users/me` | GET | Verify credentials, get `userId` |
| Validate schedule | `/users/{uid}/schedule` | GET | Check expected daily minutes |
| Load tasks | `/tasks` | GET | Build task list for LLM context |
| Load existing entries | `/timetrack` | GET | Populate Excel Sheet 1 (existing data) |
| Check one entry | `/timetrack/{uid}/{date}/{taskId}` | GET | Pre-flight check before write |
| Write entries | `/timetrack/{uid}/{date}/{taskId}` | PATCH | Push one validated time entry |
| Write all entries | `/batch` | POST | Push entire day in one call (preferred) |

---

## What the API Does NOT Provide

| Missing Feature | Workaround |
|---|---|
| No "tasks assigned to user" filter | `GET /tasks?status=open` returns only accessible tasks for the authenticated user |
| No POST for time-track | `PATCH` handles both create and update |
| No weekly totals endpoint | Must compute from raw `GET /timetrack` data |
| No natural language search | Handled by the LLM using the task list as context |
