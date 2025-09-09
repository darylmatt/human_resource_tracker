import streamlit as st
import mysql.connector
import pandas as pd
from datetime import datetime
from streamlit_js_eval import streamlit_js_eval

# ----------------------
# DATABASE CONNECTION
# ----------------------
def get_db_connection():
    return mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="root",  # if no password, leave as empty string
        database="mydb",
        port=3306
    )



# ==========================
# DATABASE FUNCTIONS
# ==========================
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
        SELECT u.full_name, pr.punch_type, pr.punch_time, pr.location_lat, pr.location_long
        FROM punch_record pr
        JOIN user u ON pr.user_id = u.user_id
        ORDER BY pr.punch_time DESC
    """, conn)
    conn.close()
    return df

# ==========================
# STREAMLIT APP
# ==========================
st.set_page_config(page_title="Punch Clock System", layout="wide")
st.title("🕒 Employee Punch Clock System")

# Simulated logged-in user
st.session_state.user_id = 1
st.session_state.full_name = "John Doe"

# Initialize session state for location
if "location" not in st.session_state:
    st.session_state.location = None

st.subheader("Step 1: Allow Browser Location Access")
st.info("Please allow your browser to share your location to punch in/out.")

# Request location using JavaScript
location = streamlit_js_eval(
    js_expressions=[
        "navigator.geolocation.getCurrentPosition(p => window.returnValue = {lat: p.coords.latitude, long: p.coords.longitude}, e => window.returnValue = null)"
    ],
    key="get_location"
)

# Update session state with location
if location:
    st.session_state.location = location
    st.success(f"📍 Location captured: {location['lat']:.6f}, {location['long']:.6f}")
else:
    st.warning("Waiting for location or permission not granted...")

# ==========================
# PUNCH IN / OUT LOGIC
# ==========================
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

# ==========================
# ADMIN VIEW: STAFF PUNCH LOCATIONS
# ==========================
st.subheader("📍 Staff Punch Locations")

df = get_all_punches()
st.dataframe(df)

if not df.empty:
    # Show on map
    st.map(df.rename(columns={"location_lat": "lat", "location_long": "lon"})[["lat", "lon"]])
else:
    st.info("No punch records found.")
