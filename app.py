import streamlit as st
import sqlite3
import hashlib
import os
from datetime import date

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

    subjects = get_subjects(student)

    if subjects:

        rows = []

        for subject in subjects:

            total, attended, absent, percentage = \
                get_attendance(
                    student["student_id"],
                    subject["subject_id"]
                )

            rows.append({
                "Subject": subject["subject_name"],
                "Total Classes": total,
                "Attended": attended,
                "Absent": absent,
                "Attendance %":
                    f"{percentage:.2f}%"
            })

        st.dataframe(
            rows,
            use_container_width=True
        )

    else:

        st.info(
            "No subjects have been added for your section."
        )


# ==========================================================
# STUDENT ATTENDANCE
# ==========================================================

def student_attendance():

    student = get_student(
        st.session_state.student_id
    )

    st.title("📊 Attendance")

    st.write(
        f"**{student['year']} | "
        f"{student['branch']} | "
        f"Section {student['section']}**"
    )

    subjects = get_subjects(student)

    rows = []

    total_all = 0
    attended_all = 0

    for subject in subjects:

        total, attended, absent, percentage = \
            get_attendance(
                student["student_id"],
                subject["subject_id"]
            )

        total_all += total
        attended_all += attended

        rows.append({
            "Subject": subject["subject_name"],
            "Total Classes": total,
            "Classes Attended": attended,
            "Classes Absent": absent,
            "Attendance %":
                f"{percentage:.2f}%"
        })

    if rows:

        st.dataframe(
            rows,
            use_container_width=True
        )

    if total_all > 0:

        overall = (
            attended_all /
            total_all
        ) * 100

    else:

        overall = 0

    st.subheader("📈 Overall Attendance")

    st.metric(
        "Overall Attendance",
        f"{overall:.2f}%"
    )


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

    st.title("🗺️ College Map")

    st.write(
        "Annamacharya Institute of Technology & Sciences, Tirupati"
    )

    st.map({
        "lat": [13.6373],
        "lon": [79.5034]
    })

    st.markdown(
        "[📍 Open in Google Maps]"
        "(https://www.google.com/maps/search/"
        "Annamacharya+Institute+of+Technology+and+Sciences+Tirupati)"
    )


# ==========================================================
# PROFILE
# ==========================================================

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

    st.subheader("📊 Update Attendance")

    conn = connect()

    students = conn.execute("""
        SELECT *
        FROM students
        ORDER BY name
    """).fetchall()

    conn.close()

    if not students:

        st.info(
            "No students added yet."
        )
        return

    student_names = {
        f"{s['name']} ({s['student_id']})":
        s["student_id"]
        for s in students
    }

    selected = st.selectbox(
        "Select Student",
        list(student_names.keys())
    )

    student_id = student_names[selected]

    student = get_student(student_id)

    st.info(
        f"{student['year']} | "
        f"{student['branch']} | "
        f"Section {student['section']}"
    )

    subjects = get_subjects(student)

    if not subjects:

        st.warning(
            "No subjects exist for this section."
        )
        return

    subject_options = {
        s["subject_name"]:
        s["subject_id"]
        for s in subjects
    }

    subject_name = st.selectbox(
        "Subject",
        list(subject_options.keys())
    )

    subject_id = subject_options[subject_name]

    attendance_date = st.date_input(
        "Date",
        date.today()
    )

    status = st.selectbox(
        "Status",
        [
            "Present",
            "Absent"
        ]
    )

    if st.button(
        "💾 Save Attendance"
    ):

        conn = connect()

        conn.execute("""
            INSERT INTO attendance
            (student_id, subject_id,
             attendance_date, status)
            VALUES (?, ?, ?, ?)
        """, (
            student_id,
            subject_id,
            str(attendance_date),
            status
        ))

        conn.commit()
        conn.close()

        st.success(
            "Attendance saved!"
        )


# ==========================================================
# ADMIN PANEL
# ==========================================================

def admin_panel():

    st.title("🛠️ Admin Panel")

    tabs = st.tabs([
        "👥 Students",
        "🖼️ Timetable",
        "📚 Subjects",
        "📊 Attendance"
    ])

    with tabs[0]:
        admin_students()

    with tabs[1]:
        admin_timetable()

    with tabs[2]:
        admin_subjects()

    with tabs[3]:
        admin_attendance()


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
            "🏫 College",
            "🗺️ College Map",
            "👤 Profile",
            "🚪 Logout"
        ]
    )

    if menu == "🏠 Home":

        student_home()

    elif menu == "🕒 Today's Timetable":

        st.title("🕒 Today's Timetable")
        st.info(
            "Daily timetable can be added from the Admin Panel."
        )

    elif menu == "📅 Full Timetable":

        student_timetable()

    elif menu == "📊 Attendance":

        student_attendance()

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
