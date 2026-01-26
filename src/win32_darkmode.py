# src/win32_darkmode.py

import ctypes
from ctypes import wintypes

# Load windows DLLs
# Desktop Window Manager API
dwmapi = ctypes.windll.dwmapi
# Windows GUI Functions
user32 = ctypes.windll.user32

# Windows 10/11 dark mode attribute ID
DWMWA_USE_IMMERSIVE_DARK_MODE = 20


def enable_dark_titlebar(hwnd):
    """
    Enables dark mode titlebar for a specfic window
    hwnd (int): Handle to the window (HWND)
    Works on windows 10 1809+ and Windows 11
    """
    try:
        # Set BOOL value to true
        value = wintypes.BOOL(True)

        # Call DwmSetWindowAttribute to apply dark mode
        dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(value),
            ctypes.sizeof(value)
        )

    except Exception as e:
        print("Dark titlebar failed:", e)
