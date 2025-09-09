import streamlit as st
import mysql.connector
import pandas as pd
from datetime import datetime

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
        JOIN users u ON pr.user_id = u.user_id
        ORDER BY pr.punch_time DESC
    """, conn)
    conn.close()
    return df

# ==========================
# LOCATION CAPTURE
# ==========================
def get_user_location():
    location_js = """
    <script>
    function sendLocationToStreamlit() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                function(position) {
                    const coords = {
                        lat: position.coords.latitude,
                        long: position.coords.longitude
                    };
                    const streamlitEvent = new CustomEvent("streamlit:location", {detail: coords});
                    window.dispatchEvent(streamlitEvent);
                },
                function(error) {
                    const errorMsg = { error: error.message };
                    const streamlitEvent = new CustomEvent("streamlit:location", {detail: errorMsg});
                    window.dispatchEvent(streamlitEvent);
                }
            );
        } else {
            const errorMsg = { error: "Geolocation is not supported by this browser." };
            const streamlitEvent = new CustomEvent("streamlit:location", {detail: errorMsg});
            window.dispatchEvent(streamlitEvent);
        }
    }
    sendLocationToStreamlit();
    </script>
    """
    components.html(location_js, height=0)

# ==========================
# MAIN APP
# ==========================
st.set_page_config(page_title="Punch Clock System", layout="wide")
st.title("🕒 Employee Punch Clock System")

# Simulated logged-in user
# In production, you would use a login system
st.session_state.user_id = 1
st.session_state.full_name = "John Doe"

# Initialize session state for location
if "location" not in st.session_state:
    st.session_state.location = None

st.subheader("Step 1: Capture Location")
st.info("Please allow browser location access to punch in/out.")

# Capture location
get_user_location()

# Temporary placeholder for demonstration (simulate location being set)
if st.button("Simulate Location Capture"):
    st.session_state.location = {"lat": 1.3521, "long": 103.8198}  # Example Singapore location

if st.session_state.location:
    st.success(f"📍 Location Captured: {st.session_state.location['lat']}, {st.session_state.location['long']}")
else:
    st.warning("Waiting for location...")

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
    st.map(df[["location_lat", "location_long"]])
else:
    st.info("No punch records found.")
