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

# src/launcher.py
import threading
import time
import ctypes
import pygame
import os
import logging
from ctypes import wintypes

from src.scrcpy_manager import ScrcpyManager
from src.win32_dock import Win32Dock, apply_docked_style, apply_undocked_style
from src.presets import PresetStore
from src.ui_pygame import show_loading_screen, resource_path

# Setup logger for this module
logger = logging.getLogger(__name__)

# WIN32/Windows Constants
WM_CLOSE = 0x0010
WM_DESTROY = 0x0002

SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020

WS_OVERLAPPEDWINDOW = 0x00CF0000
WS_VISIBLE = 0x10000000
WS_CLIPCHILDREN = 0x02000000
WS_CLIPSIBLINGS = 0x04000000
WS_EX_CONTROLPARENT = 0x00010000

SW_HIDE = 0
SW_SHOW = 5

# Windows 11 Visuals constants
DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWA_SYSTEMBACKDROP_TYPE = 38

DWMWCP_ROUND = 2
DWMSBT_MICA = 2


# Windows 11 visual helpers
def enable_dark_titlebar(hwnd):
    """Enable dark titlebar for the given window"""
    try:
        val = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(val), ctypes.sizeof(val)
        )
        logger.debug(f"Enabled dark titlebar for window {hwnd}")
    except Exception as e:
        logger.warning(f"Failed to enable dark titlebar for window {hwnd}: {e}")


def enable_rounded_corners(hwnd):
    """Enable rounded corners for the window"""
    try:
        val = ctypes.c_int(DWMWCP_ROUND)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(val), ctypes.sizeof(val)
        )
        logger.debug(f"Enabled rounded corners for window {hwnd}")
    except Exception as e:
        logger.warning(f"Failed to enable rounded corners for window {hwnd}: {e}")


def enable_mica(hwnd):
    """Enable mica backdrop"""
    try:
        val = ctypes.c_int(DWMSBT_MICA)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_SYSTEMBACKDROP_TYPE,
            ctypes.byref(val), ctypes.sizeof(val)
        )
        logger.debug(f"Enabled mica backdrop for window {hwnd}")
    except Exception as e:
        logger.warning(f"Failed to enable mica backdrop for window {hwnd}: {e}")


