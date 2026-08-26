"""
Zero-dependency smoke test — uses only the Python standard library (no
`requests`, nothing extra to install), so this always runs even on a bare
Python install.

Start the server first, THEN run this in a second terminal:
    uvicorn app.main:app --reload --port 8000      (terminal 1)
    python smoke_test.py                            (terminal 2)

It walks through the core flows end-to-end — health check, login as each of
the three demo accounts, a couple of reads per role, a wrong-password
rejection, and a role-mismatch rejection — and prints PASS/FAIL for each
step plus a final summary. If something fails, the printed response body is
usually enough to tell you what's wrong (e.g. "no such table: users" means
you forgot to run `python seed.py` first).
"""
import json
import urllib.request
import urllib.error

BASE = "http://localhost:8000"
passed, failed = 0, 0


def call(method, path, body=None, token=None, expect=200):
    global passed, failed
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        status = e.code
        try:
            payload = json.loads(e.read().decode())
        except Exception:
            payload = {}
    except Exception as e:
        print(f"FAIL  {method} {path} — couldn't reach the server ({e}). Is uvicorn running on port 8000?")
        failed += 1
        return None

    ok = status == expect
    print(f"{'PASS' if ok else 'FAIL'}  {method:6} {path:40} -> {status} (expected {expect})")
    if not ok:
        print(f"      response: {payload}")
    passed += ok
    failed += not ok
    return payload


print("=== CampusPilot backend smoke test ===\n")

r = call("GET", "/health")

print("\n-- Login as each demo account --")
student = call("POST", "/auth/login", {"email": "rohan@campuspilot.edu", "password": "student123", "role": "student"})
teacher = call("POST", "/auth/login", {"email": "priya@campuspilot.edu", "password": "teach123", "role": "teacher"})
admin = call("POST", "/auth/login", {"email": "admin@campuspilot.edu", "password": "admin123", "role": "admin"})

student_token = student["token"] if student else None
teacher_token = teacher["token"] if teacher else None
admin_token = admin["token"] if admin else None

print("\n-- Reject bad credentials / wrong role --")
call("POST", "/auth/login", {"email": "rohan@campuspilot.edu", "password": "wrongpassword", "role": "student"}, expect=401)
call("POST", "/auth/login", {"email": "rohan@campuspilot.edu", "password": "student123", "role": "admin"}, expect=403)

print("\n-- Student endpoints --")
if student_token:
    call("GET", "/student/summary", token=student_token)
    call("GET", "/student/assignments", token=student_token)
    call("GET", "/student/library/catalog", token=student_token)
    call("GET", "/student/timetable", token=student_token)

print("\n-- Teacher endpoints --")
if teacher_token:
    call("GET", "/teacher/courses", token=teacher_token)
    call("GET", "/teacher/roster", token=teacher_token)
    call("GET", "/teacher/subjects", token=teacher_token)

print("\n-- Admin endpoints --")
if admin_token:
    call("GET", "/admin/users", token=admin_token)
    call("GET", "/admin/courses", token=admin_token)
    call("GET", "/admin/fees", token=admin_token)
    call("GET", "/admin/reports/summary", token=admin_token)
    call("GET", "/admin/risk-scores", token=admin_token)

print("\n-- Cross-role access is blocked --")
if student_token:
    call("GET", "/admin/users", token=student_token, expect=403)

print(f"\n=== {passed} passed, {failed} failed ===")
if failed == 0:
    print("Backend is working correctly end-to-end.")
else:
    print("Something above needs attention — check the response bodies printed next to each FAIL line.")
