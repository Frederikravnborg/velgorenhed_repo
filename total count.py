import csv
import os # To check if file exists

# Define the filename to read from
filename = '/Users/fredmac/Documents/DTU-FredMac/1Personal/Thunderstriders/velgorenhed_repo/lap_counts FINAL.csv'
# Define the target column name
target_column_name = 'Lap Count'
# Define the expected number of columns for the relevant section
expected_columns = 3

# Initialize the total lap count
total_lap_count = 0
# Variable to store the index of the target column
lap_count_index = -1

# Check if the file exists before trying to open it
if not os.path.exists(filename):
    print(f"Error: File '{filename}' not found.")
    print("Please make sure the CSV file is in the same directory as the script.")
else:
    try:
        # Open the CSV file for reading
        with open(filename, mode='r', newline='') as csvfile:
            # Create a CSV reader object
            reader = csv.reader(csvfile)
            # Counter for rows
            row_count = 0
            # Variable to store rows
            rows = []

            # Read first 106 rows
            for row in reader:
                if row_count < 106:
                    rows.append(row)
                    row_count += 1
                else:
                    break

            # Reset reader to start with these rows
            reader = iter(rows)
            try:
                # Read the first header row to find the column index
                header = next(reader)
                print(f"Processing header: {header}")
                try:
                    # Find the index of the 'Lap Count' column
                    lap_count_index = header.index(target_column_name)
                except ValueError:
                    print(f"Error: Column '{target_column_name}' not found in header.")
                    lap_count_index = -1 # Ensure we don't proceed if column not found

            except StopIteration:
                print("Error: CSV file is empty.")
                header = None # Indicate header was not read

            # Proceed only if the header was read and the target column was found
            if header and lap_count_index != -1:
                # Iterate over each subsequent row in the CSV data
                for i, row in enumerate(reader):
                    # Check if the row has the expected number of columns for the relevant data section
                    if len(row) == expected_columns:
                        try:
                            # Get the value from the 'Lap Count' column using the found index
                            lap_count_str = row[lap_count_index]
                            # Attempt to convert the lap count to an integer and add to the total
                            total_lap_count += int(lap_count_str.strip()) # Use strip() to handle potential whitespace
                        except ValueError:
                            # Handle rows where the lap count is not a valid integer
                            # This also helps skip rows from the second section if 'Lap Count' isn't purely numeric there
                            print(f"Skipping row {i+2} (line number): Non-integer value in '{target_column_name}' column - {row}")
                        except IndexError:
                            # This shouldn't happen if len(row) == expected_columns, but good practice
                            print(f"Skipping row {i+2} (line number): Malformed row (IndexError) - {row}")
                        except Exception as e:
                            # Handle any other unexpected errors for this row
                            print(f"Skipping row {i+2} (line number) due to unexpected error: {row} - Error: {e}")
                    else:
                        # Skip rows that don't have the expected number of columns
                        # This helps ignore the second section (logging part) or other malformed lines
                        print(f"Skipping row {i+2} (line number): Unexpected number of columns ({len(row)} instead of {expected_columns}) - {row}")
                        # Optional: You could uncomment the 'break' below if you know the first section
                        # always comes before the second section and you want to stop processing entirely
                        # when the format changes.
                        # break

                # Print the final sum after processing the file
                print(f"\nTotal Lap Count from '{target_column_name}' column: {total_lap_count}")

    except FileNotFoundError:
        # This case is technically covered by the os.path.exists check, but included for completeness
        print(f"Error: File '{filename}' not found.")
    except Exception as e:
        # Handle potential errors during file opening or reading
        print(f"An error occurred: {e}")
