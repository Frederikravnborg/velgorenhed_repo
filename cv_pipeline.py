import cv2
import easyocr
import time
import requests
import numpy as np

# ----------------- Configuration -----------------
CAMERA_INDEX = 0  # Default to built-in webcam
FRAME_WIDTH = 2048
FRAME_HEIGHT = 1536
FPS = 15

# Minimum seconds between successive detections of the same runner
# Set to 30 seconds to prevent duplicate detections during 400m laps
DEBOUNCE_SECONDS = 30

# Predefined valid race numbers (update with your actual list)
VALID_RACE_NUMBERS = {"101", "102", "103", "104", "105"}

# Dashboard endpoint (make sure the dashboard is running on this URL)
DASHBOARD_UPDATE_URL = "http://localhost:5003/update"

# ----------------- Global State -----------------
# Initialize lap counts and record of last detection times for debounce
lap_counts = {num: 0 for num in VALID_RACE_NUMBERS}
last_detection_time = {num: 0 for num in VALID_RACE_NUMBERS}

# ----------------- Initialize OCR Reader -----------------
# EasyOCR will use GPU if available. If not, it falls back to CPU.
reader = easyocr.Reader(['en'], gpu=True)

# ----------------- Functions -----------------
def send_update_to_dashboard(lap_counts):
    """
    Sends the current lap count data to the dashboard via a POST request.
    """
    try:
        response = requests.post(DASHBOARD_UPDATE_URL, json=lap_counts)
        # Optionally, check response.status_code or response.json() for confirmation
    except Exception as e:
        print("Error sending update to dashboard:", e)

def process_frame(frame):
    """
    Processes a video frame: runs OCR to detect text (race numbers),
    updates lap counts if a valid number is found (applying debounce),
    and draws bounding boxes on the frame.
    """
    global lap_counts, last_detection_time

    # For OCR accuracy, convert to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Run OCR with EasyOCR.
    # The result is a list of tuples: (bounding_box, text, confidence)
    results = reader.readtext(gray, detail=1)
    
    current_time = time.time()
    for (bbox, text, conf) in results:
        # Filter out low-confidence detections (adjust threshold as needed)
        if conf < 0.5:
            continue
        
        # Clean detected text: keep only digits
        text_clean = "".join(filter(str.isdigit, text))
        
        if text_clean in VALID_RACE_NUMBERS:
            # Apply debounce logic: count a lap only if enough time has passed
            if current_time - last_detection_time[text_clean] > DEBOUNCE_SECONDS:
                lap_counts[text_clean] += 1
                last_detection_time[text_clean] = current_time
                print(f"Lap count updated for {text_clean}: {lap_counts[text_clean]}")
                
                # Send the updated lap counts to the dashboard
                send_update_to_dashboard(lap_counts)
            
            # Draw bounding box and label around the detected race number
            pts = np.array(bbox, np.int32).reshape((-1, 1, 2))
            cv2.polylines(frame, [pts], True, (0, 255, 0), 2)
            cv2.putText(frame, text_clean, (int(bbox[0][0]), int(bbox[0][1]-10)), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    
    return frame

def try_camera_index(index):
    """
    Try to open a camera with the given index and return (success, camera) tuple
    """
    cap = cv2.VideoCapture(index)
    if cap.isOpened():
        # Try to read a frame to confirm it's working
        ret, _ = cap.read()
        if ret:
            print(f"Successfully connected to camera {index}")
            return True, cap
    cap.release()
    return False, None

def main():
    # Try to open the camera feed, attempting multiple indices if needed
    cap = None
    success = False
    
    # First try the default camera index
    success, cap = try_camera_index(CAMERA_INDEX)
    
    # If default failed, try a few more indices
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
    
    print(f"Camera configuration:")
    print(f"Actual width: {cap.get(cv2.CAP_PROP_FRAME_WIDTH)}")
    print(f"Actual height: {cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}")
    print(f"Actual FPS: {cap.get(cv2.CAP_PROP_FPS)}")
    
    print("Starting video capture. Press 'q' to exit.")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break
        
        # Process the frame: detect numbers and update lap counts
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