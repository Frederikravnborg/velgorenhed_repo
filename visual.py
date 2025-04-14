import streamlit as st
import time
import pandas as pd
import numpy as np
from streamlit_autorefresh import st_autorefresh
from datetime import datetime # Already imported
# Assuming cv.py or similar defines this
# from cv import num_runners_option
# For testing, let's define it here:
num_runners_option = 100 # Or 200

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

# --- MODIFIED load_scoreboard_from_csv function ---
def load_scoreboard_from_csv(csv_file, max_rows=num_runners_option):
    import csv
    scoreboard = []
    # Define expected headers - now including 'Actual Laps'
    expected_headers = ["Race Number", "Lap Count", "Actual Laps"]
    try:
        with open(csv_file, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            try:
                header = next(reader)
            except StopIteration:
                # Return empty DataFrame with *expected* columns if file is empty
                return pd.DataFrame(columns=expected_headers)

            # Check if header is valid or at least has the first two columns
            if len(header) < 2 or "Race Number" not in header or "Lap Count" not in header:
                st.warning(f"CSV file '{csv_file}' has unexpected headers: {header}. Expected at least 'Race Number', 'Lap Count'. Processing might fail.")
                # Attempt to use standard headers if possible
                if len(header) >= 2:
                    # Keep original header if it has at least two, others will become NaN later
                     pass # Keep original header for now
                else:
                    # If header is too short, return empty with expected columns
                    return pd.DataFrame(columns=expected_headers)
            else:
                # If header looks okay, make sure it includes expected ones for DataFrame creation
                if "Actual Laps" not in header:
                    st.info("CSV is missing 'Actual Laps' column. Distance calculation might be inaccurate until CV script updates the file.")
                    # We will handle the missing column later in the processing step

            # Only read up to max_rows rows
            row_count = 0
            for row in reader:
                if row_count >= max_rows:
                    break
                # Skip rows that don't have at least Race Number and Lap Count
                if not row or len(row) < 2 or not row[0].strip() or not row[1].strip():
                    continue
                # Pad row with empty strings if it's shorter than the header
                padded_row = row + [''] * (len(header) - len(row))
                scoreboard.append(padded_row[:len(header)]) # Append only up to header length
                row_count += 1

    except FileNotFoundError:
        st.error(f"Error: CSV file '{csv_file}' not found.")
        return pd.DataFrame(columns=expected_headers) # Return empty with expected columns
    except Exception as e:
        st.error(f"Error reading CSV file '{csv_file}': {e}")
        return pd.DataFrame(columns=expected_headers) # Return empty with expected columns

    if not scoreboard:
        # Only header was present, or all rows were empty/incomplete
        return pd.DataFrame(columns=header if 'header' in locals() else expected_headers)

    # Create DataFrame using the read header and data
    df = pd.DataFrame(scoreboard, columns=header)

    # Select only the expected columns, adding 'Actual Laps' if it was missing
    if "Actual Laps" not in df.columns:
        # If 'Actual Laps' is missing, create it and initialize it based on 'Lap Count'
        # This assumes parity before the 'Actual Laps' feature was added
        df['Actual Laps'] = df['Lap Count']

    # Ensure we only keep the expected columns in the final DataFrame
    # Handle potential case where 'Lap Count' might also be missing from a bad file read
    cols_to_keep = []
    if "Race Number" in df.columns: cols_to_keep.append("Race Number")
    if "Lap Count" in df.columns: cols_to_keep.append("Lap Count")
    if "Actual Laps" in df.columns: cols_to_keep.append("Actual Laps")


    return df[cols_to_keep]
# --- End MODIFIED load_scoreboard_from_csv function ---


# Load the scoreboard from the CSV file
df = load_scoreboard_from_csv(CSV_FILE)

# Perform data processing only if the DataFrame is not empty and has required columns
if not df.empty and "Race Number" in df.columns and "Lap Count" in df.columns and "Actual Laps" in df.columns:
    # Ensure 'Race Number' is string and clean it up
    df['Race Number'] = df['Race Number'].astype(str).str.strip()
    # Convert 'Lap Count' (display laps) to numeric
    df['Lap Count'] = pd.to_numeric(df['Lap Count'], errors='coerce').fillna(0).astype(int)
    # Convert 'Actual Laps' (physical laps) to numeric
    df['Actual Laps'] = pd.to_numeric(df['Actual Laps'], errors='coerce').fillna(0).astype(int)


    # Remove rows where Race Number might be empty after stripping
    df = df[df['Race Number'] != '']

    # --- Data Integrity Check: Optional ---
    # if df['Race Number'].duplicated().any():
    #     st.warning("Duplicate Race Numbers found in CSV. Keeping first occurrence.")
    #     df = df.drop_duplicates(subset=['Race Number'], keep='first')
    # --- End Data Integrity Check ---


    # Sort rows by Lap Count (display laps) in descending order FIRST
    df_sorted = df.sort_values(by="Lap Count", ascending=False)
    # THEN set Race Number as index BEFORE renaming columns
    df_sorted = df_sorted.set_index('Race Number', drop=False) # Keep Race Number also as a column if needed


    # Rename the columns for internal use
    # Note: 'Actual Laps' column is kept but not explicitly renamed here, accessed directly later
    df_sorted = df_sorted.rename(columns={"Race Number": "Num", "Lap Count": "Laps"})

    # --- MODIFIED Calculate Distance ---
    # Calculate Distance based on the 'Actual Laps' column
    df_sorted['Distance'] = (df_sorted['Actual Laps'] * 0.4).round(1).astype(str) + " km"
    # --- End MODIFIED Calculate Distance ---

    # Get current time for checking new lap events
    current_time = time.time()

    # Function to check for a new lap (based on display Laps) and update session state accordingly
    def check_new_lap(row):
        race_number = row['Num']
        previous = st.session_state.previous_laps.get(race_number, 0)

        # Check against the 'Laps' column (display laps) for changes
        if row['Laps'] > previous:
            st.session_state.last_update[race_number] = current_time
            display_num = race_number
            st.session_state.new_runners.insert(0, display_num)
            st.session_state.new_runners = st.session_state.new_runners[:5]

        # Store the current 'Laps' (display laps) for the next check
        st.session_state.previous_laps[race_number] = row['Laps']
        return row

    # Apply the check function row by row AFTER distance is calculated
    df_sorted = df_sorted.apply(check_new_lap, axis=1)

    # --- Prepare "New:" display string ---
    # Create the dictionary mapping Num -> Laps (display laps)
    laps_dict = df_sorted.set_index('Num')['Laps'].to_dict() # Use display laps for the "New" indicator
    latest_runners_display = []
    for runner_identifier in st.session_state.new_runners:
        runner_num = runner_identifier.replace('*','')
        laps = laps_dict.get(runner_num, '?') # Get display laps
        display_entry = f"{runner_identifier} ({laps})"
        latest_runners_display.append(display_entry)
    new_laps_str = ', '.join(latest_runners_display)
    # --- End Prepare "New:" display string ---


    total_laps = df_sorted['Laps'].sum() # Show total *display* laps
    st.markdown(f"<h1>Total Laps: {total_laps} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; New: {new_laps_str}</h1>", unsafe_allow_html=True)

    # Make sure index is set correctly before splitting
    df_sorted = df_sorted.set_index('Num')
    df_sorted.index.name = "Runner"

    # Split the sorted DataFrame
    if not df_sorted.empty:
        # Keep only 'Laps' and 'Distance' columns for splitting and display
        df_to_split = df_sorted[["Laps", "Distance"]]
        split_dfs = np.array_split(df_to_split, num_columns)
    else:
        split_dfs = [pd.DataFrame(columns=["Laps", "Distance"], index=pd.Index([], name="Runner"))] * num_columns

    # Define the CSS style for larger headers
    header_style = [{'selector': 'th', 'props': [('font-size', '18px')]}]

    cols = st.columns(num_columns)

    for i, col in enumerate(cols):
        if i < len(split_dfs) and not split_dfs[i].empty:
            df_chunk = split_dfs[i].copy()
            # df_display already has the correct columns: "Laps", "Distance"
            df_display = df_chunk

            # --- Styling Function (Unchanged logic, but applied to df_display) ---
            def highlight_first_ten(row):
                try:
                    position = df_display.index.get_loc(row.name)
                    if position < 10:
                        min_alpha = 0.3
                        alpha = 1 - (position / 9) * (1 - min_alpha) if position < 9 else min_alpha
                        return [f'background-color: rgba(0, 255, 0, {alpha})'] * len(row)
                except KeyError:
                     pass
                except Exception as e:
                     pass
                return [''] * len(row)
            # --- End Styling Function ---

            if i == 0:
                styled_split_df = df_display.style.apply(highlight_first_ten, axis=1)
            else:
                styled_split_df = df_display.style

            styled_split_df = styled_split_df.set_table_styles(header_style)

            col.dataframe(styled_split_df, use_container_width=True, height=800)
        else:
            col.empty()

else:
    # Handle case where the initial CSV load resulted in an empty or incomplete DataFrame
    st.markdown("<h1>Total Laps: 0 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; New:</h1>", unsafe_allow_html=True)
    if df.empty:
         st.info("No runner data loaded. Waiting for data in lap_counts.csv...")
    else:
         st.warning(f"Loaded data is missing required columns. Expected 'Race Number', 'Lap Count', 'Actual Laps'. Found: {list(df.columns)}")
         st.info("Waiting for corrected data in lap_counts.csv...")
    # Display empty columns
    cols = st.columns(num_columns)
    for col in cols:
        col.empty()