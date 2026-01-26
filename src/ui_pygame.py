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
            logger.info(f"UI window position set to ({x_pos}, 50)")
        except Exception as e:
            logger.warning(f"Failed to set window position: {e}")

        # Create pygame window
        try:
            self.screen = pygame.display.set_mode((450, 900))
            pygame.display.set_caption("ThorCPY Controls")
            logger.info("UI window created: 450x900")
        except Exception as e:
            logger.error(f"Failed to create UI window: {e}")
            raise

        # Enable the dark titlebar for the window
        try:
            info = pygame.display.get_wm_info()
            hwnd = info.get("window")
            if hwnd:
                enable_dark_titlebar(hwnd)
                logger.debug("UI dark titlebar enabled")
        except Exception as e:
            logger.warning(f"Failed to enable dark titlebar for UI: {e}")

        # Fonts
        try:
            self.font_sm = pygame.font.Font(FONT_PATH, 12)
            self.font_md = pygame.font.Font(FONT_PATH, 15)
            self.font_lg = pygame.font.Font(FONT_PATH, 18)
            logger.debug("Custom fonts loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load custom fonts, using fallback: {e}")
            # Fallback if font fails
            self.font_sm = pygame.font.SysFont("Segoe UI", 12)
            self.font_md = pygame.font.SysFont("Segoe UI", 15)
            self.font_lg = pygame.font.SysFont("Segoe UI", 18)

        # Setup colors for the window
        self.colors = {
            "bg": hex_to_rgb("101017"),
            "panel": (30, 33, 40),
            "border": (55, 60, 72),
            "text": (225, 230, 236),
            "top": hex_to_rgb(0x00DDFF),
            "bot": hex_to_rgb(0x00DDFF),
            "accent": (90, 140, 255),
            "danger": hex_to_rgb(0xA70000),
            "success": hex_to_rgb(0xFFA600),
            "warning": (255, 190, 50)
        }
        logger.debug("UI color scheme configured")

        # Status Tracking
        self.status_msg = ""
        self.status_time = 0
        self.status_type = "info"  # "info", "success", "error", "warning"
        self.status_duration = 2.0

        # Input Tracking
        self.dragging = None
        self.preset_name = "MyLayout"
        self.active_input = False
        self.active_slider_input = None
        self.input_buffer = ""
        self.m_locked = False
        self.pressed_button = None

        # Preset caching to avoid reading file every frame
        self.cached_presets = {}
        self.preset_cache_dirty = True

        logger.info("PygameUI initialization complete")

    def invalidate_preset_cache(self):
        """Mark preset cache as needing refresh"""
        self.preset_cache_dirty = True
        logger.debug("Preset cache invalidated")

    def get_presets(self):
        """Get presets with caching to avoid reading file every frame"""
        if self.preset_cache_dirty:
            self.cached_presets = self.l.store.load_all()
            self.preset_cache_dirty = False
            logger.debug("Preset cache refreshed")
        return self.cached_presets

    def show_status(self, message, status_type="info", duration=2.0):
        """
        Show status message in UI

        Args:
            message: Status message to display
            status_type: Type of status ("info", "success", "error", "warning")
            duration: How long to show the message in seconds
        """
        self.status_msg = message
        self.status_time = time.time()
        self.status_type = status_type
        self.status_duration = duration

        log_level = {
            "info": logger.info,
            "success": logger.info,
            "warning": logger.warning,
            "error": logger.error
        }.get(status_type, logger.info)

        log_level(f"Status message: {message}")

    # Screenshot Handling
    def take_screenshot(self):
        """Captures ONLY the client area (inside view) and copies to clipboard."""
        logger.info("Screenshot requested")

        if not self.l.docked:
            logger.warning("Screenshot blocked: windows not docked")
            self.show_status("Cannot screenshot while undocked", "warning")
            return False

        hwnd = self.l.hwnd_container
        if not hwnd:
            logger.error("Screenshot failed: no container window")
            self.show_status("No container window found", "error")
            return False

        try:
            logger.debug(f"Capturing screenshot from window {hwnd}")

            # Get ONLY the inside dimensions
            rect = wintypes.RECT()
            windll.user32.GetClientRect(hwnd, byref(rect))
            w, h = rect.right - rect.left, rect.bottom - rect.top
            logger.debug(f"Screenshot dimensions: {w}x{h}")

            # Setup Device Contexts
            h_win_dc = windll.user32.GetDC(hwnd)
            h_mem_dc = windll.gdi32.CreateCompatibleDC(h_win_dc)
            h_bitmap = windll.gdi32.CreateCompatibleBitmap(h_win_dc, w, h)

            # Perform the capture
            old_obj = windll.gdi32.SelectObject(h_mem_dc, h_bitmap)
            windll.gdi32.BitBlt(h_mem_dc, 0, 0, w, h, h_win_dc, 0, 0, SRCCOPY)

            # Clipboard operations
            windll.user32.OpenClipboard(None)
            windll.user32.EmptyClipboard()
            windll.user32.SetClipboardData(CF_BITMAP, h_bitmap)
            windll.user32.CloseClipboard()
            logger.debug("Screenshot copied to clipboard")

            # Cleanup
            windll.gdi32.SelectObject(h_mem_dc, old_obj)
            windll.gdi32.DeleteDC(h_mem_dc)
            windll.user32.ReleaseDC(hwnd, h_win_dc)

            # Set visual confirmation
            self.show_status("Screenshot copied to clipboard!", "success")
            logger.info("Screenshot captured successfully")
            return True

        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}", exc_info=True)
            self.show_status("Screenshot failed", "error")
            return False

    # Slider Rendering
    def draw_slider(self, label, y, value, minv, maxv, accent, key):
        """
        Draws a slider with an interactive knob and optional input box

        Args:
            label: Display label for the slider
            y: Y position on screen
            value: Current value
            minv: Minimum value
            maxv: Maximum value
            accent: Color for the knob
            key: Attribute key for the launcher object
        """
        mx, my = pygame.mouse.get_pos()
        mdown = pygame.mouse.get_pressed()[0]

        try:
            # Slider Bar
            bar = pygame.Rect(40, y, 300, 8)
            pygame.draw.rect(self.screen, self.colors["panel"], bar, border_radius=4)

            # Knob Position
            t = (value - minv) / (maxv - minv) if (maxv - minv) != 0 else 0
            knob_x = int(bar.x + t * bar.width)
            knob = pygame.Rect(knob_x - 6, y - 6, 12, 20)
            pygame.draw.rect(self.screen, accent, knob, border_radius=4)

            # Input Box
            input_box = pygame.Rect(355, y - 12, 65, 25)
            is_active = (self.active_slider_input == key)
            box_color = self.colors["accent"] if is_active else self.colors["panel"]

            pygame.draw.rect(self.screen, self.colors["panel"], input_box, border_radius=4)
            pygame.draw.rect(self.screen, box_color, input_box, 1, border_radius=4)

            display_val = self.input_buffer if is_active else str(int(value))
            val_txt = self.font_md.render(display_val, True, self.colors["text"])
            self.screen.blit(val_txt,
                             (input_box.centerx - val_txt.get_width() // 2,
                              input_box.centery - val_txt.get_height() // 2))

            # Label
            label_txt = self.font_sm.render(label, True, self.colors["text"])
            self.screen.blit(label_txt, (40, y - 18))

            # Interaction logic for knob
            if mdown and knob.collidepoint(mx, my):
                if self.dragging != key:
                    logger.debug(f"Started dragging slider: {key}")
                self.dragging = key
                self.active_slider_input = None

            if not mdown and self.dragging == key:
                logger.debug(f"Stopped dragging slider: {key} (value={getattr(self.l, key)})")
                self.dragging = None

            if self.dragging == key:
                rel = max(0, min(1, (mx - bar.x) / bar.width))
                new_val = int(minv + rel * (maxv - minv))
                setattr(self.l, key, new_val)

            if mdown and input_box.collidepoint(mx, my) and not self.m_locked:
                logger.debug(f"Activated slider input box: {key}")
                self.active_slider_input = key
                self.input_buffer = ""
                self.active_input = False
                self.m_locked = True

        except Exception as e:
            logger.error(f"Error drawing slider '{label}': {e}", exc_info=True)

    # Render Full UI
    def render(self):
        """Renders the full control panel UI"""
        try:
            self.screen.fill(self.colors["bg"])
            mx, my = pygame.mouse.get_pos()
            m_click = pygame.mouse.get_pressed()[0]

            # Layout Sliders
            self.screen.blit(self.font_lg.render("Layout Adjustment", True, self.colors["text"]), (20, 15))
            self.draw_slider("TOP X", 80, self.l.tx, -500, 1500, self.colors["top"], "tx")
            self.draw_slider("TOP Y", 130, self.l.ty, -500, 1500, self.colors["top"], "ty")
            self.draw_slider("BOTTOM X", 210, self.l.bx, -500, 1500, self.colors["bot"], "bx")
            self.draw_slider("BOTTOM Y", 260, self.l.by, -500, 1500, self.colors["bot"], "by")

            # Undock/Dock Button
            undock_btn = pygame.Rect(40, 310, 180, 40)
            u_hover = undock_btn.collidepoint(mx, my)
            btn_text = "DOCK WINDOWS" if not self.l.docked else "UNDOCK WINDOWS"

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
            shot_btn = pygame.Rect(230, 310, 180, 40)
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
                self.screen.blit(status_txt, (225, 357))

            pygame.draw.line(self.screen, self.colors["border"], (20, 375), (430, 375))

            # Save Preset button
            self.screen.blit(self.font_lg.render("Save New Preset", True, self.colors["text"]), (20, 395))
            input_rect = pygame.Rect(40, 430, 250, 35)
            name_color = self.colors["accent"] if self.active_input else self.colors["border"]
            pygame.draw.rect(self.screen, self.colors["panel"], input_rect, border_radius=5)
            pygame.draw.rect(self.screen, name_color, input_rect, 1, border_radius=5)

            name_txt = self.font_md.render(self.preset_name, True, self.colors["text"])
            name_rect = name_txt.get_rect(center=input_rect.center)
            self.screen.blit(name_txt, name_rect)

            save_btn = pygame.Rect(300, 430, 110, 35)
            pygame.draw.rect(self.screen, self.colors["accent"], save_btn, border_radius=5)
            sv_txt = self.font_md.render("SAVE", True, (255, 255, 255))
            sv_rect = sv_txt.get_rect(center=save_btn.center)
            self.screen.blit(sv_txt, sv_rect)

            # Preset List - USE CACHED VERSION
            self.screen.blit(self.font_lg.render("Saved Presets", True, self.colors["text"]), (20, 490))
            presets = self.get_presets()  # Use cached version instead of load_all()
            y_offset = 525

            # List out all the presets from the json
            for name, data in presets.items():
                row_rect = pygame.Rect(30, y_offset, 390, 40)
                pygame.draw.rect(self.screen, self.colors["panel"], row_rect, border_radius=5)

                self.screen.blit(self.font_md.render(name, True, self.colors["text"]),
                                 (45, y_offset + 15))

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
                        self.l.tx, self.l.ty = data["tx"], data["ty"]
                        self.l.bx, self.l.by = data["bx"], data["by"]
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
                                                  "bx": self.l.bx, "by": self.l.by})
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
                            new_val = int(self.input_buffer)
                            setattr(self.l, self.active_slider_input, new_val)
                            logger.info(f"Slider {self.active_slider_input} set to {new_val} via input box")
                        except ValueError:
                            logger.warning(f"Invalid slider input: {self.input_buffer}")
                            self.show_status("Invalid number", "error", duration=1.5)
                        except Exception as e:
                            logger.error(f"Error setting slider value: {e}")
                        finally:
                            self.active_slider_input = None
                    elif event.unicode.isdigit() or (event.unicode == '-' and len(self.input_buffer) == 0):
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