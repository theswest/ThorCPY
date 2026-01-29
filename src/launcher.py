# ThorCPY – Dual-screen scrcpy docking and control UI for Windows
# Copyright (C) 2026 the_swest
# Contact: Github issues

import threading
import time
import ctypes
import pygame
import os
import logging
from ctypes import wintypes

from src.scrcpy_manager import ScrcpyManager
from src.win32_dock import Win32Dock, apply_docked_style
from src.presets import PresetStore
from src.config import ConfigManager
from src.ui_pygame import show_loading_screen

logger = logging.getLogger(__name__)

DEFAULT_LAYOUT = {"tx": 0, "ty": 0, "bx": 0, "by": 0, "global_scale": 0.6}

# Win32 Constants
WM_CLOSE = 0x0010
WM_DESTROY = 0x0002
WS_OVERLAPPEDWINDOW = 0x00CF0000
WS_VISIBLE = 0x10000000
WS_CLIPCHILDREN = 0x02000000
WS_CLIPSIBLINGS = 0x04000000
WS_EX_CONTROLPARENT = 0x00010000
SW_HIDE = 0
SW_SHOW = 5


class Launcher:
    def __init__(self):
        logger.info("Initializing Launcher with Forced Default Layout")
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32

        # 1. Load Managers
        self.store = PresetStore("config/layout.json")
        self.config = ConfigManager("config/config.json")

        # 2. PERSIST SCALE: Load scale from config, fall back to default if missing
        self.global_scale = self.config.get(
            "global_scale", DEFAULT_LAYOUT["global_scale"]
        )
        self.launch_scale = self.global_scale

        # 3. Initialize Scrcpy with the saved scale
        self.scrcpy = ScrcpyManager(scale=self.launch_scale)

        # 4. FORCED LAYOUT LOGIC (Ignoring saved tx/ty/bx/by)
        # We use the scaled dimensions from ScrcpyManager (usually 1080x1920 base)
        w1, h1 = self.scrcpy.f_w1, self.scrcpy.f_h1
        w2, h2 = self.scrcpy.f_w2, self.scrcpy.f_h2

        # Top screen is always at 0,0
        self.tx = 0
        self.ty = 0

        # Bottom screen Y is directly below Top screen
        self.by = int(h1)

        # Bottom screen X is centered relative to Top screen
        # Math: (TopWidth / 2) - (BottomWidth / 2)
        self.bx = int((w1 / 2) - (w2 / 2))

        logger.info(
            f"Layout Reset: Top(0,0), Bottom({self.bx}, {self.by}) at Scale {self.global_scale}"
        )

        self.dock = Win32Dock()
        self.running = False
        self.docked = True
        self.hwnd_container = None
        self._wndproc = None
        self.dock_lock = threading.Lock()

        # Win32 Type Setup
        self.LRESULT = ctypes.c_longlong
        self.WPARAM = ctypes.c_ulonglong
        self.LPARAM = ctypes.c_longlong
        try:
            self.user32.DefWindowProcW.argtypes = [
                wintypes.HWND,
                wintypes.UINT,
                self.WPARAM,
                self.LPARAM,
            ]
            self.user32.DefWindowProcW.restype = self.LRESULT
        except:
            pass

    def save_layout(self):
        """Saves current state, specifically ensuring global_scale is updated"""
        try:
            self.config.set("tx", self.tx)
            self.config.set("ty", self.ty)
            self.config.set("bx", self.bx)
            self.config.set("by", self.by)
            self.config.set("global_scale", self.global_scale)
            logger.info(f"Saved configuration (Scale: {self.global_scale})")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")

    def save_scale(self):
        """Utility for ui_pygame to trigger a scale-only save"""
        self.config.set("global_scale", self.global_scale)

    def _create_wnd_proc(self):
        WNDPROC = ctypes.WINFUNCTYPE(
            self.LRESULT, wintypes.HWND, wintypes.UINT, self.WPARAM, self.LPARAM
        )

        def py_wndproc(hwnd, msg, wp, lp):
            if msg in (WM_CLOSE, WM_DESTROY):
                self.stop()
                return 0
            return self.user32.DefWindowProcW(hwnd, msg, wp, lp)

        return WNDPROC(py_wndproc)

    def _create_container_window(self):
        def loop():
            while self.scrcpy.f_w1 == 0:
                time.sleep(0.1)
                if not self.running:
                    return

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

            self.user32.RegisterClassExW(ctypes.byref(wc))

            # Calculate container size to fit both stacked windows
            client_w = max(self.scrcpy.f_w1, self.scrcpy.f_w2 + abs(self.bx))
            client_h = self.scrcpy.f_h1 + self.scrcpy.f_h2

            rect = wintypes.RECT(0, 0, int(client_w), int(client_h))
            style = WS_OVERLAPPEDWINDOW | WS_VISIBLE | WS_CLIPCHILDREN | WS_CLIPSIBLINGS
            self.user32.AdjustWindowRectEx(
                ctypes.byref(rect), style, False, WS_EX_CONTROLPARENT
            )

            hwnd = self.user32.CreateWindowExW(
                WS_EX_CONTROLPARENT,
                "ThorFinalBridge",
                "ThorCPY",
                style,
                100,
                100,
                rect.right - rect.left,
                rect.bottom - rect.top,
                None,
                0,
                ctypes.c_void_p(hinst),
                None,
            )

            if hwnd:
                self.hwnd_container = hwnd
                self.dock.hwnd_container = hwnd
                self.user32.ShowWindow(hwnd, SW_SHOW)

            msg = wintypes.MSG()
            while self.running and self.user32.GetMessageW(
                ctypes.byref(msg), None, 0, 0
            ):
                self.user32.TranslateMessage(ctypes.byref(msg))
                self.user32.DispatchMessageW(ctypes.byref(msg))

        threading.Thread(target=loop, daemon=True).start()

    def _docking_monitor(self):
        while self.running:
            with self.dock_lock:
                if self.hwnd_container and self.docked:
                    t = self.user32.FindWindowW(None, "TF_T")
                    b = self.user32.FindWindowW(None, "TF_B")
                    if t and self.user32.GetParent(t) != self.hwnd_container:
                        self.user32.SetParent(t, self.hwnd_container)
                        apply_docked_style(t)
                        self.dock.hwnd_top = t
                    if b and self.user32.GetParent(b) != self.hwnd_container:
                        self.user32.SetParent(b, self.hwnd_container)
                        apply_docked_style(b)
                        self.dock.hwnd_bottom = b
            time.sleep(0.5)

    def launch(self):
        self.running = True
        self._wndproc = self._create_wnd_proc()
        show_loading_screen()

        serial = self.scrcpy.detect_device()
        if serial:
            self.scrcpy.start_scrcpy(serial)
        else:
            self.stop()
            return

        self._create_container_window()
        threading.Thread(target=self._docking_monitor, daemon=True).start()

        from src.ui_pygame import PygameUI

        pygame.init()
        self.ui = PygameUI(self)
        clock = pygame.time.Clock()

        while self.running:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.stop()
                self.ui.handle_event(ev)

            # Continuous sync using our forced BX/BY values
            if self.dock.hwnd_top or self.dock.hwnd_bottom:
                self.dock.sync(
                    self.tx,
                    self.ty,
                    self.bx,
                    self.by,
                    self.scrcpy.f_w1,
                    self.scrcpy.f_h1,
                    self.scrcpy.f_w2,
                    self.scrcpy.f_h2,
                    is_docked=self.docked,
                )
            self.ui.render()
            clock.tick(60)

    def stop(self):
        if not self.running:
            return
        self.running = False
        self.save_layout()
        import subprocess

        subprocess.run(
            ["taskkill", "/F", "/IM", "scrcpy.exe", "/T"],
            capture_output=True,
            creationflags=0x08000000,
        )
        pygame.quit()
        if self.hwnd_container:
            self.user32.PostMessageW(self.hwnd_container, WM_CLOSE, 0, 0)
        os._exit(0)