# Launcher Class
class Launcher:
    """
    Main application controller for ThorCPY.
    Handles:
    - Scrcpy device management
    - Docking/undocking windows
    - UI
    - Layout saving/loading
    - Windows visual enhancements
    """

    def __init__(self):
        logger.info("Initializing Launcher")

        self.global_scale = 0.6
        logger.debug(f"Global scale set to {self.global_scale}")

        # Handles scrcpy device windows
        self.scrcpy = ScrcpyManager(scale=self.global_scale)

        # Handles docking of TF_T and TF_B
        self.dock = Win32Dock()

        self.running = False
        self.docked = True
        self.hwnd_container = None
        self._wndproc = None

        # Threading lock to prevent race condition between toggle_dock and docking_monitor
        self.dock_lock = threading.Lock()

        # Presets
        logger.debug("Loading preset store")
        self.store = PresetStore("config/layout.json")
        saved_data = self.store.load_all()

        self.tx = saved_data.get("tx", 0)
        self.ty = saved_data.get("ty", 0)
        self.bx = saved_data.get("bx", 0)
        self.by = saved_data.get("by", 0)

        logger.info(f"Loaded layout preset: TOP({self.tx}, {self.ty}), BOTTOM({self.bx}, {self.by})")

        # Windows API handles
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32

        # Define types for window procedure
        self.LRESULT = ctypes.c_longlong
        self.WPARAM = ctypes.c_ulonglong
        self.LPARAM = ctypes.c_longlong

        # Setup DefWindowProc argtypes for safety
        try:
            self.user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, self.WPARAM, self.LPARAM]
            self.user32.DefWindowProcW.restype = self.LRESULT
            logger.debug("DefWindowProc configured successfully")
        except Exception as e:
            logger.warning(f"Failed to configure DefWindowProc: {e}")

    # Layout Saving
    def save_layout(self):
        """Save the current layout to the presets"""
        try:
            logger.info(f"Saving layout: TOP({self.tx}, {self.ty}), BOTTOM({self.bx}, {self.by})")
            self.store.save_preset("Default", {
                "tx": self.tx, "ty": self.ty,
                "bx": self.bx, "by": self.by
            })
            logger.info("Layout saved successfully")
        except Exception as e:
            logger.error(f"Failed to save layout: {e}", exc_info=True)

    # Windows Procedure
    def _create_wnd_proc(self):
        """Creates a custom windows procedure for handling messages like WM_CLOSE"""
        logger.debug("Creating window procedure")
        WNDPROC = ctypes.WINFUNCTYPE(self.LRESULT, wintypes.HWND, wintypes.UINT, self.WPARAM, self.LPARAM)

        def py_wndproc(hwnd, msg, wp, lp):
            if msg in (WM_CLOSE, WM_DESTROY):
                logger.info(f"Window message received: {'WM_CLOSE' if msg == WM_CLOSE else 'WM_DESTROY'}")
                self.stop()
                return 0
            return self.user32.DefWindowProcW(hwnd, msg, wp, lp)

        return WNDPROC(py_wndproc)

    # Container Window
    def _create_container_window(self):
        """Create the main container window that hosts the docked device windows"""

        def loop():
            logger.info("Starting container window creation thread")

            # Wait for scrcpy window dimensions
            wait_count = 0
            while self.scrcpy.f_w1 == 0:
                time.sleep(0.1)
                wait_count += 1
                if not self.running:
                    logger.warning("Container window creation aborted (running=False)")
                    return
                if wait_count % 10 == 0:
                    logger.debug(f"Still waiting for scrcpy dimensions... ({wait_count / 10}s)")

            logger.info(
                f"Scrcpy dimensions ready: TOP={self.scrcpy.f_w1}x{self.scrcpy.f_h1}, BOTTOM={self.scrcpy.f_w2}x{self.scrcpy.f_h2}")

            # Define window class
            class WNDCLASSEX(ctypes.Structure):
                _fields_ = [
                    ("cbSize", wintypes.UINT),
                    ("style", wintypes.UINT),
                    ("lpfnWndProc", ctypes.c_void_p),
                    ("cbClsExtra", ctypes.c_int),
                    ("cbWndExtra", ctypes.c_int),
                    ("hInstance", wintypes.HINSTANCE),
                    ("hIcon", wintypes.HANDLE),
                    ("hCursor", wintypes.HANDLE),
                    ("hbrBackground", wintypes.HANDLE),
                    ("lpszMenuName", wintypes.LPCWSTR),
                    ("lpszClassName", wintypes.LPCWSTR),
                    ("hIconSm", wintypes.HANDLE),
                ]

            wc = WNDCLASSEX()
            wc.cbSize = ctypes.sizeof(WNDCLASSEX)
            wc.lpfnWndProc = ctypes.cast(self._wndproc, ctypes.c_void_p).value
            wc.lpszClassName = "ThorFinalBridge"

            hinst = self.kernel32.GetModuleHandleW(None)
            wc.hInstance = hinst
            wc.hbrBackground = ctypes.windll.gdi32.GetStockObject(4)

            # Load icon
            ICON_PATH = resource_path("assets/icon.ico")
            logger.debug(f"Loading icon from: {ICON_PATH}")

            try:
                hIcon = self.user32.LoadImageW(
                    None, ICON_PATH, 1, 0, 0,
                    0x00000010 | 0x00000040
                )
                wc.hIcon = hIcon
                wc.hIconSm = hIcon
                logger.debug("Icon loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load icon: {e}")

            # Register window class
            try:
                if not self.user32.RegisterClassExW(ctypes.byref(wc)):
                    logger.error("Failed to register window class")
                else:
                    logger.debug("Window class registered successfully")
            except Exception as e:
                logger.error(f"Exception during window class registration: {e}", exc_info=True)

            # Calculate client size
            client_w = max(self.scrcpy.f_w1, self.scrcpy.f_w2)
            client_h = self.scrcpy.f_h1 + self.scrcpy.f_h2
            logger.debug(f"Calculated client size: {client_w}x{client_h}")

            rect = wintypes.RECT(0, 0, int(client_w), int(client_h))
            style = WS_OVERLAPPEDWINDOW | WS_VISIBLE | WS_CLIPCHILDREN | WS_CLIPSIBLINGS
            self.user32.AdjustWindowRectEx(ctypes.byref(rect), style, False, WS_EX_CONTROLPARENT)

            # Create the window
            try:
                hwnd = self.user32.CreateWindowExW(
                    WS_EX_CONTROLPARENT,
                    "ThorFinalBridge",
                    "ThorCPY",
                    style,
                    100, 100,
                    rect.right - rect.left,
                    rect.bottom - rect.top,
                    None, 0,
                    ctypes.c_void_p(hinst),
                    None
                )

                if not hwnd:
                    logger.error("Failed to create container window (hwnd is NULL)")
                    return

                logger.info(f"Container window created successfully (hwnd={hwnd})")

                self.hwnd_container = hwnd
                self.dock.hwnd_container = hwnd

                # Apply windows 11 visual effects
                enable_dark_titlebar(hwnd)
                enable_rounded_corners(hwnd)
                enable_mica(hwnd)

                self.user32.ShowWindow(hwnd, SW_SHOW)
                logger.info("Container window shown")

            except Exception as e:
                logger.error(f"Failed to create container window: {e}", exc_info=True)
                return

            # Message loop
            logger.debug("Entering container window message loop")
            msg = wintypes.MSG()
            while self.running and self.user32.GetMessageW(ctypes.byref(msg), None, 0, 0):
                self.user32.TranslateMessage(ctypes.byref(msg))
                self.user32.DispatchMessageW(ctypes.byref(msg))

            logger.info("Container window message loop exited")

        threading.Thread(target=loop, daemon=True).start()

    # Docking Monitor
    def _docking_monitor(self):
        """
        Continuously checks for TF_T and TF_B windows to dock them inside the container
        Adjusts positions based on current layout values
        """
        logger.info("Starting docking monitor thread")

        top_docked = False
        bottom_docked = False

        while self.running:
            # Use lock to prevent race condition with toggle_dock()
            with self.dock_lock:
                if self.hwnd_container and self.docked:
                    t = self.user32.FindWindowW(None, "TF_T")
                    b = self.user32.FindWindowW(None, "TF_B")

                    # Dock top window if found
                    if t and self.user32.GetParent(t) != self.hwnd_container:
                        logger.info(f"Docking top window (hwnd={t})")
                        self.user32.SetParent(t, self.hwnd_container)
                        apply_docked_style(t)
                        self.dock.hwnd_top = t
                        top_docked = True

                    # Dock bottom window if found
                    if b and self.user32.GetParent(b) != self.hwnd_container:
                        # Initialize bottom position if unset
                        if self.bx == 0 and self.by == 0:
                            self.bx = int((self.scrcpy.f_w1 - self.scrcpy.f_w2) / 2)
                            self.by = int(self.scrcpy.f_h1)
                            logger.info(f"Initialized bottom window position: ({self.bx}, {self.by})")

                        logger.info(f"Docking bottom window (hwnd={b})")
                        self.user32.SetParent(b, self.hwnd_container)
                        apply_docked_style(b)
                        self.dock.hwnd_bottom = b
                        bottom_docked = True

                    # Log once when both windows are docked
                    if top_docked and bottom_docked:
                        logger.info("Both windows successfully docked")
                        top_docked = False
                        bottom_docked = False

            time.sleep(0.5)

        logger.info("Docking monitor thread stopped")

    # Toggle dock / undock
    def toggle_dock(self):
        """
        Switches between docked and undocked mode
        Updates window styles and visibility
        """
        if not self.dock.hwnd_top or not self.dock.hwnd_bottom:
            logger.warning("Cannot toggle dock: windows not available")
            return

        # Use lock to prevent race condition with _docking_monitor
        with self.dock_lock:
            if self.docked:
                # Undock windows
                logger.info("Undocking windows")
                self.docked = False  # Set flag FIRST to prevent monitor from re-docking

                apply_undocked_style(self.dock.hwnd_top)
                apply_undocked_style(self.dock.hwnd_bottom)
                self.user32.ShowWindow(self.hwnd_container, SW_HIDE)

                logger.info("Windows undocked successfully")
            else:
                # Dock windows
                logger.info("Docking windows")
                self.user32.ShowWindow(self.hwnd_container, SW_SHOW)
                self.user32.SetParent(self.dock.hwnd_top, self.hwnd_container)
                self.user32.SetParent(self.dock.hwnd_bottom, self.hwnd_container)
                apply_docked_style(self.dock.hwnd_top)
                apply_docked_style(self.dock.hwnd_bottom)
                self.docked = True  # Set flag LAST after docking is complete

                logger.info("Windows docked successfully")

    # Launch app
    def launch(self):
        """
        Main app launch function
        Shows loading screen, detects device and starts scrcpy, creates container window, starts docking
        monitor, launches pygame UI loop
        """
        logger.info("=" * 60)
        logger.info("ThorCPY Launch Sequence Starting")
        logger.info("=" * 60)

        self.running = True
        self._wndproc = self._create_wnd_proc()

        # Show initial loading screen
        logger.info("Displaying loading screen")
        try:
            show_loading_screen()
        except Exception as e:
            logger.error(f"Failed to show loading screen: {e}", exc_info=True)

        # Detect device and start scrcpy
        logger.info("Detecting Android device...")
        serial = self.scrcpy.detect_device()

        if serial:
            logger.info(f"Device detected: {serial}")
            try:
                logger.info("Starting scrcpy instances...")
                self.scrcpy.start_scrcpy(serial)
                logger.info("Scrcpy instances started successfully")
            except Exception as e:
                logger.error(f"Failed to start scrcpy: {e}", exc_info=True)
                self._show_error_dialog(
                    "Scrcpy Start Failed",
                    f"Could not start scrcpy:\n{str(e)}\n\nCheck logs for details."
                )
                self.stop()
                return
        else:
            logger.error("No Android device detected")
            self._show_error_dialog(
                "Device Not Found",
                "No Android device detected.\n\n"
                "Please ensure:\n"
                "• Device is connected via USB\n"
                "• USB debugging is enabled\n"
                "• ADB drivers are installed"
            )
            self.stop()
            return

        # Create the container window for docked TF_T and TF_B
        logger.info("Creating container window")
        self._create_container_window()

        # Start docking monitor in the background
        logger.info("Starting docking monitor")
        threading.Thread(target=self._docking_monitor, daemon=True).start()

        # Pygame UI
        logger.info("Initializing Pygame UI")
        from src.ui_pygame import PygameUI

        try:
            pygame.init()
            self.ui = PygameUI(self)
            clock = pygame.time.Clock()
            logger.info("Pygame UI initialized successfully")
        except Exception as e:
            logger.critical(f"Failed to initialize Pygame UI: {e}", exc_info=True)
            self.stop()
            return

        logger.info("Entering main event loop")
        frame_count = 0

        try:
            while self.running:
                # Handle Pygame events
                for ev in pygame.event.get():
                    if ev.type == pygame.QUIT:
                        logger.info("Quit event received")
                        self.stop()
                    self.ui.handle_event(ev)

                # Sync docked windows positions
                if self.dock.hwnd_top or self.dock.hwnd_bottom:
                    self.dock.sync(self.tx, self.ty, self.bx, self.by,
                                   self.scrcpy.f_w1, self.scrcpy.f_h1,
                                   self.scrcpy.f_w2, self.scrcpy.f_h2,
                                   is_docked=self.docked)

                # Render UI
                self.ui.render()
                clock.tick(60)

                # Log heartbeat every 5 minutes
                frame_count += 1
                if frame_count % (60 * 60 * 5) == 0:  # 5 minutes at 60fps
                    logger.debug(f"Main loop running (frames: {frame_count})")

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            self.stop()
        except Exception as e:
            logger.critical(f"Unexpected error in main loop: {e}", exc_info=True)
            self._show_error_dialog(
                "Critical Error",
                f"An unexpected error occurred:\n{str(e)}\n\nCheck logs for details."
            )
            self.stop()

    def _show_error_dialog(self, title, message):
        """Display error dialog to user"""
        logger.info(f"Showing error dialog: {title}")
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(title, message)
            root.destroy()
            logger.debug("Error dialog closed")
        except Exception as e:
            logger.error(f"Failed to show error dialog: {e}", exc_info=True)
            # Fallback to console
            print(f"\n{'=' * 50}")
            print(f"ERROR: {title}")
            print(f"{'=' * 50}")
            print(message)
            print(f"{'=' * 50}\n")
            input("Press Enter to exit...")

    # Stop App
    def stop(self):
        """
        Stops the launcher, saves layout, terminates scrcpy, quits pygame, closes container window and forces exit
        """
        if not self.running:
            logger.debug("Stop called but already stopped")
            return

        logger.info("=" * 60)
        logger.info("ThorCPY Shutdown Sequence Starting")
        logger.info("=" * 60)

        self.running = False

        # Save layout
        try:
            logger.info("Saving layout before shutdown")
            self.save_layout()
        except Exception as e:
            logger.error(f"Failed to save layout during shutdown: {e}", exc_info=True)

        # Kill scrcpy process
        try:
            logger.info("Terminating scrcpy processes")
            import subprocess
            result = subprocess.run(
                ["taskkill", "/F", "/IM", "scrcpy.exe", "/T"],
                capture_output=True,
                creationflags=0x08000000,
                timeout=5
            )
            if result.returncode == 0:
                logger.info("Scrcpy processes terminated successfully")
            else:
                logger.warning(f"Taskkill returned code {result.returncode}")
        except Exception as e:
            logger.error(f"Failed to terminate scrcpy: {e}", exc_info=True)

        # Quit pygame
        try:
            logger.info("Shutting down Pygame")
            pygame.quit()
        except Exception as e:
            logger.error(f"Error during pygame quit: {e}", exc_info=True)

        # Close container window
        if self.hwnd_container:
            try:
                logger.info(f"Closing container window (hwnd={self.hwnd_container})")
                self.user32.PostMessageW(self.hwnd_container, WM_CLOSE, 0, 0)
            except Exception as e:
                logger.error(f"Failed to close container window: {e}", exc_info=True)

        logger.info("ThorCPY shutdown complete")
        logger.info("=" * 60)

        os._exit(0)