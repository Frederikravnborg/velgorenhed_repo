import csv
import random

file_path = 'lap_counts.csv'


def extract_race_numbers_from_log(filepath):
    """
    Loads a CSV file, finds the logging section starting with
    "Race Number,Lap Count,Timestamp", and extracts all subsequent
    Race Numbers into a list, preserving duplicates.

    Args:
        filepath (str): The path to the CSV file.

    Returns:
        list: A list of strings containing the race numbers from the log section.
              Returns an empty list if the log header is not found or
              if there are no log entries.
    """
    race_numbers_log = []
    found_log_header = False
    # Define the exact header that marks the start of the logging section
    log_header_row = ['Race Number', 'Lap Count', 'Timestamp']

    try:
        # Use 'newline=""' as recommended for the csv module
        with open(filepath, mode='r', newline='') as infile:
            reader = csv.reader(infile)
            for row in reader:
                # Skip empty rows that might exist between sections
                if not row:
                    continue

                if found_log_header:
                    # Once the header is found, start collecting race numbers (first column)
                    # Ensure the row has at least one column before accessing row[0]
                    if len(row) > 0:
                        race_numbers_log.append(row[0])
                elif row == log_header_row:
                    # Found the specific header marking the start of the log section
                    found_log_header = True

    except FileNotFoundError:
        print(f"Error: File not found at {filepath}")
        return [] # Return empty list on error
    except Exception as e:
        print(f"An error occurred while processing the file: {e}")
        return [] # Return empty list on other errors

    if not found_log_header:
        print(f"Warning: Log header '{','.join(log_header_row)}' not found in the file.")

    return race_numbers_log



# Call the function to extract the race numbers
extracted_numbers = extract_race_numbers_from_log(file_path)

# Print the resulting list
print(f"Extracted {len(extracted_numbers)} Race Numbers (duplicates kept):")

# Import random module

# Choose and print a random winner from the extracted numbers
if extracted_numbers:
    winner = random.choice(extracted_numbers)
    print(f"\nRandom Winner: {winner}")
else:
    print("\nNo race numbers to choose from")