import streamlit as st
import time
import pandas as pd
import numpy as np
from streamlit_autorefresh import st_autorefresh

update_interval = 1000  # milliseconds

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

st_autorefresh(interval=update_interval, limit=0, key="dashboard")

# Initialize session state to track previous lap counts and last update times
if "previous_laps" not in st.session_state:
    st.session_state.previous_laps = {}
if "last_update" not in st.session_state:
    st.session_state.last_update = {}
if "new_runners" not in st.session_state:
    st.session_state.new_runners = []

CSV_FILE = 'lap_counts.csv'

def load_scoreboard_from_csv(csv_file):
    import csv
    scoreboard = []
    try:
        with open(csv_file, newline='') as f:
            reader = csv.reader(f)
            for row in reader:
                # If the row is empty or does not have exactly 2 columns, assume end of scoreboard
                if not row or len(row) < 2:
                    break
                scoreboard.append(row)
    except FileNotFoundError:
        return pd.DataFrame(columns=["Race Number", "Lap Count"])
    
    if not scoreboard:
        return pd.DataFrame(columns=["Race Number", "Lap Count"])
    
    header = scoreboard[0]
    data = scoreboard[1:]
    return pd.DataFrame(data, columns=header)

# Load the scoreboard from the CSV file
df = load_scoreboard_from_csv(CSV_FILE)

# Convert the Race Number column to string (if data exists)
if not df.empty:
    df['Race Number'] = df['Race Number'].astype(str)
    # Convert Lap Count to integer, defaulting empty or non-numeric values to 0
    df['Lap Count'] = pd.to_numeric(df['Lap Count'], errors='coerce').fillna(0).astype(int)

# Sort rows by Lap Count in descending order and reset the index
df_sorted = df.sort_values(by="Lap Count", ascending=False).reset_index(drop=True)

# Rename the columns to match our usage
df_sorted = df_sorted.rename(columns={"Race Number": "Num", "Lap Count": "Laps"})

# Get current time for checking new lap events
current_time = time.time()

# Function to check for a new lap and update session state accordingly
def check_new_lap(row):
    race_number = row['Num']
    previous = st.session_state.previous_laps.get(race_number, 0)
    if row['Laps'] > previous:
        st.session_state.last_update[race_number] = current_time
        # Insert the new event at the front (push previous events right)
        st.session_state.new_runners.insert(0, race_number)
        # Keep only the most recent 5 events
        st.session_state.new_runners = st.session_state.new_runners[:5]
    st.session_state.previous_laps[race_number] = row['Laps']
    return row

df_sorted = df_sorted.apply(check_new_lap, axis=1)

def gradient_green(row):
    try:
        idx = int(row.name)
    except ValueError:
        idx = None
    if idx is not None and idx < 10:
        # Define minimum alpha (more transparent) for the 10th row
        min_alpha = 0.3
        steps = 10
        # Interpolate alpha from 1 (row 0) to min_alpha (row 9)
        alpha = 1 - (idx / (steps - 1)) * (1 - min_alpha)
        style = f'background-color: rgba(0, 255, 0, {alpha})'
        return [style] * len(row)
    else:
        return [''] * len(row)

# Split the sorted DataFrame into parts for a multi-column layout
num_columns = 10
split_dfs = np.array_split(df_sorted, num_columns)

total_laps = df_sorted['Laps'].sum()
latest_runners = st.session_state.new_runners
st.markdown(f"<h1>Total Laps: {total_laps} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; New: {', '.join(latest_runners)}</h1>", unsafe_allow_html=True)

cols = st.columns(num_columns)

for i, col in enumerate(cols):
    df_chunk = split_dfs[i].copy()
    
    # Keep 'Num' as a separate column; do not set it as the index yet
    df_chunk = df_chunk[["Num", "Laps"]]
    df_chunk = df_chunk.sort_values('Laps', ascending=False)
    df_chunk.set_index('Num', inplace=True)
    
    if i == 0:
        # Define gradient styling for first column's top 10 rows
        def highlight_first_ten(row):
            # Get row's position in this chunk's DataFrame
            position = df_chunk.index.get_loc(row.name)
            if position < 10:
                min_alpha = 0.3
                alpha = 1 - (position / 9) * (1 - min_alpha)
                return [f'background-color: rgba(0, 255, 0, {alpha})'] * len(row)
            return [''] * len(row)
        
        styled_split_df = df_chunk.style.apply(highlight_first_ten, axis=1)
    else:
        styled_split_df = df_chunk.style
    
    col.dataframe(styled_split_df, use_container_width=True, height=800)
