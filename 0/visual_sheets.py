import streamlit as st
import time
import pandas as pd
import numpy as np
from streamlit_autorefresh import st_autorefresh
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="DTU Thunderstriders Knækker Cancer - Lap Counts", layout="wide")

# Hide row indices via custom CSS
hide_dataframe_row_index = """
<style>
/* Hide the index column */
tbody > tr > th:first-child {
    display: none;
}
thead > tr > th:first-child {
    display: none;
}
/* Hide any blank "spacer" cells */
.blank {
    display: none;
}
</style>
"""
st.markdown(hide_dataframe_row_index, unsafe_allow_html=True)

st_autorefresh(interval=4000, limit=0, key="dashboard")

# Initialize session state to track previous lap counts and last update times
if "previous_laps" not in st.session_state:
    st.session_state.previous_laps = {}
if "last_update" not in st.session_state:
    st.session_state.last_update = {}
if "new_runners" not in st.session_state:
    st.session_state.new_runners = []

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
        # Insert the new event at the front, keeping only the most recent 5 events
        st.session_state.new_runners = st.session_state.new_runners[1:5] + [race_number]
    st.session_state.previous_laps[race_number] = row['Laps']
    return row

df_sorted = df_sorted.apply(check_new_lap, axis=1)

# Optional: highlight the top 3 rows in green
def highlight_top_rows(row):
    try:
        row_index = int(row.name)  # Convert row.name to an integer if possible
    except ValueError:
        row_index = 999999         # Fallback to a large number so it won't highlight
    
    return [
        'background-color: lightgreen' if row_index < 3 else '' 
        for _ in row
    ]

# Split the sorted DataFrame into parts for a multi-column layout
num_columns = 10
split_dfs = np.array_split(df_sorted, num_columns)

total_laps = df_sorted['Laps'].sum()
latest_runners = st.session_state.new_runners[-5:][::-1]
st.markdown(f"<h1>Total Laps: {total_laps} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; New: {', '.join(latest_runners)}</h1>", unsafe_allow_html=True)
cols = st.columns(num_columns)

for i, col in enumerate(cols):
    # Copy the DataFrame chunk
    df_chunk = split_dfs[i].copy()
    
    # Make "Num" the index, removing the default 0,1,2,... index
    df_chunk.set_index("Num", inplace=True)
    
    # (Optional) Keep only the columns you actually need displayed
    df_chunk = df_chunk[["Laps"]]

    # Apply styling if desired
    styled_split_df = df_chunk.style.apply(highlight_top_rows, axis=1)
    
    # Display with the runner's number as the index
    col.dataframe(styled_split_df, use_container_width=True, height=800)