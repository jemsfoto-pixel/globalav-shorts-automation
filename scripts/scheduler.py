"""
Local Scheduler for YouTube Shorts Automation
Executes the main pipeline at regular intervals.
"""

import time
import subprocess
import os
import sys
from datetime import datetime, timedelta

# Interval in hours
INTERVAL_HOURS = 6

def run_pipeline():
    print(f"\n{'-'*60}")
    print(f"🚀 Starting scheduled execution: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'-'*60}\n")
    
    # Force upload for scheduled runs
    os.environ["YOUTUBE_UPLOAD_ENABLED"] = "true"
    
    try:
        # Run main.py using the same python interpreter
        result = subprocess.run(
            [sys.executable, "scripts/main.py"],
            capture_output=False,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            print(f"\n✅ Execution completed successfully.")
        else:
            print(f"\n❌ Execution failed with return code: {result.returncode}")
            
    except Exception as e:
        print(f"\n❌ Scheduler error: {e}")

def main():
    print("=" * 60)
    print("🎬 YouTube Shorts local scheduler started")
    print(f"🕒 Interval: {INTERVAL_HOURS} hours")
    print("=" * 60)
    
    # Run once immediately
    run_pipeline()
    
    while True:
        next_run = datetime.now() + timedelta(hours=INTERVAL_HOURS)
        print(f"\n⏳ Next run scheduled for: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Wait for the next interval (check every minute)
        while datetime.now() < next_run:
            time.sleep(60)
            
        run_pipeline()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Scheduler stopped by user.")
        sys.exit(0)
