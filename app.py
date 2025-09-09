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

# ----------------------
# HELPER FUNCTIONS
# ----------------------
def register_user(full_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO user (full_name) VALUES (%s)", (full_name,))
    conn.commit()
    cursor.close()
    conn.close()


def get_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, full_name FROM user")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return users


def punch(user_id, punch_type, lat=None, long=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO punch_record (user_id, punch_type, location_lat, location_long) VALUES (%s, %s, %s, %s)",
        (user_id, punch_type, lat, long)
    )
    conn.commit()
    cursor.close()
    conn.close()


def get_punch_records(user_id):
    conn = get_db_connection()
    query = """
        SELECT punch_id, punch_type, punch_time
        FROM punch_record
        WHERE user_id = %s
        ORDER BY punch_time DESC
    """
    df = pd.read_sql(query, conn, params=(user_id,))
    conn.close()
    return df


def calculate_hours(df):
    df_sorted = df.sort_values(by="punch_time")
    sessions = []
    
    in_time = None
    for _, row in df_sorted.iterrows():
        if row['punch_type'] == 'IN':
            in_time = row['punch_time']
        elif row['punch_type'] == 'OUT' and in_time:
            duration = (row['punch_time'] - in_time).total_seconds() / 3600
            sessions.append({
                'Punch In': in_time,
                'Punch Out': row['punch_time'],
                'Hours Worked': round(duration, 2)
            })
            in_time = None
    return pd.DataFrame(sessions)

# ----------------------
# STREAMLIT UI
# ----------------------
st.title("HR Punch In/Out Tracker")

# State management for login
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.user_name = None

# ----------------------
# LOGIN & REGISTER
# ----------------------
if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        st.subheader("Login")
        users = get_users()
        user_dict = {name: uid for uid, name in users}

        if users:
            selected_user = st.selectbox("Select your name", [name for _, name in users])
            if st.button("Login"):
                st.session_state.logged_in = True
                st.session_state.user_id = user_dict[selected_user]
                st.session_state.user_name = selected_user
                st.success(f"Welcome back, {selected_user}!")
        else:
            st.info("No users registered yet. Please register first.")

    with tab2:
        st.subheader("Register")
        new_name = st.text_input("Full Name")
        if st.button("Register"):
            if new_name.strip() == "":
                st.error("Name cannot be empty")
            else:
                register_user(new_name.strip())
                st.success(f"Registered successfully: {new_name}")
else:
    st.sidebar.success(f"Logged in as: {st.session_state.user_name}")

    # ----------------------
    # Punch In / Out Buttons
    # ----------------------
    st.subheader("Punch In / Out")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Punch In"):
            punch(st.session_state.user_id, "IN")
            st.success("Punched IN successfully!")

    with col2:
        if st.button("Punch Out"):
            punch(st.session_state.user_id, "OUT")
            st.warning("Punched OUT successfully!")

    # ----------------------
    # Attendance Table
    # ----------------------
    st.subheader("Attendance Records")
    records_df = get_punch_records(st.session_state.user_id)

    if not records_df.empty:
        hours_df = calculate_hours(records_df)
        st.write("### Raw Punch Records")
        st.dataframe(records_df)

        st.write("### Tabulated Hours")
        st.dataframe(hours_df)
    else:
        st.info("No punch records yet.")

    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.user_name = None
        st.experimental_rerun()
