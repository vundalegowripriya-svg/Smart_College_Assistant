import streamlit as st
import sqlite3
import hashlib
import os
from datetime import date, timedelta

# ==========================================================
# APP SETTINGS
# ==========================================================

st.set_page_config(
    page_title="Smart College Assistant",
    page_icon="🎓",
    layout="wide"
)

DB = "college.db"
UPLOAD_FOLDER = "timetables"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ==========================================================
# YEAR, BRANCH AND SECTION DATA
# ==========================================================

COLLEGE_DATA = {"1st Year": {"AIML": ["1", "2", "3", "4","5","6"], "CSE": ["1", "2", "3", "4", "5","6","7"], "CSD": ["1", "2"], "CIC": ["1"], "CSIT": ["1", "2"], "ECE": ["1", "2", "3"], "EEE": ["1"], "CE": ["1"], "ME": ["1"], "AIDS": ["1", "2", "3", "4"]}, "2nd Year": {"AIML": ["1", "2", "3", "4","5"], "CSE": ["1", "2", "3", "4", "5","6","7"], "CSD": ["1", "2"], "CIC": ["1"], "CSIT": ["1", "2"], "ECE": ["1", "2", "3"], "EEE": ["1"], "CE": ["1"], "ME": ["1"], "AIDS": ["1", "2", "3", "4"]}, "3rd Year": {"AIML": ["1", "2", "3", "4","5"], "CSE": ["1", "2", "3", "4", "5","6","7"], "CSD": ["1", "2"], "CIC": ["1"], "CSIT": ["1", "2"], "ECE": ["1", "2", "3"], "EEE": ["1"], "CE": ["1"], "ME": ["1"], "AIDS": ["1", "2", "3", "4"]}, "4th Year": {"AIML": ["1", "2", "3", "4","5"], "CSE": ["1", "2", "3", "4", "5","6","7"], "CSD": ["1", "2"], "CIC": ["1"], "CSIT": ["1", "2"], "ECE": ["1", "2", "3"], "EEE": ["1"], "CE": ["1"], "ME": ["1"], "AIDS": ["1", "2", "3", "4"]}}


SEMESTERS_BY_YEAR = {
    "1st Year": ["Semester 1", "Semester 2"],
    "2nd Year": ["Semester 3", "Semester 4"],
    "3rd Year": ["Semester 5", "Semester 6"],
    "4th Year": ["Semester 7", "Semester 8"],
}

FIXED_TIME_SLOTS = [
    ("8:40", "9:30"), ("9:30", "10:20"), ("10:20", "11:10"),
    ("11:10", "12:00"), ("12:00", "12:50"), ("12:50", "1:50"),
    ("1:50", "2:40"), ("2:40", "3:30"), ("3:30", "4:20"),
]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


# ==========================================================
# DATABASE
# ==========================================================

def connect():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def password_hash(password):
    return hashlib.sha256(
        password.encode()
    ).hexdigest()


def create_database():

    conn = connect()
    cursor = conn.cursor()

    # ---------------- STUDENTS ----------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            year TEXT NOT NULL,
            branch TEXT NOT NULL,
            section TEXT NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # ---------------- TIMETABLES ----------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS timetables (
            timetable_id INTEGER PRIMARY KEY AUTOINCREMENT,
            year TEXT NOT NULL,
            branch TEXT NOT NULL,
            section TEXT NOT NULL,
            image_path TEXT NOT NULL,
            UNIQUE(year, branch, section)
        )
    """)

    # ---------------- TIMETABLE IMAGE HISTORY ----------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS timetable_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year TEXT NOT NULL,
            branch TEXT NOT NULL,
            section TEXT NOT NULL,
            semester TEXT NOT NULL,
            image_path TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(year, branch, section, semester)
        )
    """)

    # ---------------- SUBJECTS ----------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            subject_id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_name TEXT NOT NULL,
            year TEXT NOT NULL,
            branch TEXT NOT NULL,
            section TEXT NOT NULL
        )
    """)

    # ---------------- ATTENDANCE ----------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            subject_id INTEGER NOT NULL,
            attendance_date TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)

    # ---------------- DAILY TIMETABLE ----------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_timetable (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year TEXT NOT NULL,
            branch TEXT NOT NULL,
            section TEXT NOT NULL,
            day TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            subject TEXT NOT NULL,
            room TEXT
        )
    """)

    # ---------------- DAILY ATTENDANCE ----------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            attendance_date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            subject TEXT NOT NULL,
            room TEXT,
            status TEXT NOT NULL,
            UNIQUE(student_id, attendance_date, start_time, subject)
        )
    """)
    # ---------------- DATABASE MIGRATIONS ----------------
    existing_student_columns = {r["name"] for r in cursor.execute("PRAGMA table_info(students)").fetchall()}
    if "semester" not in existing_student_columns:
        cursor.execute("ALTER TABLE students ADD COLUMN semester TEXT DEFAULT 'Current'")
    if "status" not in existing_student_columns:
        cursor.execute("ALTER TABLE students ADD COLUMN status TEXT DEFAULT 'Active'")
    cursor.execute("""
        UPDATE students SET semester = CASE year
            WHEN '1st Year' THEN 'Semester 1' WHEN '2nd Year' THEN 'Semester 3'
            WHEN '3rd Year' THEN 'Semester 5' WHEN '4th Year' THEN 'Semester 7'
            ELSE 'Current' END
        WHERE semester IS NULL OR semester='' OR semester='Current'
    """)
    existing_subject_columns = {r["name"] for r in cursor.execute("PRAGMA table_info(subjects)").fetchall()}
    if "semester" not in existing_subject_columns:
        cursor.execute("ALTER TABLE subjects ADD COLUMN semester TEXT DEFAULT 'Current'")
    existing_daily_columns = {r["name"] for r in cursor.execute("PRAGMA table_info(daily_timetable)").fetchall()}
    if "semester" not in existing_daily_columns:
        cursor.execute("ALTER TABLE daily_timetable ADD COLUMN semester TEXT DEFAULT 'Current'")
    cursor.execute("""
        DELETE FROM daily_timetable WHERE id NOT IN (
            SELECT MAX(id) FROM daily_timetable
            GROUP BY year, branch, section, semester, day, start_time
        )
    """)
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_timetable_slot
        ON daily_timetable(year, branch, section, semester, day, start_time)
    """)
    cursor.execute("""
        DELETE FROM subjects WHERE subject_id NOT IN (
            SELECT MIN(subject_id) FROM subjects
            GROUP BY subject_name, year, branch, section, semester
        )
    """)
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_subject_unique
        ON subjects(subject_name, year, branch, section, semester)
    """)

    # ---------------- ATTENDANCE DAY TYPE ----------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance_days (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            attendance_date TEXT NOT NULL,
            day_type TEXT NOT NULL,
            UNIQUE(student_id, attendance_date)
        )
    """)

    # ---------------- OFFICIAL MONTHLY ATTENDANCE ----------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS monthly_attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            attendance_month TEXT NOT NULL,
            percentage REAL NOT NULL,
            UNIQUE(student_id, attendance_month)
        )
    """)

    # ---------------- ADMIN ----------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO admins
        VALUES (?, ?)
    """, (
        "admin",
        password_hash("admin123")
    ))

    conn.commit()
    conn.close()


create_database()


# ==========================================================
# SESSION
# ==========================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user_type" not in st.session_state:
    st.session_state.user_type = None

if "student_id" not in st.session_state:
    st.session_state.student_id = None


# ==========================================================
# STUDENT DATABASE FUNCTIONS
# ==========================================================

def get_student(student_id):

    conn = connect()

    student = conn.execute("""
        SELECT *
        FROM students
        WHERE student_id = ?
    """, (student_id,)).fetchone()

    conn.close()

    return student


def get_subjects(student):
    conn = connect()
    semester = student["semester"] if "semester" in student.keys() else "Current"
    subjects = conn.execute("""
        SELECT * FROM subjects
        WHERE year=? AND branch=? AND section=?
          AND (semester=? OR semester='Current' OR semester='')
        ORDER BY subject_name
    """, (student["year"], student["branch"], student["section"], semester)).fetchall()
    conn.close()
    return subjects

def get_timetable(student):

    conn = connect()

    timetable = conn.execute("""
        SELECT *
        FROM timetables
        WHERE year = ?
        AND branch = ?
        AND section = ?
    """, (
        student["year"],
        student["branch"],
        student["section"]
    )).fetchone()

    conn.close()

    return timetable


def get_attendance(student_id, subject_id):

    conn = connect()

    total = conn.execute("""
        SELECT COUNT(*) AS total
        FROM attendance
        WHERE student_id = ?
        AND subject_id = ?
    """, (
        student_id,
        subject_id
    )).fetchone()["total"]

    attended = conn.execute("""
        SELECT COUNT(*) AS attended
        FROM attendance
        WHERE student_id = ?
        AND subject_id = ?
        AND status = 'Present'
    """, (
        student_id,
        subject_id
    )).fetchone()["attended"]

    conn.close()

    absent = total - attended

    if total > 0:
        percentage = (attended / total) * 100
    else:
        percentage = 0

    return total, attended, absent, percentage


# ==========================================================
# STUDENT LOGIN
# ==========================================================

def student_login():

    st.title("🎓 Smart College Assistant")
    st.header("👨‍🎓 Student Login")

    st.info(
        "Your Year, Branch and Section are automatically "
        "loaded from your registered student account."
    )

    student_id = st.text_input(
        "Student ID"
    )

    password = st.text_input(
        "Password",
        type="password"
    )

    if st.button(
        "🔐 Login",
        use_container_width=True
    ):

        student = get_student(student_id)

        if student is None:

            st.error(
                "Student ID not found."
            )
            return

        if student["password"] != password_hash(password):

            st.error(
                "Incorrect password."
            )
            return

        if student["status"] in ["Discontinued", "Graduated"]:
            st.error(f"This student account is marked as {student['status']}.")
            return

        st.session_state.logged_in = True
        st.session_state.user_type = "student"
        st.session_state.student_id = student_id

        st.success(
            "Login successful!"
        )

        st.rerun()


# ==========================================================
# ADMIN LOGIN
# ==========================================================

def admin_login():

    st.title("🛠️ Admin Login")

    username = st.text_input(
        "Username"
    )

    password = st.text_input(
        "Password",
        type="password"
    )

    if st.button(
        "🔐 Login",
        use_container_width=True
    ):

        conn = connect()

        admin = conn.execute("""
            SELECT *
            FROM admins
            WHERE username = ?
        """, (username,)).fetchone()

        conn.close()

        if admin and admin["password"] == password_hash(password):

            st.session_state.logged_in = True
            st.session_state.user_type = "admin"

            st.success(
                "Admin login successful!"
            )

            st.rerun()

        else:

            st.error(
                "Invalid admin login."
            )


# ==========================================================
# STUDENT HOME
# ==========================================================

def student_home():

    student = get_student(
        st.session_state.student_id
    )

    st.title("🏠 Student Dashboard")

    st.success(
        f"Welcome, {student['name']}!"
    )

    # These values come ONLY from database
    year = student["year"]
    branch = student["branch"]
    section = student["section"]

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Academic Year",
            year
        )

    with col2:
        st.metric(
            "Branch",
            branch
        )

    with col3:
        st.metric(
            "Section",
            section
        )

    st.divider()

    st.subheader("📅 Your Timetable")

    timetable = get_timetable(student)

    if timetable:

        if os.path.exists(
            timetable["image_path"]
        ):

            st.image(
                timetable["image_path"],
                use_container_width=True
            )

        else:

            st.warning(
                "Timetable image not found."
            )

    else:

        st.info(
            "Timetable has not been uploaded yet."
        )

    st.subheader("📊 Your Attendance")

    current_month = date.today().strftime("%Y-%m")
    conn = connect()
    official = conn.execute("""
        SELECT percentage FROM monthly_attendance
        WHERE student_id = ? AND attendance_month = ?
    """, (student["student_id"], current_month)).fetchone()
    self_result = conn.execute("""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) AS attended
        FROM daily_attendance
        WHERE student_id = ? AND attendance_date LIKE ?
    """, (student["student_id"], current_month + "%")).fetchone()
    conn.close()

    total = self_result["total"] or 0
    attended = self_result["attended"] or 0
    self_percentage = (attended / total * 100) if total else 0

    c1, c2 = st.columns(2)
    with c1:
        st.metric("📝 My Self Attendance", f"{self_percentage:.2f}%")
    with c2:
        st.metric("🎓 Official Attendance",
                  f"{official['percentage']:.2f}%" if official else "Not updated")

    st.caption(f"Attendance shown for {current_month}. Self attendance is for your reference; official percentage is entered by Admin at month end.")


# ==========================================================
# STUDENT ATTENDANCE
# ==========================================================

