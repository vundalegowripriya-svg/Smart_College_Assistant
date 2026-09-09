import streamlit as st
import sqlite3
import hashlib
import os
from datetime import date

st.set_page_config(page_title="Smart College Assistant", page_icon="🎓", layout="wide")
DB = "college.db"
UPLOAD_FOLDER = "timetables"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

COLLEGE_DATA = {
    "1st Year": {"AIML":["1","2","3","4"],"CSE":["1","2","3","4","5"],"CSD":["1","2"],"CIC":["1"],"CSIT":["1","2"],"ECE":["1","2","3"],"EEE":["1"],"CE":["1"],"ME":["1"],"AIDS":["1","2","3","4"]},
    "2nd Year": {"AIML":["1","2","3","4"],"CSE":["1","2","3","4","5"],"CSD":["1","2"],"CIC":["1"],"CSIT":["1","2"],"ECE":["1","2","3"],"EEE":["1"],"CE":["1"],"ME":["1"],"AIDS":["1","2","3","4"]}
}

def connect():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def password_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_database():
    conn = connect(); cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS students (student_id TEXT PRIMARY KEY, name TEXT NOT NULL, year TEXT NOT NULL, branch TEXT NOT NULL, section TEXT NOT NULL, password TEXT NOT NULL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS timetables (timetable_id INTEGER PRIMARY KEY AUTOINCREMENT, year TEXT NOT NULL, branch TEXT NOT NULL, section TEXT NOT NULL, image_path TEXT NOT NULL, UNIQUE(year, branch, section))")
    cursor.execute("CREATE TABLE IF NOT EXISTS subjects (subject_id INTEGER PRIMARY KEY AUTOINCREMENT, subject_name TEXT NOT NULL, year TEXT NOT NULL, branch TEXT NOT NULL, section TEXT NOT NULL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS attendance (attendance_id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT NOT NULL, subject_id INTEGER NOT NULL, attendance_date TEXT NOT NULL, status TEXT NOT NULL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS daily_timetable (id INTEGER PRIMARY KEY AUTOINCREMENT, year TEXT NOT NULL, branch TEXT NOT NULL, section TEXT NOT NULL, day TEXT NOT NULL, start_time TEXT NOT NULL, end_time TEXT NOT NULL, subject TEXT NOT NULL, room TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS admins (username TEXT PRIMARY KEY, password TEXT NOT NULL)")
    cursor.execute("INSERT OR IGNORE INTO admins VALUES (?, ?)", ("admin", password_hash("admin123")))
    cursor.execute("CREATE TABLE IF NOT EXISTS monthly_attendance (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT NOT NULL, attendance_month TEXT NOT NULL, percentage REAL NOT NULL, UNIQUE(student_id, attendance_month))")
    cursor.execute("CREATE TABLE IF NOT EXISTS daily_attendance (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT NOT NULL, attendance_date TEXT NOT NULL, subject TEXT NOT NULL, status TEXT NOT NULL, UNIQUE(student_id, attendance_date, subject))")
    conn.commit(); conn.close()

create_database()
for k,v in [("logged_in",False),("user_type",None),("student_id",None)]:
    if k not in st.session_state: st.session_state[k]=v

def get_student(student_id):
    conn=connect(); row=conn.execute("SELECT * FROM students WHERE student_id=?",(student_id,)).fetchone(); conn.close(); return row

def get_subjects(student):
    conn=connect(); rows=conn.execute("SELECT * FROM subjects WHERE year=? AND branch=? AND section=? ORDER BY subject_name",(student["year"],student["branch"],student["section"])).fetchall(); conn.close(); return rows

def get_timetable(student):
    conn=connect(); row=conn.execute("SELECT * FROM timetables WHERE year=? AND branch=? AND section=?",(student["year"],student["branch"],student["section"])).fetchone(); conn.close(); return row

def student_login():
    st.title("🎓 Smart College Assistant"); st.header("👨‍🎓 Student Login")
    sid=st.text_input("Student ID"); pw=st.text_input("Password",type="password")
    if st.button("🔐 Login",use_container_width=True):
        s=get_student(sid)
        if s and s["password"]==password_hash(pw): st.session_state.update(logged_in=True,user_type="student",student_id=sid); st.rerun()
        else: st.error("Invalid Student ID or password.")

def admin_login():
    st.title("🛠️ Admin Login"); u=st.text_input("Username"); p=st.text_input("Password",type="password")
    if st.button("🔐 Login",use_container_width=True):
        conn=connect(); a=conn.execute("SELECT * FROM admins WHERE username=?",(u,)).fetchone(); conn.close()
        if a and a["password"]==password_hash(p): st.session_state.update(logged_in=True,user_type="admin"); st.rerun()
        else: st.error("Invalid admin login.")

def student_home():
    s=get_student(st.session_state.student_id); st.title("🏠 Student Dashboard"); st.success(f"Welcome, {s['name']}!")
    c1,c2,c3=st.columns(3); c1.metric("Academic Year",s["year"]); c2.metric("Branch",s["branch"]); c3.metric("Section",s["section"])
    st.divider(); st.subheader("📅 Today's Timetable")
    today=date.today().strftime("%A")
    conn=connect(); rows=conn.execute("SELECT * FROM daily_timetable WHERE year=? AND branch=? AND section=? AND day=? ORDER BY start_time",(s["year"],s["branch"],s["section"],today)).fetchall(); conn.close()
    if rows: st.dataframe([{"Time":f"{r['start_time']} - {r['end_time']}","Subject":r["subject"],"Room":r["room"] or "-"} for r in rows],use_container_width=True)
    else: st.info(f"No timetable entered for {today}.")
    st.subheader("📊 Official Monthly Attendance")
    month=date.today().strftime("%Y-%m"); conn=connect(); a=conn.execute("SELECT percentage FROM monthly_attendance WHERE student_id=? AND attendance_month=?",(s["student_id"],month)).fetchone(); conn.close()
    st.metric(f"Attendance - {month}",f"{a['percentage']:.2f}%" if a else "Not updated")

def student_attendance():
    s=get_student(st.session_state.student_id); st.title("📊 Attendance")
    month=st.selectbox("Select Month",[f"{date.today().year}-{m:02d}" for m in range(1,13)],index=date.today().month-1)
    conn=connect(); official=conn.execute("SELECT percentage FROM monthly_attendance WHERE student_id=? AND attendance_month=?",(s["student_id"],month)).fetchone(); rows=conn.execute("SELECT subject,SUM(status='Present') present,COUNT(*) total FROM daily_attendance WHERE student_id=? AND substr(attendance_date,1,7)=? GROUP BY subject",(s["student_id"],month)).fetchall(); conn.close()
    st.subheader("🏫 Official Attendance"); st.metric("Official Monthly Percentage",f"{official['percentage']:.2f}%" if official else "Not updated")
    st.subheader("📝 My Self-Tracked Attendance")
    if rows:
        data=[]
        for r in rows:
            pct=(r["present"]/r["total"]*100) if r["total"] else 0; data.append({"Subject":r["subject"],"Total":r["total"],"Present":r["present"],"Absent":r["total"]-r["present"],"Percentage":f"{pct:.2f}%"})
        st.dataframe(data,use_container_width=True)
        total=sum(r["total"] for r in rows); present=sum(r["present"] for r in rows); st.metric("Overall Self-Tracked %",f"{present/total*100:.2f}%" if total else "0.00%")
    else: st.info("No self-tracked attendance for this month.")

def student_daily_attendance():
    s=get_student(st.session_state.student_id); today=date.today(); day=today.strftime("%A"); st.title("📝 Mark My Attendance"); st.write(f"**{today.strftime('%d-%m-%Y')} | {day}**")
    conn=connect(); periods=conn.execute("SELECT * FROM daily_timetable WHERE year=? AND branch=? AND section=? AND day=? ORDER BY start_time",(s["year"],s["branch"],s["section"],day)).fetchall(); conn.close()
    if not periods: st.info(f"No periods entered for {day}."); return
    for r in periods:
        conn=connect(); old=conn.execute("SELECT status FROM daily_attendance WHERE student_id=? AND attendance_date=? AND subject=?",(s["student_id"],today.isoformat(),r["subject"])).fetchone(); conn.close()
        opts=["-- Not Marked --","Present","Absent"]; default=opts.index(old["status"])+0 if old and old["status"] in opts else 0
        status=st.selectbox(f"{r['start_time']} - {r['end_time']} | {r['subject']} | Room {r['room'] or '-'}",opts,index=default,key=f"att_{r['id']}")
        if status!="-- Not Marked --" and st.button(f"Save {r['subject']}",key=f"save_{r['id']}"):
            conn=connect(); conn.execute("INSERT INTO daily_attendance(student_id,attendance_date,subject,status) VALUES(?,?,?,?) ON CONFLICT(student_id,attendance_date,subject) DO UPDATE SET status=excluded.status",(s["student_id"],today.isoformat(),r["subject"],status)); conn.commit(); conn.close(); st.success("Attendance saved."); st.rerun()

def college():
    st.title("🏫 College Information"); st.subheader("Annamacharya Institute of Technology & Sciences, Tirupati"); st.write("📍 Venkatapuram, Renigunta, Tirupati, Andhra Pradesh - 517520"); st.write("🎓 B.Tech - Undergraduate Programme"); st.markdown("[🌐 Official College Website](https://aits-tpt.edu.in/)")

def college_map():
    st.title("🗺️ College Campus Map")
    st.write("College-only campus layout. No Google Maps.")
    st.info("Layout: A+B+C are combined • E Block is in front of A Block • Canteen is behind the combined block • Boys Hostel is where the old canteen was • Girls Hostel is where the old boys hostel was • Parking is on the left • Large ground is after the parking.")
    st.markdown("### 🏫 Campus Layout")
    cols=st.columns(5)
    cols[0].markdown("**👧 Girls Hostel**")
    cols[1].markdown("**🚗 Parking**")
    cols[2].markdown("**🌳 BIG GROUND**")
    cols[3].markdown("**🏢 E BLOCK**")
    cols[4].markdown("**🚪 Gate**")
    st.markdown("\n---\n")
    c1,c2,c3=st.columns([1,3,1]); c1.markdown("### 🧑 Boys Hostel"); c2.markdown("## 🏢 A + B + C BLOCK\n**Main Combined Academic Block**"); c3.markdown("### 🌳 Ground")
    st.markdown("\n---\n")
    d1,d2,d3=st.columns([1,3,1]); d1.markdown(""); d2.markdown("### 🍴 CANTEEN\nLocated behind the A+B+C combined block"); d3.markdown("")
    st.caption("From the large ground, the E Block and the main A+B+C block are visible.")

def profile():
    s=get_student(st.session_state.student_id); st.title("👤 Profile"); st.write(f"### {s['name']}"); st.write(f"**Student ID:** {s['student_id']}"); st.write(f"**Academic Year:** {s['year']}"); st.write(f"**Branch:** {s['branch']}"); st.write(f"**Section:** {s['section']}")

def admin_students():
    st.subheader("👥 Add Student"); sid=st.text_input("Student ID",key="sid"); name=st.text_input("Name",key="name"); year=st.selectbox("Year",list(COLLEGE_DATA)); branch=st.selectbox("Branch",list(COLLEGE_DATA[year])); section=st.selectbox("Section",COLLEGE_DATA[year][branch]); pw=st.text_input("Password",type="password",key="pw")
    if st.button("Add Student"):
        try:
            conn=connect(); conn.execute("INSERT INTO students VALUES(?,?,?,?,?,?)",(sid,name,year,branch,section,password_hash(pw))); conn.commit(); conn.close(); st.success("Student added.")
        except sqlite3.IntegrityError: st.error("Student ID already exists.")

def admin_timetable():
    st.subheader("📅 Upload Full Timetable"); year=st.selectbox("Year",list(COLLEGE_DATA),key="ty"); branch=st.selectbox("Branch",list(COLLEGE_DATA[year]),key="tb"); section=st.selectbox("Section",COLLEGE_DATA[year][branch],key="ts"); file=st.file_uploader("Upload timetable image",type=["png","jpg","jpeg"],key="tf")
    if st.button("Save Timetable") and file:
        path=os.path.join(UPLOAD_FOLDER,f"{year}_{branch}_{section}_{file.name}"); open(path,"wb").write(file.getbuffer()); conn=connect(); conn.execute("INSERT INTO timetables(year,branch,section,image_path) VALUES(?,?,?,?) ON CONFLICT(year,branch,section) DO UPDATE SET image_path=excluded.image_path",(year,branch,section,path)); conn.commit(); conn.close(); st.success("Timetable saved.")

def admin_daily_timetable():
    st.subheader("🕒 Daily Timetable Entry"); year=st.selectbox("Year",list(COLLEGE_DATA),key="dy"); branch=st.selectbox("Branch",list(COLLEGE_DATA[year]),key="db"); section=st.selectbox("Section",COLLEGE_DATA[year][branch],key="ds"); day=st.selectbox("Day",["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]); start=st.text_input("Start time",placeholder="09:00"); end=st.text_input("End time",placeholder="09:50"); subject=st.text_input("Subject"); room=st.text_input("Room")
    if st.button("Add Period"):
        conn=connect(); conn.execute("INSERT INTO daily_timetable(year,branch,section,day,start_time,end_time,subject,room) VALUES(?,?,?,?,?,?,?,?)",(year,branch,section,day,start,end,subject,room)); conn.commit(); conn.close(); st.success("Period added.")

def admin_subjects():
    st.subheader("📚 Add Subject"); year=st.selectbox("Year",list(COLLEGE_DATA),key="sy"); branch=st.selectbox("Branch",list(COLLEGE_DATA[year]),key="sb"); section=st.selectbox("Section",COLLEGE_DATA[year][branch],key="ss"); subject=st.text_input("Subject Name")
    if st.button("Add Subject"):
        conn=connect(); conn.execute("INSERT INTO subjects(subject_name,year,branch,section) VALUES(?,?,?,?)",(subject,year,branch,section)); conn.commit(); conn.close(); st.success("Subject added.")

def admin_attendance():
    st.subheader("📊 Update Official Attendance Percentage"); st.caption("Admin enters only the student's final monthly percentage. Daily Present/Absent is not required here.")
    conn=connect(); students=conn.execute("SELECT student_id,name FROM students ORDER BY student_id").fetchall(); conn.close()
    if not students: st.info("No students added yet."); return
    labels=[f"{x['student_id']} - {x['name']}" for x in students]; selected=st.selectbox("Student",labels); sid=selected.split(" - ",1)[0]; month=st.text_input("Month",value=date.today().strftime("%Y-%m")); pct=st.number_input("Official Attendance %",0.0,100.0,step=0.1)
    if st.button("Save Official Attendance"):
        conn=connect(); conn.execute("INSERT INTO monthly_attendance(student_id,attendance_month,percentage) VALUES(?,?,?) ON CONFLICT(student_id,attendance_month) DO UPDATE SET percentage=excluded.percentage",(sid,month,pct)); conn.commit(); conn.close(); st.success("Official attendance updated.")

def admin_monthly_attendance():
    st.subheader("📅 Monthly Official Attendance"); conn=connect(); rows=conn.execute("SELECT m.attendance_month,m.percentage,s.student_id,s.name FROM monthly_attendance m JOIN students s ON s.student_id=m.student_id ORDER BY m.attendance_month DESC,s.student_id").fetchall(); conn.close(); st.dataframe([dict(r) for r in rows],use_container_width=True) if rows else st.info("No official attendance entered yet.")

def admin_panel():
    st.title("🛠️ Admin Panel"); tabs=st.tabs(["Students","Timetable","Daily Timetable","Subjects","Attendance","Monthly Attendance"])
    with tabs[0]: admin_students()
    with tabs[1]: admin_timetable()
    with tabs[2]: admin_daily_timetable()
    with tabs[3]: admin_subjects()
    with tabs[4]: admin_attendance()
    with tabs[5]: admin_monthly_attendance()

def app():
    if not st.session_state.logged_in:
        mode=st.sidebar.radio("Login",["Student","Admin"]); student_login() if mode=="Student" else admin_login(); return
    if st.session_state.user_type=="admin":
        if st.sidebar.button("Logout"): st.session_state.clear(); st.rerun()
        admin_panel(); return
    pages={"🏠 Home":student_home,"📊 Attendance":student_attendance,"📝 Mark My Attendance":student_daily_attendance,"📅 Full Timetable":lambda:None,"🏫 College Info":college,"🗺️ College Map":college_map,"👤 Profile":profile}
    choice=st.sidebar.radio("Menu",list(pages)); pages[choice]()

app()
