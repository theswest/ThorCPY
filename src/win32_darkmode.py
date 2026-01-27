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
    Works on windows 10 1809+ and Windows 11
    Args:
        hwnd: int, Handle to the window (HWND)
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
