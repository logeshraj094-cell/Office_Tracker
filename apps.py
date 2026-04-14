import streamlit as st
import pandas as pd
from datetime import datetime, date
import os
import time

# --- 1. CONFIGURATION ---
LISTED_MEMBERS = ["logeshraj.D", "kk", "nirmal", "siva", "sabari"]
DB_FILE = "master_attendance_db.csv"

st.set_page_config(page_title="Shared Team Tracker", layout="wide", page_icon="🕒")

# --- 2. DATABASE ENGINE ---
def load_shared_data():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE)
            for col in ['Login_Time', 'Logout_Time', 'Last_Change']:
                df[col] = pd.to_datetime(df[col])
            return df
        except Exception:
            return None
    else:
        return create_fresh_df()

def create_fresh_df():
    """Generates a clean template for the team."""
    data = []
    for name in LISTED_MEMBERS:
        data.append({
            "Member": name, "Status": "Offline", "Files": 0,
            "Last_Change": datetime.now(), "Login_Time": None,
            "Logout_Time": None, "Work_Sec": 0, "Idle_Sec": 0, "Break_Sec": 0
        })
    df = pd.DataFrame(data)
    df.to_csv(DB_FILE, index=False)
    return df

def save_shared_data(df):
    for _ in range(5):
        try:
            df.to_csv(DB_FILE, index=False)
            return True
        except PermissionError:
            time.sleep(0.2)
    return False

# Load Data
df_master = load_shared_data()

# --- 3. SIDEBAR: USER PORTAL ---
st.sidebar.header("👤 Member Portal")
login_name = st.sidebar.selectbox("Select Member", ["--- Select ---"] + LISTED_MEMBERS)

if login_name != "--- Select ---":
    idx = df_master[df_master['Member'] == login_name].index[0]
    user_row = df_master.iloc[idx]
    
    is_logged_in = pd.notna(user_row['Login_Time'])
    is_logged_out = user_row['Status'] == "Logged Out"

    if not is_logged_in:
        if st.sidebar.button(f"🚀 Clock In: {login_name}", use_container_width=True):
            df_master.at[idx, 'Login_Time'] = datetime.now()
            df_master.at[idx, 'Status'] = "Idle"
            df_master.at[idx, 'Last_Change'] = datetime.now()
            save_shared_data(df_master)
            st.rerun()

    elif not is_logged_out:
        st_options = ["Working", "Idle", "Break"]
        curr_idx = st_options.index(user_row['Status']) if user_row['Status'] in st_options else 1
        new_status = st.sidebar.selectbox("Activity", st_options, index=curr_idx)
        new_files = st.sidebar.number_input("Files Done", min_value=0, value=int(user_row['Files']))

        if st.sidebar.button("💾 Update Record", use_container_width=True):
            now = datetime.now()
            last_time = pd.to_datetime(user_row['Last_Change'])
            diff_secs = (now - last_time).total_seconds()
            
            if user_row['Status'] == "Working": df_master.at[idx, 'Work_Sec'] += diff_secs
            elif user_row['Status'] == "Idle": df_master.at[idx, 'Idle_Sec'] += diff_secs
            elif user_row['Status'] == "Break": df_master.at[idx, 'Break_Sec'] += diff_secs
            
            df_master.at[idx, 'Status'] = new_status
            df_master.at[idx, 'Files'] = new_files
            df_master.at[idx, 'Last_Change'] = now
            save_shared_data(df_master)
            st.rerun()

        if st.sidebar.button("🔴 Final Logout", use_container_width=True):
            now = datetime.now()
            diff_secs = (now - pd.to_datetime(user_row['Last_Change'])).total_seconds()
            if user_row['Status'] == "Working": df_master.at[idx, 'Work_Sec'] += diff_secs
            elif user_row['Status'] == "Idle": df_master.at[idx, 'Idle_Sec'] += diff_secs
            elif user_row['Status'] == "Break": df_master.at[idx, 'Break_Sec'] += diff_secs
            df_master.at[idx, 'Logout_Time'] = now
            df_master.at[idx, 'Status'] = "Logged Out"
            save_shared_data(df_master)
            st.rerun()

# --- 4. DASHBOARD CALCULATIONS ---
report_display = []
def format_seconds(seconds):
    h, r = divmod(int(max(0, seconds)), 3600)
    m, s = divmod(r, 60)
    return f"{h:02d}h {m:02d}m"

for _, row in df_master.iterrows():
    w_s, i_s, b_s = row['Work_Sec'], row['Idle_Sec'], row['Break_Sec']
    if row['Status'] in ["Working", "Idle", "Break"]:
        live_diff = (datetime.now() - pd.to_datetime(row['Last_Change'])).total_seconds()
        if row['Status'] == "Working": w_s += live_diff
        elif row['Status'] == "Idle": i_s += live_diff
        elif row['Status'] == "Break": b_s += live_diff

    report_display.append({
        "Member": row['Member'],
        "Status": row['Status'],
        "Login": row['Login_Time'].strftime("%I:%M %p") if pd.notna(row['Login_Time']) else "---",
        "Work": format_seconds(w_s),
        "Idle": format_seconds(i_s),
        "Break": format_seconds(b_s),
        "Files": row['Files']
    })

# --- 5. MAIN UI ---
st.title("🕒 Office Status Tracker")
df_final = pd.DataFrame(report_display)

m1, m2, m3, m4 = st.columns(4)
m1.metric("🟢 Working", len(df_final[df_final["Status"]=="Working"]))
m2.metric("🟠 Idle", len(df_final[df_final["Status"]=="Idle"]))
m3.metric("🟡 Break", len(df_final[df_final["Status"]=="Break"]))
m4.metric("📂 Total Files", int(df_final["Files"].sum()))

st.dataframe(df_final, use_container_width=True, hide_index=True)

# --- 6. CLEAN/RESET OPTION (Admin Tools) ---
st.divider()
st.subheader("🛠️ Admin / End of Day Tools")
col_a, col_b = st.columns(2)

with col_a:
    # CSV Download for record keeping before cleaning
    csv_export = df_final.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Final Daily Report", data=csv_export, file_name=f"Report_{date.today()}.csv")

with col_b:
    # The "Clean" function
    st.write("✨ **Fresh Sheet for Tomorrow**")
    confirm = st.checkbox("I have downloaded the report and want to RESET all data.")
    if st.button("🧹 Clean Sheet / Reset All", type="primary", disabled=not confirm):
        df_fresh = create_fresh_df()
        save_shared_data(df_fresh)
        st.success("Database has been cleaned! Ready for the next shift.")
        time.sleep(1)
        st.rerun()