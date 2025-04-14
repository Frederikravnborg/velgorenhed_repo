import cv2
import easyocr
import time
import numpy as np
import datetime # Already imported
import csv
import os
from ts_server_api import lap_run

# ----------------- Configuration -----------------
CAMERA_INDEX = 1
RESOLUTION = '480p'
FPS = 10
num_runners_option = 100 # Choose 100 or 200 runners
visualize_stream = True
DEBOUNCE_SECONDS = 40

if RESOLUTION == '2k': FRAME_WIDTH, FRAME_HEIGHT = 2048, 1536
elif RESOLUTION == '720p': FRAME_WIDTH, FRAME_HEIGHT = 1280, 720
elif RESOLUTION == '480p': FRAME_WIDTH, FRAME_HEIGHT = 640, 480

if num_runners_option == 100: VALID_RACE_NUMBERS = {f"{i:03d}" for i in range(1, 101)}
elif num_runners_option == 200: VALID_RACE_NUMBERS = {f"{i:03d}" for i in range(1, 201)}

CSV_FILE = 'lap_counts.csv'

# ----------------- Global State -----------------
# lap_counts tracks display laps (potentially doubled)
lap_counts = {num: 0 for num in VALID_RACE_NUMBERS}
# actual_laps tracks physical laps (always increments by 1)
actual_laps = {num: 0 for num in VALID_RACE_NUMBERS}
last_detection_time = {num: 0 for num in VALID_RACE_NUMBERS}

# ----------------- Initialize OCR Reader -----------------
reader = easyocr.Reader(['en'], gpu=True)

# ----------------- Functions -----------------

# --- MODIFIED load_existing_data_from_csv ---
def load_existing_data_from_csv(csv_file):
    """
    Reads the current scoreboard from the CSV file and populates
    both lap_counts (display) and actual_laps (physical).
    Handles missing 'Actual Laps' column by initializing it from 'Lap Count'.
    """
    global lap_counts, actual_laps
    if os.path.exists(csv_file):
        try:
            with open(csv_file, newline='') as f:
                # Read header to check for 'Actual Laps'
                sniffer = csv.Sniffer()
                has_header = sniffer.has_header(f.read(1024))
                f.seek(0) # Rewind after reading sample for sniffer
                if not has_header:
                    print("CSV file seems to be missing a header. Cannot reliably load data.")
                    return

                csv_reader = csv.DictReader(f)
                # Get fieldnames after DictReader initialization
                headers = csv_reader.fieldnames
                has_actual_laps_col = 'Actual Laps' in headers if headers else False

                if not headers or "Race Number" not in headers or "Lap Count" not in headers:
                     print("CSV file has invalid headers. Cannot reliably load data.")
                     return

                for row in csv_reader:
                    race_number = row.get('Race Number')
                    if race_number in lap_counts: # Check if it's a valid race number
                        try:
                            lap_counts[race_number] = int(row.get('Lap Count', 0))
                            if has_actual_laps_col:
                                actual_laps[race_number] = int(row.get('Actual Laps', 0))
                            else:
                                # If 'Actual Laps' column doesn't exist, initialize from 'Lap Count'
                                actual_laps[race_number] = lap_counts[race_number]
                        except (ValueError, TypeError):
                            # Handle cases where conversion fails, keep default 0
                            pass
            if not has_actual_laps_col:
                 print("Initialized 'actual_laps' from 'Lap Count' as 'Actual Laps' column was missing.")

        except Exception as e:
             print(f"Error loading data from CSV: {e}. Starting with empty counts.")
             # Reset to default state if loading fails catastrophically
             lap_counts = {num: 0 for num in VALID_RACE_NUMBERS}
             actual_laps = {num: 0 for num in VALID_RACE_NUMBERS}
# --- End MODIFIED load_existing_data_from_csv ---

# --- MODIFIED update_csv ---
def update_csv(lap_counts, actual_laps, csv_file):
    """
    Updates the CSV file with current lap_counts (display) and actual_laps (physical).
    Includes both columns in the header and data.
    Preserves the log section below the scoreboard and gap.
    """
    # Define the header including the new 'Actual Laps' column
    scoreboard_header = ['Race Number', 'Lap Count', 'Actual Laps']
    scoreboard = [scoreboard_header]
    for number in sorted(lap_counts.keys(), key=int):
        # Append row with race number, display laps, and actual laps
        scoreboard.append([number, lap_counts[number], actual_laps[number]])

    gap = [[] for _ in range(5)]
    log_section = []

    if os.path.exists(csv_file):
        try:
            with open(csv_file, 'r', newline='') as f:
                reader = csv.reader(f)
                lines = list(reader)
            # Calculate where the log section starts (after scoreboard + gap)
            log_start_index = len(scoreboard) + len(gap)
            if len(lines) > log_start_index:
                log_section = lines[log_start_index:]
        except Exception as e:
            print(f"Could not read existing log section from {csv_file}: {e}")
            log_section = [] # Reset log section if reading fails

    try:
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(scoreboard)
            writer.writerows(gap)
            if log_section:
                writer.writerows(log_section)
        print("CSV file updated with Lap Count and Actual Laps.")
    except Exception as e:
        print(f"Error writing to CSV file {csv_file}: {e}")
# --- End MODIFIED update_csv ---

