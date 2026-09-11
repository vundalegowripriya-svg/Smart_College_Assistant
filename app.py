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

COLLEGE_DATA = {
    "1st Year": {
        "AIML": ["1", "2", "3", "4"],
        "CSE": ["1", "2", "3", "4", "5"],
        "CSD": ["1", "2"],
        "CIC": ["1"],
        "CSIT": ["1", "2"],
        "ECE": ["1", "2", "3"],
        "EEE": ["1"],
        "CE": ["1"],
        "ME": ["1"],
        "AIDS": ["1", "2", "3", "4"]
    },

    "2nd Year": {
        "AIML": ["1", "2", "3", "4"],
        "CSE": ["1", "2", "3", "4", "5"],
        "CSD": ["1", "2"],
        "CIC": ["1"],
        "CSIT": ["1", "2"],
        "ECE": ["1", "2", "3"],
        "EEE": ["1"],
        "CE": ["1"],
        "ME": ["1"],
        "AIDS": ["1", "2", "3", "4"]
    }
}


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
    # ---------------- DAILY ATTENDANCE MIGRATION ----------------
    existing_columns = {
        row["name"]
        for row in cursor.execute("PRAGMA table_info(daily_attendance)").fetchall()
    }

    required_columns = {
        "start_time": "TEXT DEFAULT ''",
        "end_time": "TEXT DEFAULT ''",
        "subject": "TEXT DEFAULT ''",
        "room": "TEXT",
        "status": "TEXT DEFAULT 'Present'",
    }

    for column, definition in required_columns.items():
        if column not in existing_columns:
            cursor.execute(
                f"ALTER TABLE daily_attendance ADD COLUMN {column} {definition}"
            )

    conn.commit()

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

    subjects = conn.execute("""
        SELECT *
        FROM subjects
        WHERE year = ?
        AND branch = ?
        AND section = ?
        ORDER BY subject_name
    """, (
        student["year"],
        student["branch"],
        student["section"]
    )).fetchall()

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
        ORDER BY start_time
    """, (student["year"], student["branch"], student["section"], day_name)).fetchall()

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

    student = get_student(
        st.session_state.student_id
    )

    st.title("📅 Full Timetable")

    st.write(
        f"{student['year']} | "
        f"{student['branch']} | "
        f"Section {student['section']}"
    )

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

            st.error(
                "Timetable image is missing."
            )

    else:

        st.info(
            "No timetable uploaded for your section."
        )


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
    CAMPUS_MAP_B64 = """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"""
    import base64 as _b64
    st.image(_b64.b64decode(CAMPUS_MAP_B64), caption="College Campus Model", use_container_width=True)

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
        "boys hostel": "🧑 Boys Hostel → Boys Hostel",
        "girls hostel": "👧 Girls Hostel → Girls Hostel",
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

    student = get_student(
        st.session_state.student_id
    )

    st.title("👤 Profile")

    st.write(
        f"### {student['name']}"
    )

    st.write(
        f"**Student ID:** {student['student_id']}"
    )

    st.write(
        f"**Academic Year:** {student['year']}"
    )

    st.write(
        f"**Branch:** {student['branch']}"
    )

    st.write(
        f"**Section:** {student['section']}"
    )

    st.info(
        "Your section is fixed by the administrator. "
        "You cannot switch to another section."
    )


# ==========================================================
# ADMIN - ADD STUDENT
# ==========================================================

def admin_students():

    st.subheader("👥 Add Student")

    student_id = st.text_input(
        "Student ID",
        key="admin_student_id"
    )

    name = st.text_input(
        "Student Name",
        key="admin_student_name"
    )

    year = st.selectbox(
        "Academic Year",
        list(COLLEGE_DATA.keys()),
        key="admin_student_year"
    )

    branch = st.selectbox(
        "Branch",
        list(COLLEGE_DATA[year].keys()),
        key="admin_student_branch"
    )

    section = st.selectbox(
        "Section",
        COLLEGE_DATA[year][branch],
        key="admin_student_section"
    )

    password = st.text_input(
        "Student Password",
        type="password",
        key="admin_student_password"
    )

    if st.button(
        "➕ Add Student"
    ):

        if not all([
            student_id,
            name,
            password
        ]):

            st.error(
                "Please fill all fields."
            )

        else:

            conn = connect()

            try:

                conn.execute("""
                    INSERT INTO students
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    student_id,
                    name,
                    year,
                    branch,
                    section,
                    password_hash(password)
                ))

                conn.commit()

                st.success(
                    "Student added successfully!"
                )

            except sqlite3.IntegrityError:

                st.error(
                    "Student ID already exists."
                )

            conn.close()

    st.divider()

    conn = connect()

    students = conn.execute("""
        SELECT student_id, name, year, branch, section
        FROM students
        ORDER BY year, branch, section
    """).fetchall()

    conn.close()

    if students:

        st.dataframe(
            [dict(s) for s in students],
            use_container_width=True
        )


# ==========================================================
# ADMIN - UPLOAD TIMETABLE
# ==========================================================

