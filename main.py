# ThorCPY – Dual-screen scrcpy docking and control UI for Windows
# Copyright (C) 2026 the_swest
# Contact: Github issues
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# main.py

__version__ = "0.1.0"
__app_name__ = "ThorCPY"
__author__ = "the_swest"
__description__ = "AYN Thor screen mirroring and docking tool"

import ctypes
import os
import sys
import logging
import time

# List of required folders that must exist in order to function
REQUIRED_FOLDERS = ["bin", "config", "logs"]


def check_windows_version():
    """
    Check if running on Windows 10 and show a warning.
    Windows 11 has build number 22000 or higher.
    Shows a warning message if running on Windows 10 but allows launch.
    """
    try:
        version = sys.getwindowsversion()
        build = version.build

        # Windows 11 is build 22000+
        # Windows 10 is builds 10240-19045
        if build < 22000:
            # Show warning dialog
            try:
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()
                result = messagebox.showwarning(
                    "Windows 10 Detected - Known Issues",
                    f"WARNING: You are running Windows 10 (Build {build})\n\n"
                    f"ThorCPY has known stability issues on Windows 10.\n"
                    f"The control panel may crash when the window loses focus.\n\n"
                    f"For the best experience, please upgrade to Windows 11.\n\n"
                    f"Continue anyway?"
                )
                root.destroy()
            except:
                # Fallback to console message
                print("=" * 60)
                print("WARNING: Windows 10 Detected - Known Issues")
                print("=" * 60)
                print(f"You are running Windows 10 (Build {build})")
                print(f"")
                print(f"ThorCPY has known stability issues on Windows 10.")
                print(f"The control panel may crash when the window loses focus.")
                print(f"")
                print(f"For the best experience, please upgrade to Windows 11.")
                print("=" * 60)
                input("\nPress Enter to continue anyway...")
        else:
            print(f"✓ Windows 11 detected (Build {build})")

    except Exception as e:
        print(f"Warning: Could not verify Windows version: {e}")
        # Allow to continue if version check fails


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
    Checks Windows version, sets DPI awareness, creates the launcher instance and starts the UI.
    """

    # Check Windows version and show warning if Windows 10
    print(f"Starting {__app_name__} v{__version__}")
    print("Checking system requirements...")
    check_windows_version()

    # Run the folder check
    check_runtime_structure()

    # Sets up logging
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info(f"Starting {__app_name__} v{__version__}")
    logger.info(
        f"System: Windows {sys.getwindowsversion().major}.{sys.getwindowsversion().minor} Build {sys.getwindowsversion().build}")

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    # Import launcher after checks pass
    from src.launcher import Launcher

    # Create the main launcher object and start it
    app = Launcher()
    app.launch()


if __name__ == "__main__":
    main()