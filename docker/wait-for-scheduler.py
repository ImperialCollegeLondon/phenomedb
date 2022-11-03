import os, sys
if os.environ['PHENOMEDB_PATH'] not in sys.path:
   sys.path.append(os.environ['PHENOMEDB_PATH'])
import time

def check_if_scheduler_ready():

    if os.path.exists('/opt/system/scheduler_ready'):
        return True
    else:
        time.sleep(5)
        return check_if_scheduler_ready()

if __name__ == "__main__":
    print("Running wait-for-scheduler.py...")
    ready = check_if_scheduler_ready()
    print("...Scheduler ready!")