def admin_timetable():

    st.subheader("🖼️ Upload Section Timetable")

    st.write(
        "Select the exact Year, Branch and Section "
        "for this timetable."
    )

    year = st.selectbox(
        "Select Year",
        list(COLLEGE_DATA.keys()),
        key="upload_year"
    )

    branch = st.selectbox(
        "Select Branch",
        list(COLLEGE_DATA[year].keys()),
        key="upload_branch"
    )

    section = st.selectbox(
        "Select Section",
        COLLEGE_DATA[year][branch],
        key="upload_section"
    )

    uploaded_file = st.file_uploader(
        "📤 Upload Timetable Photo",
        type=[
            "png",
            "jpg",
            "jpeg"
        ]
    )

    if uploaded_file:

        st.image(
            uploaded_file,
            caption="Timetable Preview",
            use_container_width=True
        )

    if st.button(
        "💾 Save Timetable"
    ):

        if uploaded_file is None:

            st.error(
                "Please upload a timetable photo."
            )
            return

        file_name = (
            f"{year}_{branch}_{section}.png"
        )

        file_path = os.path.join(
            UPLOAD_FOLDER,
            file_name
        )

        with open(
            file_path,
            "wb"
        ) as file:

            file.write(
                uploaded_file.getbuffer()
            )

        conn = connect()

        conn.execute("""
            INSERT INTO timetables
            (year, branch, section, image_path)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(year, branch, section)
            DO UPDATE SET image_path=excluded.image_path
        """, (
            year,
            branch,
            section,
            file_path
        ))

        conn.commit()
        conn.close()

        st.success(
            f"Timetable saved for "
            f"{year} - {branch} - Section {section}!"
        )


# ==========================================================
# ADMIN - ADD SUBJECT
# ==========================================================

def admin_subjects():

    st.subheader("📚 Add Subject")

    year = st.selectbox(
        "Year",
        list(COLLEGE_DATA.keys()),
        key="subject_admin_year"
    )

    branch = st.selectbox(
        "Branch",
        list(COLLEGE_DATA[year].keys()),
        key="subject_admin_branch"
    )

    section = st.selectbox(
        "Section",
        COLLEGE_DATA[year][branch],
        key="subject_admin_section"
    )

    subject_name = st.text_input(
        "Subject Name"
    )

    if st.button(
        "➕ Add Subject"
    ):

        if not subject_name:

            st.error(
                "Enter subject name."
            )

        else:

            conn = connect()

            conn.execute("""
                INSERT INTO subjects
                (subject_name, year, branch, section)
                VALUES (?, ?, ?, ?)
            """, (
                subject_name,
                year,
                branch,
                section
            ))

            conn.commit()
            conn.close()

            st.success(
                "Subject added successfully!"
            )


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

    st.subheader("🕒 Add Daily Timetable")

    year = st.selectbox(
        "Year",
        list(COLLEGE_DATA.keys()),
        key="daily_year"
    )

    branch = st.selectbox(
        "Branch",
        list(COLLEGE_DATA[year].keys()),
        key="daily_branch"
    )

    section = st.selectbox(
        "Section",
        COLLEGE_DATA[year][branch],
        key="daily_section"
    )

    day = st.selectbox(
        "Day",
        [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday"
        ],
        key="daily_day"
    )

    start_time = st.text_input(
        "Start Time",
        placeholder="09:30",
        key="daily_start"
    )

    end_time = st.text_input(
        "End Time",
        placeholder="10:20",
        key="daily_end"
    )

    subject = st.text_input(
        "Subject",
        key="daily_subject"
    )

    room = st.text_input(
        "Room (optional)",
        key="daily_room"
    )

    if st.button("💾 Save Daily Period"):

        if not start_time or not end_time or not subject:

            st.error(
                "Please fill Start Time, End Time and Subject."
            )

        else:

            conn = connect()

            conn.execute("""
                INSERT INTO daily_timetable
                (
                    year,
                    branch,
                    section,
                    day,
                    start_time,
                    end_time,
                    subject,
                    room
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                year,
                branch,
                section,
                day,
                start_time,
                end_time,
                subject,
                room
            ))

            conn.commit()
            conn.close()

            st.success(
                "Daily timetable period saved!"
            )

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

        student = get_student(
            st.session_state.student_id
        )

        st.title("🕒 Today's Timetable")

        today = date.today()
        day_name = today.strftime("%A")

        st.write(
            f"**{day_name} | {today.strftime('%d-%m-%Y')}**"
        )

        conn = connect()

        timetable = conn.execute("""
            SELECT start_time, end_time, subject, room
            FROM daily_timetable
            WHERE year = ?
            AND branch = ?
            AND section = ?
            AND day = ?
            ORDER BY start_time
        """, (
            student["year"],
            student["branch"],
            student["section"],
            day_name
        )).fetchall()

        conn.close()

        if timetable:

            rows = []

            for period in timetable:
                rows.append({
                    "Time": f"{period['start_time']} - {period['end_time']}",
                    "Subject": period["subject"],
                    "Room": period["room"] or "-"
                })

            st.dataframe(
                rows,
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info(
                f"No timetable has been added for {day_name} "
                f"for your section yet."
            )
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
