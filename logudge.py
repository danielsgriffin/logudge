import toml
import os
import re
import time
import subprocess
from collections import defaultdict
from datetime import datetime, timedelta

# Constants
## Log pattern matches the log timestamp and is used to find the rest of the log line.
LOG_PATTERN = r"#+\s+(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (.*)"
CHECK_INTERVAL = 10 * 60  # Default: 10 minutes
AUDIO = True
MONITORING_THRESHOLD = 20  # minutes


# Load the configuration file from the script's directory
config = toml.load(os.path.join(os.path.dirname(__file__), "config.toml"))

# Access the directories
TARGET_DIRECTORIES = config['directories']['target']

if not TARGET_DIRECTORIES:
    print("LOGUDGE_TARGET_DIRECTORIES not set. Please set the environment variable and try again. See README.md for more information.")
    exit(1)

def find_recent_logs(directory, threshold_time, latest_log_file, latest_match):
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
                            if match == latest_match:
                                print(f"No logs since {match[0]}.")
                            latest_match = match
                            
                            log_time, log_entry = match
                            log_time = datetime.strptime(log_time, "%Y-%m-%d %H:%M:%S")
                            if log_time > threshold_time:
                                logs[file_name].append((log_time, log_entry))
                                if (
                                    most_recent_time is None
                                    or log_time > most_recent_time
                                ):
                                    most_recent_time = log_time
                                    latest_log_file = file_name
    return most_recent_time, logs, latest_log_file, latest_match


def main():
    start_time = datetime.now()
    # print human-readable start time as hh:mm (24-hour clock)
    print(f"Starting Lugudge timer at {start_time.strftime('%H:%M')}")
    
    # Set initial values
    latest_log_file = None
    latest_match = None
    depth = 1
    monitoring_silent = False

    while True:
        check_time = start_time + timedelta(seconds=CHECK_INTERVAL)
        now = datetime.now()

        if now >= check_time:
            # sound the alert and use a voice to announce the check
            threshold_time = now - timedelta(seconds=CHECK_INTERVAL)
            most_recent_log_time = None
            for directory in TARGET_DIRECTORIES:
                recent_log_time, logs, latest_log_file, latest_match = find_recent_logs(
                    directory, threshold_time, latest_log_file, latest_match
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
                depth = 1
                monitoring_silent = False
            else:
                if monitoring_silent:
                    continue
                second_since_last_log = now - start_time
                minutes_since_last_log = int(second_since_last_log.seconds/60)
                message = f"No recent logs found in the last {minutes_since_last_log} minutes. Please add a new log."
                if minutes_since_last_log > MONITORING_THRESHOLD:
                    monitoring_silent = True
                    message = f"WARNING: {minutes_since_last_log} minutes exceeds the monitoring threshold. Monitoring will now be silent until a new log has been added."

                if AUDIO:
                    print("\a")  # sound the alert
                    subprocess.run(['say', message])
                print(message)
                try:
                    subprocess.run(["open", latest_log_file])
                    print("Opening last log file.")
                except TypeError:
                    print("No last log file found.")
                depth += 1
        next_check_span = CHECK_INTERVAL / depth
        # print that the next check is in approximitely x minutes
        print(f"Next check in about {int(next_check_span/60)} minutes.")
        time.sleep(next_check_span)


if __name__ == "__main__":
    main()
