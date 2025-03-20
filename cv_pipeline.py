import cv2
import easyocr
import time
import numpy as np
import gspread
from google.oauth2.service_account import Credentials
import datetime

# ----------------- Configuration -----------------
CAMERA_INDEX = 0  # Default to built-in webcam
FRAME_WIDTH = 2048
FRAME_HEIGHT = 1536
FPS = 15

# Minimum seconds between successive detections of the same runner
# Set to 30 seconds to prevent duplicate detections during 400m laps
DEBOUNCE_SECONDS = 30

# Predefined valid race numbers (update with your actual list)
VALID_RACE_NUMBERS = {str(i) for i in range(101, 301)}

# ----------------- Google Sheets Configuration -----------------
SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
          'https://www.googleapis.com/auth/drive']
# Update the path to your service account credentials file.
CREDENTIALS_FILE = 'velgoerenhedsloeb-7c4668dfdb74.json'
creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
client = gspread.authorize(creds)

# Replace with your actual Google Sheet ID from the sheet URL.
SHEET_ID = '1loQS4_aPTvNxwDkRs01sG8usJxsh4OeK2nAgI2uvwqU'
# We'll use the first sheet for both the scoreboard (top) and log (bottom).
sheet = client.open_by_key(SHEET_ID).sheet1

# ----------------- Global State -----------------
lap_counts = {num: 0 for num in VALID_RACE_NUMBERS}
last_detection_time = {num: 0 for num in VALID_RACE_NUMBERS}

# ----------------- Initialize OCR Reader -----------------
# EasyOCR will use GPU if available. If not, it falls back to CPU.
reader = easyocr.Reader(['en'], gpu=True)

# ----------------- Functions -----------------
def load_existing_data_from_sheet(sheet):
    """
    Reads the current scoreboard from the Sheet (A/B columns)
    and populates the lap_counts dictionary so we can keep
    a running total between script runs.
    
    Assumes the sheet has a header in row 1 with:
        A1: "Race Number"
        B1: "Lap Count"
    and subsequent rows contain existing race numbers and counts.
    """
    global lap_counts
    existing_data = sheet.get_all_values()  # list of lists (rows)
    # Skip header row (index 0) and parse each subsequent row
    for row in existing_data[1:]:
        if len(row) < 2:
            continue
        race_number, lap_str = row[0], row[1]
        if race_number in lap_counts:
            try:
                lap_counts[race_number] = int(lap_str)
            except ValueError:
                # If the stored value isn't a valid integer, ignore or log
                pass

def append_log_entry(runner_id, lap_count):
    """
    Appends a new log entry at the bottom of the sheet with:
    A) Existing entries
    B) New log entry
    C) Timestamp of detection
    """
    # Calculate main table rows (including header)
    main_table_rows = len(lap_counts) + 1
    log_header_row = main_table_rows + 6
    # Get existing log entries in column A from row (log_header_row+1) onward
    log_entries = sheet.col_values(1)[log_header_row:]
    next_row = log_header_row + len(log_entries) + 1
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Update log entry in columns A-C of calculated next row
    sheet.update(f'A{next_row}:C{next_row}', [[runner_id, lap_count, timestamp]])

def update_google_sheet(lap_counts):
    data = [['Race Number', 'Lap Count']]
    # Sort race numbers numerically before appending rows
    for number in sorted(lap_counts.keys(), key=int):
        data.append([number, lap_counts[number]])
    
    update_range = f'A1:B{len(data)}'
    try:
        sheet.update(update_range, data)
        # Calculate row for log header: 5 empty rows below main table
        log_header_row = len(data) + 6
        # out-comment the log header line
        # sheet.update_cell(log_header_row, 1, "Log of all entries")
        print("Google Sheet scoreboard and log header updated.")
    except Exception as e:
        print("Error updating Google Sheet scoreboard:", e)

def process_frame(frame):
    """
    Processes a video frame: runs OCR to detect text (race numbers),
    updates lap counts if a valid number is found (applying debounce),
    draws bounding boxes, and logs changes to the dashboard + Sheets.
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

                # 1) Update the scoreboard in Google Sheets
                update_google_sheet(lap_counts)
                # 2) Append a log entry for this newly detected lap
                # out-comment the log entry update
                # append_log_entry(text_clean, lap_counts[text_clean])
            
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
    cap = cv2.VideoCapture(index)
    if cap.isOpened():
        ret, _ = cap.read()
        if ret:
            print(f"Successfully connected to camera {index}")
            return True, cap
    cap.release()
    return False, None

def main():
    # 1. Load existing scoreboard data so we keep a running total
    load_existing_data_from_sheet(sheet)
    
    # 2. Try to open the camera feed, attempting multiple indices if needed
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
    
    # 3. Set camera properties
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, FPS)
    
    print("Camera configuration:")
    print(f"  Actual width:  {cap.get(cv2.CAP_PROP_FRAME_WIDTH)}")
    print(f"  Actual height: {cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}")
    print(f"  Actual FPS:    {cap.get(cv2.CAP_PROP_FPS)}")
    
    print("Starting video capture. Press 'q' to exit.")
    
    # 4. Main capture loop
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
