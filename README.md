# CampusPilot backend

A FastAPI + SQLAlchemy backend rebuilt to match the CampusPilot React frontend's
mock `api` object (`App.jsx`) field-for-field — same endpoint groupings
(`auth`, `admin`, `teacher`, `student`, `placements`), same role names
(`student` / `teacher` / `admin`, not the original `STUDENT`/`FACULTY`/`ADMIN`),
same JSON shapes, same business rules (login lockout, grievance categories,
subject-request approval flow, risk-score heuristic, etc.) — but backed by a
real database instead of an in-memory array that resets on every page reload.

## Setup

```bash
cd CampusPilot-main
pip install -r requirements.txt
python seed.py          # creates campuspilot.db (SQLite) and seeds demo data
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000/docs for interactive API docs, or http://localhost:8000/health
to confirm it's running.

Demo logins (seeded by `seed.py`, same as the frontend's login-screen "demo
credentials" panel):

| Role    | Email                     | Password    |
|---------|---------------------------|-------------|
| Student | rohan@campuspilot.edu     | student123  |
| Faculty | priya@campuspilot.edu     | teach123    |
| Admin   | admin@campuspilot.edu     | admin123    |

## How to check it's actually working

1. **`http://localhost:8000/health`** in a browser should show
   `{"status":"ok",...}`. If this doesn't load, the server isn't running —
   check the terminal you ran `uvicorn` in for an error.
2. **`http://localhost:8000/docs`** — FastAPI's interactive docs. Click
   `POST /auth/login` → "Try it out" → paste
   `{"email":"rohan@campuspilot.edu","password":"student123","role":"student"}`
   → Execute. You should get a 200 with a `token` and `user` back. This
   proves the database, password hashing, and JWT issuing all work.
3. **Run `python smoke_test.py`** (in a second terminal, while `uvicorn` is
   still running in the first) — it logs in as all three demo accounts, hits
   the main read endpoints for each role, and checks that wrong passwords
   and cross-role access get correctly rejected. It prints PASS/FAIL per
   check and a final count, with no extra dependencies to install.
4. If either of the above says something failed, the printed error message
   (or the response body `smoke_test.py` prints under a FAIL line) is the
   thing to send back — that tells you (or me) exactly what broke instead of
   just "not working."

**Important — this backend is not connected to the frontend yet.** Running
`uvicorn` and confirming the steps above pass proves the *backend* works.
The React app (`App.jsx`) still uses its own in-memory mock data and has no
`fetch()` calls to this API — so opening the frontend and logging in won't
show any different behavior until it's wired up to call this backend
instead. That's a separate, larger change to `App.jsx` — ask if you want
that done.

## What changed from the original backend zip

- **Database defaults to SQLite** (`campuspilot.db`, zero setup) instead of a
  hardcoded MySQL connection string with committed credentials. Set
  `DATABASE_URL` (e.g. `mysql+pymysql://user:pass@host/db`) to point at MySQL
  or Postgres instead — see `app/database/db.py`.
- **Role names now match the frontend**: `student`/`teacher`/`admin`
  everywhere (JWT payload, `require_role()` checks, DB column), not the
  original `STUDENT`/`FACULTY`/`ADMIN`.
- **Login now takes an optional `role`** (the portal picked on the login
  form) and rejects the login if it doesn't match the account's real role —
  ports the frontend's fix for "log into any portal with valid creds of a
  different role."
- **Brute-force lockout moved server-side**: 5 failed attempts on an email
  locks it for 45s, enforced in `app/auth/auth.py` rather than only in
  frontend React state (which a page refresh would have reset).
- **Signup rejects `role: "admin"`** — admin accounts can only be created via
  `POST /admin/users` by an existing admin, matching the frontend's "Users &
  Roles" console-only admin creation.
- **New models** to cover everything the frontend expects that the original
  backend didn't have at all: `Course`, `SubjectRequest` (+ admin
  approve/reject), `Fee`, `Assignment`, `StudyMaterial`, `ClassNotice`,
  `LeaveRequest`, `AuditLogEntry`, `Placement` + `PlacementApplication`,
  `LibraryBook` (catalog) + `LibraryRequest` (student self-service, separate
  from the original admin-only issue/return flow), and a `Grievance` model
  extended with `assignedTo`/role-scoped categories.
- **`Notification` is now broadcast-by-role** (`toRole`) instead of
  per-`user_id`, matching how the frontend's `pushNotification()` actually
  works (`{toRole, title, body}`).
