import csv
import random

# Example 2: Overnight (10 PM up to, but not including, 2 AM)
start_hour = 13
end_hour = 14

# Validate hour inputs
if not (0 <= start_hour <= 23 and 0 <= end_hour <= 23):
    raise ValueError("Error: start_hour and end_hour must be between 0 and 23.")

# Path to your CSV file
file_path = 'lap_counts.csv' #<-- Make sure this file exists and has the correct format
# --- End Configuration ---


def extract_race_numbers_from_log(filepath, start_hour, end_hour):
    """
    Loads a CSV file, finds the logging section starting with
    "Race Number,Lap Count,Timestamp", filters entries based on the
    hour of the timestamp, and extracts matching Race Numbers into a
    list, preserving duplicates.

    Args:
        filepath (str): The path to the CSV file.
        start_hour (int): The starting hour of the interval (inclusive, 0-23).
        end_hour (int): The ending hour of the interval (exclusive, 0-23).
                        Interval can wrap around midnight (e.g., start=22, end=2).

    Returns:
        list: A list of strings containing the race numbers from the log section
              that fall within the specified time window.
              Returns an empty list if the log header is not found,
              if there are no log entries, or on error.
    """
    race_numbers_log = []
    found_log_header = False
    log_header_row = ['Race Number', 'Lap Count', 'Timestamp']
    processed_count = 0
    matched_count = 0

    try:
        with open(filepath, mode='r', newline='') as infile:
            reader = csv.reader(infile)
            for row_index, row in enumerate(reader):
                # Skip empty rows
                if not row:
                    continue

                if found_log_header:
                    processed_count += 1
                    # Ensure the row has the timestamp column (index 2)
                    if len(row) >= 3:
                        timestamp_str = row[2]
                        try:
                            # Extract hour directly from string (faster if format is fixed)
                            # Assumes 'YYYY-MM-DD HH:MM:SS' format
                            hour = int(timestamp_str[11:13])

                            # --- Time Window Check ---
                            in_window = False
                            if start_hour <= end_hour:
                                # Normal interval (e.g., 14 to 16)
                                # Checks if hour is start_hour or later, but strictly less than end_hour
                                if start_hour <= hour < end_hour:
                                    in_window = True
                            else:
                                # Interval crosses midnight (e.g., 22 to 2)
                                # Checks if hour is start_hour or later OR strictly less than end_hour
                                if hour >= start_hour or hour < end_hour:
                                    in_window = True
                            # --- End Time Window Check ---

                            if in_window:
                                race_numbers_log.append(row[0]) # Append Race Number (index 0)
                                matched_count += 1

                        except (IndexError, ValueError):
                            print(f"Warning: Skipping row {row_index + 1} due to invalid timestamp format: {row}")
                            continue # Skip to the next row if timestamp is bad
                        except Exception as e_inner:
                             print(f"Warning: An unexpected error occurred processing row {row_index + 1} ({row}): {e_inner}")
                             continue # Skip to the next row
                    else:
                        print(f"Warning: Skipping row {row_index + 1} due to missing columns: {row}")

                elif row == log_header_row:
                    # Found the specific header marking the start of the log section
                    found_log_header = True

    except FileNotFoundError:
        print(f"Error: File not found at {filepath}")
        return [] # Return empty list on error
    except Exception as e:
        print(f"An error occurred while opening or reading the file: {e}")
        return [] # Return empty list on other errors

    if not found_log_header:
        print(f"Warning: Log header '{','.join(log_header_row)}' not found in the file.")

    print(f"Processed {processed_count} log entries.")
    print(f"Found {matched_count} entries within the {start_hour:02d}:00 to {end_hour:02d}:00 time window.")

    return race_numbers_log


# --- Main Execution ---

with open(file_path, 'r') as f:
    pass # File exists

# Call the function to extract the race numbers within the specified time window
print(f"\nExtracting race numbers logged between {start_hour:02d}:00 (inclusive) and {end_hour:02d}:00 (exclusive)...")
extracted_numbers = extract_race_numbers_from_log(file_path, start_hour, end_hour)

# Print the count of extracted numbers
print(f"\nExtracted {len(extracted_numbers)} Race Numbers (duplicates kept) for the time window.")
# You can uncomment the line below if you want to see the list itself
# print(extracted_numbers)

# Choose and print a random winner from the filtered list
if extracted_numbers:
    winner = random.choice(extracted_numbers)
    print(f"\n---> Random Winner from this time slot: Race Number {winner} <---")
else:
    print("\nNo race numbers found in the specified time window to choose a winner from.")