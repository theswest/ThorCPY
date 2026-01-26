# main.py

__version__ = "0.0.1"
__app_name__ = "ThorCPY"
__author__ = "the_swest"
__description__ = "AYN Thor screen mirroring and docking tool"

import ctypes
import os
import sys
import logging
import time
from src.launcher import Launcher

# List of required folders that must exist in order to function
REQUIRED_FOLDERS = ["bin", "config", "logs"]

def check_runtime_structure():
    """
    Checks that all required folders exist in the application directory.
    Works for Python files and PyInstaller
    If any folder is missing, prints an error message and exits.
    """
    # Determine the base folder (sys.executable if PyInstaller, directory if script)
    base = os.path.dirname(sys.executable if hasattr(sys, "_MEIPASS") else __file__)

    # Check for missing folders
    missing = [f for f in REQUIRED_FOLDERS if not os.path.isdir(os.path.join(base, f))]
    if missing:
        print(f"ERROR: Missing required folders: {missing}")
        print("ThorCPY must be placed in a folder containing bin/, config/, logs/")
        input("Press Enter to exit...")
        sys.exit(1)

# Run the folder check before launch
check_runtime_structure()


def setup_logging():
    """
    Configure application-wide logging
    """
    log_dir = os.path.join(
        os.path.dirname(sys.executable if hasattr(sys, "_MEIPASS") else __file__),
        "logs"
    )
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, f"thorcpy_{time.strftime('%Y%m%d')}.log")

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )


def main():
    """
    Main entry point for the application
    Sets DPI awareness, creates the launcher instance and starts the UI.
    """

    # Sets up logging
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info(f"Starting {__app_name__} v{__version__}")

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    # Create the main launcher object and start it
    app = Launcher()
    app.launch()

if __name__ == "__main__":
    main()
