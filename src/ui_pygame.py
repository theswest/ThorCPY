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

# src/ui_pygame.py
import pygame
import os
import tkinter as tk
import time
import logging
from ctypes import windll, byref, wintypes
import sys
from src.win32_darkmode import enable_dark_titlebar

# Setup logger for this module
logger = logging.getLogger(__name__)

# Clipboard and GDI Constants
CF_BITMAP = 2  # Clipboard format for bitmap images
SRCCOPY = 0x00CC0020  # BitBlt copy mode (straight pixel copy)


# Returns the absolute path for PyInstaller or python run
def resource_path(rel):
    """
    Get absolute path to resource, works for dev and for PyInstaller

    Args:
        rel: Relative path to resource

    Returns:
        Absolute path to resource
    """
    try:
        if hasattr(sys, "_MEIPASS"):
            path = os.path.join(sys._MEIPASS, rel)
            logger.debug(f"Resource path (PyInstaller): {path}")
            return path
        path = os.path.join(os.path.abspath("."), rel)
        logger.debug(f"Resource path (dev): {path}")
        return path
    except Exception as e:
        logger.error(f"Failed to resolve resource path for '{rel}': {e}")
        return rel


# Hex to RGB conversion to allow hex code usage
def hex_to_rgb(hex_color):
    """
    Convert hex color to RGB tuple

    Args:
        hex_color: Hex string (e.g., "#FF0000" or "FF0000") or int (0xFF0000)

    Returns:
        tuple: (r, g, b)
    """
    try:
        if isinstance(hex_color, int):
            hex_color = f"{hex_color:06x}"

        if isinstance(hex_color, str):
            hex_color = hex_color.lstrip("#")

        rgb = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
        return rgb
    except Exception as e:
        logger.error(f"Failed to convert hex color '{hex_color}': {e}")
        return (255, 255, 255)  # Default to white


# Font path
FONT_PATH = resource_path("assets/fonts/CalSans-Regular.ttf")
ICON_PATH = resource_path("assets/icon.png")


# Loading Screen Manager
def show_loading_screen():
    """
    Shows a small startup screen for about 2 seconds.
    """
    logger.info("Initializing loading screen")

    try:
        pygame.init()
    except Exception as e:
        logger.error(f"Failed to initialize pygame for loading screen: {e}")
        return

    # Load an icon
    try:
        icon_surface = pygame.image.load(ICON_PATH)
        pygame.display.set_icon(icon_surface)
        logger.debug("Loading screen icon set successfully")
    except Exception as e:
        logger.warning(f"Failed to load icon for loading screen: {e}")

    # Initialize window
    try:
        screen = pygame.display.set_mode((400, 200))
        pygame.display.set_caption("ThorCPY Loading...")
        logger.debug("Loading screen window created")
    except Exception as e:
        logger.error(f"Failed to create loading screen window: {e}")
        return

    # Enable the dark titlebar for the window
    try:
        info = pygame.display.get_wm_info()
        hwnd = info.get("window")
        if hwnd:
            enable_dark_titlebar(hwnd)
            logger.debug("Loading screen dark titlebar enabled")
    except Exception as e:
        logger.warning(f"Failed to enable dark titlebar for loading screen: {e}")

    # Setup font and clock
    try:
        font = pygame.font.Font(FONT_PATH, 36)
        logger.debug("Loading screen font loaded")
    except Exception as e:
        logger.warning(f"Failed to load custom font, using default: {e}")
        font = pygame.font.SysFont("Arial", 36)

    clock = pygame.time.Clock()

    # 2s at 60fps
    logger.debug("Starting loading screen animation (120 frames)")
    for i in range(120):
        try:
            screen.fill((18, 20, 24))
            txt = font.render("Starting ThorCPY...", True, (200, 200, 200))
            screen.blit(txt, (60, 80))
            pygame.display.flip()
            clock.tick(60)
        except Exception as e:
            logger.error(f"Error during loading screen render at frame {i}: {e}")
            break

    # Close window
    try:
        pygame.display.quit()
        logger.info("Loading screen closed")
    except Exception as e:
        logger.warning(f"Error closing loading screen: {e}")