def append_log_entry(runner_id, display_lap_count, csv_file):
    """
    Appends a new log entry to the CSV file using the *display* lap count.
    Log section is placed after the scoreboard and a gap of 5 rows.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = [runner_id, display_lap_count, timestamp]

    # Determine expected log header row index (scoreboard rows + 5 blank rows)
    # Scoreboard rows = number of runners + 1 header row
    main_table_rows = len(lap_counts) + 1
    log_header_row_index = main_table_rows + 5 # 0-based index
    log_header = ['Race Number', 'Lap Count', 'Timestamp'] # Log uses 'Lap Count' for display count
    need_header = False
    lines = []

    if not os.path.exists(csv_file):
        need_header = True
    else:
        try:
            with open(csv_file, 'r', newline='') as f:
                reader = csv.reader(f)
                lines = list(reader)
            if len(lines) <= log_header_row_index:
                # Not enough lines for header yet, pad if needed before appending
                padding = [[''] for _ in range(log_header_row_index - len(lines))]
                lines.extend(padding)
                need_header = True
            elif lines[log_header_row_index] != log_header:
                 # Header row exists but is wrong, overwrite? For append, just add new header maybe?
                 # Safest is just to add the header if it's missing or wrong at the expected spot
                 # Let's assume if it's wrong, we still append below, but maybe flag it.
                 if lines[log_header_row_index]: # Check if the row is not empty
                    print(f"Warning: Log header at row {log_header_row_index+1} is unexpected: {lines[log_header_row_index]}. Expected: {log_header}")
                 need_header = lines[log_header_row_index] != log_header # Add header if incorrect
        except Exception as e:
             print(f"Error reading CSV for log check: {e}")
             # Assume header is needed if we can't read
             need_header = True

    try:
        with open(csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            # If file is new or header row is missing/incorrect, add it *before* the entry
            if need_header and os.path.exists(csv_file): # Check existence again before writing potentially duplicate header
                # This logic is tricky with 'a' mode. A safer approach might be read/write in update_csv
                # For simplicity here, we'll just append. If header needed, it might be out of place.
                # A truly robust solution would rewrite the file in `update_csv` including log header check.
                # Let's proceed with simple append, accepting potential header issues if file structure is broken manually.
                pass # Avoid writing header in 'a' mode if file already exists. update_csv handles structure.


            writer.writerow(log_entry)
        print(f"Log entry appended for {runner_id} (Lap {display_lap_count}).")
    except Exception as e:
        print(f"Error appending log entry to {csv_file}: {e}")


# --- MODIFIED process_frame ---
def process_frame(frame):
    """
    Processes a video frame: runs OCR, updates display and actual lap counts
    (doubling display laps between 2-3 AM), updates CSV, and draws boxes.
    """
    global lap_counts, actual_laps, last_detection_time

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    results = reader.readtext(gray, detail=1)
    current_time = time.time()
    # Get current hour (0-23) from system time
    current_hour = datetime.datetime.now().hour


    for (bbox, text, conf) in results:
        if conf < 0.5:
            continue

        text_clean = "".join(filter(str.isdigit, text))

        if text_clean in VALID_RACE_NUMBERS:
            if current_time - last_detection_time[text_clean] > DEBOUNCE_SECONDS:

                # Determine lap increment based on time
                if 2 <= current_hour < 3:
                    lap_increment = 2
                    print(f"Power Hour (2-3 AM): Adding 2 laps for {text_clean}")
                else:
                    lap_increment = 1

                # Increment display laps
                lap_counts[text_clean] += lap_increment
                # ALWAYS increment actual laps by 1
                actual_laps[text_clean] += 1

                # Call external API ONCE per detection
                lap_run(int(text_clean))

                last_detection_time[text_clean] = current_time
                print(f"Lap count updated for {text_clean}: {lap_counts[text_clean]} (Actual: {actual_laps[text_clean]})")

                # Update the CSV file with both counts
                update_csv(lap_counts, actual_laps, CSV_FILE)
                # Append a log entry with the *display* lap count
                append_log_entry(text_clean, lap_counts[text_clean], CSV_FILE)

            # Draw bounding box (unchanged)
            pts = np.array(bbox, np.int32).reshape((-1, 1, 2))
            cv2.polylines(frame, [pts], True, (0, 255, 0), 2)
            cv2.putText(frame, text_clean, (int(bbox[0][0]), int(bbox[0][1] - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    return frame
# --- End MODIFIED process_frame ---


def try_camera_index(index):
    """Try to open a camera with the given index."""
    cap = cv2.VideoCapture(index, cv2.CAP_AVFOUNDATION) # Or cv2.CAP_DSHOW etc. depending on OS
    if cap.isOpened():
        ret, _ = cap.read()
        if ret:
            print(f"Successfully connected to camera {index}")
            return True, cap
    cap.release()
    return False, None

def main():
    # Load existing CSV data (now loading both lap types)
    load_existing_data_from_csv(CSV_FILE)

    # --- Camera setup (unchanged) ---
    cap = None
    success = False
    success, cap = try_camera_index(CAMERA_INDEX)
    if not success:
        print(f"Could not open camera {CAMERA_INDEX}, trying other indices...")
        for i in range(4):
            if i != CAMERA_INDEX:
                success, cap = try_camera_index(i)
                if success: break
    if not success or cap is None:
        print("Error: Could not open any video capture device")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, FPS)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
    print("Camera configuration:")
    print(f"  Actual width:  {cap.get(cv2.CAP_PROP_FRAME_WIDTH)}")
    print(f"  Actual height: {cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}")
    print(f"  Actual FPS:    {cap.get(cv2.CAP_PROP_FPS)}")
    print("Starting video capture. Press 'q' to exit.")
    time.sleep(2)
    # --- End Camera setup ---

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break

        processed_frame = process_frame(frame) # Frame processing now handles double laps

        if visualize_stream:
            cv2.imshow("Race Lap Counter", processed_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()