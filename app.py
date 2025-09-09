import streamlit as st
import mysql.connector
import pandas as pd
from datetime import datetime
import bcrypt
from streamlit_js_eval import streamlit_js_eval

# ----------------------
# DATABASE CONNECTION
# ----------------------
def get_db_connection():
    return mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="root",
        database="mydb",
        port=3306
    )

# ==========================
# DATABASE FUNCTIONS
# ==========================
def register_user(full_name, password, role_id, employment_type_id):
    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO user (full_name, password_hash) VALUES (%s, %s)", (full_name, hashed_pw))
    user_id = cursor.lastrowid
    cursor.execute("INSERT INTO user_role (user_id, role_id, employment_type_id) VALUES (%s, %s, %s)",
                   (user_id, role_id, employment_type_id))
    conn.commit()
    cursor.close()
    conn.close()
    return user_id

def login_user(full_name, password):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM user WHERE full_name=%s", (full_name,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    if user and bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return user["user_id"]
    return None

def get_last_punch(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT punch_type FROM punch_record
        WHERE user_id = %s
        ORDER BY punch_time DESC
        LIMIT 1
    """, (user_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row["punch_type"] if row else None

def punch(user_id, punch_type, lat, long):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO punch_record (user_id, punch_type, punch_time, location_lat, location_long)
        VALUES (%s, %s, %s, %s, %s)
    """, (user_id, punch_type, datetime.now(), lat, long))
    conn.commit()
    cursor.close()
    conn.close()

def get_all_punches():
    conn = get_db_connection()
    df = pd.read_sql("""
        SELECT u.full_name, r.role_name, e.type_name AS employment_type,
               pr.punch_type, pr.punch_time, pr.location_lat, pr.location_long
        FROM punch_record pr
        JOIN user u ON pr.user_id = u.user_id
        JOIN user_role ur ON u.user_id = ur.user_id
        JOIN role r ON ur.role_id = r.role_id
        JOIN employment_type e ON ur.employment_type_id = e.employment_type_id
        ORDER BY pr.punch_time DESC
    """, conn)
    conn.close()
    return df

def get_roles():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM role")
    roles = cursor.fetchall()
    cursor.close()
    conn.close()
    return roles

def get_employment_types():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM employment_type")
    types = cursor.fetchall()
    cursor.close()
    conn.close()
    return types

# ==========================
# STREAMLIT APP
# ==========================
st.set_page_config(page_title="Punch Clock System", layout="wide")
st.title("🕒 Employee Punch Clock System")

# --------------------------
# Registration / Login
# --------------------------
if "user_id" not in st.session_state:
    st.session_state.user_id = None

tab1, tab2 = st.tabs(["Login", "Register"])

with tab1:
    st.subheader("Login")
    login_name = st.text_input("Full Name", key="login_name")
    login_pw = st.text_input("Password", type="password", key="login_pw")
    if st.button("Login"):
        user_id = login_user(login_name, login_pw)
        if user_id:
            st.session_state.user_id = user_id
            st.success(f"Logged in as {login_name}")
        else:
            st.error("Invalid credentials")

with tab2:
    st.subheader("Register")
    reg_name = st.text_input("Full Name", key="reg_name")
    reg_pw = st.text_input("Password", type="password", key="reg_pw")
    roles = get_roles()
    role_options = {r["role_name"]: r["role_id"] for r in roles}
    selected_role = st.selectbox("Role", options=list(role_options.keys()))
    types = get_employment_types()
    type_options = {t["type_name"]: t["employment_type_id"] for t in types}
    selected_type = st.selectbox("Employment Type", options=list(type_options.keys()))
    if st.button("Register"):
        if reg_name and reg_pw:
            user_id = register_user(reg_name, reg_pw, role_options[selected_role], type_options[selected_type])
            st.success(f"User {reg_name} registered successfully! You can now login.")
        else:
            st.error("Please provide full name and password")

# --------------------------
# Punch In / Out
# --------------------------
if st.session_state.user_id:
    st.subheader("Step 1: Allow Browser Location Access")
    st.info("Please allow your browser to share your location to punch in/out.")

    location = streamlit_js_eval(
        js_expressions=[
            "navigator.geolocation.getCurrentPosition(p => window.returnValue = {lat: p.coords.latitude, long: p.coords.longitude}, e => window.returnValue = null)"
        ],
        key="get_location"
    )

    if location:
        st.session_state.location = location
        st.success(f"📍 Location captured: {location['lat']:.6f}, {location['long']:.6f}")
    else:
        st.warning("Waiting for location or permission not granted...")

    st.subheader("Step 2: Punch In / Punch Out")
    last_punch = get_last_punch(st.session_state.user_id)

    col1, col2 = st.columns(2)
    with col1:
        if last_punch == "IN":
            st.button("Punch In", disabled=True)
        else:
            if st.button("Punch In"):
                if st.session_state.location:
                    lat, long = st.session_state.location["lat"], st.session_state.location["long"]
                    punch(st.session_state.user_id, "IN", lat, long)
                    st.success(f"Punched IN at {lat}, {long}")
                else:
                    st.error("Location not available. Please enable location services.")
    with col2:
        if last_punch != "IN":
            st.button("Punch Out", disabled=True)
        else:
            if st.button("Punch Out"):
                if st.session_state.location:
                    lat, long = st.session_state.location["lat"], st.session_state.location["long"]
                    punch(st.session_state.user_id, "OUT", lat, long)
                    st.success(f"Punched OUT at {lat}, {long}")
                else:
                    st.error("Location not available. Please enable location services.")

# --------------------------
# Admin / Punch Records
# --------------------------
st.subheader("📍 Staff Punch Locations")
df = get_all_punches()
st.dataframe(df)

if not df.empty:
    st.map(df.rename(columns={"location_lat": "lat", "location_long": "lon"})[["lat", "lon"]])
else:
    st.info("No punch records found.")