- **Fixed a real bug** in `app/ai/attendance_ocr.py`: it hardcoded
  `pytesseract.pytesseract.tesseract_cmd` to a Windows-only path
  (`C:\Program Files\Tesseract-OCR\tesseract.exe`), which would silently
  break OCR on any Linux/macOS host. Now only overrides it if `TESSERACT_CMD`
  is set; otherwise relies on `tesseract` being on `PATH`.
- **`POST /teacher/attendance/ocr`** tries the real OCR pipeline if a photo
  is uploaded, and automatically falls back to the same simulated
  present/absent detection the frontend mock used if OCR isn't available in
  the environment (no Tesseract installed, etc.) — so the flow still works
  end-to-end without extra setup. Install `requirements-ocr.txt` +
  the `tesseract-ocr` system package for the real thing.
- **`app/ai/notifier.py` was removed** — it referenced the old
  per-`user_id` `Notification` shape; superseded by `notify()` in
  `app/common.py`.
- **`app/ai/risk_model.py`, `grievance_classifier.py`, `placement_matcher.py`
  are now unused** (left in place, harmless) — replaced with logic in
  `app/common.py` that matches the frontend's own heuristics exactly
  (`computeRiskScore`, `autoClassifyGrievance`) instead of the original
  backend's different formulas, since the goal here was matching the
  frontend, not the original backend's design.
- Old routers/schemas that don't map onto the frontend's actual `api`
  surface (`attendance_router`, `fee_router`, `feedback_router`,
  `grievance_router`, `job_router`, `library_router`, `risk_router`,
  `timetable_router` and their schema files) were removed and replaced with
  five routers organized the same way the frontend's `api` object is:
  `auth_router`, `admin_router`, `teacher_router`, `student_router`,
  `placements_router`, plus `notification_router` and `copilot_router`.
- **CORS is wide open** (`allow_origins=["*"]`) so a local Vite dev server on
  a different port can call this — tighten before deploying anywhere real.
- **Password hashing and JWTs no longer use passlib/bcrypt/python-jose.**
  The first version of this backend did, and that combination
  (passlib 1.7.x + a recent bcrypt) has a well-known runtime crash —
  `AttributeError: module 'bcrypt' has no attribute '__about__'` — the
  moment anyone actually logs in, even though `pip install` succeeds and the
  server starts fine. That's the single most likely reason a first run of
  this backend would have looked "not working." It's rewritten to use only
  the Python standard library (`hashlib`'s PBKDF2) for password hashing and
  PyJWT for tokens — both have effectively zero native-dependency risk. See
  `app/auth/auth.py` for the full explanation in the code comments.

## What was actually verified this round

The sandbox this was built in still has no package-registry network access
(`pip install` can't run here — confirmed by trying again), so a real
`uvicorn` boot still wasn't possible. What I could do instead, and did:

- **Executed every module** (not just syntax-checked it) against
  structurally-faithful stand-ins for FastAPI/SQLAlchemy — every router,
  every `APIRouter()`/`Depends()`/`require_role()` call, every model class
  definition actually ran, and all 60 routes registered with zero import
  errors, zero duplicate paths.
- **Ran the real password-hashing and JWT code** (`hash_password`,
  `verify_password`, `create_access_token`, `decode_token` in
  `app/auth/auth.py`) against the actual PyJWT + hashlib libraries — both
  are already present in my environment, so this part is genuinely tested,
  not just reviewed: hash → verify(correct password) → True, verify(wrong
  password) → False, encode → decode → same payload back, all confirmed.
- **Cross-referenced every model column, schema field, and route path**
  used across all seven routers against their definitions programmatically
  — zero mismatches.

What still hasn't run is the full `fastapi` + `sqlalchemy` + real SQLite
stack together end-to-end — that's what `smoke_test.py` above is for. Please
run it and tell me what it prints; if anything fails, that output is exactly
what I need to fix it for real instead of guessing again.

- **`Fee`/risk lookups match students by display name**, not a foreign key
  (`Fee.student == User.name`) — carried over as-is from the frontend mock's
  own design (`feeStatusForStudentName`). Fine for a demo with unique names;
  would need a real FK if two students ever share a name.
- **Leave requests** (`POST /teacher/leave`) stay `"pending"` forever now —
  the frontend mock auto-resolved them after a timer purely for demo pacing,
  which isn't something a real backend should do (that's an admin decision).
  There's no admin approve/reject endpoint for these yet since the original
  mock never had one either; worth adding if this becomes a real workflow.