def student_attendance():
    student = get_student(st.session_state.student_id)

    st.title("📊 My Attendance")
    st.write(f"**{student['year']} | {student['branch']} | Section {student['section']}**")

    view_mode = st.radio(
        "📅 Calculation Type",
        ["Monthly Calculation", "Custom Date Range"],
        horizontal=True,
        key="attendance_calc_mode"
    )

    if view_mode == "Monthly Calculation":
        selected_month = st.selectbox(
            "Select Month",
            [f"{date.today().year:04d}-{m:02d}" for m in range(1, 13)],
            index=date.today().month - 1,
            key="student_att_month"
        )
        start_date = date.fromisoformat(selected_month + "-01")
        if start_date.month == 12:
            end_date = date(start_date.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(start_date.year, start_date.month + 1, 1) - timedelta(days=1)
        range_label = selected_month
    else:
        c1, c2 = st.columns(2)
        with c1:
            start_date = st.date_input(
                "From Date",
                value=date.today().replace(day=1),
                max_value=date.today(),
                key="attendance_range_start"
            )
        with c2:
            end_date = st.date_input(
                "Till Date",
                value=date.today(),
                max_value=date.today(),
                key="attendance_range_end"
            )
        range_label = f"{start_date.strftime('%d-%m-%Y')} to {end_date.strftime('%d-%m-%Y')}"

    if start_date > end_date:
        st.error("From Date cannot be after Till Date.")
        return

    conn = connect()
    official = None
    if view_mode == "Monthly Calculation":
        official = conn.execute("""
            SELECT percentage FROM monthly_attendance
            WHERE student_id = ? AND attendance_month = ?
        """, (student['student_id'], selected_month)).fetchone()

    rows = conn.execute("""
        SELECT subject,
               COUNT(*) AS total,
               SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) AS attended,
               SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END) AS absent
        FROM daily_attendance
        WHERE student_id = ?
          AND attendance_date BETWEEN ? AND ?
          AND status IN ('Present', 'Absent')
        GROUP BY subject
        ORDER BY subject
    """, (student['student_id'], str(start_date), str(end_date))).fetchall()

    holiday_count = conn.execute("""
        SELECT COUNT(*) AS total
        FROM attendance_days
        WHERE student_id = ?
          AND attendance_date BETWEEN ? AND ?
          AND day_type = 'Holiday'
    """, (student['student_id'], str(start_date), str(end_date))).fetchone()['total'] or 0
    conn.close()

    if view_mode == "Monthly Calculation":
        st.subheader(f"🎓 Official Monthly Attendance — {selected_month}")
        if official:
            st.metric("Official Percentage", f"{official['percentage']:.2f}%")
        else:
            st.info("Admin has not entered the official percentage for this month yet.")

    st.divider()
    st.subheader(f"📝 My Self Attendance — {range_label}")

    if rows:
        data = []
        total_all = attended_all = 0
        for r in rows:
            total = r['total'] or 0
            attended = r['attended'] or 0
            absent = r['absent'] or 0
            pct = (attended / total * 100) if total else 0
            total_all += total
            attended_all += attended
            data.append({
                "Subject": r['subject'],
                "Total Classes": total,
                "Present": attended,
                "Absent": absent,
                "Attendance %": f"{pct:.2f}%"
            })

        overall = (attended_all / total_all * 100) if total_all else 0
        st.dataframe(data, use_container_width=True, hide_index=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Total Classes", total_all)
        with c2:
            st.metric("Present", attended_all)
        with c3:
            st.metric("Absent", total_all - attended_all)
        with c4:
            st.metric("Self Attendance %", f"{overall:.2f}%")
        st.info(f"🏖️ Holidays in this range: {holiday_count}. Holidays are not counted as classes.")
    else:
        st.info("No self-attendance records found for this date range.")
        if holiday_count:
            st.info(f"🏖️ Holidays in this range: {holiday_count}. Holidays are not counted as classes.")

    st.caption("Your self-attendance is only for your personal reference. Admin's official monthly percentage is separate.")


# ==========================================================
# STUDENT DAILY ATTENDANCE
# ==========================================================

def student_daily_attendance():
    student = get_student(st.session_state.student_id)
    st.title("📝 Mark My Attendance")
    st.caption("Use the calendar to mark today or correct a previous date. Holiday dates are not counted in attendance calculations.")

    selected_date = st.date_input(
        "📅 Select Attendance Date",
        value=date.today(),
        max_value=date.today(),
        key="self_attendance_date"
    )
    selected_str = str(selected_date)
    day_name = selected_date.strftime("%A")

    conn = connect()
    day_record = conn.execute("""
        SELECT day_type FROM attendance_days
        WHERE student_id = ? AND attendance_date = ?
    """, (student["student_id"], selected_str)).fetchone()

    timetable = conn.execute("""
        SELECT start_time, end_time, subject, room
        FROM daily_timetable
        WHERE year = ? AND branch = ? AND section = ? AND day = ?
          AND (semester = ? OR semester = 'Current' OR semester = '')
        ORDER BY CASE start_time
            WHEN '8:40' THEN 1 WHEN '9:30' THEN 2 WHEN '10:20' THEN 3
            WHEN '11:10' THEN 4 WHEN '12:00' THEN 5 WHEN '12:50' THEN 6
            WHEN '1:50' THEN 7 WHEN '2:40' THEN 8 WHEN '3:30' THEN 9 ELSE 99 END
    """, (student["year"], student["branch"], student["section"], day_name, student["semester"])).fetchall()

    existing = conn.execute("""
        SELECT start_time, subject, status
        FROM daily_attendance
        WHERE student_id = ? AND attendance_date = ?
    """, (student["student_id"], selected_str)).fetchall()
    conn.close()

    existing_status = {(r["start_time"], r["subject"]): r["status"] for r in existing}
    current_day_type = day_record["day_type"] if day_record else "Class Day"

    st.write(f"**{day_name} | {selected_date.strftime('%d-%m-%Y')}**")
    day_type = st.radio(
        "Day Type",
        ["Class Day", "Holiday", "Weekly Off"],
        index={"Class Day": 0, "Holiday": 1, "Weekly Off": 2}.get(current_day_type, 0),
        horizontal=True,
        key=f"day_type_{selected_str}"
    )

    if day_type in ["Holiday", "Weekly Off"]:
        label = "🏖️ Holiday" if day_type == "Holiday" else "🛌 Weekly Off"
        if st.button(f"Save {label}", use_container_width=True):
            conn = connect()
            conn.execute("""
                INSERT INTO attendance_days (student_id, attendance_date, day_type)
                VALUES (?, ?, ?)
                ON CONFLICT(student_id, attendance_date)
                DO UPDATE SET day_type = excluded.day_type
            """, (student["student_id"], selected_str, day_type))
            conn.execute("DELETE FROM daily_attendance WHERE student_id = ? AND attendance_date = ?", (student["student_id"], selected_str))
            conn.commit()
            conn.close()
            st.success(f"{selected_date.strftime('%d-%m-%Y')} saved as {day_type}.")
            st.rerun()
    else:
        if current_day_type in ["Holiday", "Weekly Off"]:
            if st.button("📚 Change back to Class Day", use_container_width=True):
                conn = connect()
                conn.execute("DELETE FROM attendance_days WHERE student_id = ? AND attendance_date = ?", (student["student_id"], selected_str))
                conn.commit()
                conn.close()
                st.rerun()

        if not timetable:
            st.info(f"No timetable has been added for {day_name} for your section yet.")
        else:
            st.subheader(f"Classes on {selected_date.strftime('%d-%m-%Y')}")
            for i, period in enumerate(timetable):
                lookup = (period["start_time"], period["subject"])
                saved = existing_status.get(lookup)
                options = ["-- Not Marked --", "Present", "Absent"]
                default_index = options.index(saved) if saved in options else 0

                status = st.selectbox(
                    f"{period['start_time']} - {period['end_time']} | {period['subject']} | Room: {period['room'] or '-'}",
                    options,
                    index=default_index,
                    key=f"self_att_{selected_str}_{i}"
                )

                if st.button("💾 Save", key=f"self_att_save_{selected_str}_{i}"):
                    if status == "-- Not Marked --":
                        st.warning("Please select Present or Absent first.")
                    else:
                        conn = connect()
                        conn.execute("DELETE FROM attendance_days WHERE student_id = ? AND attendance_date = ?", (student["student_id"], selected_str))
                        conn.execute("""
                            DELETE FROM daily_attendance
                            WHERE student_id = ?
                              AND attendance_date = ?
                              AND start_time = ?
                              AND subject = ?
                        """, (
                            student["student_id"],
                            selected_str,
                            period["start_time"],
                            period["subject"]
                        ))

                        conn.execute("""
                            INSERT INTO daily_attendance
                            (student_id, attendance_date, start_time, end_time, subject, room, status)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            student["student_id"],
                            selected_str,
                            period["start_time"],
                            period["end_time"],
                            period["subject"],
                            period["room"],
                            status
                        ))
                        conn.commit()
                        conn.close()
                        st.success(f"{period['subject']} saved as {status} for {selected_date.strftime('%d-%m-%Y')}.")
                        st.rerun()

    st.divider()
    st.subheader("📈 Quick Calculation")
    month_start = selected_date.replace(day=1)
    if month_start.month == 12:
        month_end = date(month_start.year + 1, 1, 1) - timedelta(days=1)
    else:
        month_end = date(month_start.year, month_start.month + 1, 1) - timedelta(days=1)
    conn = connect()
    summary = conn.execute("""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) AS present,
               SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END) AS absent
        FROM daily_attendance
        WHERE student_id = ? AND attendance_date BETWEEN ? AND ?
          AND status IN ('Present', 'Absent')
    """, (student["student_id"], str(month_start), str(month_end))).fetchone()
    day_offs = conn.execute("""
        SELECT day_type, COUNT(*) AS total FROM attendance_days
        WHERE student_id = ? AND attendance_date BETWEEN ? AND ?
        GROUP BY day_type
    """, (student["student_id"], str(month_start), str(month_end))).fetchall()
    conn.close()
    off_counts = {r["day_type"]: r["total"] for r in day_offs}
    holidays = off_counts.get("Holiday", 0)
    weekly_offs = off_counts.get("Weekly Off", 0)

    total = summary["total"] or 0
    present = summary["present"] or 0
    pct = present / total * 100 if total else 0
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Classes Marked", total)
    with c2: st.metric("Present", present)
    with c3: st.metric("Absent", (summary["absent"] or 0))
    with c4: st.metric("Monthly %", f"{pct:.2f}%" if total else "-")
    st.caption(f"🏖️ Holidays: {holidays}  |  🛌 Weekly Offs: {weekly_offs} (not counted in attendance).")


# ==========================================================
# ADMIN MONTHLY ATTENDANCE
# ==========================================================

def admin_monthly_attendance():
    st.subheader("📅 Official Monthly Attendance")

    month = st.text_input(
        "Month",
        value=date.today().strftime("%Y-%m"),
        help="Use YYYY-MM, for example 2026-09.",
        key="official_month_view"
    )

    conn = connect()
    rows = conn.execute("""
        SELECT s.name, s.student_id, s.year, s.branch, s.section,
               m.percentage
        FROM students s
        LEFT JOIN monthly_attendance m
          ON s.student_id = m.student_id
         AND m.attendance_month = ?
        ORDER BY s.name
    """, (month,)).fetchall()
    conn.close()

    data = []
    for r in rows:
        data.append({
            "Student": r['name'],
            "Student ID": r['student_id'],
            "Year": r['year'],
            "Branch": r['branch'],
            "Section": r['section'],
            "Official Monthly %": f"{r['percentage']:.2f}%" if r['percentage'] is not None else "Not updated"
        })

    if data:
        st.dataframe(data, use_container_width=True, hide_index=True)
    else:
        st.info("No students added yet.")

# ==========================================================
# STUDENT TIMETABLE
# ==========================================================

def student_timetable():
    student=get_student(st.session_state.student_id)
    st.title("📅 Full Timetable")
    st.write(f"{student['year']} | {student['branch']} | Section {student['section']} | {student['semester']}")
    conn=connect()
    row=conn.execute("""SELECT * FROM timetable_images WHERE year=? AND branch=? AND section=? AND (semester=? OR semester='Current') ORDER BY CASE WHEN semester=? THEN 0 ELSE 1 END, id DESC LIMIT 1""", (student['year'],student['branch'],student['section'],student['semester'],student['semester'])).fetchone()
    conn.close()
    if row and os.path.exists(row['image_path']): st.image(row['image_path'], use_container_width=True)
    else:
        old=get_timetable(student)
        if old and os.path.exists(old['image_path']): st.image(old['image_path'], use_container_width=True)
        else: st.info("No timetable uploaded for your section and semester.")

# ==========================================================
# COLLEGE INFORMATION
# ==========================================================

def college():

    st.title("🏫 College Information")

    st.subheader(
        "Annamacharya Institute of Technology & Sciences, Tirupati"
    )

    st.write(
        "📍 Venkatapuram, Renigunta, "
        "Tirupati, Andhra Pradesh - 517520"
    )

    st.write(
        "📞 +91-9948661276"
    )

    st.write(
        "🎓 B.Tech - Undergraduate Programme"
    )

    st.markdown(
        "[🌐 Official College Website]"
        "(https://aits-tpt.edu.in/)"
    )


# ==========================================================
# MAP
# ==========================================================

def college_map():
    st.title("🗺️ College Campus Explorer")
    st.caption("Search a place to see its block and floor. More rooms and class details can be added after you collect photos.")

    # Exact campus model supplied by the user, embedded so it works after deployment.
    CAMPUS_MAP_B64 = """iVBORw0KGgoAAAANSUhEUgAABXgAAAOECAIAAACU6c44AAC2oElEQVR4nOzdd3wT9ePH8UtHuictlNVBy96bskFBpiwBBVlfJ+6ve/6++vWrfhVc6FcUFxsRQZQhe+9RZoGWUkpZBVq698jvj2C4Xto0TS7JJXk9H/0j98nd5XPNZdw7n6FKy0sVAAAAAAAA5OBi6woAAAAAAADHQdAAAAAAAABkQ9AAAAAAAABkQ9AAAAAAAABkQ9AAAAAAAABkQ9AAAAAAAABkQ9AAAAAAAABkQ9AAAAAAAABkQ9AAAAAAAABkQ9AAAAAAAABkQ9AAAAAAAABkQ9AAAAAAAABkQ9AAAAAAAABkQ9AAAAAAAABkQ9AAAAAAAABkQ9AAAAAAAABkQ9AAAAAAAABkQ9AAAAAAAABkQ9AAAAAAAABkQ9AAAAAAAABkQ9AAAAAAAABkQ9AAAAAAAABkQ9AAAAAAAABkQ9AAAAAAAABkQ9AAAAAAAABkQ9AAAAAAAABkQ9AAAAAAAABkQ9AAAAAAAABkQ9AAAAAAAABk42brChir1/jJtq4CAAAAAAC2tHfFEltXoWaqtLxUW9fBEPIFAAAAAAAklJw4KDdoIGIAAAAAAMAAZcYNSgwaiBgAAAAAADCS0uIGxQ0GScoAAAAAAIDxlHYdrawWDUr77wAAAAAAIAiC+8VbhlcojQq1Tk2qo5x2DQoKGkgZAAAAAAAKUWOyYJhNcgeFZA1KCRpIGQAAAAAASmBmxCBm/bhBCVmDIoIGUgYAAAAAgG0ZzhfOnj1rePOWLVsauNeaiYPNswbbBw2kDAAAAAAAG6ouYqgxXKhOdaGD1eIG22YNbjZ8bAAAAAAAbEs/ZTA5X9DfgyRxcL94y+ZjRlqBjVs00JwBAAAAAGATlogYqqTfwMEKcYMNGzXQogEAAAAA4HQkKYOFIgbxzsVxg2M3bbBliwaaMwAAAAAArE+cMlg0YtAnjhssnTXYqlGDi00eFQAAAAAAm7BhyiB5RBnn0VQUggYAAAAAgLOwbcqg/7gOmTXYrOsE/SYAAAAAANaku6q3VcQgoetGYbk+FDbpPUGLBgAAAACA41NayiCIauJg7RoIGgAAAAAADk6BKYOWQ2YNBA0AAAAAAEdmL9fw9lLPGhE0AAAAAAAclsmjP957772hIh9//LFkhcWLF+vubdeunck1dLyxIQkaAAAAAACOz8xOE99+++3t27flqoyE0jp0mImgAQAAAADgmGQcmiEvL+/rr782u0bVcqTBGggaAAAAAAAOSPYr9h9++OHWLWukAPaeNRA0AAAAAAAcmVwdEwoLCz///HNZdlUlh+lA4WbrCljPxCEjP3juFf3y+554+MLlVAMb+vv4xq1YLylMS791z6MPFZeU6K+/7cdl4fUb6haTr6QOfvxhi+5QQt4jFQQhPilx1HOPVreVp9pjz6KVgX7+kvIbGbd6TRln4OHMqao+Hy/v/l17dGndrl2zliFBQYF+/p5qj7zCgvTM2+dTU+LOnN519GBSaop4E/3jLSwqajt2cJX7bxYRtX7uAnFJjU+EYIHnQqu8vDy/qDAzOzspNSXu7Ol1u7ddSbuuuzfQz3/Dd4tCAoPEmyxZt/pf//usuh1OH/XA2088Jy4pLSsd9eyjiZcumn8sNTLmibDcq6Zrm3bD+gxs27R5o7AGft4+bq6uRSXF2Xm5NzPSU9OuX7iccvZC0vGEM7ezs3SbbJq3uEmj8Foe5V3rdm17/r/vVnlQ4gO3zqNInPljq9rdXVzSbtx9BYWFFq1PjYbNnCY+FU3QPLJJn87durXtENWwcaCfv7+Pb35RYVZO9tWbN47En9x3/Ojh0ycMbG7ROiv5H6uE91VLf2IKFjg9DByyRWuiT+3u3rtTt86t2nRs0bpendAAPz8/H9+S0pKCwsIbGemXrl05k5x0JP7E8XNnS8tKtZtY6BPEjphw2ldJmV/GanyjKCopzs3Pv3rj+umkxI17dx44eUyj0RhTSdM+WfSZ8KFsJDv6livX0wRB7kYBarW6pKREEIQFCxY888wzDRo0kHHnVXK/eKs0KtTSj2IhThQ0jBs0tMrysfcOnfXzd7XdW1hI6LT7H5j321Kz6yX/DuU9UkEQWsc069iy9bGz8VXeO3LAvfrvv0aSpap1AoMef2DSxCEjfL19JHcF+PoF+PpFN44Y0qvfm489fTLx3HtzvziRcMa02ppA9udCy9XV1d/H19/HN6JBw3t69Hpx2mO//PXnh99/rf3anZWb885Xs+e+84F4k0nDRq3dueXw6ZP6e2tUL+ylaY9LCr9aukDyHdFCx2IOM1810Y3DP3rh9U4t20jKfby8fby8G4TW69Cita5wyJNTjflmCaXp3Krts5Nn9O7YRVKufQWF128Y277Ts5Omn01O+mb5or92b7dJJRVIye+rgnyfmMo5PWSviZ+Pz4zREyYNHy2JDARB8PLw9PLwrBMY1Cq66dA+AwRByM7L/Wv39n9983l5ebmFPkHsgrynvR19GRPzVHt4qj1Cg4I7tGj98IgxCSnJb375iXVe4Lb6UFb4t9wq2fBpsl+yNBN46KGHli1bVlJSUlJS8umnn3766afm77NKZ8+ebdmypYV2bjXO0nUiskEj/XcurTED73N1MeX/8MSEyQG+fubVS/4dWuJIBUGYMrLa1HbqyLGm7VOWqvbu1HXdN/MfGTtR/2uBvnbNWnRq2brG1eRioedCn6uLy+Tho+e+84FKpdKWbN6/+88dW8TrqFSqD59/zUOt1t/8P8++4uXpKS45nZTw3Yol4hKrHUttmfyqaRYRtXzWN9UdlD6Xv/+3sBcqlerph6Yum/WV/sWbvpZNYr56471ZL73p5eFZ48oOT8nvqzpmfmIq5/SwRE26tmm/7pv5z02eoZ8yVCnA1+/BoffrPiBk/wSxC/Ke9nb0Zcyw5pFNls/6emD3XpbYuZhtP5QV+y3XSFZ7mtCgQYNp06Zpby9btuzSpUu2rY/COUvQUF2mKAhC3TohvTp2NWGfAb5+T0yYbEalLLJDSxypIAhDe/er8vtKl9btWjZpato+za/qqIGDf35/tpFfpKzPQs9Fdfp27n5//3t1i/+e+8WtzEqz70Q1bPzc5BmSrR4YNKx3p0o1KS0rffXTD8vLy8WFVj4W45n2qnFRuXz6ytuB/jL8+APFenfmC/+c8qiLqhYfc2PuGfLDex+7uTlRWz99Cn9f1THzE1M5p4fsNRnSu/+Sj79sEFrPnFrJ+wmifLKf9nb0ZaxGbm5uX77+r7AQCzbetvmHsjK/5daKFZ4meyTjZBM6//znP728vARBKC0tnT17dufOneXas4QDTD/hFF+nXFQuowfeZ2CFcYOG7jp60IQ9T71/3MI/V6aly/b0m7lDyx2pu5v7g0Pv/3rZAkn51Ptr6J9WHfOr2qNdx49feF2lF2lv3r/7960bjyecyczO9lCrQwKD2jZr0btj12F9Bkh+dbEo2Z8LXe9HF5VLUEDAwG4933zsGT+fSj+8jB543x/bN2tva5u/fvt/H4pXeHTsg+t2bTtz4bx2MSQw6I3HnpY80Jwl8yVNXi13XsnChFdNz46dJV8dziYn/e+XhXFnT2dkZard3esEBLaKbtalddv7evVrWDdMsnmVXb5Dg4L3L1ktLsnKyeny4Ajja2WTR1FCfUzu0G7AQ8PunzxijKTwctq1b35ZtOfY4fTMTH9f3y6t2z4y9kHJL07d23V854nnDHRHl73OivrHKvx9VcLkT0xLnx42rEnXNu0/e+Ud/dji+Ln4FZvWHz1z6kbGrcLiYj9vn3p1QlrHNOvSqt29sb2D/AMk68v4CaJ8sp/2dvRlTKj8RuGp9ohq1Hj6qPGSi2QvD8+ZEx7+1zeWGv3OzA9l8ynwW66EEp4maIWGhj766KNfffWVIAgrVqxo2LBhjZs4Lado0dCzQ6f6oXXFJZJ+hvf26O3v42vCnj3VHs9P/odZlZN1h5Y7UkEQHhp2v6urq7ikbp2Q+3r2NW1vZlbVzc3tw+dflfyek19Y8Oi/Xp35/lub9u26mZFeWlaaV5Cfcu3Kmh1bXvv8ox6TR89Z8nNeQYFpFa4tyz0XFZqKjKzMFZvW/fvbLyV3tW3WQry45cAeXe6g5erq+t8XXtc9j+8+/aKk7fGp8+f0uz1b9Lwynwmvmt6Vf0nIzc+f/NpzG/bsuJmRXl5eXlhUdOVG2qZ9uz78/n/9pk946NVntx3cW8EwS/bD38f3lRlPSgoPnjw2bOb0FZvWXb91s7SsNCMrc+PeXRNffnrx2t8la04aNspyvw0qmfLfVyVM+8RUzukhe01cXV0/fP5Vyah7RSXFL8/+4IEXZy7fsCYpNSU3P7+srCwzJ/vcxQsrN//1xpcf95g06ol/v3H49AnJYHJyfYIonCVOezv6MiZRVFJ8Njnptc8/+n3rBsld98b2luUhqqSED2VFfcs1zFZPk92xXEOAZ555xtfXVxAEbcpg0RkotOy0UYNTBA3jBg0TL968nfHmlx+LSzzU6pGiNue1MnbQ0OjGEaZXTtYdyn6kN29n6G7XqxM6uPIb7qRho3RvyhWaivSsTKtVdeKQkeJxxQVB0Gg0z//33R2HD1S3SX5hwZwlP6/YtM74SprDomed1vZD+yQlAb5+kh+y3v/2S0nz11bRTR8b95AgCIN79h3Sq5/4rtKy0lc/+0i/yasVjsVMtX3VSD7+k6+k5uTnVbfy4dMnHn/vDUaCtCPTR4+XfIHLysl55sP/Kywukqyp0Wj+PffLU+fPiQtVKtWzk6ZZvJbKo/z3VX0mfGIq5/SQvSYPDhkZ1bCxZNuXZr2/ettGA9Uor6jYemDvQ68+W1gkfVxZPkEUzhKnvR19GavOknV/SErq1Qn19vIyf89VstWHsmK/5RrJyk+T/ZJ9tsjg4OAnnnhC3n1Wyd7nuXT8oMHX22dQzz7ikjU7tly8elkyuuzYe6vtSaVPPCeNq4vLKzPMPdVk2aEljvTAyWMXr17WLYpHxNE2M9Mt7ji0Py39ptWqOnqAtD3whj07DHwtsDJLPBf6svNyJSUVFRUVmgpxSVZuzttfzZKs9uyk6e2bt3r3qX9Kyr9c/PN5vSav1jkWE5jzqpEMwhQTHlE3uI5sNYOtDendX1KycM3KzJzsKleu0FR8tWS+pLB/11hPtYcFqqZoCn9f1THzE1M5p4fsNRk1UPoMbty7a+PeXSbX0PxPEOWT/bS3oy9jBly7dUO/MNDXUmMo2OpDWbHfco1k5acJYk899VR4+N2pqcW3oeP4QcOIfvdIvhBoo31JwN++eUvjfxU5nZSwYe9O3eK9PXp3NG/MbVl2aIkj1Wg0S0TNNbu2ad88son29rC+A8QD5yxcs8pqVQ3w9WvXXDrjy9L10ljXhizxXOjTn28p5doV/dW2Htj7x7ZN4hIPtfqXWV9JPsVPnT/3fVVNXq1zLCYw51Uj+Wz28fJe8dncGaPHRzZoJGcVYQt1AoOaRURJCv/as8PAJjuPHpTM6K52d+/Suq3sdVMy5b+v6pjz2lfO6SF7TQJ8/do3byXZZPHaWnw0V8nMTxCFs8Rpb0dfxgxoWLeKwUSz8nJk2bk+W30oK/NbrvGs/DRBzJ8BxY3g+EHDuMp5YUJK8tnkJEEQ1u3aVlZWVmnN6oeH1ffp/Hni9oGvzphpXjVl2KGFjvS3zX+Jv9lM+TvuFee+F69e3nvsiNWq2iwyShJ+l5aVxp09bXwFquPl6Zm0fleVf+vnSocIMsBCz4XEPXrzGG07KO1MofXvb78Utw8UBMHdrVIn3pLS0lc/+6i8okLQY51jMY3Jr5pdR6QjMDWsG/bW489u+WHpkV/WLvjgs1dmPHFPj16yzEmOGhl43SWt3/X2E8/Vam8x4ZGSksLioguphiagKi8vP5dyocb9WK7OFlKrSir/fVXM5Ne+dU4Pm9TEcs+gOZ8gCmeJf5odfRkz4OHh0jFKb2akS3IuGdnwQ1mB33KNZ+WnCWL6k03QqEGfgwcNUQ0bS37o0KWJWbk5O45Uaho3esBg42e1vXj1srh7Xtc27QZ262lOVc3coeWONK8g/3dRBDtqwGB/H9+2TVuIfzlZtGaVxuhRecyvap0A6RREtzJvF5eUGFkBS7Pcc6GlUqnqBAaNHzz8rcefFZdn5+X+uOqXKjfJzst9+6vZBvY5Z8lPVTZ5tfSxmMnkV82eY0ckwzLpBPr79+rY5Ynxk7/7v48OLv1j/gefmfnShpXpj5+fkZkp6VKk72ZGut5+AmWslfIp/H1VwuTXvnJOD9lrov8Mpmdm6j+DT06YXF3uc2Bp1b/km/wJonyyn/Z29GWsSp5qjxZR0f/95+v63XA2H9hjzp4Ns+GHsgK/5dbIVk+TfbHExJY2YdeTXDr49JaSpLBCU/Hn9i26xdXbNt3b4+7orHXrhPTu1G3nEWM75s1Z8vOogYO9PO5McfTyjCd2HD5Q47cEC+3Qoke6aM2qycNHa297eXqOGzysVZMY3b0FhYWrtkiHvbVoVf18peP05ttozPMqWei50P4qWN292Xm5T/77DQMjFW07uHf1to1VTrZ0MvHc978tq3Iri55XsjD5VfPcR//30/uzW4rOZH2urq69O3bp3bHLziMH/vnxvw2MTQXlkMz5KghCgd7QevoK9IbB09+PY1P4+6o+0177yjk9ZK+J/jOYV5Bvau2kTPsEqVHfzt1/el86BoT5/vHOK0ZOHCj7aW9HX8Z0DH+70CosLvr218Um7Nx4NvxQVtq33Cop5GkCasWRWzToz2G7/3jcjYy7adC2g3slb1IP1KYJ083bGfNXr9AtNouIGnOvoSlzLbdDSx9pUmrK/hNxusUZo8cP73uPbnHV1g3Gf5uRpaq5edKPFh9vbyMrYGmWfi70FRYX/bpx7bCZ06v7NUDn/W/nSJq/CneavH5YZZNX6x+LCUx+1dzKvD3+xZmfL/qhuqHXxPp16THnzX+bXktYUW6+9O3I++9rUQO8PaXr6O/HsSn5fbVKpr32lXN6yF4TSz+Dtf0EsQvy/tPs6MtYrZSXl7/4yfvXb8kwxqQBNvxQVtq3XNNY52mCln6/CS16T0g4couGXp26hIWEiktWVx7QqKS09K/d2ycOGakruadH7wBfP/3B/Ksz77elDw0dFfj3cCDPP/yPNTu2GN7EEju0wpEuWrMqtn0n7e0GofUkdxm5E7mqmpEt/d0+NCjYQ602v5VvYVFR27HSdmhazSKijOlObIXnQkKlUqnd3cvKy2pcMzsv96ffl7/+yFPiwrU7t1Y3R5T1j8U0Jr8Mi0qK/7ds4bwVy/p07tarQ2ftKFCSabR1enfs0qtjF7m6v1qTRjCrJa2ZDXGNYeB1ZwL9L6l1goJcVC6Gf+uuWydEbz9ZBtaXt84WUqtKKvl9tTomvPatc3oYQ/aaVPkMqt3dS0pLzaro32r7CWIX5D3t7ejLmPGSUlPe/PIT/XErLPHJYsMPZUV9yzVBdU8TZLFlSy0u7k6erOFnP6fiyEHDOL1pY2a99Oasl940sIna3X1E/3vFI9Aalpuf/83yRW8+9rR2sUFovSmiwWNMYNoOrXCkWw/suXbrhuTNVxCEvceOXLhsaPAqS1T1/KWU8ooKca82dzf3Ti3biANpW7HCcyHhqfYYPfC+2Padxv3zybT0Grpv6X95MvB1yvrHYhozX4alZaXbDu7ddnCvIAieao82TZt3ad1ueN8BLZs0lazZr0t3ewwaCgoLNRqNSqXSlajV6irXdFG5qN0rjfFWXlFRVFxs2frJ7YLeZY+Xh2d0eISBPuSurq4tIqMlhXZ9+WQCJb+vVseE175yTg/Za1LlM9ihRetDp46L1//21yXf/rpEe3v1nO/bxDQ3vs61+gSxC/Ke9nb0ZcyAktLS3Py8Kzeunz6fsHn/7r3Hj1YZCljuk8UmH8qK+pZrDCOfJlhCdc0ZdPcePXrUapVROIcNGvx8fAbF9ql5PT3j7h1aq1f74rWrpo9+QPfeNHPilDLRUNgmqO0OrXOk5RUVS9etfnm6dLryWgW9clU1KzfnZMJZyVg7k4aNsvkXYos+F9pfBVUqVZ2AwD6du7807TFxal6vTui3//fhuBeekKsJq9VeQbKQ62VYVFJ8JP7kkfiT3/66+K3Hn50xerz4Xv2vIHahvKIir6BA3CHc1cUlOCDwdnaWZM2Q4GBJSU5ert19d0nPyky8dFEyceDQ3v0NXL/169zd28tLXFJSWnok/pSlqqhIin1fNay2r33lnB6y16TKZ/ChofdLggZF2XX0YMywvjasgIynvR19GZMwrX2WdT5ZrPahrKhvuVWyi2Z0gITDjtEwot89HtVkq4a1a9aiVtNWlZSWfrHoR91ioJ+/eN5dE9R2h1Y70l82rJH8dnHlRlp18ylWScaqrt6+SbLOkN79+3ftYcLOZWSF50Kj0aRnZf6+dcNDrz4r6ebXJqb5w+Y1qBGz2nklC9lfhoIgLF23WlJSWlZz/xRlSryULCnpIBpPW6djC2lhQop0Q7uwYc8OScnUkeMCq5ny2kXl8syk6ZLCHYf3F5XYWVMO8ynzfdUwE177yjk9ZK+J/jM4vN/APp27mVlPxybXaW9HX8bkYuVPFkt/KCvqWy4Uy3BzBuPXcRIOGzToN16y3Lart26S9+t4rXZotSPNyslZu3OruGTputW1mmVDxqou37Am9fpVcYlKpfry9Xf7dan2y4GPl/ezk6aPHzzc5DrUyJpn3eW0a5/89K2k8PmH/yHXLNPWPBZZ1OpV848xE//z7Mttm7YwsE6TxtIRfW7oTSxnLw6cOCYpmTbqAXGTV0EQXFQu00dNkKx28KR0Q7swf/UKSQwX6O//9Zvve6o9JGuqVKp3nnyuXbNKZ4JGo/lqqekDB9gvZb6v1qi2H8HKOT1kr4n+M+iicvnqjfcGdIuVpcIOSa7T3o6+jMlFxk8WJXwoK+pbLuAYHLPrRJNG4R1aVGoIN++3pfpXZTq/zPq6S+t2usXR99w3e/53xjdBr9BUfDp/3rx3/2tabc3ZoZWPdOGalbppe4pLSn7dtNbIDWWvallZ2VtzZv38/mw3t7vnsI+X94///mTz/t2rtmw4kXj2dnaWh7s6JCiobdMWfTp1G9q7v7eX1wfzvjK+zrVi5edCEIQVG9dOH/WAOAX39/GdOXHKRz/8rxb1ror1j8V8tXoZ+np7Pzj0/geH3n/91s3th/cfPxd/7uKFtPRbOfl5nmqPenVCBsX2fnz8ZMlWCm9DbsCKTWufnDBZPKRWr45dvnn7P3OXL0pISVYJquZR0c88NK1rm3birUrLSn/bvN7qlZVBTn7erJ+/ff+Zl8WFPdp1XD93/je/LNpz7HB6Vqa/j2/nVm0fHfdg51ZtJZsvXf/H2eTzVqyvUijwfdUYtf0IVs7pIXtNqnwGfb19vn/3451HDqzetunY2dPpmZkVmopAP/82TVuEBErbtDshWU57O/oyJiMZP1kU8qGsnG+5gGNwzKBhnN5UMdsPGWr7tP3QfvGrPTQouG+X7tsP7Tf+Ebcd2nf49ImubdrXqp7m79DKRxqflGhyd0rZq7r/RNzrX3w866U3JfH5oNg+pvWRM5P1z7ryiopZ87/77v8+EhdOGTl24Z8rr95MM34/+qx/LLIw4WVYP7TupGGjJg0bVeOaFy5f2nvc/kaC1LpyI23hmlWS3q01vlLmr/7NOhNl1Tg9+De/LPxs4Q+12uey9X+2iIyePGKMuDC8fsP//vN1wxsePHns/e/m1OqxFMuEf6zS3leNVNvXvqVPD+P/87LXpLpnsF+XHgZ+ondy5p/2dvRlTEaW+GSx7Yeyor7lQoGM7xPBkJBaDth1wkXlMnpgpeFSsnJz4s4YmvFF/73AhCZMH1cfW5qmxh3a6khNYKGqrt628R//90pGlnR6Kuuz1XOx9cDew6crzaOjdnd/ceqjtd2PmB2dV/pkfxlq5RXkv/LpB2V2O0aDIAj//fGbHYcPGL/+1gN7Z8//znL1sYJ3537xxaIfa9Xw9fetGx7912t2/USbTznvq7VS29e+ck4P2Wtip8+gbZnzT7PrD00z2eqTRWkfys58DgAGOGDQ0LtT13p1Ks1hu+voIcONkRIvXZT8Ajywe6/a9nU/fi5+8/7dtdrEzB3a6khNYLmq7j56aPhT03/6fXleQX6N1Th1/lzc2Xija10LNnwuPvl5rqTk/gGD9GeBMp4dnVf6jHwZxp05FXf2tJHf7I+fi3/wlWdOJp4zu3a2VF5e/vi7r8+eP6/GV0pufv4nP3078/237L0Np0aj+XrZgodeedaY+c/OJic9+9G/Xvn0w8LiIivUTeEU8r5aK7X9CFbO6WGJmtTqGRQE4UbGre9/Wzb5tWeNrbQjMvm0t+sPTTPJ9cli7x/KznwOKFZp1J1npGXLlrLssLZDPMo1JKSu/rojsiMO2HWito2XtHYcPjB5+GjdotrdfUS/exbXcpa+2fO/G9i9l3hCZjMZ3qENj7S2LFrV9KzMD7//35wl8/t16d61Tfv2zVuGBAYH+Pp5eHgUFBbeysxIvpIad+b0jsP7E6ufNsxMNnwujp2N37h313297jb2U6lUrz0yc/pbL9ZqPzp2dF5VyZiX4Z5jR/YcOxLo79+lVbsOLVo1i4hqWK9+3eA6Xp6eanf3wqKi3Pz8i1cvxyclbtq369i5eLub4rFKFZqKb39dvHDNyuF9BnZr2751TPOQwCA/Hx+NRsjNz0vPyjx9PuHQ6ePrd28vLHKci+2jZ05Ne+vF5pFN+nbp3rVN+yaNwgN9/f18fAqKirJys6/evHEk/uTeY0cOnz5h65oqixLeV2vLhI9g5ZwestfE8DOYV5B/7daN5CupZ5OT9p+IMzCnplMx7bS39w9NM8nyyWLvH8pOfg4A1VGl5aXa5IF76Y3pAgAAAACAmdwv3tLeOHv2rJm7Mrl5gvkjNcjVomHviiVm1sQEDth1AgAAAAAAi2LQRwMIGgAAAAAADsjMYRqqa85w9OhRbcqgu2H8tkaSa4AJWyFoAAAAAAA4DouOnqifLFi0aYM9jgQpEDQAAAAAAGCM6jIFulFIEDQAAAAAAByK+ZNcSvo+GOglUd0KJveesOuJLbUIGgAAAAAAqJbxDRZo2qBls6DBJnNsAAAAAACcigmNGsSNEWqbHYjXN6FRg7zDQNrqupsWDQAAAAAARyNLvwPTWijI0q7BfvtNCAQNAAAAAADHVqtmAtpmCDUOymCYbvNaNWqw91ktdWwZNNB7AgAAAABgISY3CpBrqAWT9yNLcwYbXnHTogEAAAAA4JhMmH5C3gEdjd+bA0w2oWPjoIFGDQAAAAAAK1ByxwTZ62bba21aNAAAAAAAHJa4gYAyswZxrRygOYOghKCBRg0AAAAAAMuxl6t3uepp86ts2wcNggL+CwAAAAAAB2bCYA3WIfvQDEq4vlZE0CAo438BAAAAAHBUCswaHDJlEARBlZaXaus63NVr/GRbVwEAAAAA4LDcL97S3T579qytqmGJcRkUkjIIymnRoKWc/wsAAAAAwPEoYWxIx04ZBKUFDYLC/jsAAAAAAAdj26zB4VMGQWldJ8ToRgEAAAAAsBBxHwrBKt0oJKGGLCmD0iIGLeUGDVrEDQAAAAAAS5BkDYLF4gb9dhPmpwzKjBi0lB406JA4AAAAAABkZ9G4QfaIQcn5go7dBA0AAAAAAFhC/y6Dqyw3OXGobuiHHUc2mbZD+0LQAAAAAABAtXGDVo2hg+FxJZ0kYtAiaAAAAAAA4C7DiUOtOFW+oEPQAAAAAACAlJlxg3NGDFoEDQAAAAAA1KDG3MGZkwUJggYAAAAAACAbF1tXAAAAAAAAOA6CBgAAAAAAIBuCBgAAAAAAIBuCBgAAAAAAIBuCBgAAAAAAIBuCBgAAAAAAIBuCBgAAAAAAIBuCBgAAAAAAIBuCBgAAAAAAIBuCBgAAAAAAIBuCBgAAAAAAIBuCBgAAAAAAIBuCBgAAAAAAIBuCBgAAAAAAIBuCBgAAAAAAIBuCBgAAAAAAIBuCBgAAAAAAIBuCBgAAAAAAIBs341ddtXCt5eoBAAAAAACUbOzUEcaspkrLSzW8BvkCAAAAAADQMZw4GAoaiBgAAAAAAECVqosbqh2jgZQBAAAAAABUp7rcoOqggZQBAAAAAAAYVmV6UEXQQMoAAAAAAACMoZ8hSIMGUgYAAAAAAGA8SZLgYuA+AAAAAACAGonzBJcqSwEAAAAAAIynSxVcJMsAAAAAAAAm0GYL1U5vCQAAAAAAUFuqtLxUmjMAAAAAAABZ0KIBAAAAAADIhqABAAAAAADIxoV+EwAAAAAAQC60aAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALJxGTt1hK3rAAAAAAAAHAQtGgAAAAAAgGwIGgAAAAAAgGxcBEGg9wQAAAAAADDf2KkjaNEAAAAAAABkcydooFEDAAAAAAAwhzZbcJEsAwAAAAAA1JYuVXCpshQAAAAAAMBI4jxBOkYDWQMAAAAAADCeJEmoYjBIsgYAAAAAAGAM/Qyh6lknyBoAAAAAAIBhVaYH1U5vSdYAAAAAAACqU11uoErLSzW85aqFay1QHwAAAAAAYJcMN02oOWjQIXEAAAAAAMBpGdn1oRZBAwDAYVgnO6YXHgAASmCT34z5GuDMCBoAwLlY/6sG3zMAALAVmzdL52uAc6p2MEgAgOOxybcNm3/FAQDAOSnhI1gJdYD1ETQAgLOw4Sc9XzIAALAy5Xz4KqcmsBqCBgBwCjb/jLd5BQAAcB5K+9hVWn1gaQQNAOD4FPLprpBqAADg2JT5gavMWsFCCBoAwMEp6nNdUZUBAMDxKPmjVsl1g7wIGgDAkSnwE12BVQIAwDEo/0NW+TWELAgaAMBhKfazXLEVAwDAftnLx6u91BPmIGgAAAAAAACyIWgAAMek8J8LFF49AADsi319sNpXbWECggYAAAAAACAbggYAAAAAACAbggYAcEB20SLRLioJAIDy2eNHqj3WGcYjaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALIhaAAAAAAAALJxs3UFlOKLiS/ZugqAo3lh+ae2rgJgG/MeHmDrKgC28fji7bauAuzMqHvG27oKsJkFCxbYugqO4I+tK2xdhSqo0vJSbV0HWyJfAKyAxMH6Vi1ca+sqGGXs1BG2roKcyBcAHRIHGEC4AFiIckIHJw0ayBcAmyBxsBqCBmsiXwAMIHGAGBEDYAVKiBuccYwGUgbAVnj1wfGQMgCG8RqB1qh7xpMyANahhJebc7VoMHCR89zMmdasCeAM5sydW91dNG2wNFo0WIGBy6dnZwy2Zk0A5fjq503V3UXTBqdl+IInukVbq9UEcEgXzp0ycK+tWjc4UdBQZcpAvgBYQZWJA1mDRRE0WFqVKQP5AqBTZeJA1uCEqksZyBcA2VWXONgka3CWoEE/ZSBiAKxMP24ga7AcggaL0k8ZiBiAKunHDWQNTkU/ZSBfAKxAP3GwftbgFGM0kDIASqD/umPIBtgjUgbAePqvDoZscB6kDICt6L/WrD9kg+O3aJBcyRAxADYnadpAuwZLoEWDhUiukYgYACNJmjbQrsHhSa5qiBgAm5A0bbBmuwYHb9FAygAokOSVSLsG2AtSBsBkktcL7RocGykDoBCSV5812zU4eNAgRsoAKAevR9g7UgagtnjVOAlSBkBRbJU1OHLQwM+kgL3g1Qrl4wdYQF68phwSKQOgQDbJGhw2aKDTBKBwdKCAHaHTBCALOlA4FVIGQDms/3p02KBBjJQBUCZem7BHpAyAOXgFOTDrD2sPwDRWeLU6RdAAAAAAwGpozgAojZVflY4ZNIjbYPOTKaBk4lcovSegTOLW3fwYC5hP/Dqi94TDEP9ASsoAKJP4tWnpRg2OGTQAAAAAAACbIGgAAAAAYDpGZwDskUVfuQ4YNNBvArAv9J6AktFvArAEek84MPpNAEpmtVeoAwYNAAAAAADAVggaAAAAAACAbAgaAAAAAJiI+SYA+2KduScIGgAAAAAAgGwIGgAAAAAAgGwIGgAAAAAAgGwIGgAAAAAAgGwIGgAAAAAAgGwIGgAAAAAAgGwIGgAAAAAAgGwIGgAAAAAAgGwIGgAAAAAAgGwIGgAAAAAAgGwIGgAAAAAAgGwIGgAAAAAAgGwIGgAAAAAAgGzcbF0BAAAAAKhkyfzvtTcmT3/MtjUxgErKhUo6Hlo0AAAAAAAA2RA0AAAAAAAA2RA0AAAAAAAA2RA0AAAAAAAA2RA0AAAAAAAA2RA0AAAAAAAA2RA0AAAAAAAA2RA0AAAAAAAA2RA0AAAAAAAA2RA0AAAAAAAA2RA0AAAAAAAA2RA0AAAAAAAA2RA0AAAAAAAA2RA0AAAAAAAA2RA0AAAAAAAA2RA0AAAAAAAA2RA0AAAAAAAA2RA0AAAAAAAA2RA0AAAAAAAA2RA0AAAAAAAA2RA0AAAAAAAA2RA0AAAAAAAA2RA0AAAAAAAA2RA0AAAAAAAA2RA0AAAAAAAA2RA0AAAAAAAA2RA0AAAAAAAA2RA0AAAAAAAA2RA0AAAAAAAA2RA0AAAAAAAA2bjZugJOLSMr6+ipU0kpKZevX88rKCgoLHR1cfHy9AwNDm4YFta8SZM2zZv7+/pKttqyd+/i33/XLTYMC/vg5Zeru1dM7e7u7eUVFhoaExHRo2PHRvXrV7ma4f0bptFoTickHDxxIuXy5dvZ2UXFxa4uLl5eXsEBAfVCQho3aBAdHh4TGenuVosTz8j6bN+/f8HKlbrFunXqfPLGG9VV8sTZs6cTE5NSUrJycvIKClxdXHy9vesEBTVv0qR9q1YxERHyHuarH310MyPD+EPW8lCrv/vwQ/3/gAHR4eHvPPecbtGcpxIAAAAATEPQYBs3MzJ+Xbcu7vTpiooKcXl5eXlJaWl2bm7SpUs7Dx50dXHp0Lr1jPHjfb29zX/QktLSktLSrJyccxcurNu+fUBs7MOjR7u4yNaq5XZ29txFi86npIgLKyoqSnNzc3JzU65cOXj8uCAIMZGRbz/zjFwPWluHT578bf36G+np4sIyQSguKcnIykq8eHHN1q3NoqImjRoV2ahRlXuwi8MEAAAAAFuh64QN7I+L+7/PPjty8qQkZdBXXlFx9NSprJwc2eug0Wi27du3Yv16uXZYXFLy8dy5ksvvqh+6pqO2EI1Gs3j16v8tXChJGfQlXrz4n6+/3n3okP5dyj9MAAAAALAtggZrO3j8+Lxly4qKi21dEUEQhE27dxcWFcmyq407d9Z4AW9bK//6a8uePUauXFZW9tOKFXHx8ZJy5R8mAAAAANgWXSes6lZGxve//KLRaMSFocHBA3v2bNW0ad06ddTu7gWFhTdv305KSTly8qQxv5wbpuuWX1xSknbr1m/r159KSNDdW15efv7ixXYtW5r5KIIgHDl1SrzYrmXLYf37NwwL8/b0zC8oSL1+/cz58/vj4jKzs81/LBMkXry4dts2cYmrq+u9vXr17tKlXmhoeXn55evXt+7dq+31oKXRaL5ftmz2m2/6iPqtmHaY+qNF5ObnP/uvf4lL/v3ii+ENGhhzLAy1AAAAAEDJCBqs6re//iorKxOXxHbqNGP8eLW7u67Ez9fXz9c3Ojz8vr59r9+8uXrTJheVyvyH9lCrIxo2fGrKlKf/7//EXTZy8vLM37kgCLdu39bd9vX2fn7GDNe/R3/w9/Nr4+fXplmz8cOGHT558uS5c7I8Yq38vnGjeFGlUj07bVqHVq3uLLu7N4uKahYV1ah+/ZV//aVbrbCoaMPOneOGDtWVKPwwAQAAAMDm6DphPYVFRUdOnhSXxEREPPrgg+KUQaJ+3bozH364Qb16ctXBy9NTMo2Fr4+PLHsWN9Pw9PR0rWqMSZVK1a19+0cnTpTlEY2XnZt7NilJXNK/R4+7KYPIiIEDoytPObH/2DHxopIPEwAAAACUgKDBek4nJJRXHiBw1ODBVV6pWk5BYWF2bq64RK4Uo2FYmO52+u3bPy5frpyxDM6cPy8pGRAbW+WaKpVqQI8e4pL027dviWamVPJhAgAAAIAS0HXCeq7fuiVedHNzaxkTY7VH143RIP5NvkOrVnXr1JFl/327dbtw6ZJucffhw7sPH64TFNS4fv0G9epFNWrUNCoq0N/f/Ae6mpY2vZYjFEiyALW7e+P69atbWdKiQRCEmxkZoX//l6x2mAYY+A+8PnNmi+hoiz46AAAAABhG0GA9uZVHQwjw9XVzdRWXnDp37tMfftDf0Nfb++t//9u0BzVwUVq/bt2p48aZtlt9fbt1O5uUdKByR4OMzMyMzMzjZ84IgqBSqaLDwwf37dutfXu5HtRIeQUF4kV/Pz9V9cNeBPj5SUpy8/N1t5V8mAAAAACgBHSdsB5NzatYiZen5/ABA95+5pnggAC59qlSqZ6cPPkfEyaEBgdXuYJGo0m6dOmbRYvm/PxzWXm5XI9rFE0t/veGV1X0YQIAAACAAtCiwXokozBm5+WVlZdLGjVYh0ajqdBoPDw8ZN9z327d+nTtmnTp0pnz55NTUy9fu3Zbbz7LuPj4PzZvHjdkiOyPXh3JgJe5eXkajaa6Rg05lcewEATBT2+8TGUeJgAAAAAoAUGD9dQPDRUvlpWVJSYnt2ra1Po1KSou/mvHjrRbt56bPt1AJwLTqFSqppGRTSMjtYvZubmnExLWbd9+7cYN3To7Dx40+Qq8YVjYB1V1Btm+f/+ClSur3KReSIh4sbik5Mr1640bNKhyZfEQDFpVDmNh6cM0oLr/AAAAAAAoAV0nrKd1s2aSOSb+3LJFPDRj2xYt5s+ePX/27K/ee0+uB20YFjZ/9uwfPv74Py+/LBk14Fh8/Na9e+V6oOoE+Pn16tLl5ccfFxfm5ObmFxZa+qF19Afd3HHgQHUr7zh4ULwYEhwcasR4mUo4TAAAAABQAoIG6/H28urctq245NyFCwtXrZLMeWkJbq6ujcLCZj78cKfWrcXlv2/aJNeV8DeLFu04cKCktLS6CkiaTrjI3ZLCgEB/f0nWsG3//pPnzumvuW779qSUFHFJbMeO4kUlHyYAAAAAKAFdJ6xq3NChcadPi8cI3L5/f+LFi/f26tUyJiYoIMDNza24uDj16lVLPLpKpZo6btyZpKSi4mJtSX5BwZotWx4cOdL8nV+/devQiRPL/vyzQ6tWrZs1i2rcODgw0NPDo6Cw8OLly79v3Chuu+Ht5eXl6Wn+gxpvzH33nU1K0i1qNJovf/55UO/evbp0CQsNLS8vv3z9+ta9eyXTSXh5eg7p109covDDBAAAgCW0bNH87der7bu64Ie5hYVFGbdvJ19MOXw07tTpM5pqBiN3dXX5+ovZ/nrTnL38+jvX09JMeHSNRlNcXJyXn3/9elri+Qv7Dx6u1X5++Hnh9p27JavVCQ5+6/WX69Wt1O974+atC5f8YsxOqqztp19+HXfshH6Vlsz/XrzYu2ePPfuqbXosCEKTqMg2rVs1axodVq+er4+Pt7d3eXlZYVFRRsbt62k3ki4knzl77srVawb2AOsgaLCqeiEhj0ycOG/ZMvFbz9W0tOoGF5BdoL//fX37/rF5s65ky969g3r3rhMUVN0mBibIFAThq/feE4+VWFxScvD48YPHjxuuRsfKDSusoFlU1PCBA9dt26YrKS8v37Bz54adO6vbRKVSPfbQQz7e3vp32fYwa/WMyLIhAMilsKj05Y9X12qTt2YOblC3FnMkGX4IVxcXtdrVx0sdGuzbuH5Qm6b1o8NDqlxTfz9qd7fP3xxjfE3Ert3MPpOUdv7SrZsZeQWFJQVFJR5qNx8vjzqB3tHhIc2j6sZEhNa8F5GikrL489cvpKZfuno7J6+ooLCkpKzcU+3u7+sZFurfpHGdVjFh9UP9TTuivILirxbtupKWJS708/F4dkq/hvVkm68KcCRubm5+fr5+fr6REeED+/dNvXzlux9+TrmUqr9m+3Zt9VMGQRD69Ir9deXvJjy0SqXy9PT09PQMqVOnbZvWY0eP3LZj14LFy8pNnf4spE6dt19/OTS00nvjhk1bFi1dbtoOtSaOG3Ps+Mnq8hdjdOzQbtSIYU1joiXlrq5qtVod4O/fJCqyV2x3QRCuXLm64vc/jhw9VtVuYCUEDdYW26lTWXn5olWrqmt+b2lD+/ffvn9/Tl6edrGsrGzlhg2PP/SQ1Srg5ek5ZvBgqz2czgNDhxYXF28xblgKNze3qWPHdjIjKbDVYQIADCivqCgsqigsKk3PzD974camPeciGwZPGd01LMS/5o1Nknw5fd2OM+eSb0jKC4tKC4tK0zPzEi7eXL/zTMN6gUP6tuzUqlGNO8zNL96899zeuItFxdIvEgVFJQVFJWnpOcfPXlm16UREg+AJwzpGNqx6Pubq5OQVzVm48/qtHHFhgK/nc9P6We6/BDiY8MaN3nnj1f/O/vx80gXJXX169axyk949e6xYtdqc63AtlUp1z4B+np6e33z3gwmbh4bUeev1V0JDKo1Qtn7DpiW/rDCzYo0aNewV291wa4XqqNXqqZMfHNCvj/GP1bF9O4IG22KMBhvo07Xruy+80LZFixpnfFC7u/fu2vW1J5+U8dE9PTzuHzRIXLI/Li71mrnti7q0rTqdlQgLDX195syQ4Np96ZGFSqV6eMyYp6dMqXIWCbGYyMi3nn66b7du+ncp/zABALWScvX2pz9uz8jKl33PGkHYsOvsZz/v0E8Z9F29kfXjiv0LVx8qKTX0I+TZCzc+mLtp6/5E/ZRB36Vrty9ezqhFjQUhK7fw8/k7JClDkL/3P2cMIGUAasXT02Pm44+4u1X6WdfHx7tjh3ZVrl+nTnCrFs3levResd2jm0TVdqu6oaHvvPGqJGVY+9dG81MGrQfGjHJ1da3tVq6uri8+/7TxKQMUghYNttGgXr2XHn302o0bcfHxiRcvXr95M7+goKi42EOt9vb0rBca2rh+/ZYxMa2aNlW7u8v+6AN69Ni0a9fNjDtfPjQazfK1a1+pPGNCbY0aNGjkPfckp6aeTUq6eOXKjfT0rJwc7WAQnh4ewYGB4Q0adGzVqmPr1ia8v8ioa/v2Xdq1O37mzOnExKSUlKycnPzCQheVytfbOyQ4uGlUVMfWrWMiIqrb3F4OEwBgvIKiktVbTj3yQA95d/vr+rhdh6U/Zhp28MSl29kFz07pK5mmSuvQyUsLfz9k7s+d1cvIyp+zcGd6ZqXMpU6gz/PT+tUJpG8dIPXDzwsfnTFVe/ufr7zZM7bb6PtHiJOFenVDO3XscPDwEV1JbPdukuhBrE+v2PizVYxWXt2ja4dF8PT0jI6KnDZlUsMG9cUrdO7Y4ULyReMPp169um+/9nJwcKX+1H+u+2v5ilXG78Sw0NCQgf37bN66o1ZbTZ8yqW3rVpLC62lpm7fuOHsuIT3jdnFxsY+3d3BwUHSTqHZtW7dv19bAPxlWw3NgSw3q1WtQr15tt7q3V697e/Uy7V4tV1fXT954w5w9VMnFxSUmMjImMtKEbQ0wsj4DYmMHxMYas0OVStWxdWuTB1CQ5TD9fHzmz55t5MomPyMmbwgAVmPOwAcmPERpWfn1WzmrNp04n3JLvM6phGtl5RVurrK19NxzNFk/ZQgJ8hnSp2WL6Hp+Pp6FRaUXUtO37k9Irtzo4HzKrRV/HX9weCfJtokpNxf/cUQ/ZWjfomH39hGRDYN9vD3Kyspz8otTr90+e+FGXPyVktIy4yt863belwt2ZuYUiAvrBvs+P61/oL+X8fsBnNPNW7dW/7murKz8oQnjxOVtWrcUBw19elX6sno+6YJ4xIGuXTr/vGhp8d+jthupqKgo/uy5eT/+/N47b4rLJUM5GlY/rN5br78cFBgoLly9Zt2KlatrVZkajb5/xM7d+0pKSoxcPzIiXL8tw5p1G35d+XuFaOa+nNzcnNzclEupW7fv9Pbyundgf09GZLc1uk4AAABn4e7mGl4/6PGJPSVNBkrLyrNz5ZnvWRCEwqLS1VtOSgqbRoa+NfO+2I5RQf7ebq4ufj4eHVo2fPEfA/t1jZGsuefIBclAjOUVFUv+PCqZD9tT7fbUpN6PT+zZvkXDAD8vN1cXTw/3usG+XdqETxnV9aOXRw7v39rTw6iflNLScz6fv0OSMoSF+L8wYwApA2C8o3HSQQGCggJ1t+uH1YuJbiK+96cFi/Py77Yh8vT06NpZGjIaKfnipbKyStmi2kNt5LYN6oe9/forkpTh9z/Xyp4yCIIQGBAwZNA9xq8/ZtQISWfz7Tt3/7JiZUXl90OxgsLCP9f9ZdrImpARQQMAAHAu3p5q/etn88dg09l+8HxhUaUxFHy81I+Oj1W7S3vVqQRh/NAO4Q0qtVXWCML6nWfEJXuPXkzPzJNs+I8HerRuWqmltJin2m1Yv1axHWvupH31RvYX83dIcpaG9QL+OaN/gC8/CQK1Ymj8td6VmzNcvnI19fKVw0fixIWSJg+1e2xVpSu77Oyc6tYUa1C//luvvxwYWGlCmVWr1/y26g+Ta6LvaNxx3e0Rw4Z4VzWtmz53d/d2bSq1QS4qKv7lVyvN1gczETQAAADnUlhUmpVT6brazdUlKMCoL77GOHbmiqSkf/emvt4eVa6sUqmG95P25os/f7207O6okIdOXpKs0LFVIwMpg/FSr2d+uWBHbn6lptrh9YOen9a/ugoDqE6Xzh0kJZmZWdobKpWqd89KA8HsP3hIEIT9Bw+LC1u3aiEZJcFIMU2iXCt3/jp7LsGYDYcNGRQYUCll+G3VHytX/2lCHQxY9ceakpI78auPj/fIYfcZs1WzmGi1ulK7jOMnT4nbgEDJCBoAAICzKCuvuJyW9f2v+yTdELq2Da9y/EUT5OYXX7uZLSnsaHDeylYxYR7qSn0cysorLqSma28XFJVcunpbsknvLtKZ5E1QVl4+Z8HO/MJKnaWjGtV5blo/Hy9jG10DEAQhNDRk9Mjh48aMkpSfjj+rvdGyRfOQyhOfHTh0RBCEs+cScnJydYUqlap3bO0GpvX09GjTuuXjj04XF966lX6oclsJI/268vff/1xrwoaGZWVlb9q6Tbc4ZPC9Af41T2RTp450BrcLycky1wwWw2CQAADAZkpKy55+r9qJ0wZ0b/rAkA4WfQhBEMJC/EcPqnrCOROk3ZI2V1a7u4aFGJoa2cVF1bBegGRUyOu3clo0qScIwrWbORWVu3W4ubo0aVzDVM3GqKjQFFaeJjMmPGTm5D6ear4fAjXTTTkhCMIXsz7SX+HGzVtHjx3X3pb0ibiYcunGjZuCIFRUVBw8fHTQPf11d/XuFfvnur+MeXRxBcRycnI/m/NNaWnNk+BKJF9M+XNtzQ9tmjVr/xrYv6+3l5cgCGq1evT9wxcsXmZ4E/1J5XNy8iQlfXv3fOLRGVVu/tOCxVu37zS1vjAXLRoAAIDz6tkx6uVHB8rYTSCvQDpivJ+Pp2QwM30BftIxI3T7ycsvktzl7+vp7ib/JMpNI0OffrgvKQMgi6Ki4rnzftQO0KhWq7t1qTTK4wFRj4kDhyr1nmjYoH6TqEjTHrS4uHjr9p1vvPNe6uXLJmzeJCrysX9Mq/H9yjR5+fnr1m/ULQ7s3zc0pKbAtIqaWG6GX8iMoAEAADivw6dS12w7LR4QwUySNgKCIHgYcenu4S5dp+jv4SQLikzZoQluZxXk6oUaAEyQevnK+x99cj7pzhy33bp0ksy2qO03oZWQeD4zK0t8rzlDQlZUaAqLTH8h9+vTy3JZw1+btmTn3Gnz5ebmpt/TRCInR9pAzE+vjQMUi6ABAAA4r9Ky8p2Hkr5dtresvNrJ0mrFy8NdUlJcUlblmpXWKZWu4+l5Zz/enqbs0AQZWflfzN8hmd4CgDHKy8vz8vJSLqVu37n7k0+/fPP//p1yKVV3r2S+iaQLyekZd7tKaTSag4eOileI7d7N1dWUVkseHh6D7un/1msvubtL3zeqo0tDdPr16fX4I9MtkTUUFxf/8ec63WLvnj0aNWxgYP2MDOnwNNFNap5JBwpB6zgAAGAzane3z98cY7WHqKjQZOUWnr2QtmbbafFUC+eSb2zdn3hf7xbmP5x+L4zc/CKNRmP4W7tkdknxfnx9pHNM5uQVlZaVW6L3xO3sgs9/3vH8tH516/CzIVCDH35eqBslYeojT1a3WlBQYJtWLcUlMdFNlsz/3sCe/fx8O7ZvdyTumOFH375zt7e3d0x01IPjx0WEN9bdFd0k6qGJDyysaQQErZ279x44dGTKpIniwr69e6oE4bsf58s476/W1h27hg4ZrO00oVKpxo8bbWDlxKQLJSWlavXd0KRDuzZeXl6FhXffMHft2bdrzz7t7e/nztGOAQEloEUDAABwFi4uquAA716dmswYJx3XfV+cPIOZh4VKL9FLSsvT0nOrXFmrokJz9YZ0oor6of66Gy6VQ4qy8grJyJGmUbu73X9PW0lhVm7h5/N3pKVLWywDME3vnj1MaB1gZO+JgoKCk6fiP/h4triJhCAIgwb2N9xYQGzDpi2Llv4irUDvnk9YoF1DWVmZeO7MLp06Gli5tLT0dPwZcYmXl9cDY+6Xt0qwEIIGAADgdJpF1VVXHhYhPTO/oKikuvWN5+fj2aBugKTw2JkrBjY5k5Qm6Q3h5uoSHR6ive3jpY5oKJ3jbc8RaWtn09zXu8XYwe0lhTl5RV/M36E/SScAE/TuacqACx3at/X19TVy5fz8gkVLlotLXFxcJoyrRWOxDZu2LlxSVdbw6AzZs4Y9e/dfuXrNyJX159ocMvje+4cPlbdKsASCBgAA4Hw0Gv3Ry4uK5Rn7oGOrRpKSHQfP5xdWnWJoNJr1O89ICls3rS/uGdGtXYRkhWNnrsSfv252TQVBEO6JbTZ+qPRHxdz84i/m77iSliXLQwBOq0lUpPEtC8Tc3Nxiu3c1fv0jcceSL6aISzp36lCr2Ss2bt6q39uiT69Y2bMGjUazYuVqI1dOvpiyc/deSeHE8WP/8+7b/fr0rlevrlqtdnNz8/f3a9O6pZsrwwIoCE8GAABwOgkXb5aUSmeakGuSywHdm247kFgomi0iv7Dkh1/3PzW5t2RgBY0grNhw/NK1SgOeqQRhWL9W4pJenaO27k8UD9OoEYSffjvwj/GxrWPCqqxDUUnZtv2JQf5esR1rHjutf7cYVxfV8nVx4uglv7DkywU7n53SN7xBUI17AFAlyTCQpWVlM599UTzEgNgH770TGRGuW+zTK3bz1u3GP9Zvq/549aXnxSUPjBn1yWdfGr+HjVu2aQRh2sMPiQv79IpVqYRvv/9ZxvEajsQdS7pwMSbaqJEdf16wOKxe3ebNmooLoyIjHn9kmlz1gSXQogEAADiLCo3mdnbBnqPJP688KLmrfqi/2l2e4RW9PN1H39tOUpiYcvM/32zafzwlK6ewvKIir6D4xLmrn/20feehJMmavbtENwoLFJe4urhMGtnZ1aXS17aikrJvluyet3zfiXNXs3MLyysqikrKbt3OO3r68qI/Dr/56Zp1O+KNb6PRp0v05Pu7SH63LCgqmbNw58UrMowHATghV1dXSauE4ydOVpcyCIKw/8Ah8WJ0k6gG9atOEqt04tTpxMpTSLRv16ZpTLTxexAEYdOWbfMXLZUU9u4Z++RjMrdr+PW3VUauWVpW9slnc/ZV/udA+WjRAAAAbKaktOzp91YYWGFIn5YjB7ax6ENo1fjLf62q2rtzk6s3snYdrvSlPz0zb/Efhw0/StPI0PFDO+iXN4+q+/CoLgt/PyT5SfHEuasnzl01vE8jxXaMcnV1WbT6cIXod8vC4tKvF+16anIf3ZgRAIzUoX1bf79Ko8Mavlref/DwgxPGia/n+/SKXf7b78Y/4srf/3jjlRfFJQ+MGWX85lqbt24XBM30KZPFhb17xgqC6tvvf5KrXUP82XOn48+2ad2y5lUFoaio6H/ffh937PjokcMbNWpoeGWNRnP+QvK2HbsOHKzh/RYWRdAAAACcXdPI0AHdm9a8Xm1MGNbJ39dz3Y4zxn8v794+4sHh0pYLOt3aRfj5eCz4/ZB4Yk55dWsX4eriMv/3gxUVd+tcVFL29eLdT03q3TQy1EKPCzgkycwRRUXFx0+cNLB+xu3b55MuNGsaoyvp1bPHrytXG/8ecjr+7LmExBbNm+lKjLySl9i8dYcgCNMeniROPbTTZ3z7/U8m7LBKy39b1ab1W8avv//g4f0HD7ds0bxN65bNmzYNCanj6+Pt4eFRXFxcUFh482b61WvXki4knzwVn53DvDm2R9AAAACcl6uLS58uTUYPaufiIvPI6ipBGNq3VfOouut2nDmXfMPwyg3rBQ7p27KT3iiSEi2jw96aOXjz3oS9cReLiksNrxzeICiqcZ3aVVoQOrdp7Oqq+um3g+UVFbrCktKy/y3Z/eRDvVo0qVfbHQKO4ey5hMnTH5MUPjpjqoFNvvhqbm0f5b0PPjb+0av0/kezJCVL5n9vwn42b92hjRtMqIyRj5J8MUW3mq6Se/YdMLzV2XMJZ88l1Lhz2BxBAwAAcCKuLi4earcAP896If5NI0I6tGoU6OdluYdr0jjk2Sl9r93MPpOUdv7SrZvpufmFJYXFpR7ubj7e6uAAn+jwkBZN6sZEGNtYwM/Hc+zg9sP6tYpPSrtwKf3i1YzcvOKCopLS0nIPtZu/r2e9EL8mjUNaNw3Tn2XTSB1aNnp0gsuPK/aXld/NGkrLyr9dtvexiT2rG34SAAAdggYAAGAlXp7u//vXeLt4CHmr2qBuQIO6Aff2bC7XDj093Du3bty5dWPjN6nVEbVr3uDLt8eZVDUAAJh1AgAAAAAAyIegAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyMbN1hUAAAAAgEomT3/M1lWoGZWUC5V0PLRoAAAAAAAAsiFoAAAAAAAAsiFoAAAAAAAAsiFoAAAAAAAAsiFoAAAAAAAAsiFoAAAAAAAAsnHAoOGF5Z/qbs+ZO9eGNQFgDPHrVPz6BZTg8cXbdbe/+nmTDWsCOBLxq0n8KgMAOAYHDBoAAAAAAICtEDQAAAAAAADZOGbQQO8JwF7QbwLKR+8JQF70mwAAh+eYQQMAAAAAALAJpwgaaNQAKBOvTdgjGjUA5uAVBADOwGGDBkkbbK5nAKWRvCrpNwElk7Tu5koJMI3ktUO/CQBwVA4bNAhctwD2g1crlI8rIkBevKYcxh9bV+huXzh3yoY1AWAM8etU/PqVlyMHDRI0agCUg9cj7B2NGoDa4lUDAM7DwYMGOlAACkSnCdgpOlAAJqPTBAA4FVVaXqqt62BxX0x8SVLy3MyZNqkJ4OT0wz5SBgtZtXCtratglLFTR9i6CrU27+EBkpJnZwy2SU0Au6AfyZEyOJ5R94wXL0a3aGurmgAwTNK/ia4TZtG/kqFpA2B9pAxwDPrXSDRtAKpDyuAkLHetAsByLPrKdbPcrhXlheWfSto1aK95aNoAWEGV0R4pA+zX44u3S9o1aK+maNoA6FQZwJEyAICTcIquEzr6fSh0SBwA2RloOkTKYGl0nbAC/T4UOiQOcFoGGviQMjg8cQcKek8ACmSd+Sa0nCto0DIQNwCwNCIG6yBosBoDcQMALSIGJ8FIDYCSWW10Bi2nGKNBguscwFZ49cHxcAUFGMZrxHkwUgNgL6zwanWWMRokdFc7tG4ArIB8AY5Ndx1F6wZAh3wBF86dolEDoBCS5gxW4IxdJ6pE4gDIjnzBhug6YVskDnBa5AugAwWgNFbuNKFF0AAADoigAQBgK2QNgHLYJGUQnHOMBgAAAAAWIrmSsX6bbQBatkoZBIIGAAAAAPLSzxqIGwBr0n/RWXm4VoIGAAAAADLTv6ohawCsQ/+1Zv1JYZx01gkAAAAAFvXH1hWS8Rp01z8M3ADIrroszyZTzxI0AAAAALAI/axBi8QBkIvhtkI2SRkEggYAAAAAlqO9zqkybhDoTwFYjK0iBi2CBgAAAACWZThuACAj20YMWgQNAAAAAKyBuAGwKCVEDFoEDQAAAACsR3wtROgAmEk54YIYQQMAAAAA21DmNZLdWbVwra2rYIqxU0fYugqwFBdbVwAAAAAAADgOggYAAAAAACAbggYAAAAAACAbggYAAAAAACAbggYAAAAAACAbggYAAAAAACAbggYAAAAAACAbggYAAAAAACAbggYAAAAAACAbggYAAAAAACAbggYAAAAAACAbggYAAAAAACAbggYAAAAAACAbggYAAAAAACAbggYAAAAAACAbggYAAAAAACAbggYAAAAAACAbggYAAAAAACAbN1tXQLmmvvmcrasAR7bwwznWfLipL3xjzYeDsxndKdyaD/fFC6Ot+XCwRy98sdrWVQAAwHkRNEiRL8A6dGeaRRMH8gVYx+q4VO0NiyYO5Aswnu5sIXEAAMD6CBruImKATWhPPNnjBiIG2IQ2cZA9biBigMm0Jw9xAwAA1sQYDXeQMsC25D0DSRlgW7oGDrIgZYD5OIsAALAmWjQIQvXXeJOmTbJyTeAkli5Yql849c3nZGnXUF3KMGnmo+bvHNC3dO4P+oWr41JladdQ3fXha6/w/oxqfTyrivfYL14YTbsGAACsQ5WWJ+fvTvZIP2UgX4DV6CcOZmYN+ikD+QKsRj9xqDFrGDt1hIF79VMG8gXUin7iQNYAwCGtWrjW1lUwheGvAbBrzh40SFIGIgbYhCRuMDlrkKQMRAywCUncYDhrMPANQ5IyEDHAZJK4gawBgOMhaIDSOPUYDaQMUAjJuWfaeA2kDFAIybln2ngNpAyQkeT8YbwGAAAszXmDBlIGKIqZWQMpAxTFzKyBlAGyI2sAAMCanDRoIGWAApmcNZAyQIFMzhpIGWAhZA0AAFiNkwYNYqQMUA7zz0ZSBiiH+WcjKQPkxRkFAIB1OGPQYFoHeMD6jDlXq5vMElAaYxo18CMzrInzDQAAC3HGoEGM5gxQGnPOSZozQGnMOSf58RmWwHkFAIAVOHvQAAAAAAAAZOR0QQP9JmBfDJ+x9JuAfTHce4J27LA+zjoAACzB6YIGMfpNQJlMOzPpNwFlMu3MpH07LIezCwAAS3PqoAEAAAAAAMiLoAEAAAAAAMiGoAEAAAAAAMiGoAEAAAAAAMiGoAEAAAAAAMiGoAEAAAAAAMiGoAEAAAAAAMiGoAEAAAAAAMiGoAEAAAAAAMiGoAEAAAAAAMiGoAEAAAAAAMiGoAEAAAAAAMiGoAEAAAAAAMiGoAEAAAAAAMiGoAEAAAAAAMiGoAEAAAAAAMiGoAEAAAAAAMiGoAEAAAAAAMiGoAEAAAAAAMiGoAEAAAAAAMiGoAEAAAAAAMiGoAEAAAAAAMiGoAEAAAAAAMiGoAEAAAAAAMiGoAEAAAAAAMiGoAEAAAAAAMiGoAEAAAAAAMiGoAEAAAAAAMiGoAEAAAAAAMiGoAEAAAAAAMiGoAEAAAAAAMiGoAEAAAAAAMiGoAEAAAAAAMiGoAEAAAAAAMjGzdYVAFCDVQvX2roKgKVwesPmOAkBAJAdLRoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBs3GxdAZiipKTk9On45ORL165dLyjILyoqdnNz9fHxCQ0NCQ8Pb9myeWhoiDH7Wb16bVzcMf1yNzdXtdojICCgfv16LVo0a968uUpVw7ZTpkxq2jTayPpnZGScOhWfknIpI+N2QUGhIGi8vLyDggIiIiLatGkZFhZW4x5q9R+osaqpqZcXLVpaXFyiKxk4sF///n2NPByYb/WyZXEHDuiXu7m5qT08AoKC6jdq1KJNm+Zt2qj0z0XL7Fay7ZQnn2zasqUxD5px8+apuLiUCxcybt4sKCgQNBovH5+g4OCI6Og2HTuGNWxY4x5KiotPHzuWfP78tcuXC/LyigoL3dzcfPz8QuvVC2/SpGW7dqH16tWqqqnJyYu+/ba4uFhXMnDo0P5DhhhzOJBXXn7REy9+VVZWLi78/IPHG4QF13ZX383/a9vuE/rl7m6unp7qkDoBkY3rdunQtHOHpvovGsm2b/xzQoc2TYx83Os3bu89ePZsYur1G5l5eYUaQePn4xUaEtCyWeMeXVpEhtercQ9FxSX7Dp2NP5d68VJaTm5BQUGxm7trgJ9PwwZ1WjRt1LVjs4b16xhf1YSkKx99/mth0d038PGj+jxwfy8jDwcAAFgCQYOdqajQ7Nmzd8+e/UVFReLykpKKkpKszMysxMSkLVu2jRlzf8eO7U1+lLKy8rKygoKCguvXr8fFHW/cuOGkSQ/6+HibXX2hsLBw7doNp0/HazQacXlpaU5OTs6lS5d37drTrFnT++8f7u/vV+UeZP8PpKSkLl68rKTk7pfUe+8d0Ldv79ofHORXVlZWVlZWkJ9//cqVuAMHGkdGTnrsMR9fX2XutrCgYO1vv52Oi5Oe3llZOVlZl5KTd23e3Kx16/snTvQPCKhyDxUVFXu2bt2zdWtRYaG4vKSkpCQjIzMjI/HMmS1r146ZNKlj9+5G1irlwoXF331XIkoZ7h0xou+gQbU8OMhj36EzkpRBEIRd+049OLafXA9RWlZemleYm1d48VLa9j0nmzZp8OpzD/j7yfAGnpdf9NOSTfsOnZWc4RkluRmZuefOX/l93f5O7aIfmzokOKjaN/A//jqwZsPB/IJKb+DlxRU3i7NupmcdO3lh2cqdM/8xvH+vtsZU6Wzi5f9+saJIFBM/OLbfmOGxtT84AAAgJ7pO2JPi4uL58xdt2bJdco2tT3zZbL7Ll6/++ec68/eTkXF77twfTp06LfmSKpGYeH7u3O+vXbuuf5fs/4GLF1MWLVoqXnnQoHtIGRTrckrKn8uXK3O3GbduzZ0169TRozWc3vHxc2fNunb5sv5dxUVF8//3vy1r10pSBn3Gv8Avnj+/6NtvxSnDoJEjSRlsaOfeU/qFu/ZLs1cZnU++9v3CDebv5/qNzNf//fPeg2cMVzXu5IXX//1z8qU0/bsKC4vfn73sl1U7JSmDPnFwYED8uUsfff6reOVJD/QnZQAAQAlo0WA3yssrfvllRUrKJV2Ju7t7bGz3tm1bBQcHazSa7OzsCxdSDh8+cutWumkPoetTUFhYdPLkqfXrN+i+TyYkJBQWFnl5eZpc/6Ki4iVLfsnKytKVNGrUYODA/o0aNXJxUV27dn3Hjt3JyRe1d+Xn5y9ZsvzJJx/187v7I7Ps/4ELFy4uXfpLaWmZruS++wb16tXD5GOEXHSN/wsLCk4ePbp+5UrdtU3C6dOFBQVe3qb8PGuh3QqCUFRYuGTevKzbt3UljSIiBg4b1igiwsXF5drlyzs2bkxOTNTelZ+bu+T77598+WU/f3/d+uXl5b/89FNKUpKuxF2tju3Xr22nTsEhIRqNJjsz80Ji4uE9e27duGFkrS4kJCz9/vvS0lJdyX2jR/caMMC0Y4T5rqXdTrpYRYSacTsn/tylNi0jzdm5rk9BfkHR7gPx85du1r2BHzl+Pr+gyMfb9DfwgsLiT+asuJWerSuJiao/YXTfptENXFxUySlpK9fsO302RXtXdk7BJ3N+++j/pgcFVHoD//Sb388kpOpKPNTuwwZ16dmtZb26QRqNJj0j5/TZS5u2x129nmFMlU6dSfnkq99KSu6+gU+ZMHDEfd1MPkYAACAjgga7cfDg4QsXLuoWvb29pk+fEhZ2tzdsaGhoaGho9+5d4+KOubm5mvNYXl6e3bt3PX06/tKlO7+7VlRosrOzzQkadu7cnZ5+9+tjZGTEtGmTXV1dRYvhy5f/dubMOW1Jbm7u5s1bx44dpdtE3v9AUtKFpUt/LSu7+yV16NDBsbHGNkeHdXh5e3fv0+d0XNyl5GRtSUVFRXZmpsmJgIV2u3PTpvSbN3WLkTEx05566u7pHRMzLTp6+c8/nzlxp6t5bnb25j//HPvww7pNDu7efSEhQbfo7eMz/emnxQM6hIaFhYaFde/TJ+7AATe3mt+6k86dW/rDD2WilGHomDGx/fubdoCQhbg5g6uri7eXR27endYrO/edNjNo0PHx9hwysPP+Q2fPnb+iLamo0KRn5JgTNKxas+9a2t0crVXz8LdenKh7m23VPLxls8affbP6UNydczgzK2/pbzuefmSEbpMNW4+eOpOiW/Tz9Xrn5YciGtfVlTRqENKoQch9Aztv333Czb2GN/ATpy/O+nqlOCae9uA9wwZ1NfkAAQCAvOg6YR/Kysp37dojLrn//uHia2wdlUro3Llj+/btZK+Dl5eXydsWFxcfPnxEt6hSqUaPHqG7DNMVjhw5TK1215WcPHkqO/vOD2jy/gcSE5OWLl0uThmGDRtCymAvvHx8FLXb4qKiw3vunpwqlWr0Qw9VcXqPH69Wq3UlJ48ezc7M1N4uKyvbtWmTeP37J06scthIlUrVOTa2fdcaLqgSz5xZ+v334pRh2LhxpAy2pdEIew7E6xbbt2nSs9vdMTsPHk0wsr+AaXx9TE8ZCguLN+2I0y2qVKonpg+VhLkqlerRKfd5eNx9A99zID79do72dmlZ+e/r9onXf2zqEHHKINqPMLBv+76xbQzU59jJC7O++k2cMsyYNIiUAQAARSFosA8pKZcKCgp0iyEhIa1aGTUAvmmKiooPHTqamnq3G3mjRg0CAvwNbGLYxYspJSV3r3kiIyOCg6sYYt3Hx6d582a6xYoKzfnzF7S3ZfwPJCYmLlv2q248NpVKGDFiaI8efElVoqLCwkN79qRevNuSpVFEREBgoKJ2e/H8efGgCZExMcEhVUz74uPn17zN3cunioqK82fPam+nJCUV5Ofr7gqpV69Ve9MHc02Mj1/2ww+6HE2lUo0YP75HX2ZRsbH4cym6C29BEHp1a9mzWyvdYnFx6cGjCVVtV2sFhcWbth9LSLqiK4mJql8n2PQ38PhzqcXFd9/AWzUPD6sbpL9agL935/YxusWKCs3xU3daDJ1NSNW13RAEoWH9Ot07NzetMnEnkmb/b1Wp6A38kYcHD7mns2l7AwAAFkLXCfsgHphAEATjJ5KslUWLllZZHhQU+MADY8zZc2rqFfFieHjj6tZs3LjxqVN3f/RLTb3SpUsnQdb/wMGD4rYVwsiRw7UPAeVY9O23VZYH1anzwNSpStutOLAQBCG8SbXTBDaOijoVd/eX4dSLF7v07CkIgnhoBkEQjJxHszoHd+/W3VapVCMnTNA+Cmxr577TuttqtVuXjk091Oo6wf4Zf6cPO/ee7tfTqKkWqvTR579WWV43JPDZx+83ebeCICRcuCpebB5T7RStzWMa7Tt0VreYmHT13n4dBEEQD80gCEJ7o6fS1Ldxm7hthfDolCHahwAAAIpCiwb7kJubK14MCalT3ZqyU6vVw4cPqbIBgvHy8vLEi4GBVc/tJwhCUFClu3QbWuI/oFIJo0aNIGWwF2oPj+HjxlXZWMC2u83LyREvBgZV8WOvVlDl15Fuw9zKewipW0WTchOoVKpRDz5IyqAEkgYLndrFeHqoVSohtmsLXeGZhEviJg+y8PRQz5g8qMoGCMbLyq70Bh5ap9o38NCQSndl5dzZMDOr0h4ahJn1gaKlUgmPTxtKygAAgDLRosE+SGZzFPf0trSSkpLFi3/p1Sv2vvvuNXknxaLZ9QRBcHev9sRzd3cXLxYX3zlwy/wHVIKgkmM/sIaS4uLF8+b1GjjwvlGjal7birstrnxySs7hSndVPm91GxaJugUJgqD28DCtJlCsg0cTxL0PdKMz9OrWau3GQ9rbGo2wa9/psSPkDIaKiks+/nLFyPu6PzzB9NlGCgsrDR6hVlf7Bu5R+a6Cgjvv/PkFlT4CPD3keQNXqXgDhyHppxaYv5OQttPM3wkAOCGCBvvg6VlpHC9xh3AZ6aa3LC4uuXLlytq1f2Vk3BlmfO/e/VFREc2aNTVtzx6VL5zEg3hJiKfiEwTBw+POgVviP6DRaP74Y40gaDp16mj+3iAj3TyUxcXFV1JS1q5YkXHrlvauvdu2RcXENGvdWjm79ah8ckrO4Up3VT5vdRt6Vp7toqRyMGcyjUbzxy+/CILQqQeTttrYzn1355vw8lR3anen81eTyLCwukFpN+8MC2pO0KCb3rKwqOR88rWfFm+8fuPObtdsPNiqRbjuQWvLy6tSLiCeUVKiuPJd3t533vl9vCt9BMgy7KVGo/lu/nqNRjOwj+kDmsAByJImmLZ/MggAMICuE/bBz89PvCieJ9ISPDzU0dFNxo2rNC6DeGiD2vL19RUvZmVlV7dmZmalu3QbyvgfCAi427hXoxH++GPt0aNxBtaHDXl4eEQ3bz5uyhRx4cE9e6pb3ya79fWvNMxe1t9zSejLvH1bvKjb0K/yHsQzZZogQNR3Q5s1HN2/35wdwkwZt3Piz90dpKBLx6biVl3iuSeu37idWHlABBN4earbtYp85rFK4zJs3HbU5B0GBlR6A7+VUe0b+K30SncF+t/ZMCiw0h7EM2XWVohoVEuNRpi34K+tu46bvDfYnfRTCyR/VAYAlIkWDfYhMjJCPLnj+fMXhg61+IM2bNhArXbXzRZx44bpFz/h4Y3Ei+L5LCQuX650l25DGf8Dw4cPOXo0LiHhvHZRoxH+/HOdRiMwWINiNQwPV6vVumYsN65dU9Ruw6OixIupycnVrXlZMmzk3xtGxsTs2rxZV37+7NmhY0wffnX4Aw8c3bcvIf7OoKoajebP5cs1Gg2DNdjKrv3xGo1Gt7h7f/zu/fHVrrzvdLPoakdbNF50ZH0PD3ddf43LV26ZvKvmleuTkFRtFCKe6kIQhGZ/DxvZqnn47+vupl0nTicLwj2mVWbG5EFbd52IO3Fn/FSNRvh+4QaNRmCwBkdlX1fvktrS5AGAM6NFg32IjAz3FjWuTk9PP3PmrIH15SL6biwUFRVWv2INoqIixR3XU1Iu3b5dxS9a+fkFCQmJukUXF1VMzJ22vjL+B1xdXR98cHzz5ne7gWg0wpo16w4fpl2DconOROmIBjbfbVTTpuLBF1KSkm6np+uvlp+Xl3D67rwDLi4uMS3uDAQYGR3t7eOjuyv9xo0zJ06YVhlBe4Y/8khzUTcQjUaz5tdfD+/da/I+YY7d+0/XvNLf9h06q5u70Vyi8zuvoKj69WrQukW4h/ruG/iZhFRdXw+xnNyCoyfuzp/i4qJq3+ZOlNayWWM/Xy/dXVevZ5g8l6ebm+tLT43pJJpHU6MRfli0YcvO46btEArkMG0EHOZAAMAEtGiwD25ubn379tqw4e5vnn/+uS44ODgsrJ5kTY1GOHbsmKurW/v2pk+TpnX16jVxb3MfH18DKxvm4eHRrVuXvXv3/11JzerVa6dNm+zq6qpbR6PRrFmzTteAQhCEtm3b6uankPc/oM0ali//7dy5RN1Wa9eu02g03boxH7viXE1NFY9u4FO5H43Nd+vh6dmtd++927ZpFzUazeply6Y99ZT09P71V/HYIm07dw78exIKN3f3voMGbVi9Wnfvn8uXB4eEhDWU/rKt0WiOHTzo6ubWvksXA1XSZg3Lf/rp3N/RhkajWbtihUaj6da7t2mHCdMkJV+7er0WXb3yC4qOHj/fo0uLmlc16ELK9WLR22mgv4+BlQ3z8vIYPKDTmo0HtYsajea7+X+99eJEN7dKZ/j3CzeKB7zs3b21bn4Kd3e30cNjFy3fprv3+4UbwuoGRTSWTrCi0Qjb95xwd3PrE1vtgCnarOHzuauPHL/bMO2HRRsqKjSDBzDgjr2yxKX4cy89Z/5O5nw6x/ydCJUPkJYOAJwBQYPd6N69W0LC+YsXU7SLBQWF33//c8+e3du0aR0cHKzRaLKzsy5cSDl8+OitW7eGDx9izmMVF5dcuXJ17dr14sImTaKqW98Y/fr1PncuQTe6ZErKpR9/XDBwYP/GjRupVKpr167v3LnrwoW7Dcv9/HwHDx4o3oO8/wFXV9eJE7VZw50f1jQaYd269YKg6dbN0CUcrEk3aqO4sEmzZkrbbb/Bg8+dOqUbWjIlKenHL78cOGxY46golUp17fLlnRs3Xki4+xOun7//4JEjxXvo3rdvQnz8xfN3LpwK8vO//+KLnv37t+nYMTg0VKPRZN++fSEx8fDevbfS0oY/8ECNVXJ1dZ34j38s//nnc6fuDEOo0WjW/fabIAhkDda0c9/d5gwqlTB39jOSAQsEQSgvr3jk+S8LC+8MArpz7ylzgobCopKk5Gs/Lt4oLmzTMtLkHQqCMGZE7JHjibrRJc8kpP7r4yUTR/dpGt3QRaVKvpS2cs3eU2dSdOsHBfhOeqC/eA9D7+kSd+JC/LlL2sXcvMJ3Plw0fHDX2K4tw+oGaTSaWxnZp89e2rzj2JVr6TMmDzJcHzc31xefGvPZ3N+PHLubNfy0ZKMgaAYPoBOcPTE/X5AlTTBt/yZnELqjJnEA4MAIGuyGq6vLQw+NX7Lkl0uX7oxiUFpaunPnnp07zR0YT2fRoqXV3eXu7tanj6EO3tVtGxwc9MILzwiC4OnpOXnygwsWLMnOvjNa2JUrVxcuXFLlVt7e3pMmTZQMACn7f8DV1WXixAd+/fW3s2fvZg1r1/6l0Wi6d+9q2j4hi0XfflvdXe7u7n3uNXGmVXN2W922wSEhL7zzjqeX1+THH1/wzTfZf48EeeXSpYVz51a5ibePz6THHvMTDUoqCIKrq+tDjzyyZN68S38P8VBaUrJz06admzYZqJVhrq6uE2fM+PXnn8+KsgZtu4buffqYvFsYr6ysfN+hM7rFqIgw/ZRBEARXV5f2raMOHDmnXTxx+mJ2Tn5ALdsgfPT5r9XdpVa7jRpqaOaR6ratVzdwzkdPCoLg4+356nPjP/j0l/TbOdq7kpKvffDZ8iq38vP1euXZcZIjdXV1eenpMZ/M+e3c+TvjOBSXlK5au2/V2n0GKmaAq6vLizPHfD539eFjdxum/bh4U4VGM2QgDdOUzuR8wdKxQq3oV6a20QOJAwAHRtBgTzw9PWfMmLZr1+59+w4UFRmaAE+tlmWW8jt8fX3Gjx8bHBxU86oGhYTUmTnzsbVr18fHnxUPjSbRtGn0/fePCAjw179L9v+Aq6vLhAkPrFix8syZc7rCdes2aDRCjx5kDYrj6+c3ftq04JAQBe42pG7dma+8snbFivjjxw2d3i1b3v/ggwGBgfp3eXp5zXj22V2bNu3bsaOo0NCQKMa/wF1dXSfMmLFiwQLxoA/rfvtNo9H06NvXyJ3AZHEnk/Ly7w6O0Ll9tTMEd2ofrQsayisq9hw4M3ywPG9BAf4+zz9xf726gWbup0FY8H//NePHxRsPHEkwcIZ3aNPk8WlD6gRX8Qbu4+35r1cnr1q7b92mQwWFht7APT2MfQP/58zRX3z7x6G4u82Ffl6yWdAIQ+4ha1AiE/IFRSULNZLU1vjcgcQBgOMhaLAzLi6q/v37xsb2OH36dHLypWvXrhcUFBQXF7m6uvn6+oSEhERENG7ZskVoqFmXTCqV4O7u7uPjU7du3aZNY9q3b+Ph4VHzZkbw9vaaMGFcenrGqVOnU1IuZWTcLiws1GgELy+voKCAiIiINm1a1a8fZmAPsv8HXF1dJkwY9+uvq8SjS65fv0Gj0cTGdjPraGE2lUrl7u7u4+dXt379pi1btu/SxcPTU7G79fbxmTB9evrNm6eOHk1JSsq4dauwoEAjCF7e3kHBwRHR0W06dqzfqJGBPbi4uPQfMiR2wIDTcXHJ589fu3y5IC+vuKjI1c3N188vpF69iCZNWrZrF1pPOjSJAa6urhOmT/91/nxx1rB+5UqNRhPbr5/pRwsj7NxbaRjIzu2jq1uzY9tolUqlu4Dfue+UyUGDSiWo1e4Bfj6NG4Z0aBvdp0crLy953sD9fL1eeHL0tbTbew+e0Q4JmZdfqNEIvj6eoSEBrZo1ju3aMjLc0Mnp4qJ64P5ewwd33XfoTPy51OSUtNy8goLCYnc3twB/nwb1g1s0bdytU7OG9esYWSVXV5cXZo768ts/xKNL/rx0c4VGM+xeOsEpRW3zBfsKFwwQH4iRoQOJAwCHoUrLS615LQcy9c27b/qTpk2yYU0AA5YuuNsVZXSLwdWttjru7ut30sxHLVsnwFRL5/6guz26U3h1q6XG3V3ttVd4f4YFfTzr7ntseCfePC2lVhGDw+QLhtWqewVxAxze2KkjbF0FWAotGgAAACAn4yMGJ8kXdHTHa0zioP03EjcAsEcEDQAAAJAB+YLxjE8c6E8BwB4RNAAAAMAsRkYM5Av6aps4EDcAsAsEDQAAADCRMRED+YIxjEwciBsA2AWCBgAAANQaEYOFaP9pxA0A7BpBAwAAAGqhxoiBfMF8xjRwIG4AoFgEDQAAADCW4ZSBiEF2NTZwSD+1gKwBgNIQNAAAAKBmRAw2ZDhuoGkDAKUhaAAAAIAhRAwKQdwAwF4QNAAAAKBaBlIGIgabqDFuIGsAYHMEDQAAAKgCEYOSGYgbaNoAwOZcbF0BAAAAKA4pg10w8FwYM/8oAFgILRoAAABwFxGDfaFpAwAFImgAAADAHdWlDEQMCmc4biBrAGBldJ0AAACAkH5qASmDvavumTLw5AKAJdCiAVC6sVNHVHfX6rhvrFkTQHbi0/uLuB9sWBM4LQPvsU5l3ivjqywnYrA7hps2PD5rhdVrBGtYtXCtrasAVEKLBgAAAKdGyuB4qnvuqnuuAUBetGgAAABwXlVeeRIxOIDqmjbMe2U87RoAWBotGgAAAJzRvFfGkzI4vCqfzeqeegCQC0EDAACA06G7hPOgGwUA66PrBAAAgHOhIYOzoRsFACujRQMAAIATIWVwWtV1o7B+TQA4PIIGAAAAZ0HK4OTIGgBYB0EDAACAUyBlgEDWAMAqCBoAAAAcHykDdMgaAFgaQQMAAICDI2WABFkDAIsiaAAAAHBkpAyoElkDAMtheksAAACHpX/dSMQAnSqnvWTOSwDmo0UDAACAYyJlgDH0zwraNQAwE0EDAACAAyJlgPHIGgDIi6ABAADA0ZAyoLbIGgDIiKABAADAoXB9CLlwLgEwDUEDAACA42COCZiMeSgAyIWgAQAAwJGRMsB4nC0AZEHQAAAA4CAYmgHmY7AGAOYjaAAAAHAEpAyQC1kDADMRNAAAANg9UgbIi6wBgDkIGgAAABwNKQPMx1kEwGQEDQAAAPaNn5phHZxpAIxE0AAAAGDH6DQBy6EDBQDTEDQAAADYK1IGWBpZAwATEDQAAAAAAADZEDQAAADYJZozwDpo1ACgtggaAAAA7A8pA6yJrAFArRA0AAAAAAAA2RA0AAAA2BmaM8D6aNQAwHgEDQAAAPaNlAHWwZkGwEgEDQAAAPaEn5GhHJyNAKpE0AAAAGDH+JEZ1sT5BsAYbrauAIAaPPvZ49Xf2cFq1QAAKAE/IENp5r0y/vFZK2xdCwDKQosGAAAAe8XPy7A+zjoANXKuoMHgL8MAAACKJmnOwPUebEVy7tHQBoCEU3SdIF8AAAAAAMA6HD9oIGWAvRswsFN1d62eX2HNmgAAbIjmDFCU5156bs6nc3SLjNQAQMyRgwYiBgAAAAAArMxhx2ioMmUw8MswAACAYtEHHsrHWQpAxzGDBv2UYcDATqQMAADAMdBvAkrAeQigOg4YNFSZMtikJgAAAObjh2LYC85VAFqOFjRIUgYaMgAAAAfDz8hQDs5GAFVyqKBBP2WwVU0AAAAAAHBOjhM0kDIAAADHw6yWUDjJOUnvCQCCwwQNpAwAAAAAACiBIwQNpAwAAMAh8eMw7BHnLQBHCBrESBkAAICjot8ElIkzE4CE3QcN+pNZAgAAAAAAW7HvoIFOEwAAAAAAKIp9Bw1ipAwAAMCRMN8E7AhzTwAQc5ygAQAAAAAA2JwdBw3ifhM0ZwAAAAAAQAnsOGgAAABwVLQ8h73jHAacmZutK2AiJpsAAADOw3IDNKSl3Tp69PT58xevXbuRn19QVFTs4eERHBwQEdGobdvmHTq08vT0MLD5n39uXrVqo6Two49erV+/bpXrb9myd/Hi38Ulbds2f+mlxySrpafffvnlD3WLdevW+eSTN7S3X331o5s3M4w8Oh0PD/V3331YZQWqEx0d/s47d//tMm5Y20O2F8+99NycT+fYuhYAFMFegwYx+k0AAADU1vXrN5cvX3vixFmNRiMuLygoLCgovHIlbe/eI15enqNGDRoypF91O9mz50hVhYfHjx9uZDVOnUo4c+Z8q1ZNa1V5u+aEhwzA2dB1AgAAwOns23f0X//6/PjxM5KUQaKwsOjo0VPV3ZuQkFxl44K9e49WVFQYX5lff11nuBqOxwkPGYBTIWgAAABwLgcPHv/++19KSkrN3M/u3YerLM/Kyjl9OsH4/aSkXDl06ISZlbEvTnjIAJyKXXadYL4JAADgwCSj6Mk7QMPNmxnff/+L5Of0Ro3CBg/u27JldGBgQHl5eWZmdmLixX37jiYkJFe3n6Ki4iNHTuoWg4ICMjOzdYu7dx9u166l8bVaufKvLl3aurq61rim/sgFubn5zz77L3HJv//9Ynh4A2Met2HDsA8+eNn4epq/oY7xh2xHJMM0zHtl/OOzVtiwPgBsxalbNCxdsNTWVQCqYNqZuXTuD7LXBDCfaWfmx7N4f4alcHatXPlXWVmZuKRfv+7vvfdi377dQkPruLu7eXp61K9ft1+/7m+88dRbbz3TuHHVV+yHD58sKirWLQ4e3CcmJkK3eOxYfH5+gfG1unkzY/v2/bU8FPvmhIcMwHk4XdAwekIrW1cBqAXDZ+zo6U73EoZdG90p3MC9L3yx2loVAe5wwrOusLBI3AxBEIRmzaKmTRvn6lr1B0rTppFTp46t8q49e+72m3BxcYmN7dSrVxddSVlZ+f79x2qsT926dXS3//hjizi5cFROeMgAnBBXKQAAAM7i9OnE8vJKwzTef/8gF5dafyG8eTMjMfGibrFNm2aBgf7du3dwc7vbLXf37kM17qdDh1a6dhC5uXnr1++obU3sjhMeMgAnZJdjNMho6YKlk6ZNsnUtgLvM6dGzdO4Pk2Y+KmNlADOZ06Pn41lLX3uF92fIjH4T16/fFC+6ubm1aBFtwn727DksHuVB25bB29urY8dWhw/faTFx6dLVy5evN25c3/CuJkwY8eGH/9Pe3rhx5z339AwI8DOhSqa5ejVt+vSqh1p4/fWZBv45Jm8o2PqQAcAKnLFFA70nYC+MOVfpPQF7YbjfhJYTtmOHDTnn+ZabmydeDAjwdXOr9WCEGo1m794jukUvL89Ondpob4t7TwjGNWpo1iyqQ4c7n3fFxSWrV2+qbX3sjhMeMgBnwyUKQ0JCQcw/GxkSEsph/tnIj8+Ql72cUZIpJ+RVea4JQRBUJuzkzJnzGRlZusXu3Tu4u99pJNu2bQt/f1/dXfv3HysvL69xh+PHD9N139i162Ba2i0TamVfnOeQLXo+A1AsJw0aJD8UkzVACSTnofFNbySNGsgaoASS89CY5gxakh+Z7eXKEMonOZfsqDmDvHNbilMAQRCys3PLymoOAiR27z4sXhS3YnB1denRo6NuMTc378SJszXusGHDMN1Oyssrfvvtr9pWye448CHLe8YCsFPOO0bD6AmtVv96RrfIYA2wLZNThjvrT3dZPf/u4F4M1gDbMjll0Hrhi9VfvDBat8hgDTCf/aYMsqtfP1S8WFZWdu7chTZtmhm/h8LCori40+KSDz742sD6u3cf1nWsMGDMmPsOHjxWUlIqCMKRIye7dm1nfJXM0bBh2AcfVD3UgoU21LHVIQOAFThpiwYt2jVAIcxMGe5sRbsGKIOZKYMW7RogI1IGsdatm0lmsvzzz80avQ4VBhw4cOfa2EgnT57NycmtcbXg4IBBg3rrFleudJxf+KvjhIcMwHk4ddAgVJU1EDfAmvRPOXMGK9XPGogbYE36p5xpKYOWftZA3IDa0j9tnDxlEATB29urc+e24pLExIsLF66SzHmpc/58yqJFq8Qle/YcrnLN6pSXV+zbF2fMmsOHD/Tx8dbevnkzo1aPYqec8JABOAnn7TqhI+lDIYh+XqYzBSykujzL/ClRJH0oBNHPy3SmgIVUl2eZkzJoSfpQCKKfpulMAQOqy6RIGbTGjRsaF3daPDTD9u37k5JSBg/u26JFdFCQf1lZeVZWTkJC8v79cefOXWjaNFK35vXrNy9cSK3tI+7Zc3jIkH41rubt7TVy5D2//LKmtvu3X054yACcBEGDIFSVNWjRugHWJNfEq/pZgxatG2BN5qcMWvpZgxatG1BbpAw69eqFPPLIxHnzlol7TFy+fP3HH5fXuK1kGMhBg3pPnjy6yjVffPE/t29naW9fuZJ28eLlqKjGNe7/3nt7bd68WzylhaVdvZo2fXq1Qy189dV7fn4+8m4oYf1DBgArcPauEzpyXeMBppH3DJT0oQCsTK6UQYvrQ5iPs0giNrbTP/4xQa12r9VWFRUV+/YdFZd07dq+upW7dKnUQcPIDhdubm5jxw6pVa3snRMeMgBnwNXIXaMntCJugPVZ6MQbPd2FuAHWN7pTuLwpg9YLX6zmQhGm4eSpTp8+Xd9994W2bVuoVCoDq3l5eerGdDh1KiErK0d3V0CAn7hXhUSXLpXmUDhw4FhZWZkxFevZs3PjxvWNWdNhOOEhA3B4dJ2Q0l3yVdmZApCLdVItXdZQZWcKQC6WCBf06S4Xq+xMAYgRLhijQYN6L7306LVrN+Li4hMTL16/fjM/v6CoqNjDQx0UFBAe3qBduxadOrXx9PTQri/pN9GlS1sDIUXTppEBAX7Z2Xfmm8jPLzx69HT37h1qrJVKpRo/fvhnnzlRdz8nPGQADk+VllfrEX1s7tnPHtfdHjCwkw1rAsBpbd92dxD1r16cZ8OaVGnVwrW2roJRxk4dYesqAIoz75Xx4sXnXnrOVjUBTDPn0znixcdnrbBVTZyHvXzuS/A1wIHRshoAAAAAAMiGoAEAAAAAAMiGoAEAAAAAAMiGoAEAAAAAAMiGoAEAAAAAAMiGoAEAAAAAAMiGoAEAAAAAAMiGoAEAAEC55nw6x9ZVAGqBMxaAQNAAAACgKI/PWmHrKgCy4XwGnBNBAwAAAAAAkA1BAwAAAAAAkA1BAwAAAAAAkA1BAwAAAAAAkA1BAwAAAAAAkA1BAwAAgLJIBupnvkDYC8m5ypQTgNMiaAAAAAAAALIhaAAAAIB9eOut2e+++4Wta1E7+/YdnT795fj487auCABYj5utKwAAAAAbKC0t27370OHDJ69cuV5QUOTr6x0UFBATExkb2zE6OsLWtZNNZmb2+vXb4+PPZ2Rkenp6hIWFdunSLja2k6+vt62rBgAOi6BBcfbMrrB1FQD59X6Z9lMAYLo5n8557qXnZNxhevrtzz//6erVNF1JdnZudnZuSsqVLVv2zJ79ZkhIsIwPZytpabfef39Ofn6hdrG4uCQ7OzchITk5OfWJJybZtm6Oh8FEAOgQNCgF+QIcm+4MJ3EAAGM8PmvFvFfGW2jnpaVl2pShUaP6I0fe07x5Ez8/n/z8wszM7KSklH374lQqlYUe2srWrNman1/YqlXTceOGNGwYVlZWnpZ289ChE7aul1NgJEjAmRE02B4RA5yK9oQnbgAAG9q9+9DVq2kxMRGvvTbT3f3Ot0F/f19/f9+IiIb33NNLt+a+fUfnzVv2yitP3L6d+ddfO2/cSJ86dWy/ft1zc/NXr9547Fh8dnaev79vhw6txo69z8/PV7vVunXbVqxY//HHr9erF6Lb1euvf+zj4/XOO8+Jd5udnbNmzdZbtzJCQoJHjx7co0dHcT0zMrJ++WXN6dMJgiC0bdv84YfH1PZI09JuqlSqp5+e4uNzp6NETExkTEyk/gEaqIlGozl+/Mz27QdSU6/m5xfUqxc6YEDsPff0FD9QWVnZxo279u8/duPGLW9vr+bNm4wePbhBg3pV1mrduu0rVqwbOLDnlCljyssr1q3bduDAsYyMTG9vr4iIhsOHD2zWLKq2RwoAikLQYGOkDHBOe2ZXkDUAgK0cPnxSEIQJE0boUgbDdu48oGsFoNFoCguL/vOfr27cSNeWZGZmb9++Pz4+8d13X/D29jK+Gnv3Htm376j2dlrare++WxoY6N+iRbS2JD+/8MMPv87IyNIuHjp04vr1W+Xl5eI6//Of7+fm5v/ww3+re4jQ0DoXLqTm5ubrggYTapKScuXLL3/WrXzlyvVFi1bl5eWPGjVIW1JWVv7JJ98lJl7ULmZn5x46dCIjI1ObqohpNJolS1Zv2bJ37Ngh999/ryAIy5b9uXXrXu29JSWlWVk58fHnDRwRANgFggZbqi5lmDTJUk0lAZtYurSKxpNkDQBgmKT3hIzDNFy9mubu7ta0aaSuJDX12v/932e6xfHjhw0fPlC3eOTIqYkTR8TGdgoM9BcEYeXKv27cSG/SJHzKlDENGtS7du3G4sW/X7iQumbN1okTRxhfjYMHj0+ePLp79/Zubm5bt+5duXLDjh0HdJf369dvy8jIatWq6aRJ94eG1klJuTJ//m9pabciIxsZ/xDDhw84evTUf/7zVffuHWNiIho3btCwYT39jiGGa+Li4tK9e4eBA3s2bBjm6uqSnJy6YMHKdeu23XdfX09PD0EQNm7clZh4sX79ug8+ODI6OqKioiIhIfnkyXOSRykrK/v226XHjp1+5JGJffp01RYeO3Y6ODhg5swpERENi4tLUlIub9y4y/gDVA7JAA30mwCcHEGDzeinDOQLcFS6c1uSOJA1AIBNFBYWeXl5GT8QQ9++3YYO7a9bPHr0tFrt/vzzMwIC/ARBiIpq/NxzM1599aOjR0/VKmi4776+gwb11t4eOfLeXbsOX7lyXXfvsWNnfHy8nnlmqraVRPPmTZ5+esrbb38q3sPnn79j+CEaN27w3nv/XLdu+8GDx7QNB3x8vHr16jJmzH1eXp5G1iQiouHMmQ/rFlu3bvbggyPnzJmfnJzaqlVTQRAOHIhzd3d78cVHQ0PvjKDZtWu7rl3biWtSUFA4a9a8lJQrzz8/o127lrpyX18ff39fbeijVru3bduibdsWhg8KAJSPoME2JCkDEQOchPZUF8cNZA0AYH1eXp6FhYUajUaXNYSHN5g/f7YgCKdOnfv00x8k62svp3Vu3coID2+oTRm0AgL8wsMbXLiQKt5njSQjEYSEBN26dVu3ePNmRvPmTcR9MRo1qi9+UCM1aFDvscceFAQhIyMrJeXKkSMnN23anZJy5Y03ntJV1XBNBEHYs+fwrl2HrlxJKyws0mg02sKsrBztjRs30hs3bqBLGar044/Li4qKX399pq6hhNbDD4/5+uuF77zzaevWzSIjG7Vu3VQ31AUA2C++39sAKQOcnOScZ6QSADCSXNMHNmwYVlpalpR0ycj19Qc4MBwmVJk1lJaWSkrc3d0lW+mu4atT0/2G1KkT2LlzmyeemNSnT7fExIsJCclG1uSvv3b88MPyxMSLBQWF4vLS0rK/a1Vztbp1a+/i4vLHH5tLSir9H5o1i5o9+83x44ep1e579x556aUPlixZbcwOFYWJLQFIEDRYGykDIJA1AIBxLNTRXduq/9df15aVlZmweWhondTUa9nZubqSnJzc1NRrISFB2ohB+5t8evrdRgHp6bdv386u1aPUrVsnJeVyQUGhruTKles5ObkGNjGSr6+3IAg3b2YYuf7OnQf9/f1ee+3J//3v/Z9++mT+/NnPPz9DvEJYWOjly9fEx6uve/eOM2dOTkxM/uyzH4qKisV3qdXu7dq1HDt2yEsvPfbUU1M2b95z5MipWh6TsjBAAwCCBqsiZQB0yBoAwFb69OnWoEG98+dT3ntvzsGDx7OycsrLK/LzCy5cSN27Vzv5gqEWC506tS4pKf3qq/kpKVdKSkovXbo6Z8784uKSTp3aaFeoX7+uIAgrV264fv1mSUlpUlLKnDnza/srfceOrfLzC7/+euGVK2nFxSWJiRf/979FtT3Sb75Z9MsvaxISkjMzs8vKyjMzs7du3btlyx5BEOrWrWP8flxdXTw81B4e6sLC4uPHzyxevFp8b48enUpLyz777MeTJ8/l5xfk5OQdPnzyxx9/leyka9f2Tz89NSkp5dNPv9dmDWVlZf/5z9f798fdvJmhrd6pUwlC5YwGAOwRYzTYDCkDMGnS+ConpAAA6Fhi7gl3d7cXX3zk889/unz52ty5iyX3tmgR3bdvVwObDx8+8PDhk0lJl9599wtdYd26dUaOvFd7OyYmIiqqcXJy6htvfKIrqdWFvSAIw4YNPHDg2Jkz599+e7a2pHHj+mFhoeJ1apzeMjMz+9ChExs27JSUt2vXonnzJkbWpHPntuvWbfv3v+/2DujRo2NGRqZu8b77+hw7Fp+UlPLZZ3eHt4iODtffVadObZ55ZtrXXy+cNWveyy8/5ubmlpSUkpSUIl5HrXbv2LG1kXVTAuabAKCPFg3Www+2gGG8RgDAakJCgt9994UpU8a2bBnj6+vt6uri7+/brl3Lp56a8tprTxoej9DLy/Ptt58ZOLBnUFCAq6tLYKD/gAGxb7/9rI/P3YEbn3lmWocOrTw81N7eXr16dXnxxUddXGr3tdPHx+vNN5/p2rWdp6eHl5dnly7tXnnlcVdX11rt5Omnp06aNKplyxhtVb29vWJiIidPHv3cczOMH7RyzJj7Ro68t06dIDc3twYN6k2bNk43RYWWm5vba689OXbsfQ0a1HNzcwsM9O/evcMjj0yscm8dOrR6/vkZqalXP/nku5KS0rfffrZ37y5169Zxc3MLDg7o3r3DO+88K8lTAMDuqNLyUm1dh1p79rPHdbcHDOxkw5rUivgiiuYMgI64UYMdzUCxfVuc7vZXL86zYU2qtGrhWltXwShjp9ZiJjzAaYlbNGiZ36gBkIX+MJC0aLAJe/ncl+BrgAOzm+/0AAAAzokrN9gLzlUAWgQNVkKbcMAYvFIAwBjMJggl4DwEUB2CBhug3wQgxisCAGrED8VQPs5SADoEDQAAAAAAQDYEDQAAAHZA8nMxrdZhW8xqCcAAggYAAAAAACAbggYAAAD7QKMGKATNGQAYRtAAAABgr8gaYH2cdQBqRNAAAABgN/jpGErDOQlAH0EDAACAHePnZVgT5xsAYxA0AAAA2BPH+AH5+PEz06e/HBd32tYVgVkc42wEIDs3W1cAAAAAZpnz6ZznXnquVptcu3bj6NFTR4+eTkm5EhQU8Pnn7xi/7eHDJ//3v4UvvPCPDh1aGVgtMfHihx/+T7/8ueemd+rUpla1tYLS0rLduw8dPnzyypXrBQVFvr7eQUEBMTGRsbEdo6MjbF07paA5AwAjETQAAADYmcdnrZj3ynhxSa2yhvLyijffnGWBetmr9PTbn3/+09WrabqS7Ozc7OzclJQrW7bsmT37zZCQYBtWTyH0UwaaMwCoDkEDAACAc1GphAYN6nXu3KZTpzZz5y4uLS2z3GMNGdLvwQdHWm7/5istLdOmDI0a1R858p7mzZv4+fnk5xdmZmYnJaXs2xenUqlsXUcAsDMEDQAAAPbHnEYNLi4uH374ioEVysrK163bduDAsYyMTG9vr4iIhsOHD2zWLEoQhJUrN6xZs0UQhC+++Em7cu/eXR599EETD0MkNzd/9eqNx47FZ2fn+fv7dujQauzY+/z8fI1cYd++o/PmLXvllSdu387866+dN26kT506tl+/7jU+7u7dh65eTYuJiXjttZnu7ne+G/v7+/r7+0ZENLznnl7akvj487NmfffQQ/ffd19f8ebvvfdldnbO7NlvHThwTFuBmzfTN2zYmZmZHRHRcOrUcY0b1798+dovv6xJSrrk5eU5aFDv4cMHmv/vsjKaMwCoFQaDBAAAsEv6V3pydaFftuzP33/feP36zZKS0qysnBMnzn7yyXey7Lk6hYVF//nPV1u37rt9O7u8vDwzM3v79v3vv/9VQUGhkSto7dx54Mcff7127UZ5eblGoxEE4Z//fP/RR1838NCHD58UBGHChBG6lKFKrVrF1KsXsnPnQXHh5cvXLl683K9fDxcXF10FFixYeeNGeklJ6fnzKbNnz7t8+fqHH34TH3++uLgkKytnxYr12ke0I6QMAGqLFg0AAACo5Nix08HBATNnTomIaFhcXJKScnnjxl3au8aNGxIe3sCYwSC1NmzYuWHDTt1iixbRr78+U3+19eu337iR3qRJ+JQpYxo0qHft2o3Fi3+/cCF1zZqtEyeOMGYFrSNHTk2cOCI2tlNgoL+RB3v1apq7u1vTppG6ktTUa//3f5/pFsePHzZ8+ECVSjVgQOwvv6w5fz5Ft/KOHQddXV3E7Sbi4uKnT3+gS5d2FRXlS5b8cfDg8Y8++qZNm+YPPDA0MND/+PEz3367ZOvWvV27tjOyegBgjwgaAKCSuH9XGLNagNBBd/vtPd9YqjaOLm41/zrZ/GfVU7auAmzAzFEhq+Pr6+Pv76u9nFar3du2bdG2bQsz92nY0aOn1Wr355+fERDgJwhCVFTj556b8eqrHx09ekqbI9S4glbfvt2GDu0v3nONE2oUFhZ5eXkZMxBDnz5dV678a+fOg9r/TElJ6f79cR06tBaHGkOG9O3fv4f29oQJIw4ePO7l5fnEE5Pc3FwFQejevcOOHQeuXr1hzP9EIWjOAMAEBA0AIAhG5wuAYr099k5qQ+LgbCyRNTz88Jivv174zjuftm7dLDKyUevWTcVjJdSKkYNB3rqVER7eUBsiaAUE+IWHN7hwIVWj0ahUqhpX0Ba2atW0tjX08vIsLCwU7yQ8vMH8+bMFQTh16tynn/6gW9PHx7tbtw6HDh2fPHmUl5fnkSMnCwoKBw7sKd5bTEyk7nZwcIAgCFFRjbUpw9+FgefOXahtJW2FlAGAaRijAYCzi/t3BSkDHMnbY7/RhQ5wErJf+zVrFjV79pvjxw9Tq9337j3y0ksfLFmyWjvkgeXU2KTAmMkffHy8a/u4DRuGlZaWJSVdMmblgQNjtQ0ZBEHYseNAvXohrVrFiFdwd3fX3dYmF5KhH1QqwdL/ScshZQBgJIIGAE6NiAGOiqzByZk/KqRa7d6uXcuxY4e89NJjTz01ZfPmPUeOnNLe5eKiEgShokLOq+XQ0Dqpqdeys3N1JTk5uamp10JCgrSX6zWuYDLtcAm//rq2rKzmaT6joyPCwxvs3HkwLe1WYuLFAQNiHXjyS7nGFgXghOg6AcB5VZcyjB7/qJVrAphp9Yof9AvfHvsN3Sich4wdKMrKyv7732/vuadndHREcHBgbm7eqVMJgiCkp9/WruDt7SUIwpkziW3aNFOr3Q3ty2idOrVeu3bbV1/Nf/jhMQ0a1Lt+/eaiRauKi0s6dWpj5Aom69On25Yte8+fT3nvvTkjRgxs3ryJn59vUVFRWlr63r1HBUEQhEpRwsCBPefP/23Rot/d3d169+5q5qMrFp0mAJiDoAGAk9JPGcgXYL90Z68kcSBrcCq1yho++ODr8+dTdIvTp78sCEJkZKN3331BoxGSklKSklLE66vV7h07ttbejoxspFa7b9myd8uWvYIg9O7d5dFHHzSz8sOHDzx8+GRS0qV33/1CV1i3bp2RI+81coXq/POf7+fm5v/ww3+rW8Hd3e3FFx/5/POfLl++NnfuYsm9LVpE9+1bKU2Ije20fPna+PjEXr26+PrWuqeGXSBlAGAmuk4AcEaSlGH0+EdJGeAY9E9m+lA4Ff2rQRNav7u7u7399rO9e3epW7eOm5tbcHBA9+4d3nnn2bCwUO0KXl6eTz75cOPG9cVjHJrJy8vz7befGTiwZ1BQgKurS2Cg/4ABsW+//ayPj5eRK5gjJCT43XdfmDJlbMuWMb6+3q6uLv7+vu3atXzqqSmvvfakZCBMDw91t27tBUEYMCDW/IdWIFIGAOZTpeWl2roOtfbsZ4/rbg8Y2MmGNTHentl3r2omTRpvYE3ACS1devcbTO+XLR6A6qcMln5EwPokTRto1+A8JI0atMyf8BJi7733ZWlp2X/+85KtKyK/KpMpggblW7Vwra2rYIqxU0fUvBLsEy0aADgXUgY4Cdo1OK0qrwkZ1U8u5eXlmzbtvnjxcq9enW1dF/mRMgCQC0EDACdCygCnQtbgtLgytJBFi35/5JHXli79w8vLs2/fbraujjVwLgEwDUEDACdFygBnwHnutGQZrAH6VCpVWFjoM89M8/FxtGEgGZoBgIwIGgA4i+omswScB40anApZg+ymTBnz88+z/vvf11q3bmrrusiMlAGAvAgaADgjfuaF8+Bsd2ZkDTAGKQMA2bnZugIAAACwlMdnrZDMQ6G9qmQeCgiM/gjAYmjRAMAp0G8C0KL3hBNiHgpUiZQBgOUQNABwOrQkh7PhnAdZAyRIGQBYFEEDAACA4yNrgA4pAwBLI2gAAABwCmQNEEgZAFgFQQMAAICzIGtwcqQMAKyDoAEAAMCJkDU4LVIGAFbD9JYAAADORX/OS4FpLx1adUESKQMAC6FFAwAAgNOp7gqTpg2Oh5QBgPURNAAAADijx2etoBuFw6uuuwQpAwCLousEAACA86IbhaOiIQMAG6JFAwAAgFOjG4XjIWUAYFu0aAAAAHB2VbZrEGjaYIcMxEOkDACshhYNAAAAMNRvn6YN9sJAQwZSBgDWRIsGAAAA3EHTBjtFQwYAikLQAAAAgLu016XEDfaCiAGAAtF1AgAAAFIGrlHpSaEcpAwAlIkWDQAAAKgCTRuUjIgBgJIRNAAAAKBa1Y3aIBA32IjhFiWkDACUgKABAAAAhhho2iAQN1gREQMAe0HQAAAAgJoRN9gQEQMA+0LQAAAAAGMZ6EkhEDdYQI1Db5IyAFAgggYAAADUguGmDYLo2pjEwWTGTO1BxABAsQgaYD2HDx/esGGDuESlUrm4uLi5uXl6evr4+AQFBYWFhTVr1iwkJESuh9Bxd3f39PQMCgqqX79+y5YtGzduXOPmoaGhTz75pPGPrtFozp8/n5ycfOXKldzc3MLCQhcXF29v74CAgPDw8KZNmzZq1MjIXWVkZCQkJKSmpqanpxcWFpaUlKjVan9//7CwsOjo6GbNmqnV6trW/MaNG4sXLy4oKNCVBAQETPn/9u48LKorwfv4raIooABBQBQVREFANIoYjQIRcQXUxLjEuCVxOk86SXem3yQ983RmJt0zbfrpmd6mn/R0Z5lkjCbGfYvGPYgYFTdi3IgSBAskoAiyr0W9f1Tneq2Csqi6RW3fz9N/3Hvq3lPn3JTVnF+de+6qVf3797e8jwAAGDw0bhCY4GAVIgYAboCgAY6k1+t1Op1Op2tra6urq6uoqLhy5cqXX34ZHR09bdq0brMAq3V0dHR0dDQ0NGi12tOnT8fExCxcuNDX11eu+gsLC3NycmpqaqSFOp2urq6urq5Oq9V+9dVXkZGRc+bMiYiIMFNPdXX1kSNHioqKjMpbW1tbW1tv37598eJFHx+fqVOnTp482fLmVVRUbNiwobW1VSwJCQlZuXJlUFCQ5ZUAAGDE8rhBIHEwy5J8QSBiAOAiCBrgjEpLS9etW5eRkZGammqntyguLt6+ffuKFStkqe3AgQNnz5596GFlZWVr167Nzs5OSkrq9oCLFy/u27evo6PDfD1tbW3ffvut5UFDWVnZxo0b29raxJKwsLBVq1YFBARYWAMAAGZYEjcIJA7dsTBfEIgYALgUggY4Kb1en5OT09nZmZ6ebqe3uHHjRkVFxeDBg22sJycnx5KUwUCn0+3du9fPzy8+Pt7opStXruzevdvGxpgqKSnZvHmzNLwYOHDgypUrNRqN7O8FAPBk4kiYxOGhyBcAuDeCBjiMuI5Ae3t7fX19eXl5QUHBrVu3pMfk5eUNGTIkNjbWxrcQBKGpqencuXN5eXnSA7RarY1BQ1lZ2YkTJ6QlSqVy4sSJ48aNCw0N1el0t2/fPnv27JUrV8QD9Hr97t27X331VT8/P7GwtrbWNGUIDw+fNGlSdHR0YGBgV1dXfX19WVnZxYsXtVqthc0rKiratm1bZ2enWDJ48OAVK1bIeM8IAABGLJzgIHhe4mB5viAQMQBwZQQNcDy1Wh0WFhYWFpaUlJSfn3/48GHpqzk5OVYHDVL+/v7p6enXrl2rqqoSC1taWmysNjc3V7qrUCiefvrpkSNHGnZVKlVkZGRkZGR4ePjRo0fFw9ra2vLz8zMyMsSSo0eP6nQ6aVXjx4/Pzs5WKpViieEqjR8/vqys7NKlSw9tW2Fh4Y4dO7q6usSSyMjIZcuW+fj49K6TAAD0nuVxg+DuiUOv8gWBiAGA6yNogHOZPHlyXV3dmTNnxJKqqqpbt24NGTLEHm/n7+9vy+mNjY2lpaXSkuTkZDFlkEpLS7t+/bp0vsbly5fFoKGtra2wsFB6fGRk5Ny5cxUKRbfvawgvzLft0qVLu3fv1uv1Ykl0dPQzzzzj7e1t/kQAAGRk+f0UBtIxuUuHDr0NFwTyBQBuhKABTufxxx8/e/asdIRcXFxse9DQ1NRUUFAgnc4gCIKNcyVKSkqMSpKTk3s6eMKECdKg4d69e7W1tYZHS964cUM670AQhKlTp/aUMljCcCOG9BrGxsYuWbJEpeKfPADAMXqbOAgmY3Unzx2sSBYMyBcAuB9GHXA6Go1m0KBB33//vVhSXV1tXVV37txZs2ZNT6+mpKSEhIRYV7NBbW2tdNfb23vgwIE9HWyalYhBg1EHvby8hg0bZkvDpIsyCIIQHx+/aNEiLy8vW+oEAEAWViQOBqYjeQdGD1bHCiLyBQBujKABzigoKEgaNDQ1Nclbv1KpzMzMnDBhgo31NDc3S3f9/f3NTEMwfZakeLpRPQEBATKGAhqNZsGCBaQMAABnY3XiIDIz2pclg7A9TTBFvgDAExA0wBlJ5/wLgmDLTQTd6urqysvLU6lU48aNk7dm6xj1V17Nzc1bt25dunQp900AAJyTdOxtdehgxB4ZgdUIFwB4GgYecEb19fXSXY1GI/tbNDY2fv7553q9PikpyepKjBrW1NSk1+t7ikUaGxt7Ot1oTcrGxkadTifjHIQbN25s3LiRlSABAM7PHqGDQxAuAPBkBA1wOs3NzZWVldKS0NBQ66oaMGDASy+9ZNhub2+vrq7Oy8srKioSD8jJyRk9erTVw2/DCguijo6O27dv97RMg3QlSKPTjTqo0+lu3rw5YsQI61plqDkoKEj6RIzS0tINGzbwbEsAgAsxGqs7ee5AsgAAIoIGOJ28vDyjWwliYmJsr1atVg8ePHjx4sW/+93vdDqdobCpqamysvKhj4rsyfDhw41KCgoKsrKyuj24oKBAuhscHCwGDSNGjFAqldIHTxw/fnz48OFW3zOiUqmWLVu2ZcuW4uJisbCsrOzTTz9dsWKFr6+vddUCAOBApiN5B0YPxAoAYAZBA5xLfn7+2bNnpSXh4eG2P9vSDKPbNHolICAgOjpaOnHg/PnzI0eONH1q5smTJ8vLy6UlY8aMEbd9fX0TEhKuXr0qlmi12v3792dmZiqVStP3LSsru3z5ck+JhoFKpVq6dOm2bduuX78uFlZUVHzyyScrV6708/OzqIcAADgxM6N9WTII0gQAsA5BAxyvvb29oaGhrKysoKDA9P6CGTNmyLIYZHt7+927d48dOyZOZzCwccidnp4uDRr0ev3mzZsnTZo0duzY0NDQrq6uqqqqc+fOXb58WXqWj4/P5MmTpSUZGRnXrl2Ttu38+fPl5eWTJk2Kjo4ODAzU6XQNDQ1arfbSpUs3b960ZBaGl5fXkiVLduzYUVhYKBZWVlauX79+5cqVRgtDAADgTsgIAMCBCBrgMHfu3FmzZo35Y6ZOnWo6O0DGt1CpVEOHDrXu9DfeeEOj0URFRaWmpp44cUIs7+rqys/Pz8/P7+lEhULx5JNPGgUcISEh8+fP37Vrl7Swqqpqz549Ztr/UEqlctGiRbt27ZImHbdv316/fv2qVatMn7gJAAAAADbqZlY24AyUSuX06dPT09Pt+i6pqalqtdrGSqZPnz5x4kQLD/by8po7d258fLzpS4888sj8+fNlfwilQqFYsGCB0cM1qqur161bZ8ttIwAAAADQLWY0wBkNGzZs+vTpZuYa2M7LyyslJWXq1Kmy1JaZmRkVFZWTk1NbW2vmsKFDh2ZmZkZERPR0QFJS0pAhQw4fPixdxNGUj49PQkKC5c1TKBTz58/38vI6f/68WFhTU7Nu3bpVq1YFBwdbXhUAAAAAmEfQAAdTKpUqlcrX19ff379///6DBg2Kj48PCwuT/Y0UCoW3t7dGowkNDR02bNiYMWOCgoJkrD8xMXHUqFFFRUXFxcW3bt1qaGhoaWlRKpV+fn5BQUFRUVFxcXGWRCcDBgxYvnx5dXX1tWvXtFrt3bt3W1pa2tra1Gp1v379Bg4cGBsbGx8fb8VEjOzsbJVKdfr0abHk3r17hqwhJCSkt7UBAAAAQLcIGtB3Jk6caPktBg55CxtPVygUcXFxcXFxVtcgCgsLCwsLS01NtfB4C1s+e/bs2bNn29Y0AAAAADCHNRoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsWAwSAOS3f/+Wb745Y1ru5aVSq32CgoLDw4eMHDl65MhEQVCYqaem5k5h4QWttri2trqlpUmvF/z8NEFBIZGRIxISxg0cOFg8sr297aOP/lBXd/8Bq3PmLBw/PsW0zgMHtl64cP/hI8OGxS5b9mOxGS0tzRcvnikpuXbnTmVra4tCIfj6anx8/AID+4WFDRowICIqakT//pY+F8boOjz99AsjRhg/mTUv78DJk0fE3blzlz7ySDcrm1p+KUz1qlPvvvsb6WW0RFLSlMzMRab97Ulycurs2U+Ju5ZcJQAAABdC0AAAfUen62xp6WxpaaqsvHXx4pnBg4ctXrxaowkwPbK1tfnQoZ2FhRf0er20vKGhrqGhrry85NSpL2NiRmVmLg4MDBIEQa32ycpasmnTB+KRubn7YmNHG14VlZXduHDh/pjW29s7K2uJmDIUFxfu3buxpaVZekpjY31jY/3du1WlpUWCySC5D/T2Uhhxzk4BAAC4MW6dAACHqai4eeDANtPy2trqtWv/fPXq10ZDayPFxYVr1/53ZWW5YTc6Om7s2Eniq21trYcP75Qer9N17t+/VRDu15menh0cHGrYrqws37HjY6MBucNZdylEztkpAAAA98aMBgCwO3EyfGtry5UrBYcP7xJH+0VFV1tbW3x9/cSD29pat279qK6uRiyJiIiaOnXO4MHDFApFZWX5yZNHDL/DC4LQ3Ny4bdv/Pf/8/wsI6CcIwowZT5SUXGtoqDO8ev365WvXLsXHP2LYPXHiSE3NHbHaIUOiJ0xIE3fz8g7odDrDtre3evr0eTExif7+Ae3t7dXVVTduFF66dK6xsV7mS2OWLZfC6k69/PK/GjXj0KGdBQUnxN2FC5+PixtjSfu5CQIAAHgmZjQAQN/x9fWbMCF16NBosUSv76qvf2BFgJMnH4gDoqJiVq78yfDh8T4+vmq1T1RUzNKlL4rZgSAIjY31ubn7DNs+Pr5z5iyS1nb48M62tlZBEO7cqczPPyqWq1SquXOXKhR/v2lCp9PdvFkkvpqaOnP8+JR+/YK9vFR+fprIyOHp6dmvvPJvmZmLAwICbb4MlrLlUgjO2ikAAAC3R9AAAA7m66sRt9vaWgsKToq7CoUiK2uJl5eX9HiFQjFnziJvb7VYcuVKQX39PcN2bGxiYuJ48aXGxvqjR/fq9fr9+7d2denE8rS0OSEhA8Td5uZG8Zd/QRD69etv2k6lUpmUNDklZWbvu2gN2y+FE3YKAADAExA0AEDfaWtr/frrk+XlpWJJRERUv37B4q5WW9zR0S7uRkXFdPuIB40mIDY2UdzV67tu3PhW3J016ynpApMXLpz+4otNFRU3xZJBgyIfeyxdWqHRAP7cueNNTQ296Jgd2H4pnLBTAAAAnoA1GgDA7rZs+bDb8uDgkCeeWC4tuXWrVLo7ZEh0T3UOHRpdWHhBemJS0mTDtp+fZvbshbt2rf/hRf3ly+fFI5VKr7lzn1YoHgiaNZqAwMAgcXGHigrtu+/+Jjo6bujQ4YMGDR00aKh0FQmr9XQdumX7peibTpnRU39/9rP/8PPzt+tbAwAAOBBBAwA4hlrtM2vWU0a/0jc2PvCTe1BQN7P9f3gpxMyJCQlj4+PHXrt20fTElJQZAwZEmJZPmJCWm/uFuNvZ2fndd1e/++6qIAgKhSI8fHBCwrjx4ydLb/SwK1kuhbN1CgAAwBNw6wQAOEZ7e9vWrR8dPbr3wcJW6a5K5d3T6UYvGVZ8lJo9+ynT8fOAAREpKTO6rfCxx6aNGTOh25f0en1V1a1jx/a9995vDaP0PiDLpXC2TgEAAHgCZjQAgN2Jjzlsb2+rqLh58OCO2tpqw0unT+dGRcXExIwy7KrVvtITOzs7eqrT6CUfH1+jA/z9A2fNenLPno1iiUKhnDt3qVLpJXRHoVDMm7csIWHcmTPHtNob4gM4pVpbW3buXL969WthYQN7apgZ3T7uMS/vwMmTR0wPluVS9EGnzODxlgAAwDMRNABA31GrfaKj4554Yvm6de+IhefPnxCDBqPnLNbVPfDkywdfqpHudvuAxvj4cdKgISio/6BBQ823MDY2MTY2sbm5Uau9UVFx89atm99/r+3q6hIP0Ok6CwpOzJ690Hw9tpPxUjhPpwAAADwBQQMA9LWIiEhvb7X4SIU7d74XXzJa8tBoQUQp6aMrTE+0kUYTkJAwNiFhrCAILS3NublffPPNafHVqqpbMr5XT2S/FM7QKQAAAE/AGg0A4BD35/C3traI21FRMd7e91cc0GqLxZsspJqbG6XLCigUyuHD4+3TTsHPTzNnziLpOgg6XZeZ4+Vi10vhqE4BAAB4AoIGAOhr339f1tFxf1kBf//7U/19fHyTk1PFXb1ev3//Vp1OJz1dr9cfPLhdnBAhCMLo0ePNPJTBQps2vV9Scq3bVQw6Otq7uu63ITCwn43vZQlZLoWzdQoAAMATcOsEAPSd9va2igrtwYPbpYXR0bHS3SlTZly/fln89V6rLd6w4a+PP545ZMgwhUJRWVl+4sTh0tIi8fiAgH7Tps21vW1lZSWlpUXBwSGjRiVFRo4IDx/s5+ff0dF++3bF8eMHpCsaDB8eZ/vbWcL2S+GEnQIAAHB7BA0AYHdbtnzY00sqlffkydOlJb6+fkuW/GjTpvfr6+8ZSioqtJs3f9Dt6X5+/osWrQ4IkO3X+Hv3ak6dyjl1KqenA4KDQ8aOnSTX25kn16VwVKd6+u8eHBz60ktvynsWAACA8+DWCQBwGH//wCVLfhQcHGpUHhIyYPXq1xMSxikUCjOnjxiRsHr1axERkbI0Rq1WP/SYAQMGPfPMj6VLG9ibjZfCOTsFAADg3pjRAAB9SeHt7e3vHxAWNigmJiExMdnHx7fb4/z8NAsWrKqpuXP16teGdRBbWpoFQe/rqwkKComMHDFq1LiBA4fI2LKf/vRX5eUlt26VVlaW37t3t6Ghrr29ratLr1arAwODwsMHx8WNiYt7RKns64TalkvhtJ0CAABwY4rKRq2j29Brr/7pRXE7Y3qyA1tiua/+cP9O4OXLlziwJYAT+uyzreJ22s/tMuQr+PX9f4MLlrxgj7cAnNmurffvyHh7xysObAkAQHY71u91dBOssfDZeY5uAuyF33AAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoAAAAAAIBsCBoc4LPPtjq6CYAT4V8EAAAA4E4IGvpI2s+51MDD8S8FAAAAcHX8TQ8AAAAAAGRD0OAYzBUHDPi3AAAAALgZgoa+w5xwwDz+jQAAAABugD/rHYYfcgH+FQAAAADuh6ChTxn9YMsoC57M6PPPdAYAAADAPfCXfV8jawAEUgYAAADAffHHvQOQNcDDkTIAAAAAbkzl6AZ4qLSfK7/6Q5e4axh3LV++xHEtAvqCaaxGygAAAAC4GYIGhzHKGgTJGIzEAW6mp2k7pAwAAACA+yFocCTTrMGAmyngCUgZAAAAALfEH/oOxlgLnolPPgAAAOCumNHgeIYRV7dTGwD3Q8QAAAAAuDeCBmchjr5IHOCWyBcAAAAAD0HQ4HQYjwEAAAAAXBdjWgAAAAAAIBuCBgAAAAAAIBuCBgAAAAAAIBuCBgAAAAAAIBuCBgAAAAAAIBuCBgAAAAAAIBuCBgAAAAAAIBuCBgAAAAAAIBuCBgAAAAAAIBuCBgAAAAAAIBuCBgAAAAAAIBuCBgAAAAAAIBuCBgAAAAAAIBuCBgAAAAAAIBuCBgAeZ9fWDx3dBKBP8ZkHAAB9iaABgEdI/iVfd4AgCMLbO15xdBMAAICb4y9vAAAAAAAgG4IGAJ6ImeTwHHzaAQBAHyNoAOApuHsC4L4JAADQB/izG4CH4mdeeAI+5wAAoO8RNADwIEaTGhiDwb0ZfcKZzgAAAPoGQQMAz0LWAA9BygAAAByFoAGAxyFrgNsjZQAAAA6kcnQDAMABkn+pLPh1l7hrGJUtWPKC41oEyMM0OCNlAAAAfYygAYCHMsoaBMkIjcQBLqeniTmkDAAAoO8RNADwXKZZgwE3U8A9kDIAAACHYI0GAB7NaL0GwG2QMgAAAEdhRgMAT2fIGrqd2gC4IiIGAADgWAQNACAIkqkNJA5wUeQLAADASRA0AMADLLyZ4mhOgbj9l9c/sFtzAAAAABfDzckAAAAAAEA2BA0AAAAAAEA2BA0AAAAAAEA2BA0AAAAAAEA2BA0AAAAAAEA2BA0AAAAAAEA2BA0AAAAAAEA2BA0AAAAAAEA2BA0AAAAAAEA2BA0AAAAAAEA2BA0AAAAAAEA2BA0AAAAAAEA2BA0AAAAAAEA2Kkc3AAAAZ5e99C1HNwHOZd/mNY5uAgAAzktR2ah1dBus8eqfXhS3M6YnO7AlADzQ0ZwCcfsvr3/gwJbArsgX8FAkDgCcwY71ex3dBGssfHaeo5sAe2FGAwAAxogYYCHDR4W4AQAAKdZoAADgAaQM6C0+MwAASLlD0CCdwwwA9sZ3jntjxAjr8MkBAEDkqkEDN0UDcAZ8F7kZxoqwBZ8fAAAMXDVoAABAXowSYTs+RQAACC4dNEh/SGQmM4C+wfMm3BXjQ8iFzxIAAC4cNAAAAAAAAGfjPkEDkxoA2BvfM+6Kn6AhLz5RAAAP59pBg9G8ZcYAAOzH6BuG+yYAAACAbrl20CDwtz4AR+CbBwAAAOiJywcNRpjUAMAe+G5xY8xyhz3wuQIAeDJ3CBq4gQKAXXHTBAAAAGA5dwgaBLIGAHZDygAAAAD0ipsEDQJZAwA7IGUAAAAAest9ggaBrAGArEgZAAAAACu4VdAgdJc1EDcA6C3Trw5SBgAAAMBC7hY0CN2NB8gaAFjO9BuDlAEAAACwnBsGDUIPWQNxAwDzuv2iIGUAAAAAekXl6AbYy19e/+DVP71oVCgOITKmJ/d5iwA4KTMpJCkDHOvTP//7qNhoacnCl35xs7zS6LDHkkb/7e1/kpZ8eeLcP//2f7qt882fPLc4K0NasvjlfykpqzD/7qcKLv30l3/sqWH/u3H3ext2Ss9dMCf9rVdXG7Zv363Neu61bhtjxtiE2OkpE8YljowIDwsKDFAohOaW1srbd2+UVXx95fqx019X19zr6Vzzfdz7f3+MCA+1vCUvvvmf5y99K3T3n8PUv//5wz1HvrK8cgAA3JLbBg3CDyME07hBIHEA8LCbqogY4JwWZk777w83GRdmTbPwdJXKa1baRKPC7Iwpf12/3ZZWrVgwZ+Pnh+saGm2pRBQ9NOKtf1ydlBhnVB4UGBAUGBAfMyxr2pRfvPLsj9/8z4LL10xPt1MfAQCA5dw5aDDodmqDiPspAJgiZYDTmj8j7a/rtrV3dIolIcH9pj1maWie9ui4oMAAo8KsaSl/+2SHXq+3ulUaP9/nFme/s3aL1TWIUh8d+1+/+Imfr4/5w5QKha+PutuX7NRHAABgOfcPGgTJmMFM4gAA5AtwfkGBAdNTHz2Qmy+WPDlrqkrlZeHpWRlTTAsjwkOTEkd+feW6LQ1bOm/mpzsP1Nyrt6WSkdGRRilDbn7B9v1HrxaVNjY39wvwjx8xLG3iuPkzUv01fj1V8tA+zvuHN6QvBfprcjf/Tdz94/9+9tnuQw9tqtG9JAAAQMo9F4PsyV9e/4CBBABTfDnAhSzKvL/6gEKheCoz3cIT/TV+Uycmibt3a+vE7eyMFBtb5euj/tHT822s5J9eWiFNGX7//qdvvP3OyfOX7tU3dHbqau7Vnyq49Pv3P8187rV12/dJp3WI7NpHAABgIc8KGgwMIwrGFYCH46sAruVqUYlhI3lMfPTQCMP25PFjhgwcYNi+8sMBPZmVNlGt9jZsNza1vPvpDvGlmWkTvVVWTnIUB/wLszIGhoVYV4kgCKNHDp8wJkHcPfLV2U17jnR7ZHNL6ztrt5y7WGj6kp36CAAAesXT/x+XAQYAwCUcP/tNWEhweGh/QRAWZk7704cbBUFY9MMykFeLSr79rnT0yOFmapD+pH/87IUvT55785Vnvby8BEHoF+CfNnHc0VPnrWjYniPH5898XO2tUnurXnjmid/8z8dWVCIIQsqjY6W7n+0+aEUlduojAADoFU+c0QAAgMvp6urafSjPsD1/Rppa7R0WEjx1UpKhZPuBXPOnDwwLGT8mXtw9eup8fUNTweX76zJYfWfB7bu1O/YfNWw/MfPxIYMGWFdP3PAocbu9o/OhEzRM2a+PpqYkP3J+78dG/8vZ2P0jRQEA8DQEDQAAuIadB491dXUJgtAv0H9m6sQFs6cafqtvam45eCzf/LlZ06YoFQrDdlt7+4lzFwVBkP68nzZxXKC/xrqGfbRlT2tbuyAIKpXXi8uetK6S/kGB4rZhUQZxN7R/kOmo/tjmd41qsGsfAQCA5QgaAABwDVXVNYbBsyAIi7MyFsz++zKQ+3NPtbS2mT83a9r9ZzGcKrhsyAVy8wvEJz6qvVUz0yZa17Cae/Wb9/59PYXsjJRhQwdZV4/IuudQ2rWPAADAcp6+RgMAAC5k+4HcxyclCYIwLnHk/cIf7lzoycjoyNjooeLu0ZN//5G/qrrmqmRlh+yMlJ0Hj1nXsHXb9i3Jnq7x81UqlS+teOr0hau9raG2rkHc7h/Uz8vLS6fTmTneSB/0UYrHWwIAYAYzGgAAcBknzn5TVV0jLbl8rfh6SZn5s+ZOv782gU6nyztzQdwVB+SCIIwfHTdoQKh1DatraPxs9yHD9qy0SSOHDTV/vKmi0vu9UHurEkdGi7t3a+smzHt+wrzn/+V3xrdLiPqgjwAAwELMaAAAwGV06fU7Dx57acVTYsn2/bnmT1EqFHPSJ4u7Xl5eRzf9tdsjFQpF1rQpa7futa5tn+zc//S8Gf0C/BUKxcKsjN6efuLcxR8vXyDuLp0389K3xRae22d9BAAAlmBGAwAArmT3oTzDkpCCIDQ2tRw6ftr88Y+OHWV4KKYlbHkuQ2NTyyc7Dhi21d69/iXjyvUbX1+5/4SIrGlT5s9Ms/DcPusjAACwBEEDAACu5PbdWvG+gC+OnjAseWhGr8bVI6IGx8cMs7ptGz8/JF1qobd+/8EGaXd+9bMfrXnjxeQx8QH+fiqVV3ho/4SY6G5P7Ms+AgCAh+LWCQAAXMwbb79j4ZFqtff0lAni7pa9X/7Xe58YHeProz684R2Nr69hNztjyrXim9Y1rKW17eOtX7z2wjPWnX6t+Oa//v693/7zy2q1tyAICoUiOyPloSFCH/fRYEryI+f3fmxavj/31L/94X1bagYAwA0wowEAALc17bFkf42fuLv3y69Mj2lta885cU7czZw6WalQWP2OW/Z9eafmntWn5+YXPPfGr799WArQ0dmZd+Zrw3bf9xEAAJjHjAYAANxWVsYUcbu0/PsrRSXdHvZFzsl5M/6+IEJYSPDEpMTTX1+x7h3b2zs+2rznFy+vsu50QRCul5St+NmvJo1LzJgyYVziyIFh/QP9NZ06XWNTS3nlneKb5ecvfXuy4FJ9Q5Ph+L7vIwAAME9R2ah1dBsAAHCY7KVvOboJcE/7Nq9xdBMAeIod613yYToLn53n6CbAXrh1AgAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQAAAAAAyIagAQDg0fZtXuPoJsAN8bkCAHgyggYAAAAAACAbggYAAAAAACAbggYAgKdjljvkxScKAODhCBoAAAAAAIBsCBoAAOAnaMiGzxIAAAQNAAAIAuNDyIFPEQAAAkEDAAAiRomwBZ8fAAAMCBoAALiPsSKswycHAAARQQMAAA9gxIje4jMDAICUytENAADA6RjGjdlL33J0Q+DsiBgAADBF0AAAQPfEMSSJA4yQLwAAYAZBAwAAD8GoEgAAwHKs0QAAAAAAAGRD0AAAAAAAAGRD0AAAAAAAAGRD0AAAAAAAAGRD0AAAAAAAAGRD0AAAAAAAAGRD0AAAAAAAAGRD0AAAAAAAAGRD0AAAAAAAAGRD0AAAAAAAAGRD0AAAAAAALmzhs/Mc3YRec8U2w3IEDQAAAAAAQDYEDQAAAAAAQDYEDQAAAADg2lzrTgTXai2sQNAAAAAAAABkQ9AAAAAAAC7PVaYJuEo7YQuCBgAAAABwB84/hnf+FkIWBA0AAAAA4CaceSTvzG2DvAgaAAAAAMB9OOd43jlbBTshaAAAAAAAt+Jso3pnaw/sjaABAAAAANyN84ztnacl6DMEDQAAAADghpxhhO8MbUDfU1Q2ah3dBgAAAACAvexYv7fv35SIwZP9f8M0dTjhaz1fAAAAAElFTkSuQmCC"""
    import base64 as _b64
    st.image(_b64.b64decode(CAMPUS_MAP_B64), caption="College Campus Model", use_container_width=True)

    # Live campus map using the verified AITS Tirupati coordinates.
    st.subheader("📍 Live Campus Map")
    st.caption("Use the live map to view the real campus area. The custom campus model above remains the college-specific guide.")

    st.components.v1.html(
        """
        <iframe
            title="AITS Tirupati Campus Map"
            src="https://www.openstreetmap.org/export/embed.html?bbox=79.4940%2C13.6595%2C79.5058%2C13.6682&layer=mapnik&marker=13.66383%2C79.499926"
            style="width:100%;height:420px;border:0;border-radius:12px;"
            loading="eager">
        </iframe>
        """,
        height=420,
    )

    col1, col2 = st.columns(2)
    with col1:
        st.link_button(
            "🗺️ Open Live Campus Map",
            "https://www.openstreetmap.org/?mlat=13.66383&mlon=79.499926#map=16/13.66383/79.499926",
            use_container_width=True,
        )
    with col2:
        st.link_button(
            "📍 Open in Google Maps",
            "https://www.google.com/maps/search/?api=1&query=13.66383,79.499926",
            use_container_width=True,
        )

    st.info("AITS Tirupati: Venkatapuram Village, Renigunta Mandal, Tirupati, Andhra Pradesh 517520\n\nCoordinates: 13.66383, 79.499926")

    locations = {
        "library": "📚 Library → B Block, 2nd Floor",
        "auditorium": "🎤 Auditorium → A + B + C Combined Block, Ground Floor",
        "canteen": "🍴 Canteen → Canteen Building, Ground Floor (snacks); 1st Floor (gym)",
        "gym": "🏋️ Gym → Canteen Building, 1st Floor",
        "snacks": "🍴 Snacks → Canteen Building, Ground Floor",
        "a block": "🏢 A Block → A + B + C Combined Block",
        "b block": "🏢 B Block → A + B + C Combined Block",
        "c block": "🏢 C Block → A + B + C Combined Block",
        "d block": "🏢 D Block → D Block, behind the A + B + C Combined Block",
        "e block": "🏢 E Block → E Block, in front of A Block",
        "boys hostel": "🧑 Boys Hostel → Left side of D Block and in front of Girls Hostel",
        "girls hostel": "👧 Girls Hostel → Girls Hostel, opposite/in front of Boys Hostel",
        "parking": "🚗 Parking → Parking area, left side of the campus",
        "ground": "🌳 Ground → Large ground, after the parking area",
        "main gate": "🚪 Main Gate → Main entrance",
    }

    query = st.text_input("🔎 Search campus location", placeholder="Example: library")
    if query.strip():
        q=query.strip().lower()
        matches=[v for k,v in locations.items() if q in k or q in v.lower()]
        if matches:
            for m in matches: st.success(m)
        else:
            st.warning("Location not added yet. Add its details after taking the class/room photos.")

    st.subheader("📍 Campus Locations")
    st.dataframe([{"Place":k.title(),"Location":v} for k,v in locations.items()], use_container_width=True, hide_index=True)

def profile():
    student = get_student(st.session_state.student_id)
    st.title("👤 Profile")
    st.write(f"### {student['name']}")
    st.write(f"**Student ID:** {student['student_id']}")
    st.write(f"**Academic Year:** {student['year']}")
    st.write(f"**Semester:** {student['semester']}")
    st.write(f"**Branch:** {student['branch']}")
    st.write(f"**Section:** {student['section']}")
    st.write(f"**Status:** {student['status']}")
    st.divider()
    st.subheader("🔐 Change Password")
    current_password=st.text_input("Current Password", type="password", key="profile_current_password")
    new_password=st.text_input("New Password", type="password", key="profile_new_password")
    confirm_password=st.text_input("Confirm New Password", type="password", key="profile_confirm_password")
    if st.button("🔐 Change Password", use_container_width=True):
        if student['password'] != password_hash(current_password): st.error("Current password is incorrect.")
        elif not new_password: st.error("Enter a new password.")
        elif new_password != confirm_password: st.error("New passwords do not match.")
        else:
            conn=connect(); conn.execute("UPDATE students SET password=? WHERE student_id=?", (password_hash(new_password), student['student_id'])); conn.commit(); conn.close(); st.success("Password changed successfully!")

# ==========================================================
# ADMIN - ADD STUDENT
# ==========================================================

def admin_students():
    st.subheader("👥 Student Management")
    st.caption("Edit year/semester/password/status without creating a new account. Use Deactivate-style statuses when a student leaves temporarily or permanently.")
    mode=st.radio("Action",["➕ Add Student","✏️ Edit Student","🗑️ Delete Student"],horizontal=True,key="student_admin_mode")
    years=list(COLLEGE_DATA.keys())
    conn=connect(); students=conn.execute("SELECT * FROM students ORDER BY year, branch, section, name").fetchall(); conn.close()
    statuses=["Active","Repeating Year","On Leave","Discontinued","Graduated"]
    if mode=="➕ Add Student":
        student_id=st.text_input("Student ID",key="add_student_id"); name=st.text_input("Student Name",key="add_student_name")
        year=st.selectbox("Academic Year",years,key="add_student_year"); branch=st.selectbox("Branch",list(COLLEGE_DATA[year].keys()),key="add_student_branch"); section=st.selectbox("Section",COLLEGE_DATA[year][branch],key="add_student_section"); semester=st.selectbox("Semester",SEMESTERS_BY_YEAR[year],key="add_student_semester"); password=st.text_input("Student Password",type="password",key="add_student_password"); status=st.selectbox("Status",statuses,key="add_student_status")
        if st.button("➕ Add Student",use_container_width=True):
            if not all([student_id,name,password]): st.error("Please fill Student ID, Name and Password.")
            else:
                conn=connect()
                try:
                    conn.execute("INSERT INTO students (student_id,name,year,branch,section,password,semester,status) VALUES (?,?,?,?,?,?,?,?)",(student_id,name,year,branch,section,password_hash(password),semester,status)); conn.commit(); st.success("Student added successfully!"); st.rerun()
                except sqlite3.IntegrityError: st.error("Student ID already exists.")
                finally: conn.close()
    elif mode=="✏️ Edit Student":
        if not students: st.info("No students added yet."); return
        choices={f"{x['name']} ({x['student_id']})":x['student_id'] for x in students}; label=st.selectbox("Select Student",list(choices.keys()),key="edit_student_select"); sid=choices[label]; cur=next(x for x in students if x['student_id']==sid)
        name=st.text_input("Student Name",value=cur['name'],key=f"edit_name_{sid}"); year=st.selectbox("Academic Year",years,index=years.index(cur['year']) if cur['year'] in years else 0,key=f"edit_year_{sid}"); branches=list(COLLEGE_DATA[year].keys()); branch=st.selectbox("Branch",branches,index=branches.index(cur['branch']) if cur['branch'] in branches else 0,key=f"edit_branch_{sid}"); secs=COLLEGE_DATA[year][branch]; section=st.selectbox("Section",secs,index=secs.index(cur['section']) if cur['section'] in secs else 0,key=f"edit_section_{sid}"); sems=SEMESTERS_BY_YEAR[year]; semester=st.selectbox("Semester",sems,index=sems.index(cur['semester']) if cur['semester'] in sems else 0,key=f"edit_semester_{sid}"); pw=st.text_input("New Password (leave blank to keep current)",type="password",key=f"edit_password_{sid}"); status=st.selectbox("Status",statuses,index=statuses.index(cur['status']) if cur['status'] in statuses else 0,key=f"edit_status_{sid}")
        if st.button("💾 Save Student Changes",use_container_width=True):
            conn=connect()
            if pw: conn.execute("UPDATE students SET name=?,year=?,branch=?,section=?,semester=?,status=?,password=? WHERE student_id=?",(name,year,branch,section,semester,status,password_hash(pw),sid))
            else: conn.execute("UPDATE students SET name=?,year=?,branch=?,section=?,semester=?,status=? WHERE student_id=?",(name,year,branch,section,semester,status,sid))
            conn.commit(); conn.close(); st.success("Student updated successfully!"); st.rerun()
    else:
        if not students: st.info("No students added yet."); return
        choices={f"{x['name']} ({x['student_id']})":x['student_id'] for x in students}; label=st.selectbox("Select Student to Permanently Delete",list(choices.keys()),key="delete_student_select"); sid=choices[label]; st.warning("For students who are only leaving/pausing, use Edit and choose On Leave or Discontinued instead."); confirm=st.checkbox("I understand this permanently deletes this student and their attendance records.",key=f"confirm_delete_{sid}")
        if st.button("🗑️ Delete Student Permanently",disabled=not confirm,use_container_width=True):
            conn=connect()
            for table in ["daily_attendance","attendance_days","attendance","monthly_attendance"]: conn.execute(f"DELETE FROM {table} WHERE student_id=?",(sid,))
            conn.execute("DELETE FROM students WHERE student_id=?",(sid,)); conn.commit(); conn.close(); st.success("Student deleted permanently."); st.rerun()
    st.divider(); conn=connect(); rows=conn.execute("SELECT student_id,name,year,semester,branch,section,status FROM students ORDER BY year,branch,section,name").fetchall(); conn.close()
    if rows: st.dataframe([dict(r) for r in rows],use_container_width=True,hide_index=True)

# ==========================================================
# ADMIN - UPLOAD TIMETABLE
# ==========================================================

def admin_timetable():
    st.subheader("🖼️ Timetable Photo Management")
    year=st.selectbox("Select Year",list(COLLEGE_DATA.keys()),key="upload_year"); branch=st.selectbox("Select Branch",list(COLLEGE_DATA[year].keys()),key="upload_branch"); section=st.selectbox("Select Section",COLLEGE_DATA[year][branch],key="upload_section"); semester=st.selectbox("Select Semester",SEMESTERS_BY_YEAR[year],key="upload_semester")
    uploaded=st.file_uploader("📤 Upload Timetable Photo",type=["png","jpg","jpeg"],key="timetable_photo")
    if uploaded: st.image(uploaded,caption="Timetable Preview",use_container_width=True)
    if st.button("💾 Save / Replace Timetable",use_container_width=True):
        if uploaded is None: st.error("Please upload a timetable photo.")
        else:
            path=os.path.join(UPLOAD_FOLDER,f"{year}_{branch}_{section}_{semester}.png".replace(" ","_")); open(path,"wb").write(uploaded.getbuffer())
            conn=connect(); conn.execute("INSERT INTO timetable_images (year,branch,section,semester,image_path) VALUES (?,?,?,?,?) ON CONFLICT(year,branch,section,semester) DO UPDATE SET image_path=excluded.image_path,created_at=CURRENT_TIMESTAMP",(year,branch,section,semester,path)); conn.commit(); conn.close(); st.success("Timetable saved/replaced!"); st.rerun()
    st.divider(); st.subheader("📋 Saved Timetables")
    conn=connect(); rows=conn.execute("SELECT * FROM timetable_images ORDER BY year,branch,section,semester").fetchall(); conn.close()
    if not rows: st.info("No semester timetable photos saved yet."); return
    for r in rows:
        c1,c2=st.columns([5,1]); c1.write(f"**{r['year']} | {r['branch']} | Section {r['section']} | {r['semester']}**")
        if os.path.exists(r['image_path']): c1.image(r['image_path'],width=420)
        if c2.button("🗑️ Delete",key=f"delete_tt_image_{r['id']}"):
            conn=connect(); conn.execute("DELETE FROM timetable_images WHERE id=?",(r['id'],)); conn.commit(); conn.close();
            try: os.remove(r['image_path'])
            except OSError: pass
            st.rerun()

# ==========================================================
# ADMIN - ADD SUBJECT
# ==========================================================

def admin_subjects():
    st.subheader("📚 Subject Management")
    action=st.radio("Action",["➕ Add Subject","✏️ Edit Subject","🗑️ Delete Subject"],horizontal=True,key="subject_action")
    year=st.selectbox("Year",list(COLLEGE_DATA.keys()),key="subject_admin_year"); branch=st.selectbox("Branch",list(COLLEGE_DATA[year].keys()),key="subject_admin_branch"); section=st.selectbox("Section",COLLEGE_DATA[year][branch],key="subject_admin_section"); semester=st.selectbox("Semester",SEMESTERS_BY_YEAR[year],key="subject_admin_semester")
    conn=connect(); rows=conn.execute("SELECT * FROM subjects WHERE year=? AND branch=? AND section=? AND (semester=? OR semester='Current' OR semester='') ORDER BY subject_name",(year,branch,section,semester)).fetchall(); conn.close()
    if action=="➕ Add Subject":
        name=st.text_input("Subject Name",key="new_subject_name")
        if st.button("➕ Add Subject",use_container_width=True):
            if not name.strip(): st.error("Enter subject name.")
            else:
                conn=connect()
                try: conn.execute("INSERT INTO subjects (subject_name,year,branch,section,semester) VALUES (?,?,?,?,?)",(name.strip(),year,branch,section,semester)); conn.commit(); st.success("Subject added!"); st.rerun()
                except sqlite3.IntegrityError: st.error("That subject already exists for this semester.")
                finally: conn.close()
    elif rows:
        choices={f"{r['subject_name']} (ID {r['subject_id']})":r['subject_id'] for r in rows}; label=st.selectbox("Select Subject",list(choices.keys()),key="subject_manage_select"); sid=choices[label]; cur=next(r for r in rows if r['subject_id']==sid)
        if action=="✏️ Edit Subject":
            name=st.text_input("Subject Name",value=cur['subject_name'],key=f"edit_subject_{sid}")
            if st.button("💾 Save Subject",use_container_width=True): conn=connect(); conn.execute("UPDATE subjects SET subject_name=? WHERE subject_id=?",(name.strip(),sid)); conn.commit(); conn.close(); st.success("Subject updated!"); st.rerun()
        else:
            st.warning("This removes the subject from this semester. Historical attendance is kept.")
            if st.button("🗑️ Delete Subject",use_container_width=True): conn=connect(); conn.execute("DELETE FROM subjects WHERE subject_id=?",(sid,)); conn.commit(); conn.close(); st.success("Subject deleted!"); st.rerun()
    elif action!="➕ Add Subject": st.info("No subjects saved for this group.")
    if rows: st.dataframe([dict(r) for r in rows],use_container_width=True,hide_index=True)

# ==========================================================
# ADMIN - ATTENDANCE
# ==========================================================

def admin_attendance():
    st.subheader("📊 Update Official Attendance Percentage")
    st.caption("Admin only: enter the student's final monthly attendance percentage. No daily Present/Absent entry is required here.")

    conn = connect()
    students = conn.execute("SELECT * FROM students ORDER BY name").fetchall()
    conn.close()

    if not students:
        st.info("No students added yet.")
        return

    student_names = {f"{s['name']} ({s['student_id']})": s['student_id'] for s in students}
    selected = st.selectbox("Select Student", list(student_names.keys()), key="admin_pct_student")
    student_id = student_names[selected]

    month = st.text_input(
        "Attendance Month",
        value=date.today().strftime("%Y-%m"),
        help="Use YYYY-MM, for example 2026-09.",
        key="admin_pct_month"
    )

    conn = connect()
    existing = conn.execute("""
        SELECT percentage FROM monthly_attendance
        WHERE student_id = ? AND attendance_month = ?
    """, (student_id, month)).fetchone()
    conn.close()

    percentage = st.number_input(
        "Official Attendance Percentage (%)",
        min_value=0.0,
        max_value=100.0,
        value=float(existing["percentage"]) if existing else 0.0,
        step=0.5,
        key="admin_pct_value"
    )

    if st.button("💾 Save Official Percentage", use_container_width=True):
        if len(month) != 7 or month[4] != "-":
            st.error("Please enter the month as YYYY-MM.")
            return

        conn = connect()
        conn.execute("""
            INSERT INTO monthly_attendance (student_id, attendance_month, percentage)
            VALUES (?, ?, ?)
            ON CONFLICT(student_id, attendance_month)
            DO UPDATE SET percentage = excluded.percentage
        """, (student_id, month, float(percentage)))
        conn.commit()
        conn.close()
        st.success(f"Official attendance updated to {percentage:.2f}% for {month}.")

# ==========================================================
# ADMIN PANEL
# ==========================================================

def admin_daily_timetable():
    st.subheader("🕒 Daily Timetable Management")
    st.caption("Fixed timings. Saving the same slot again replaces it instead of creating a duplicate.")
    year=st.selectbox("Year",list(COLLEGE_DATA.keys()),key="daily_year"); branch=st.selectbox("Branch",list(COLLEGE_DATA[year].keys()),key="daily_branch"); section=st.selectbox("Section",COLLEGE_DATA[year][branch],key="daily_section"); semester=st.selectbox("Semester",SEMESTERS_BY_YEAR[year],key="daily_semester"); day=st.selectbox("Day",DAYS,key="daily_day")
    edit_id=st.session_state.get("edit_daily_tt_id")
    conn=connect(); er=conn.execute("SELECT * FROM daily_timetable WHERE id=?",(edit_id,)).fetchone() if edit_id else None; conn.close()
    labels=[f"{a} - {b}" for a,b in FIXED_TIME_SLOTS]; default=labels.index(f"{er['start_time']} - {er['end_time']}") if er and f"{er['start_time']} - {er['end_time']}" in labels else 0
    chosen=st.selectbox("Class Timing",labels,index=default,key=f"daily_time_{edit_id or 'new'}"); start_time,end_time=chosen.split(" - ")
    subject=st.text_input("Subject",value=(er['subject'] if er and er['year']==year and er['branch']==branch and er['section']==section and er['semester']==semester and er['day']==day else ""),key=f"daily_subject_{edit_id or 'new'}")
    room=st.text_input("Room (optional)",value=((er['room'] or "") if er else ""),key=f"daily_room_{edit_id or 'new'}")
    if st.button("💾 Save / Update Period",use_container_width=True):
        if not subject.strip(): st.error("Please enter a subject.")
        else:
            conn=connect(); conn.execute("DELETE FROM daily_timetable WHERE year=? AND branch=? AND section=? AND semester=? AND day=? AND start_time=?",(year,branch,section,semester,day,start_time)); conn.execute("INSERT INTO daily_timetable (year,branch,section,day,start_time,end_time,subject,room,semester) VALUES (?,?,?,?,?,?,?,?,?)",(year,branch,section,day,start_time,end_time,subject.strip(),room.strip(),semester)); conn.commit(); conn.close(); st.session_state.pop("edit_daily_tt_id",None); st.success("Timetable period saved/updated!"); st.rerun()
    if edit_id and st.button("↩️ Cancel Edit",use_container_width=True): st.session_state.pop("edit_daily_tt_id",None); st.rerun()
    st.divider(); st.subheader("📋 Saved Timetable")
    conn=connect(); rows=conn.execute("SELECT * FROM daily_timetable WHERE year=? AND branch=? AND section=? AND semester=? AND day=? ORDER BY CASE start_time WHEN '8:40' THEN 1 WHEN '9:30' THEN 2 WHEN '10:20' THEN 3 WHEN '11:10' THEN 4 WHEN '12:00' THEN 5 WHEN '12:50' THEN 6 WHEN '1:50' THEN 7 WHEN '2:40' THEN 8 WHEN '3:30' THEN 9 ELSE 99 END",(year,branch,section,semester,day)).fetchall(); conn.close()
    if not rows: st.info("No periods saved for this day yet.")
    for r in rows:
        c1,c2,c3=st.columns([5,1,1]); c1.write(f"**{r['start_time']} - {r['end_time']}** | {r['subject']} | Room: {r['room'] or '-'}")
        if c2.button("✏️ Edit",key=f"edit_daily_{r['id']}"): st.session_state.edit_daily_tt_id=r['id']; st.rerun()
        if c3.button("🗑️ Delete",key=f"delete_daily_{r['id']}"): conn=connect(); conn.execute("DELETE FROM daily_timetable WHERE id=?",(r['id'],)); conn.commit(); conn.close(); st.rerun()

def admin_panel():
    st.title("🛠️ Admin Panel")

    tabs = st.tabs([
        "👥 Students",
        "🖼️ Timetable",
        "🕒 Daily Timetable",
        "📚 Subjects",
        "📊 Attendance",
        "📅 Monthly Attendance"
    ])

    with tabs[0]:
        admin_students()

    with tabs[1]:
        admin_timetable()

    with tabs[2]:
        admin_daily_timetable()

    with tabs[3]:
        admin_subjects()

    with tabs[4]:
        admin_attendance()

    with tabs[5]:
        admin_monthly_attendance()


# ==========================================================
# STUDENT MENU
# ==========================================================

def student_app():

    student = get_student(
        st.session_state.student_id
    )

    st.sidebar.title("🎓 Student Menu")

    st.sidebar.success(
        f"{student['year']}\n"
        f"{student['branch']}\n"
        f"Section {student['section']}"
    )

    menu = st.sidebar.radio(
        "Navigation",
        [
            "🏠 Home",
            "🕒 Today's Timetable",
            "📅 Full Timetable",
            "📊 Attendance",
            "📝 Mark My Attendance",
            "🏫 College",
            "🗺️ College Map",
            "👤 Profile",
            "🚪 Logout"
        ]
    )

    if menu == "🏠 Home":

        student_home()

    elif menu == "📅 Full Timetable":

        student_timetable()

    elif menu == "🕒 Today's Timetable":
        st.title("🕒 Today's Timetable")
        today=date.today(); day_name=today.strftime("%A")
        st.write(f"**{day_name} | {today.strftime('%d-%m-%Y')}**")
        if day_name=="Sunday":
            st.success("🛌 Sunday — Weekly Off. No classes today.")
        else:
            conn=connect(); timetable=conn.execute("""SELECT start_time,end_time,subject,room FROM daily_timetable WHERE year=? AND branch=? AND section=? AND day=? AND (semester=? OR semester='Current' OR semester='') ORDER BY CASE start_time WHEN '8:40' THEN 1 WHEN '9:30' THEN 2 WHEN '10:20' THEN 3 WHEN '11:10' THEN 4 WHEN '12:00' THEN 5 WHEN '12:50' THEN 6 WHEN '1:50' THEN 7 WHEN '2:40' THEN 8 WHEN '3:30' THEN 9 ELSE 99 END""",(student['year'],student['branch'],student['section'],day_name,student['semester'])).fetchall(); conn.close()
            if timetable: st.dataframe([{"Time":f"{p['start_time']} - {p['end_time']}","Subject":p['subject'],"Room":p['room'] or "-"} for p in timetable],use_container_width=True,hide_index=True)
            else: st.info(f"No timetable has been added for {day_name} for your section and semester yet.")
    elif menu == "📊 Attendance":

        student_attendance()

    elif menu == "📝 Mark My Attendance":

        student_daily_attendance()

    elif menu == "🏫 College":

        college()

    elif menu == "🗺️ College Map":

        college_map()

    elif menu == "👤 Profile":

        profile()

    elif menu == "🚪 Logout":

        st.session_state.logged_in = False
        st.session_state.user_type = None
        st.session_state.student_id = None

        st.rerun()


# ==========================================================
# MAIN
# ==========================================================

if not st.session_state.logged_in:

    st.title("🎓 Smart College Assistant")

    login_type = st.radio(
        "Login as",
        [
            "👨‍🎓 Student",
            "🛠️ Admin"
        ],
        horizontal=True
    )

    if login_type == "👨‍🎓 Student":

        student_login()

    else:

        admin_login()

else:

    if st.session_state.user_type == "student":

        student_app()

    elif st.session_state.user_type == "admin":

        st.sidebar.title("🛠️ Administrator")

        if st.sidebar.button(
            "🚪 Logout"
        ):

            st.session_state.logged_in = False
            st.session_state.user_type = None

            st.rerun()

        admin_panel()
