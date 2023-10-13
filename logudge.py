import os
import re
import time
import subprocess
from collections import defaultdict
from datetime import datetime, timedelta
from iterfzf import iterfzf
import threading

# Constants
## Log pattern matches the log timestamp and is used to find the rest of the log line.
LOG_PATTERN = r"#+\s+(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (.*)"
SLEEP_INTERVAL = 60 # Sleep for a minute before checking again
CHECK_INTERVAL = 10 * 60  # Default: 10 minutes
AUDIO = True

# Get the directories from the environment variable
target_dirs = os.environ.get(
    "LOGUDGE_TARGET_DIRECTORIES", "").split(";")

# If the environment variable is not set or is empty, fall back to a default list or an empty list
TARGET_DIRECTORIES = target_dirs if target_dirs[0] else []

if not TARGET_DIRECTORIES:
    print("TARGET_DIRECTORIES not set. Please set the environment variable and try again. See README.md for more information.")
    exit(1)

def find_recent_logs(directory, threshold_time, last_log_file):
    """
    Search for recent log entries in the directory
    and return the time of the most recent log entry.
    """
    most_recent_time = None
    # logs is a default dict with a list as the default value
    logs = defaultdict(list)

    for root, _, files in os.walk(directory):
        # get .md files with modified time > threshold_time
        modified_files = [
            os.path.join(root, file_name)
            for file_name in files
            if file_name.endswith(".md")
            and os.path.getmtime(os.path.join(root, file_name))
            > threshold_time.timestamp()
        ]
        if modified_files:
            for file_name in modified_files:
                if file_name.endswith(".md"):
                    with open(os.path.join(root, file_name), "r") as f:
                        content = f.read()
                        matches = re.findall(LOG_PATTERN, content)
                        # distinguish between log time and log entry (the two matches)
                        for match in matches:
                            print(match)
                            print(type(match))
                            log_time, log_entry = match
                            log_time = datetime.strptime(log_time, "%Y-%m-%d %H:%M:%S")
                            if log_time > threshold_time:
                                logs[file_name].append((log_time, log_entry))
                                if (
                                    most_recent_time is None
                                    or log_time > most_recent_time
                                ):
                                    most_recent_time = log_time
                                    last_log_file = file_name
    return most_recent_time, logs, last_log_file


def get_input(prompt, timeout=60):
    """
    Wait for input from the user for the given number of seconds.
    """
    result = []

    def worker():
        result.append(input(prompt))

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        print("\nTime's up! Exiting.")
        thread.join()  # If the thread did not finish, wait for it to do so
        return None
    else:
        return result[0]


def main():
    start_time = datetime.now()
    print(f"Starting Lugudge timer at {start_time}")
    last_log_file = None
    while True:
        check_time = start_time + timedelta(seconds=CHECK_INTERVAL)
        now = datetime.now()

        if now >= check_time:
            # sound the alert and use a voice to announce the check
            threshold_time = now - timedelta(seconds=CHECK_INTERVAL)
            most_recent_log_time = None
            for directory in TARGET_DIRECTORIES:
                recent_log_time, logs, last_log_file = find_recent_logs(
                    directory, threshold_time, last_log_file
                )
                if recent_log_time:
                    if (
                        most_recent_log_time is None
                        or recent_log_time > most_recent_log_time
                    ):
                        most_recent_log_time = recent_log_time

            if most_recent_log_time:
                print(f"Latest log found at {most_recent_log_time}.")
                for file_name, log_entries in logs.items():
                    print(f"File: {file_name}")
                    for log_entry in log_entries:
                        print(f"  {log_entry}")
                print("Resetting timer...")
                start_time = most_recent_log_time
                print(f"Resetting Lugudge timer at {start_time}")
                if AUDIO:
                    print("\a") # sound the alert
                    subprocess.run(['say', 'Found recent log, continuing.'])
                while True:
                    user_input = get_input(
                        "Do you want to open the last log file or find a log file to add to? (y/i/x/quit): ",
                        60,
                    )

                    if user_input is None:
                        break
                    elif user_input.lower() == "y":
                        subprocess.run(["open", last_log_file])
                    elif user_input.lower() == "i":
                        selected_file = iterfzf(logs.keys())
                        subprocess.run(["open", selected_file])
                    elif user_input.lower() == "x":
                        break
                    elif user_input.lower() == "quit":
                        exit()
                    else:
                        print("Invalid input. Please enter y, i, x, or quit.")

            else:
                if AUDIO:
                    print("\a")  # sound the alert
                    subprocess.run(
                        ['say', 'No recent logs found in the last 10 minutes. Please add a new log.'])
                print(
                    f"No recent logs found in the last {CHECK_INTERVAL} seconds. Please add a new log."
                )
                try:
                    subprocess.run(["open", last_log_file])
                except TypeError:
                    print("No last_log_file found.")
                _input = input("Press enter to continue...")
                start_time = now
                print(f"Resetting Lugudge timer at {start_time}")
        time.sleep(SLEEP_INTERVAL)


if __name__ == "__main__":
    main()
