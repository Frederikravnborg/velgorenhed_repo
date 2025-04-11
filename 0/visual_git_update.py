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
tbody > tr > th:first-child {
    display: none;
}
thead > tr > th:first-child {
    display: none;
}
.blank {
    display: none;
}
</style>
"""
st.markdown(hide_dataframe_row_index, unsafe_allow_html=True)

st_autorefresh(interval=update_interval, limit=0, key="dashboard")

if "previous_laps" not in st.session_state:
    st.session_state.previous_laps = {}
if "last_update" not in st.session_state:
    st.session_state.last_update = {}
if "new_runners" not in st.session_state:
    st.session_state.new_runners = []

# Use the *raw* link - not the "blob" link
CSV_URL = "https://raw.githubusercontent.com/Frederikravnborg/velgorenhed_repo/main/lap_counts.csv"

@st.cache_data(ttl=60)
def load_scoreboard_from_github():
    # Only read the first (header) + 201 data lines = 202 total
    df_temp = pd.read_csv(
        CSV_URL,
        nrows=202,         # <-- only read up to line 201 + header row
        on_bad_lines="skip"  # optional safeguard if lines 1..201 have issues
    )
    # Convert columns to the correct data types
    df_temp.columns = ["Race Number", "Lap Count"]  # force 2-column naming
    df_temp["Race Number"] = df_temp["Race Number"].astype(str)
    df_temp["Lap Count"] = pd.to_numeric(df_temp["Lap Count"], errors="coerce").fillna(0).astype(int)
    return df_temp

df = load_scoreboard_from_github()

# Sort
df_sorted = df.sort_values(by="Lap Count", ascending=False).reset_index(drop=True)
df_sorted = df_sorted.rename(columns={"Race Number": "Num", "Lap Count": "Laps"})

current_time = time.time()

def check_new_lap(row):
    race_number = row["Num"]
    previous = st.session_state.previous_laps.get(race_number, 0)
    if row["Laps"] > previous:
        st.session_state.last_update[race_number] = current_time
        st.session_state.new_runners.insert(0, race_number)
        st.session_state.new_runners = st.session_state.new_runners[:5]
    st.session_state.previous_laps[race_number] = row["Laps"]
    return row

df_sorted = df_sorted.apply(check_new_lap, axis=1)

def gradient_green(row):
    try:
        idx = int(row.name)
    except ValueError:
        idx = None
    if idx is not None and idx < 10:
        min_alpha = 0.3
        steps = 10
        alpha = 1 - (idx / (steps - 1)) * (1 - min_alpha)
        style = f"background-color: rgba(0, 255, 0, {alpha})"
        return [style] * len(row)
    else:
        return [""] * len(row)

num_columns = 10
split_dfs = np.array_split(df_sorted, num_columns)

total_laps = df_sorted["Laps"].sum()
latest_runners = st.session_state.new_runners
st.markdown(
    f"<h1>Total Laps: {total_laps}  &nbsp;&nbsp;&nbsp;&nbsp;"
    f"New: {', '.join(latest_runners)}</h1>",
    unsafe_allow_html=True
)

cols = st.columns(num_columns)

for i, col in enumerate(cols):
    df_chunk = split_dfs[i].copy()
    df_chunk = df_chunk[["Num", "Laps"]].sort_values("Laps", ascending=False)
    df_chunk.set_index("Num", inplace=True)
    
    if i == 0:
        def highlight_first_ten(row):
            position = df_chunk.index.get_loc(row.name)
            if position < 10:
                min_alpha = 0.3
                alpha = 1 - (position / 9) * (1 - min_alpha)
                return [f"background-color: rgba(0, 255, 0, {alpha})"] * len(row)
            return ["" for _ in range(len(row))]
        styled_split_df = df_chunk.style.apply(highlight_first_ten, axis=1)
    else:
        styled_split_df = df_chunk.style
    
    col.dataframe(styled_split_df, use_container_width=True, height=800)