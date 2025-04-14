import csv
from datetime import datetime
import os

SUMMARY_FILE = "lap_summary.csv"
LOG_FILE = "lap_log.csv"

def initialize_summary_file():
    """Create a summary CSV with runners 1 to 100 and 0 laps if it doesn't exist."""
    if not os.path.exists(SUMMARY_FILE):
        with open(SUMMARY_FILE, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["Runner", "Total Laps"])
            for i in range(1, 101):
                writer.writerow([i, 0])

def update_summary(runner_number):
    """Update lap count for a specific runner in the summary CSV."""
    rows = []
    updated = False
    
    with open(SUMMARY_FILE, mode="r", newline="") as file:
        reader = csv.reader(file)
        rows = list(reader)
    
    for i in range(1, len(rows)):  # skip header
        if rows[i][0] == str(runner_number):
            current_laps = int(rows[i][1])
            rows[i][1] = str(current_laps + 1)
            updated = True
            break
    
    if updated:
        with open(SUMMARY_FILE, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerows(rows)

def log_lap(runner_number):
    """Append a new lap log entry with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([runner_number, timestamp])
    return timestamp

def log_lap_run():
    initialize_summary_file()
    print("Enter runner number (1-100). Type 'q' to quit.")
    
    while True:
        user_input = input("Runner number: ")
        
        if user_input.lower() == 'q':
            print("Logging complete. Goodbye!")
            break
        
        try:
            runner = int(user_input)
            if 1 <= runner <= 100:
                update_summary(runner)
                timestamp = log_lap(runner)
                print(f"Runner {runner} logged a lap at {timestamp}.")
            else:
                print("Please enter a number between 1 and 100.")
        except ValueError:
            print("Invalid input. Please enter a number or 'q' to quit.")

log_lap_run()
