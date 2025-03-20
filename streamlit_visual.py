import streamlit as st
import time
import pandas as pd
import numpy as np
from streamlit_autorefresh import st_autorefresh
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="Real-Time Lap Counter Dashboard", layout="wide")
st_autorefresh(interval=4000, limit=0, key="dashboard")

# Initialize session state to track previous lap counts and last update times
if "previous_laps" not in st.session_state:
    st.session_state.previous_laps = {}
if "last_update" not in st.session_state:
    st.session_state.last_update = {}

# Set up Google Sheets API credentials
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('velgoerenhedsloeb-7c4668dfdb74.json', scope)
client = gspread.authorize(creds)

# Open your Google Sheet by name
sheet = client.open("24-Hour Charity Run").sheet1

# Fetch all records from the sheet and load them into a DataFrame
data = sheet.get_all_records(expected_headers=["Race Number", "Lap Count"])
df = pd.DataFrame(data)

# Convert the Race Number column to string
df['Race Number'] = df['Race Number'].astype(str)

# Convert the Lap Count column to integers, defaulting empty/non-numeric to 0
df['Lap Count'] = pd.to_numeric(df['Lap Count'], errors='coerce').fillna(0).astype(int)

# Sort rows by Lap Count in descending order and reset the index
df_sorted = df.sort_values(by="Lap Count", ascending=False).reset_index(drop=True)

# Rename the columns
df_sorted = df_sorted.rename(columns={"Race Number": "Num", "Lap Count": "Laps"})

# Get current time for checking new lap events
current_time = time.time()

# Function to check for a new lap and update session state accordingly
def check_new_lap(row):
    race_number = row['Num']
    previous = st.session_state.previous_laps.get(race_number, 0)
    if row['Laps'] > previous:
        st.session_state.last_update[race_number] = current_time
    st.session_state.previous_laps[race_number] = row['Laps']
    return row

df_sorted = df_sorted.apply(check_new_lap, axis=1)

# Function to show a modal popup in the center of the screen
def show_modal(message):
    st.markdown(
        f"""
        <style>
        .modal {{
            position: fixed;
            top: 40%;
            left: 50%;
            transform: translate(-50%, -50%);
            background-color: rgba(255,255,255,0.95);
            padding: 30px;
            border: 2px solid #000;
            border-radius: 8px;
            z-index: 1000;
            text-align: center;
        }}
        </style>
        <div class="modal">
            {message}
        </div>
        """,
        unsafe_allow_html=True
    )

# Check if any runner has a new lap (i.e. updated in the last 5 seconds)
new_lap_rows = df_sorted[df_sorted.apply(lambda row: (current_time - st.session_state.last_update.get(row['Num'], 0)) < 5, axis=1)]
if not new_lap_rows.empty:
    # For example, show a popup for the first runner with a new lap.
    runner = new_lap_rows.iloc[0]
    show_modal(f"Runner {runner['Num']} just completed a new lap!")

# (Optional) Define a function to highlight top rows if needed.
def highlight_top_rows(row):
    return ['background-color: lightgreen' if row.name < 3 else '' for _ in row]

# Split the sorted DataFrame into parts for a multi-column layout.
num_columns = 10
split_dfs = np.array_split(df_sorted, num_columns)

st.title("Real-Time Lap Counter Dashboard")
cols = st.columns(num_columns)
for i, col in enumerate(cols):
    styled_split_df = split_dfs[i].style.apply(highlight_top_rows, axis=1).hide(axis="index")
    col.dataframe(styled_split_df, use_container_width=True, height=800)