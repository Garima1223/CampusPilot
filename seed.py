"""
Seeds the database with the same demo fixture data the frontend's mock DB
object (App.jsx) ships with, so the app is immediately usable with the exact
demo credentials shown on the login screen's "demo credentials" panel.

Run once after the tables exist:
    python seed.py
Safe to re-run — it skips seeding if any users already exist.
"""
from app.database.db import Base, engine, SessionLocal
from app.models.models import User, Course, Fee, Placement, LibraryBook, Grievance
from app.auth.auth import hash_password

Base.metadata.create_all(bind=engine)
db = SessionLocal()

try:
    if db.query(User).count() > 0:
        print("Database already has users — skipping seed. Delete campuspilot.db to reseed from scratch.")
    else:
        users = [
            User(name="Meera Iyer", email="admin@campuspilot.edu", password_hash=hash_password("admin123"),
                 role="admin", id_label="ADM-001", status="active"),
            User(name="Dr. Priya Sharma", email="priya@campuspilot.edu", password_hash=hash_password("teach123"),
                 role="teacher", id_label="STF-114", status="active", phone="+91 98200 11234",
                 department="Computer Science", designation="Associate Professor",
                 qualification="Ph.D. in Computer Science, IIT Delhi", joined="12 Jul 2018", office="Block B, Room 214",
                 bio="Teaches data structures & algorithms; research interests in graph theory and competitive programming pedagogy."),
            User(name="Prof. Arjun Kapoor", email="arjun@campuspilot.edu", password_hash=hash_password("teach123"),
                 role="teacher", id_label="STF-092", status="active", phone="+91 98450 88213",
                 department="Computer Science", designation="Assistant Professor",
                 qualification="M.Tech in Database Systems, IIT Bombay", joined="3 Jan 2021", office="Block B, Room 118",
                 bio="Handles database systems labs; maintains the department's applied-DB research group."),
            User(name="Rohan Mehta", email="rohan@campuspilot.edu", password_hash=hash_password("student123"),
                 role="student", id_label="CS21B045", status="active"),
            User(name="Ananya Rao", email="ananya@campuspilot.edu", password_hash=hash_password("student123"),
                 role="student", id_label="CS21B012", status="active"),
            User(name="Kabir Singh", email="kabir@campuspilot.edu", password_hash=hash_password("student123"),
                 role="student", id_label="CS21B078", status="active"),
            User(name="Diya Nair", email="diya@campuspilot.edu", password_hash=hash_password("student123"),
                 role="student", id_label="CS21B033", status="active"),
            User(name="Zoya Khan", email="zoya@campuspilot.edu", password_hash=hash_password("student123"),
                 role="student", id_label="CS21B061", status="active"),
        ]
        db.add_all(users)

        courses = [
            Course(code="CS301", name="Data Structures", dept="Computer Science", faculty="Dr. Priya Sharma", students=5),
            Course(code="CS315", name="Database Systems", dept="Computer Science", faculty="Prof. Arjun Kapoor", students=5),
            # NOTE: "Dr. Ritu Nair" has no matching user account — ported as-is
            # from the frontend's own mock fixture, which has the same gap
            # (course.faculty is a free-text display string, not a real FK).
            Course(code="MA201", name="Discrete Mathematics", dept="Mathematics", faculty="Dr. Ritu Nair", students=5),
        ]
        db.add_all(courses)

        fees = [
            Fee(student="Rohan Mehta", total=85000, paid=85000, status="paid"),
            Fee(student="Ananya Rao", total=85000, paid=40000, status="partial"),
            Fee(student="Kabir Singh", total=85000, paid=0, status="overdue"),
            Fee(student="Diya Nair", total=85000, paid=85000, status="paid"),
            Fee(student="Zoya Khan", total=85000, paid=60000, status="partial"),
        ]
        db.add_all(fees)

        placements = [
            Placement(company="Nexora Systems", role="Software Engineer Intern", package="₹8 LPA", location="Bengaluru",
                      min_cgpa=7.5, min_attendance=75, deadline="5 Sep", posted_by="Meera Iyer", status="open"),
            Placement(company="Vantage Analytics", role="Data Analyst", package="₹6.5 LPA", location="Pune",
                      min_cgpa=7, min_attendance=70, deadline="10 Sep", posted_by="Meera Iyer", status="open"),
            Placement(company="Orbit Cloud", role="Backend Developer", package="₹9.2 LPA", location="Hyderabad",
                      min_cgpa=8, min_attendance=80, deadline="1 Sep", posted_by="Meera Iyer", status="open"),
        ]
        db.add_all(placements)

        books = [
            LibraryBook(title="Introduction to Algorithms", author="Cormen, Leiserson, Rivest, Stein", category="Computer Science", copies=4),
            LibraryBook(title="Database System Concepts", author="Silberschatz, Korth, Sudarshan", category="Computer Science", copies=2),
            LibraryBook(title="Discrete Mathematics and Its Applications", author="Kenneth Rosen", category="Mathematics", copies=3),
            LibraryBook(title="Operating System Concepts", author="Silberschatz, Galvin, Gagne", category="Computer Science", copies=1),
            LibraryBook(title="Computer Networking: A Top-Down Approach", author="Kurose, Ross", category="Computer Science", copies=0),
            LibraryBook(title="Linear Algebra and Its Applications", author="Gilbert Strang", category="Mathematics", copies=5),
        ]
        db.add_all(books)

        db.commit()

        grievances = [
            Grievance(raised_by="Rohan Mehta", role="student", category="Infrastructure",
                      description="Wi-Fi has been down in Block B library for three days, can't access online course material.",
                      status="open"),
            Grievance(raised_by="Ananya Rao", role="student", category="Academic",
                      description="My CS315 lab attendance for 14 Aug was marked absent even though I attended — please recheck.",
                      status="in-review", assigned_to="Meera Iyer"),
            Grievance(raised_by="Kabir Singh", role="student", category="Fees & Finance",
                      description="Paid the partial fee installment on 10 Aug but the portal still shows it as overdue.",
                      status="resolved", assigned_to="Meera Iyer"),
        ]
        db.add_all(grievances)
        db.commit()

        print("Seeded: 8 users, 3 courses, 5 fee records, 3 placements, 6 library books, 3 grievances.")
        print("Demo logins — Student: rohan@campuspilot.edu / student123"
              " | Faculty: priya@campuspilot.edu / teach123 | Admin: admin@campuspilot.edu / admin123")
finally:
    db.close()
