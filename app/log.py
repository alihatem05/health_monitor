from datetime import datetime, timezone
import os

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "health_monitor.log")

def log(category: str, message: str) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    line = f"[{timestamp}] {category} - {message}\n"
    with open(LOG_FILE, "a") as f:
        f.write(line)