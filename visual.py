import streamlit as st
import time
import pandas as pd
import numpy as np
from streamlit_autorefresh import st_autorefresh
from datetime import datetime # Added for time checking
from cv import num_runners_option

update_interval = 1000    # milliseconds

st.set_page_config(page_title="DTU Thunderstriders Knækker Cancer - Lap Counts", layout="wide")

if num_runners_option == 200:
    num_columns = 10
else: # num_runners_option == 100
    num_columns = 5 # Half the columns for half the runners

st_autorefresh(interval=update_interval, limit=0, key="dashboard")

# Initialize session state to track previous lap counts and last update times
if "previous_laps" not in st.session_state:
    st.session_state.previous_laps = {}
if "last_update" not in st.session_state:
    st.session_state.last_update = {}
if "new_runners" not in st.session_state:
    # Stores runner identifiers (e.g., "123" or "123*")
    st.session_state.new_runners = []

CSV_FILE = 'lap_counts.csv'

# --- load_scoreboard_from_csv function (Unchanged from your 'new script') ---
def load_scoreboard_from_csv(csv_file, max_rows=num_runners_option):  # Added max_rows parameter
    import csv
    scoreboard = []
    try:
        with open(csv_file, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            try:
                header = next(reader)
            except StopIteration:
                return pd.DataFrame(columns=["Race Number", "Lap Count"])

            if len(header) < 2 or "Race Number" not in header or "Lap Count" not in header:
                st.warning(f"CSV file '{csv_file}' has unexpected headers: {header}. Expected 'Race Number', 'Lap Count'. Processing might fail.")
                if len(header) >= 2:
                    header = ["Race Number", "Lap Count"] + header[2:]
                else:
                    return pd.DataFrame(columns=["Race Number", "Lap Count"])

            # Only read up to max_rows rows
            row_count = 0
            for row in reader:
                if row_count >= max_rows:
                    break
                if not row or len(row) < 2 or not row[0].strip() or not row[1].strip():
                    continue
                scoreboard.append(row[:len(header)])
                row_count += 1
    except FileNotFoundError:
        st.error(f"Error: CSV file '{csv_file}' not found.")
        return pd.DataFrame(columns=["Race Number", "Lap Count"])
    except Exception as e:
        st.error(f"Error reading CSV file '{csv_file}': {e}")
        return pd.DataFrame(columns=["Race Number", "Lap Count"])

    if not scoreboard:
        # Only header was present, or all rows were empty/incomplete
        return pd.DataFrame(columns=header)

    # Create DataFrame using the read header and data
    df = pd.DataFrame(scoreboard, columns=header)
    # Select only the required columns, even if more were read
    return df[["Race Number", "Lap Count"]]
# --- End load_scoreboard_from_csv function ---


# Load the scoreboard from the CSV file
df = load_scoreboard_from_csv(CSV_FILE)

# Perform data processing only if the DataFrame is not empty
if not df.empty:
    # Ensure 'Race Number' is string and clean it up
    df['Race Number'] = df['Race Number'].astype(str).str.strip()
    # Convert 'Lap Count' to numeric, coercing errors to NaN, then fill NaN with 0 and convert to integer
    df['Lap Count'] = pd.to_numeric(df['Lap Count'], errors='coerce').fillna(0).astype(int)

    # Remove rows where Race Number might be empty after stripping
    df = df[df['Race Number'] != '']

    # --- Data Integrity Check: Ensure unique Race Numbers ---
    # if df['Race Number'].duplicated().any():
    #     st.warning("Duplicate Race Numbers found in CSV. Keeping first occurrence.")
    #     df = df.drop_duplicates(subset=['Race Number'], keep='first')
    # --- End Data Integrity Check ---


    # Sort rows by Lap Count in descending order FIRST
    df_sorted = df.sort_values(by="Lap Count", ascending=False)
    # THEN set Race Number as index BEFORE renaming columns
    # This preserves the Race Number association correctly
    df_sorted = df_sorted.set_index('Race Number', drop=False) # Keep Race Number also as a column if needed later


    # Rename the columns for internal use (using the column, not the index name)
    df_sorted = df_sorted.rename(columns={"Race Number": "Num", "Lap Count": "Laps"})

    # --- Calculate Distance ---
    df_sorted['Distance'] = (df_sorted['Laps'] * 0.4).round(1).astype(str) + " km"
    # --- End Calculate Distance ---

    # Get current time for checking new lap events
    current_time = time.time()
    current_hour = datetime.now().hour # Get current hour (0-23)

    # Function to check for a new lap and update session state accordingly
    # Uses the 'Num' column for lookup
    def check_new_lap(row):
        race_number = row['Num'] # Use the 'Num' column value
        previous = st.session_state.previous_laps.get(race_number, 0)

        if row['Laps'] > previous:
            st.session_state.last_update[race_number] = current_time

            # --- Double Lap Check ---
            display_num = race_number
            if current_hour == 2: # Check if current time is between 2:00 AM and 2:59 AM
                 display_num += "*" # Append indicator for "New:" list
            # --- End Double Lap Check ---

            st.session_state.new_runners.insert(0, display_num)
            st.session_state.new_runners = st.session_state.new_runners[:8]

        st.session_state.previous_laps[race_number] = row['Laps']
        return row

    # Apply the check function row by row AFTER distance is calculated
    # Note: This apply might reset the index if not careful, but we re-set it later anyway.
    df_sorted = df_sorted.apply(check_new_lap, axis=1)

    # --- Prepare "New:" display string ---
    # Create the dictionary mapping Num -> Laps *after* check_new_lap potentially modified Laps
    laps_dict = df_sorted.set_index('Num')['Laps'].to_dict() # Re-set index temporarily for dict creation
    latest_runners_display = []
    for runner_identifier in st.session_state.new_runners: # e.g., "123" or "456*"
        runner_num = runner_identifier.replace('*','') # Get actual number
        laps = laps_dict.get(runner_num, '?') # Lookup laps using the actual number
        display_entry = f"{runner_identifier} ({laps})" # Format as "Number(*) (Laps)"
        latest_runners_display.append(display_entry)
    new_laps_str = ', '.join(latest_runners_display)
    # --- End Prepare "New:" display string ---


    total_laps = df_sorted['Laps'].sum()
    st.markdown(f"<h1>Total Laps: {total_laps} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; New: {new_laps_str}</h1>", unsafe_allow_html=True)

    # Make sure index is set correctly before splitting
    df_sorted = df_sorted.set_index('Num') # Set 'Num' as the final index before splitting
    df_sorted.index.name = "Runner" # Name the index column

    # Split the sorted DataFrame (which now has 'Runner' index)
    if not df_sorted.empty:
        split_dfs = np.array_split(df_sorted, num_columns)
    else:
        # Ensure columns match df_sorted for consistency
        split_dfs = [pd.DataFrame(columns=["Laps", "Distance"], index=pd.Index([], name="Runner"))] * num_columns

    cols = st.columns(num_columns)

    for i, col in enumerate(cols):
        # Check if the split chunk is valid and not empty
        if i < len(split_dfs) and not split_dfs[i].empty:
            # The chunk already has the correct index ('Runner')
            df_chunk = split_dfs[i].copy()

            # Select only the columns needed for display ('Laps', 'Distance')
            # The index ('Runner') is already set correctly from df_sorted
            df_display = df_chunk[["Laps", "Distance"]]

            # --- Corrected Styling Function ---
            # Uses the index ('Runner') of df_display to find position
            def highlight_first_ten(row):
                # Get the row's position (0, 1, 2...) within this specific chunk (df_display)
                try:
                    # Find the integer position of the index label (row.name which is the Runner number)
                    position = df_display.index.get_loc(row.name)
                    if position < 10:
                        min_alpha = 0.3
                        # Ensure division by 9 (steps-1) for 10 items (0 to 9)
                        alpha = 1 - (position / 9) * (1 - min_alpha) if position < 9 else min_alpha
                        # Apply style to all columns in the row ('Laps', 'Distance')
                        return [f'background-color: rgba(0, 255, 0, {alpha})'] * len(row)
                except KeyError:
                     pass # Should not happen if row.name is always in df_display.index
                except Exception as e:
                     # Catch other potential errors during styling
                     # st.error(f"Styling error for runner {row.name}: {e}") # Optional: for debugging
                     pass # Return default style

                # Default: return empty styles for the row
                return [''] * len(row)
            # --- End Corrected Styling Function ---


            # Apply styling only to the first column (i == 0)
            if i == 0:
                # Apply the corrected styling function
                styled_split_df = df_display.style.apply(highlight_first_ten, axis=1)
            else:
                styled_split_df = df_display.style # No special styling for other columns

            # Display the styled DataFrame chunk - Index ('Runner') is now visible
            col.dataframe(styled_split_df, use_container_width=True, height=800)
        else:
            # If a chunk is empty, display nothing or a placeholder
            col.empty()

else:
    # Handle case where the initial CSV load resulted in an empty DataFrame
    st.markdown("<h1>Total Laps: 0 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; New:</h1>", unsafe_allow_html=True)
    st.info("No runner data loaded. Waiting for data in lap_counts.csv...")
    # Display empty columns
    cols = st.columns(num_columns)
    for col in cols:
        col.empty()