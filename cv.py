import cv2
import easyocr
import time
import numpy as np
import datetime
import csv
import os

# ----------------- Configuration -----------------
CAMERA_INDEX = 1  # Set to the device index corresponding to your iPhone camera feed via Continuity Camera (e.g. 0 or 1)

RESOLUTION = '480p'    # '480p', '720p', or '2k'

FPS = 10

# Minimum seconds between successive detections of the same runner
DEBOUNCE_SECONDS = 40


if RESOLUTION == '2k':
    FRAME_WIDTH =  2048
    FRAME_HEIGHT =  1536
elif RESOLUTION == '720p':
    FRAME_WIDTH =  1280
    FRAME_HEIGHT =  720
elif RESOLUTION == '480p':
    FRAME_WIDTH =  640
    FRAME_HEIGHT =  480

# Predefined valid race numbers (update with your actual list)
VALID_RACE_NUMBERS = {f"{i:03d}" for i in range(1, 201)}

# CSV file configuration
CSV_FILE = 'lap_counts.csv'

# ----------------- Global State -----------------
lap_counts = {num: 0 for num in VALID_RACE_NUMBERS}
last_detection_time = {num: 0 for num in VALID_RACE_NUMBERS}

# ----------------- Initialize OCR Reader -----------------
# reader = easyocr.Reader(['en'], gpu=True)
reader = easyocr.Reader(['en'], gpu=True)

# ----------------- Functions -----------------
def load_existing_data_from_csv(csv_file):
    """
    Reads the current scoreboard from the CSV file and populates the lap_counts dictionary.
    Assumes the CSV has a header: "Race Number", "Lap Count"
    """
    global lap_counts
    if os.path.exists(csv_file):
        with open(csv_file, newline='') as f:
            csv_reader = csv.DictReader(f)
            for row in csv_reader:
                race_number = row['Race Number']
                try:
                    lap_counts[race_number] = int(row['Lap Count'])
                except ValueError:
                    pass

def update_csv(lap_counts, csv_file):
    """
    Updates the CSV file with the current lap_counts.
    The CSV file will have the scoreboard (with header "Race Number", "Lap Count") at the top,
    followed by 5 blank rows as a gap, then the existing log section is preserved.
    """
    scoreboard = [['Race Number', 'Lap Count']]
    for number in sorted(lap_counts.keys(), key=int):
        scoreboard.append([number, lap_counts[number]])

    # Create gap of 5 blank rows
    gap = [[] for _ in range(5)]

    log_section = []
    if os.path.exists(csv_file):
        with open(csv_file, 'r', newline='') as f:
            reader = csv.reader(f)
            lines = list(reader)
        if len(lines) > len(scoreboard) + 5:
            log_section = lines[len(scoreboard)+5:]

    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(scoreboard)
        writer.writerows(gap)
        if log_section:
            writer.writerows(log_section)
    print("CSV file updated.")

def append_log_entry(runner_id, lap_count, csv_file):
    """
    Appends a new log entry to the CSV file.
    If the log header is not present, it adds it.
    The log section is placed after the scoreboard and a gap of 5 rows.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = [runner_id, lap_count, timestamp]

    # Determine expected log header row index (scoreboard rows + 5 blank rows)
    main_table_rows = len(lap_counts) + 1  # Scoreboard rows count
    log_header_row = main_table_rows + 5
    log_header = ['Race Number', 'Lap Count', 'Timestamp']
    need_header = False

    if not os.path.exists(csv_file):
        need_header = True
    else:
        with open(csv_file, 'r', newline='') as f:
            reader = csv.reader(f)
            lines = list(reader)
        if len(lines) < log_header_row + 1:
            need_header = True
        else:
            if lines[log_header_row] != log_header:
                need_header = True

    with open(csv_file, 'a', newline='') as f:
        writer = csv.writer(f)
        if need_header:
            writer.writerow(log_header)
        writer.writerow(log_entry)
    print(f"Log entry appended for {runner_id}.")

def process_frame(frame):
    """
    Processes a video frame: runs OCR to detect text (race numbers),
    updates lap counts if a valid number is found (applying debounce),
    draws bounding boxes, and updates the CSV file.
    """
    global lap_counts, last_detection_time

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    results = reader.readtext(gray, detail=1)
    current_time = time.time()

    for (bbox, text, conf) in results:
        if conf < 0.5:
            continue
        
        # Keep only digits in the detected text
        text_clean = "".join(filter(str.isdigit, text))
        
        if text_clean in VALID_RACE_NUMBERS:
            # Debounce check: only count a lap if enough time has passed
            if current_time - last_detection_time[text_clean] > DEBOUNCE_SECONDS:
                lap_counts[text_clean] += 1
                last_detection_time[text_clean] = current_time
                print(f"Lap count updated for {text_clean}: {lap_counts[text_clean]}")

                # Update the CSV file with the new scoreboard
                update_csv(lap_counts, CSV_FILE)
                # Append a log entry for this newly detected lap
                append_log_entry(text_clean, lap_counts[text_clean], CSV_FILE)

            # Draw bounding box and label around the detected race number
            pts = np.array(bbox, np.int32).reshape((-1, 1, 2))
            cv2.polylines(frame, [pts], True, (0, 255, 0), 2)
            cv2.putText(frame, text_clean, (int(bbox[0][0]), int(bbox[0][1] - 10)), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    
    return frame

def try_camera_index(index):
    """
    Try to open a camera with the given index and return (success, camera) tuple.
    """
    cap = cv2.VideoCapture(index, cv2.CAP_AVFOUNDATION)
    if cap.isOpened():
        ret, _ = cap.read()
        if ret:
            print(f"Successfully connected to camera {index}")
            return True, cap
    cap.release()
    return False, None

def main():
    # Load existing CSV data so we keep a running total (if the file exists)
    load_existing_data_from_csv(CSV_FILE)
    
    # Try to open the camera feed, attempting multiple indices if needed
    cap = None
    success = False
    
    success, cap = try_camera_index(CAMERA_INDEX)
    if not success:
        print(f"Could not open camera {CAMERA_INDEX}, trying other indices...")
        for i in range(4):  # Try indices 0-3
            if i != CAMERA_INDEX:
                success, cap = try_camera_index(i)
                if success:
                    break
    
    if not success or cap is None:
        print("Error: Could not open any video capture device")
        return
    
    # Set camera properties
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
    # Main capture loop
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break
        
        processed_frame = process_frame(frame)
        
        # (Optional) Display the processed frame with overlays for debugging
        cv2.imshow("Race Lap Counter", processed_frame)
        
        # Exit when 'q' is pressed.
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()