# Main Pygame UI class
class PygameUI:
    """
    Main controller UI
    Renders the control panel and manages user interaction
    """

    def __init__(self, launcher):
        logger.info("Initializing PygameUI")

        # Reference to the main launcher and controller object
        self.l = launcher

        try:
            pygame.init()
            logger.debug("Pygame initialized for UI")
        except Exception as e:
            logger.error(f"Failed to initialize pygame: {e}")
            raise

        # Load Icon
        try:
            icon_surface = pygame.image.load(ICON_PATH)
            pygame.display.set_icon(icon_surface)
            logger.debug("UI window icon set successfully")
        except Exception as e:
            logger.warning(f"Failed to load UI icon: {e}")

        # Position the UI on the far right of the screen
        try:
            root = tk.Tk()
            sw = root.winfo_screenwidth()
            root.destroy()
            x_pos = sw - 460
            os.environ['SDL_VIDEO_WINDOW_POS'] = f"{x_pos},50"
            logger.debug(f"UI window position set to ({x_pos}, 50)")
        except Exception as e:
            logger.warning(f"Failed to position UI window: {e}")

        # Create UI window
        try:
            self.screen = pygame.display.set_mode((450, 900))
            pygame.display.set_caption("ThorCPY Control Panel")
            logger.debug("UI window created successfully")
        except Exception as e:
            logger.error(f"Failed to create UI window: {e}")
            raise

        # Enable the dark titlebar for the window
        try:
            info = pygame.display.get_wm_info()
            hwnd = info.get("window")
            if hwnd:
                enable_dark_titlebar(hwnd)
                logger.debug("UI window dark titlebar enabled")
        except Exception as e:
            logger.warning(f"Failed to enable dark titlebar for UI window: {e}")

        # Load font
        try:
            self.font_lg = pygame.font.Font(FONT_PATH, 24)
            self.font_md = pygame.font.Font(FONT_PATH, 16)
            self.font_sm = pygame.font.Font(FONT_PATH, 14)
            logger.debug("UI fonts loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load custom fonts, using default: {e}")
            self.font_lg = pygame.font.SysFont("Arial", 24)
            self.font_md = pygame.font.SysFont("Arial", 16)
            self.font_sm = pygame.font.SysFont("Arial", 14)

        # Color Palette
        self.colors = {
            "bg": hex_to_rgb("#121418"),
            "panel": hex_to_rgb("#1e2128"),
            "border": hex_to_rgb("#2d3139"),
            "text": hex_to_rgb("#c8cdd8"),
            "accent": hex_to_rgb("#4a90e2"),
            "top": hex_to_rgb("#e74c3c"),
            "bot": hex_to_rgb("#3498db"),
            "success": hex_to_rgb("#2ecc71"),
            "danger": hex_to_rgb("#e74c3c"),
            "warning": hex_to_rgb("#f39c12")
        }

        # Slider interaction
        self.dragging = None  # Currently dragged slider
        self.m_locked = False  # If mouse has been released
        self.pressed_button = None  # Track which button was pressed

        # Status message
        self.status_msg = ""
        self.status_time = 0
        self.status_duration = 2.0
        self.status_type = "info"

        # Preset input
        self.preset_name = "NewPreset"
        self.active_input = False

        # Slider input
        self.active_slider_input = None
        self.input_buffer = ""

        # Cached presets (only reload when invalidated)
        self._preset_cache = None
        self._preset_cache_time = 0

        # Track scale changes
        self._scale_changed = False
        self._original_scale = self.l.global_scale

        logger.info("PygameUI initialization complete")

    def invalidate_preset_cache(self):
        """Invalidate the preset cache to force reload on next access"""
        self._preset_cache = None
        logger.debug("Preset cache invalidated")

    def get_presets(self):
        """Get presets with caching to avoid repeated file I/O"""
        current_time = time.time()

        # Cache for 0.5 seconds or until invalidated
        if self._preset_cache is None or (current_time - self._preset_cache_time) > 0.5:
            self._preset_cache = self.l.store.load_all()
            self._preset_cache_time = current_time
            logger.debug(f"Preset cache refreshed with {len(self._preset_cache)} presets")

        return self._preset_cache

    def show_status(self, msg, status_type="info", duration=2.0):
        """
        Display a status message

        Args:
            msg: Message to display
            status_type: Type of message (info, success, error, warning)
            duration: How long to show the message in seconds
        """
        logger.debug(f"Showing status: [{status_type}] {msg}")
        self.status_msg = msg
        self.status_type = status_type
        self.status_time = time.time()
        self.status_duration = duration

    def take_screenshot(self):
        """
        Takes a screenshot of both windows and copies it to the clipboard
        """
        logger.info("Taking screenshot of docked windows")
        user32 = windll.user32
        gdi32 = windll.gdi32

        try:
            if not self.l.hwnd_container or not self.l.docked:
                logger.warning("Screenshot aborted: container not available or not docked")
                self.show_status("Must be docked to screenshot", "warning")
                return

            # Get container window area
            rect = wintypes.RECT()
            if not user32.GetClientRect(self.l.hwnd_container, byref(rect)):
                logger.error("Failed to get container client rect")
                self.show_status("Screenshot failed", "error")
                return

            w = rect.right - rect.left
            h = rect.bottom - rect.top
            logger.debug(f"Container dimensions: {w}x{h}")

            # Get Device Context (DC) handles
            hwnd_dc = user32.GetDC(self.l.hwnd_container)
            if not hwnd_dc:
                logger.error("Failed to get container DC")
                self.show_status("Screenshot failed", "error")
                return

            mem_dc = gdi32.CreateCompatibleDC(hwnd_dc)
            if not mem_dc:
                logger.error("Failed to create compatible DC")
                user32.ReleaseDC(self.l.hwnd_container, hwnd_dc)
                self.show_status("Screenshot failed", "error")
                return

            bitmap = gdi32.CreateCompatibleBitmap(hwnd_dc, w, h)
            if not bitmap:
                logger.error("Failed to create compatible bitmap")
                gdi32.DeleteDC(mem_dc)
                user32.ReleaseDC(self.l.hwnd_container, hwnd_dc)
                self.show_status("Screenshot failed", "error")
                return

            # Select bitmap into memory DC
            old_bitmap = gdi32.SelectObject(mem_dc, bitmap)

            # Copy pixels from window to bitmap
            success = gdi32.BitBlt(mem_dc, 0, 0, w, h, hwnd_dc, 0, 0, SRCCOPY)

            if not success:
                logger.error("BitBlt failed during screenshot")
                self.show_status("Screenshot failed", "error")
            else:
                # Copy to clipboard
                user32.OpenClipboard(0)
                user32.EmptyClipboard()
                user32.SetClipboardData(CF_BITMAP, bitmap)
                user32.CloseClipboard()
                logger.info("Screenshot copied to clipboard successfully")
                self.show_status("Screenshot copied to clipboard", "success")

            # Cleanup
            gdi32.SelectObject(mem_dc, old_bitmap)
            gdi32.DeleteObject(bitmap)
            gdi32.DeleteDC(mem_dc)
            user32.ReleaseDC(self.l.hwnd_container, hwnd_dc)

        except Exception as e:
            logger.error(f"Screenshot error: {e}", exc_info=True)
            self.show_status("Screenshot failed", "error")

    def draw_slider(self, label, y_pos, val, min_val, max_val, color, attr_name):
        """
        Draw a slider control with editable value box

        Args:
            label: Label text for the slider
            y_pos: Y position to draw at
            val: Current value
            min_val: Minimum value
            max_val: Maximum value
            color: Color for the slider
            attr_name: Attribute name (tx, ty, bx, by) for keyboard input
        """
        try:
            mx, my = pygame.mouse.get_pos()
            m_click = pygame.mouse.get_pressed()[0]

            # Label
            self.screen.blit(self.font_md.render(label, True, self.colors["text"]), (40, y_pos))

            # Value Box (right-aligned, clickable for keyboard input)
            val_box = pygame.Rect(350, y_pos, 60, 25)
            box_hover = val_box.collidepoint(mx, my)
            box_active = (self.active_slider_input == attr_name)

            box_color = self.colors["accent"] if box_active else (
                self.colors["border"] if box_hover else self.colors["panel"])
            pygame.draw.rect(self.screen, box_color, val_box, border_radius=3)

            # Format value based on slider type
            if box_active:
                val_text = self.input_buffer
            elif attr_name == "global_scale":
                val_text = f"{val:.2f}"
            else:
                val_text = str(int(val))

            val_render = self.font_sm.render(val_text, True, self.colors["text"])
            val_rect = val_render.get_rect(center=val_box.center)
            self.screen.blit(val_render, val_rect)

            # Activate input box on click
            if m_click and box_hover and not self.m_locked:
                if not box_active:
                    self.active_slider_input = attr_name
                    if attr_name == "global_scale":
                        self.input_buffer = f"{val:.2f}"
                    else:
                        self.input_buffer = str(int(val))
                    self.active_input = False
                    logger.debug(f"Activated slider input for {attr_name}")
                self.m_locked = True

            # Slider Track
            track_y = y_pos + 30
            track_rect = pygame.Rect(40, track_y, 370, 4)
            pygame.draw.rect(self.screen, self.colors["border"], track_rect, border_radius=2)

            # Slider Handle
            norm_val = (val - min_val) / (max_val - min_val) if max_val != min_val else 0.5
            handle_x = 40 + int(norm_val * 370)
            handle_rect = pygame.Rect(handle_x - 8, track_y - 6, 16, 16)
            handle_hover = handle_rect.collidepoint(mx, my)

            handle_color = self.colors["text"] if handle_hover or self.dragging == attr_name else color
            pygame.draw.circle(self.screen, handle_color, (handle_x, track_y + 2), 8)

            # Drag interaction
            if m_click and handle_hover and not self.m_locked and not self.dragging:
                self.dragging = attr_name
                logger.debug(f"Started dragging slider: {attr_name}")

            if self.dragging == attr_name and m_click:
                new_norm = max(0.0, min(1.0, (mx - 40) / 370))
                new_val = min_val + new_norm * (max_val - min_val)
                setattr(self.l, attr_name, new_val)

                # Track if global_scale changed
                if attr_name == "global_scale" and abs(new_val - self._original_scale) > 0.01:
                    self._scale_changed = True

            if not m_click and self.dragging == attr_name:
                logger.debug(f"Stopped dragging slider: {attr_name}")
                # Save scale separately when scale slider released
                if attr_name == "global_scale":
                    self.l.save_scale()
                else:
                    self.l.save_layout()
                self.dragging = None

        except Exception as e:
            logger.error(f"Error drawing slider '{label}': {e}", exc_info=True)

    def render(self):
        """
        Main render loop for the UI
        """
        try:
            mx, my = pygame.mouse.get_pos()
            m_click = pygame.mouse.get_pressed()[0]

            self.screen.fill(self.colors["bg"])

            # Title
            title_txt = self.font_lg.render("ThorCPY Control Panel", True, self.colors["text"])
            self.screen.blit(title_txt, (20, 20))

            pygame.draw.line(self.screen, self.colors["border"], (20, 60), (430, 60))

            # Layout controls header
            self.screen.blit(self.font_lg.render("Layout Controls", True, self.colors["text"]), (20, 80))

            # Global Scale Slider
            scale_label = f"GLOBAL SCALE (restart required) - Active: {self.l.launch_scale:.2f}"
            self.draw_slider(scale_label, 120, self.l.global_scale, 0.3, 1.0, self.colors["accent"], "global_scale")

            # Restart notice for scale changes
            if hasattr(self, '_scale_changed') and self._scale_changed:
                restart_txt = self.font_sm.render("Restart ThorCPY to apply scale", True, self.colors["warning"])
                self.screen.blit(restart_txt, (40, 165))

            # Sliders
            self.draw_slider("TOP X", 190, self.l.tx, -500, 1500, self.colors["top"], "tx")
            self.draw_slider("TOP Y", 250, self.l.ty, -500, 1500, self.colors["top"], "ty")
            self.draw_slider("BOTTOM X", 310, self.l.bx, -500, 1500, self.colors["bot"], "bx")
            self.draw_slider("BOTTOM Y", 370, self.l.by, -500, 1500, self.colors["bot"], "by")

            # Undock/Dock Button
            undock_btn = pygame.Rect(40, 420, 180, 40)
            u_hover = undock_btn.collidepoint(mx, my)
            btn_text = "DOCK  WINDOWS" if not self.l.docked else "UNDOCK  WINDOWS"

            btn_color = self.colors["panel"]
            text_color = self.colors["text"]

            pygame.draw.rect(self.screen, btn_color, undock_btn, border_radius=5)
            utxt = self.font_md.render(btn_text, True, text_color)
            text_rect = utxt.get_rect(center=undock_btn.center)
            self.screen.blit(utxt, text_rect)

            # Dock button logic
            if m_click and u_hover and not self.m_locked and not self.dragging:
                self.pressed_button = "dock"

            if not m_click and self.pressed_button == "dock":
                if u_hover:
                    logger.info("Dock toggle button clicked")
                    self.l.toggle_dock()
                self.pressed_button = None

            # Screenshot Button
            shot_btn = pygame.Rect(230, 420, 180, 40)
            s_hover = shot_btn.collidepoint(mx, my)

            if self.l.docked:
                s_color = self.colors["panel"] if not s_hover else self.colors["border"]
                s_text_color = self.colors["text"]
                s_label = "SCREENSHOT"
            else:
                s_color = (45, 48, 56)
                s_text_color = (100, 105, 115)
                s_label = "LOCKED (UNDOCKED)"

            pygame.draw.rect(self.screen, s_color, shot_btn, border_radius=5)
            stxt = self.font_md.render(s_label, True, s_text_color)
            stxt_rect = stxt.get_rect(center=shot_btn.center)
            self.screen.blit(stxt, stxt_rect)

            if s_hover and m_click and not self.m_locked and self.l.docked and not self.dragging:
                self.take_screenshot()
                self.m_locked = True

            # Status Messages
            if time.time() - self.status_time < self.status_duration:
                color_map = {
                    "success": self.colors["success"],
                    "error": self.colors["danger"],
                    "warning": self.colors["warning"],
                    "info": self.colors["text"]
                }
                status_color = color_map.get(self.status_type, self.colors["text"])
                status_txt = self.font_sm.render(self.status_msg, True, status_color)
                self.screen.blit(status_txt, (225, 467))

            pygame.draw.line(self.screen, self.colors["border"], (20, 485), (430, 485))

            # Save Preset button
            self.screen.blit(self.font_lg.render("Save New Preset", True, self.colors["text"]), (20, 505))
            input_rect = pygame.Rect(40, 540, 250, 35)
            name_color = self.colors["accent"] if self.active_input else self.colors["border"]
            pygame.draw.rect(self.screen, self.colors["panel"], input_rect, border_radius=5)
            pygame.draw.rect(self.screen, name_color, input_rect, 1, border_radius=5)

            name_txt = self.font_md.render(self.preset_name, True, self.colors["text"])
            name_rect = name_txt.get_rect(midleft=(input_rect.left + 10, input_rect.centery))
            self.screen.blit(name_txt, name_rect)

            save_btn = pygame.Rect(300, 540, 110, 35)
            pygame.draw.rect(self.screen, self.colors["accent"], save_btn, border_radius=5)
            sv_txt = self.font_md.render("SAVE", True, (255, 255, 255))
            sv_rect = sv_txt.get_rect(center=save_btn.center)
            self.screen.blit(sv_txt, sv_rect)

            # Preset List
            self.screen.blit(self.font_lg.render("Saved Presets", True, self.colors["text"]), (20, 600))
            presets = self.get_presets()
            y_offset = 635

            # List out all the presets from the json
            for name, data in presets.items():
                row_rect = pygame.Rect(30, y_offset, 390, 40)
                pygame.draw.rect(self.screen, self.colors["panel"], row_rect, border_radius=5)

                name_txt = self.font_md.render(name, True, self.colors["text"])
                name_y = y_offset + (40 - name_txt.get_height()) // 2
                self.screen.blit(name_txt, (45, name_y))

                # Load button
                l_btn = pygame.Rect(260, y_offset + 5, 70, 30)
                pygame.draw.rect(self.screen, self.colors["success"], l_btn, border_radius=4)
                l_txt = self.font_sm.render("LOAD", True, (0, 0, 0))
                self.screen.blit(l_txt, l_txt.get_rect(center=l_btn.center))

                # Delete Button
                d_btn = pygame.Rect(340, y_offset + 5, 70, 30)
                pygame.draw.rect(self.screen, self.colors["danger"], d_btn, border_radius=4)
                d_txt = self.font_sm.render("DEL", True, (255, 255, 255))
                self.screen.blit(d_txt, d_txt.get_rect(center=d_btn.center))

                # Load and delete interaction logic
                if m_click and not self.m_locked:
                    if l_btn.collidepoint(mx, my):
                        logger.info(f"Loading preset: {name}")

                        # Get preset's original scale
                        preset_scale = data.get("global_scale", self.l.launch_scale)
                        current_scale = self.l.launch_scale  # Use actual window scale, not slider value

                        # Scale positions if preset was created at different scale
                        if abs(preset_scale - current_scale) > 0.01:
                            scale_factor = current_scale / preset_scale
                            self.l.tx = int(data["tx"] * scale_factor)
                            self.l.ty = int(data["ty"] * scale_factor)
                            self.l.bx = int(data["bx"] * scale_factor)
                            self.l.by = int(data["by"] * scale_factor)
                            logger.info(
                                f"Scaled preset from {preset_scale} to {current_scale} (factor: {scale_factor:.2f})")
                        else:
                            self.l.tx, self.l.ty = data["tx"], data["ty"]
                            self.l.bx, self.l.by = data["bx"], data["by"]

                        # Force immediate sync after loading preset
                        self.force_window_sync()
                        self.show_status(f"Loaded preset: {name}", "success")
                        self.m_locked = True
                    if d_btn.collidepoint(mx, my):
                        logger.info(f"Deleting preset: {name}")
                        self.l.store.delete_preset(name)
                        self.invalidate_preset_cache()  # Refresh cache after deletion
                        self.show_status(f"Deleted preset: {name}", "warning")
                        self.m_locked = True

                y_offset += 45

            # Handle Save button click and input field
            if m_click and not self.m_locked:
                if input_rect.collidepoint(mx, my):
                    if not self.active_input:
                        logger.debug("Activated preset name input field")
                    self.active_input = True
                    self.active_slider_input = None
                if save_btn.collidepoint(mx, my):
                    try:
                        logger.info(f"Saving preset: {self.preset_name}")
                        self.l.store.save_preset(self.preset_name,
                                                 {"tx": self.l.tx, "ty": self.l.ty,
                                                  "bx": self.l.bx, "by": self.l.by,
                                                  "global_scale": self.l.launch_scale})  # Save actual window scale
                        self.invalidate_preset_cache()  # Refresh cache after save
                        self.show_status(f"Saved preset: {self.preset_name}", "success")
                        self.m_locked = True
                    except ValueError as e:
                        logger.warning(f"Failed to save preset: {e}")
                        self.show_status(str(e), "error", duration=3.0)
                        self.m_locked = True
                    except Exception as e:
                        logger.error(f"Unexpected error saving preset: {e}", exc_info=True)
                        self.show_status("Failed to save preset", "error")
                        self.m_locked = True

            if not m_click:
                self.m_locked = False

            pygame.display.flip()

        except Exception as e:
            logger.error(f"Error during UI render: {e}", exc_info=True)

    def force_window_sync(self):
        """
        Force an immediate window sync
        This is called after loading a preset to prevent windows from disappearing
        """
        try:
            if not self.l.docked:
                logger.debug("Skipping force sync - not docked")
                return

            if not (self.l.dock.hwnd_top and self.l.dock.hwnd_bottom):
                logger.warning("Cannot force sync - window handles not available")
                return

            # Reset the last sync time to bypass throttling
            self.l.dock._last_sync = 0

            # Ensure both windows are visible
            user32 = windll.user32
            SW_SHOW = 5

            logger.debug("Force syncing windows and ensuring visibility")

            # Show both windows
            user32.ShowWindow(self.l.dock.hwnd_top, SW_SHOW)
            user32.ShowWindow(self.l.dock.hwnd_bottom, SW_SHOW)

            # Force immediate sync with new positions
            self.l.dock.sync(
                self.l.tx, self.l.ty,
                self.l.bx, self.l.by,
                self.l.scrcpy.f_w1, self.l.scrcpy.f_h1,
                self.l.scrcpy.f_w2, self.l.scrcpy.f_h2,
                is_docked=True
            )

            # Force a redraw
            SWP_NOZORDER = 0x0004
            SWP_NOACTIVATE = 0x0010
            SWP_FRAMECHANGED = 0x0020
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001

            user32.SetWindowPos(
                self.l.dock.hwnd_top, 0, 0, 0, 0, 0,
                SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE
            )
            user32.SetWindowPos(
                self.l.dock.hwnd_bottom, 0, 0, 0, 0, 0,
                SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE
            )

            logger.info("Force window sync completed successfully")

        except Exception as e:
            logger.error(f"Error during force window sync: {e}", exc_info=True)

    # Keyboard input for sliders and presets
    def handle_event(self, event):
        """
        Handle keyboard and other pygame events

        Args:
            event: pygame event object
        """
        try:
            if event.type == pygame.KEYDOWN:
                # Slider Input
                if self.active_slider_input:
                    if event.key == pygame.K_BACKSPACE:
                        self.input_buffer = self.input_buffer[:-1]
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        try:
                            # Handle float for global_scale, int for others
                            if self.active_slider_input == "global_scale":
                                new_val = float(self.input_buffer)
                                if abs(new_val - self._original_scale) > 0.01:
                                    self._scale_changed = True
                            else:
                                new_val = int(self.input_buffer)

                            setattr(self.l, self.active_slider_input, new_val)
                            logger.info(f"Slider {self.active_slider_input} set to {new_val} via input box")

                            # Save scale separately for global_scale, layout for others
                            if self.active_slider_input == "global_scale":
                                self.l.save_scale()
                            else:
                                self.l.save_layout()
                                self.force_window_sync()
                        except ValueError:
                            logger.warning(f"Invalid slider input: {self.input_buffer}")
                            self.show_status("Invalid number", "error", duration=1.5)
                        except Exception as e:
                            logger.error(f"Error setting slider value: {e}")
                        finally:
                            self.active_slider_input = None
                    elif event.unicode.isdigit() or (event.unicode == '-' and len(self.input_buffer) == 0) or (
                            event.unicode == '.' and '.' not in self.input_buffer):
                        self.input_buffer += event.unicode

                # Preset Name Input
                elif self.active_input:
                    if event.key == pygame.K_BACKSPACE:
                        self.preset_name = self.preset_name[:-1]
                    elif event.key == pygame.K_RETURN:
                        logger.debug("Preset name input deactivated via Enter")
                        self.active_input = False
                    else:
                        self.preset_name += event.unicode

        except Exception as e:
            logger.error(f"Error handling event: {e}", exc_info=True)