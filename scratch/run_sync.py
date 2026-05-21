import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from main import run_m0_sync_process

def main():
    print("Starting Lead Assigner Sync Process...")
    try:
        count = run_m0_sync_process()
        print(f"Sync process finished. Total assigned leads: {count}")
    except Exception as e:
        print(f"Error during sync process: {e}")

if __name__ == "__main__":
    main()
