import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# --- 1. SETTINGS & CONNECTION ---
st.set_page_config(page_title="Remote Team Tracker", layout="wide")

# Connect to Google Sheets using the "Secrets" you saved
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # ttl=0 means it always gets the freshest data from the sheet
    return conn.read(ttl=0)

def save_data(df):
    conn.update(data=df)
    st.cache_data.clear()

# Load the master data
df_master = load_data()

# Ensure time columns are handled correctly
for col in ['Login_Time', 'Logout_Time', 'Last_Change']:
    if col in df_master.columns:
        df_master[col] = pd.to_datetime(df_master[col])

# --- 2. SIDEBAR: MEMBER PORTAL ---
st.sidebar.header("👤 Member Portal")
LISTED_MEMBERS = df_master["Member"].tolist()
login_name = st.sidebar.selectbox("Select Your Name", ["--- Select ---"] + LISTED_MEMBERS)

if login_name != "--- Select ---":
    idx = df_master[df_master['Member'] == login_name].index[0]
    user_row = df_master.iloc[idx]
    
    # Logic for Clock In
    if pd.isna(user_row['Login_Time']):
        if st.sidebar.button(f"🚀 Clock In: {login_name}", use_container_width=True):
            df_master.at[idx, 'Login_Time'] = datetime.now()
            df_master.at[idx, 'Status'] = "Idle"
            df_master.at[idx, 'Last_Change'] = datetime.now()
            save_data(df_master)
            st.rerun()

    # Logic for Status Update & Logout
    elif user_row['Status'] != "Logged Out":
        st_options = ["Working", "Idle", "Break"]
        curr_idx = st_options.index(user_row['Status']) if user_row['Status'] in st_options else 1
        new_status = st.sidebar.selectbox("Current Activity", st_options, index=curr_idx)
        new_files = st.sidebar.number_input("Files Completed", min_value=0, value=int(user_row['Files']))

        if st.sidebar.button("💾 Update Status", use_container_width=True):
            now = datetime.now()
            last_time = pd.to_datetime(user_row['Last_Change'])
            diff_secs = (now - last_time).total_seconds()
            
            # Add time to the correct category
            if user_row['Status'] == "Working": df_master.at[idx, 'Work_Sec'] += diff_secs
            elif user_row['Status'] == "Idle": df_master.at[idx, 'Idle_Sec'] += diff_secs
            elif user_row['Status'] == "Break": df_master.at[idx, 'Break_Sec'] += diff_secs
            
            df_master.at[idx, 'Status'] = new_status
            df_master.at[idx, 'Files'] = new_files
            df_master.at[idx, 'Last_Change'] = now
            save_data(df_master)
            st.rerun()

        if st.sidebar.button("🔴 Final Logout", use_container_width=True):
            df_master.at[idx, 'Logout_Time'] = datetime.now()
            df_master.at[idx, 'Status'] = "Logged Out"
            save_data(df_master)
            st.rerun()

# --- 3. LIVE DASHBOARD ---
st.title("🕒 Remote Team Live Tracker")

# Format seconds for display
def format_time(seconds):
    h, r = divmod(int(max(0, seconds)), 3600)
    m, _ = divmod(r, 60)
    return f"{h}h {m}m"

# Create display table
display_list = []
for _, row in df_master.iterrows():
    w_s, i_s, b_s = row['Work_Sec'], row['Idle_Sec'], row['Break_Sec']
    
    # Calculate live time if active
    if row['Status'] in ["Working", "Idle", "Break"]:
        live_diff = (datetime.now() - pd.to_datetime(row['Last_Change'])).total_seconds()
        if row['Status'] == "Working": w_s += live_diff
        elif row['Status'] == "Idle": i_s += live_diff
        elif row['Status'] == "Break": b_s += live_diff

    display_list.append({
        "Member": row['Member'],
        "Status": row['Status'],
        "Login": row['Login_Time'].strftime("%I:%M %p") if pd.notna(row['Login_Time']) else "---",
        "Work": format_time(w_s),
        "Idle": format_time(i_s),
        "Break": format_time(b_s),
        "Files": row['Files']
    })

st.dataframe(pd.DataFrame(display_list), use_container_width=True, hide_index=True)

# --- 4. ADMIN CLEAN/RESET ---
st.divider()
if st.checkbox("Show Reset Option (End of Day Only)"):
    if st.button("🧹 Clean Sheet for Tomorrow", type="primary"):
        df_master["Status"] = "Offline"
        df_master["Files"] = 0
        for col in ["Work_Sec", "Idle_Sec", "Break_Sec"]: df_master[col] = 0
        df_master["Login_Time"] = None
        df_master["Logout_Time"] = None
        df_master["Last_Change"] = datetime.now()
        save_data(df_master)
        st.success("Sheet Cleaned!")
        st.rerun()
