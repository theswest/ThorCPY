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

# src/scrcpy_manager.py

import os
import subprocess
import time
import shutil
import logging

# Setup logger for this module
logger = logging.getLogger(__name__)

# Process creation flags
CREATE_NO_WINDOW = 0x08000000 # Prevents console window from appearing

# Default UI scaling
DEFAULT_UI_SCALING = 0.6

# Top screen base resolution
TOP_SCREEN_BASE_WIDTH = 1920
TOP_SCREEN_BASE_HEIGHT = 1080

# Resolution calculation factors for the bottom screen
# These are device-specific ratios for the AYN Thor
TOP_BOTTOM_SCALE_FACTOR = 5.23
BOTTOM_WIDTH_SCALE_FACTOR = 2.95
BOTTOM_HEIGHT_SCALE_FACTOR = 2.57

# Scrcpy startup retry config
SCRCPY_RETRY_COUNT = 2
SCRCPY_START_DELAY = 1.0

# ADB command timeouts
ADB_CAPTURE_OUTPUT = True
ADB_SERVER_TIMEOUT = 10
ADB_TASKKILL_TIMEOUT = 5

# Logging constants
LOG_MULT = 60 # Width of log separator lines
LOGFILE_ENCODING = "utf-8"

# Scrcpy default parameters
DEFAULT_MAX_FPS = "120"
DEFAULT_RENDER_DRIVER = "opengl"

# Video bitrate calculation constants
BITRATE_CALC_SCALE_FACTOR = 1.5
TOP_BITRATE_MINIMUM = 8
TOP_BITRATE_SCALE = 32
BOTTOM_BITRATE_MINIMUM = 6
BOTTOM_BITRATE_SCALE = 24

# AYN Thor Screen Constants
TOP_SCREEN_DISPLAY_ID = "0"
TOP_SCREEN_WINDOW_TITLE = "ThorCPY Top Screen"
BOTTOM_SCREEN_DISPLAY_ID = "4"
BOTTOM_SCREEN_WINDOW_TITLE = "ThorCPY Bottom Screen"

# Timing delays for process management
DISPLAY_INIT_DELAY = 1.2  # Wait for first display to initialize
SCRCPY_CREATION_DELAY = 0.3  # Check if process survives startup
SCRCPY_RETRY_DELAY = 0.7  # Wait between retry attempts

# Process termination timeouts
PROCESS_TERMINATE_TIMEOUT = 2
SCRCPY_TERMINATE_TIMEOUT = 3

# Main ScrcpyManager class
class ScrcpyManager:
    """
    Manages scrcpy instances for controlling and displaying the Thor's screens
    Handles device detection, window launching, scaling, resolution and process management and shutdown
    """

    def __init__(self, scale=DEFAULT_UI_SCALING, scrcpy_bin=None, adb_bin=None, enable_audio_top=True):
        """
        Initialize the scrcpy manager.

        Args:
            scale: float, scaling factor for window resolution
            scrcpy_bin: optional custom path to scrcpy binary
            adb_bin: optional custom path to adb binary
            enable_audio_top: if True, enable audio on top window
        """
        logger.info(f"Initializing ScrcpyManager (scale={scale}, audio={enable_audio_top})")

        self.scale = scale
        self.processes = [] # Track all scrcpy subprocess instances
        self.serial = None
        self.enable_audio_top = enable_audio_top

        # Calculate top screen resolution based on scale
        base_w1 = TOP_SCREEN_BASE_WIDTH
        base_h1 = TOP_SCREEN_BASE_HEIGHT
        self.f_w1 = int(base_w1 * self.scale)
        self.f_h1 = int(base_h1 * self.scale)
        logger.debug(f"Top window resolution: {self.f_w1}x{self.f_h1}")

        # Calculate bottom screen resolution based on scale
        pxi = (base_w1 * self.scale) / TOP_BOTTOM_SCALE_FACTOR
        self.f_w2 = int(BOTTOM_WIDTH_SCALE_FACTOR * pxi)
        self.f_h2 = int(BOTTOM_HEIGHT_SCALE_FACTOR * pxi)
        logger.debug(f"Bottom window resolution: {self.f_w2}x{self.f_h2}")

        # Locate scrcpy and adb binaries
        self.scrcpy_bin = scrcpy_bin or self._resolve_bin("scrcpy")
        self.adb_bin = adb_bin or self._resolve_bin("adb")

        if self.scrcpy_bin:
            logger.info(f"scrcpy binary found: {self.scrcpy_bin}")
        else:
            logger.warning("scrcpy binary not found")

        if self.adb_bin:
            logger.info(f"adb binary found: {self.adb_bin}")
        else:
            logger.warning("adb binary not found")

        # Retry config
        self.scrcpy_retry_count = SCRCPY_RETRY_COUNT
        self.scrcpy_start_delay = SCRCPY_START_DELAY
        logger.debug(f"Retry count: {self.scrcpy_retry_count}, Start delay: {self.scrcpy_start_delay}s")

    def _resolve_bin(self, name):
        """
        Finds binary in local ./bin folder or system path.

        Args:
            name: Binary name (e.g., "scrcpy" or "adb")

        Returns:
            Full path to binary or None if not found
        """
        logger.debug(f"Resolving binary: {name}")

        # Check local bin folder first
        local = os.path.join(os.getcwd(), "bin", f"{name}.exe")
        if os.path.exists(local):
            logger.info(f"Found {name} in local bin folder: {local}")
            return local

        # Fallback to system PATH
        found = shutil.which(name)
        if found:
            logger.info(f"Found {name} in system PATH: {found}")
            return found

        logger.warning(f"Binary '{name}' not found in local bin or system PATH")
        return None


    def detect_device(self):
        """
        Detect and return serial of first connected Android ADB device.

        Starts ADB server if needed, then queries for authorized devices.
        Ignores unauthorized devices to prevent connection issues.

        Returns:
            Device serial string or None if no device found
        """
        logger.info("Starting ADB device detection")

        if self.serial:
            logger.info(f"Device already detected: {self.serial}")
            return self.serial

        if not self.adb_bin:
            logger.error("Cannot detect device: ADB binary not found")
            return None

        # Start ADB server
        try:
            logger.debug("Starting ADB server")
            result = subprocess.run(
                [self.adb_bin, "start-server"],
                capture_output=ADB_CAPTURE_OUTPUT,
                text=True,
                timeout=ADB_SERVER_TIMEOUT,
            )
            if result.returncode != 0:
                logger.warning(f"ADB start-server returned code {result.returncode}")
            else:
                logger.debug("ADB server started successfully")
        except subprocess.TimeoutExpired:
            logger.error("ADB start-server timed out")
        except Exception as ADBStartError:
            logger.error(f"Failed to start ADB server: {ADBStartError}", exc_info=True)

        # Query for devices
        try:
            logger.debug("Querying connected devices")
            out = subprocess.check_output([self.adb_bin, "devices"], text=True, timeout=ADB_SERVER_TIMEOUT)
            logger.debug(f"ADB devices output:\n{out}")

            # Parse device list (skip header line)
            lines = out.strip().splitlines()[1:]
            devices = [
                line.split()[0] for line in lines if "device" in line and "unauthorized" not in line
            ]

            if devices:
                self.serial = devices[0]
                logger.info(f"Device detected: {self.serial}")
                if len(devices) > 1:
                    logger.info(
                        f"Multiple devices found ({len(devices)}), using first: {self.serial}"
                    )
                return self.serial
            else:
                logger.warning("No devices found in ADB device list")

        except subprocess.TimeoutExpired:
            logger.error("ADB devices command timed out")
        except subprocess.CalledProcessError as DeviceSearchError:
            logger.error(f"ADB devices command failed: {DeviceSearchError}", exc_info=True)
        except Exception as DeviceSearchException:
            logger.error(f"Unexpected error during device detection: {DeviceSearchException}", exc_info=True)

        return None

    # Start Scrcpy Windows
    def start_scrcpy(self, serial=None, extra_top_args=None, extra_bottom_args=None):
        """
        Launch both scrcpy windows.

        Launches the top screen first, waits for it to be initialized, then launches the bottom screen.
        Both windows are configured with:
        Borderless mode, optimized bitrates, 120FPS cap, openGL

        Args:
            serial: Device serial (uses detected device if None)
            extra_top_args: Additional CLI arguments for top window
            extra_bottom_args: Additional CLI arguments for bottom window

        Returns:
            list: Popen objects for [top_process, bottom_process]

        Raises:
            RuntimeError: If device serial missing or scrcpy binary not found
        """
        logger.info("=" * LOG_MULT)
        logger.info("Starting scrcpy instances")
        logger.info("=" * LOG_MULT)

        if serial:
            self.serial = serial
            logger.debug(f"Using provided serial: {serial}")

        if not self.serial:
            logger.error("Cannot start scrcpy: No device serial provided")
            raise RuntimeError("No device serial provided to ScrcpyManager.start_scrcpy")

        if not self.scrcpy_bin:
            logger.error("Cannot start scrcpy: scrcpy binary not found")
            raise RuntimeError("scrcpy binary not found")

        logger.info(f"Device serial: {self.serial}")
        logger.info(f"Scrcpy binary: {self.scrcpy_bin}")

        # Base arguments for both windows
        base = [
            self.scrcpy_bin,
            "-s",
            self.serial,
            "--window-borderless",
            "--max-fps",
            DEFAULT_MAX_FPS,
            "--render-driver",
            DEFAULT_RENDER_DRIVER,
            "--mouse-bind=++++", # Enable all mouse bindings
        ]

        # Calculate bitrates based on resolution
        bitrate_top = f"{max(TOP_BITRATE_MINIMUM, int(TOP_BITRATE_SCALE * 
                                                      (self.scale**BITRATE_CALC_SCALE_FACTOR)))}M"
        bitrate_bottom = f"{max(BOTTOM_BITRATE_MINIMUM, int(BOTTOM_BITRATE_SCALE * 
                                                            (self.scale**BITRATE_CALC_SCALE_FACTOR)))}M"
        logger.info(f"Video bitrates - Top: {bitrate_top}, Bottom: {bitrate_bottom}")

        # Top window arguments
        top_args = base + [
            "--display-id",
            TOP_SCREEN_DISPLAY_ID,
            "--window-title",
            TOP_SCREEN_WINDOW_TITLE,
            "--window-width",
            str(self.f_w1),
            "--video-bit-rate",
            bitrate_top,
        ]

        # Audio only on the top window to avoid conflicts
        if not self.enable_audio_top:
            top_args += ["--no-audio"]
            logger.debug("Audio disabled for top window")
        else:
            logger.debug("Audio enabled for top window")

        if extra_top_args:
            top_args += extra_top_args
            logger.debug(f"Extra top args: {extra_top_args}")

        # Bottom window arguments (Always no audio)
        bottom_args = base + [
            "--display-id",
            BOTTOM_SCREEN_DISPLAY_ID,
            "--window-title",
            BOTTOM_SCREEN_WINDOW_TITLE,
            "--window-width",
            str(self.f_w2),
            "--video-bit-rate",
            bitrate_bottom,
            "--no-audio",
        ]

        if extra_bottom_args:
            bottom_args += extra_bottom_args
            logger.debug(f"Extra bottom args: {extra_bottom_args}")

        # Start top screen first
        logger.info(f"Starting TOP window ({TOP_SCREEN_WINDOW_TITLE})")
        logger.debug(f"Top window command: {' '.join(top_args)}")
        p0 = self._start_with_retry(top_args, "top")

        # Wait for top screen to initialise before starting bottom
        logger.info(f"Waiting {self.scrcpy_start_delay}s before starting bottom window")
        time.sleep(DISPLAY_INIT_DELAY)

        # Start bottom screen
        logger.info(f"Starting BOTTOM window ({BOTTOM_SCREEN_WINDOW_TITLE})")
        logger.debug(f"Bottom window command: {' '.join(bottom_args)}")
        p1 = self._start_with_retry(bottom_args, "bottom")

        logger.info("Both scrcpy instances started successfully")
        logger.info("=" * LOG_MULT)
        return [p0, p1]

    def _start_with_retry(self, cmd, label):
        """
        Start a process and retry on failure.
        Logs to ./logs/ if possible.

        Args:
            cmd: Command list to execute
            label: Label for logging (e.g., "top" or "bottom")

        Returns:
            Popen instance

        Raises:
            Exception: If all retry attempts fail
        """
        logger.debug(
            f"Starting scrcpy {label} window with {self.scrcpy_retry_count} retry attempts"
        )
        last_exc = None

        for attempt in range(1, self.scrcpy_retry_count + 1):
            try:
                logger.debug(
                    f"Attempt {attempt}/{self.scrcpy_retry_count} for {label} window"
                )

                # Create log file for subprocess output
                logfile = None
                try:
                    logs_dir = os.path.join(os.getcwd(), "logs")
                    os.makedirs(logs_dir, exist_ok=True)
                    stamp = time.strftime("%Y%m%d_%H%M%S")
                    log_path = os.path.join(logs_dir, f"scrcpy_{label}_{stamp}.log")
                    logfile = open(log_path, "w", encoding=LOGFILE_ENCODING)
                    logger.debug(f"Scrcpy {label} output logging to: {log_path}")
                except Exception as LogFileCreationError:
                    logger.warning(f"Failed to create scrcpy log file: {LogFileCreationError}")
                    logfile = None

                # Redirect output to log file
                stdout = logfile if logfile else subprocess.DEVNULL
                stderr = logfile if logfile else subprocess.DEVNULL

                # Start process
                proc = subprocess.Popen(cmd, stdout=stdout, stderr=stderr, creationflags=CREATE_NO_WINDOW)

                # Verify process didn't instantly crash
                time.sleep(SCRCPY_CREATION_DELAY)
                if proc.poll() is not None:
                    raise RuntimeError(
                        f"Scrcpy {label} process died immediately (exit code: {proc.poll()})"
                    )

                # Start process hidden
                self.processes.append(proc)
                logger.info(
                    f"Scrcpy {label} window started successfully (PID: {proc.pid})"
                )
                return proc

            except Exception as ScrcpyStartError:
                last_exc = ScrcpyStartError
                logger.warning(f"Scrcpy {label} start attempt "
                               f"{attempt}/{self.scrcpy_retry_count} failed: {ScrcpyStartError}")
                if attempt < self.scrcpy_retry_count:
                    logger.debug(f"Waiting {SCRCPY_RETRY_DELAY}s before retry...")
                    time.sleep(SCRCPY_RETRY_DELAY)

        # All attempts failed
        logger.error(f"All {self.scrcpy_retry_count} attempts to start scrcpy {label} window failed")
        raise last_exc

    # Check if process is alive
    def _check_process_alive(self):
        """
        Check if any processes that were tracked have died

        Returns the first process that is no longer alive or None if all are running.

        Returns:
            Popen object of dead process or None if all alive
        """
        for processName, process in enumerate(self.processes):
            try:
                if process.poll() is not None:
                    logger.warning(f"Process {processName} "
                                   f"(PID: {process.pid}) is no longer alive (exit code: {process.poll()})")
                    return process
            except Exception as ProcessCheckError:
                logger.error(f"Error checking process {processName} status: {ProcessCheckError}")
                return process
        return None

    # Stop Process
    def stop(self):
        """
        Stop and cleanup all scrcpy windows politely, then forcefully if needed.

        Shuts down in the following order:
        1) Gracefully terminate (SIGTERM)
        2) Wait for proceesses to exit
        3) Force kill if needed (taskkill)
        4) Device-side cleanup (kill scrcpy-server, app_process)
        5) Remove ADB port forwards

        Safe to call multiple times
        """
        logger.info("=" * LOG_MULT)
        logger.info("Stopping ScrcpyManager")
        logger.info("=" * LOG_MULT)

        if not self.processes:
            logger.info("No scrcpy processes to stop")
            return

        logger.info(f"Stopping {len(self.processes)} scrcpy process(es)")

        # Attempt graceful termination
        for processName, process in enumerate(list(self.processes)):
            try:
                if process.poll() is None:
                    logger.debug(f"Terminating process {processName} (PID: {process.pid})")
                    process.terminate()
                else:
                    logger.debug(f"Process {processName} (PID: {process.pid}) already stopped")
            except Exception as TerminationError:
                logger.warning(f"Error terminating process {processName}: {TerminationError}")

        # Wait for graceful exit, then force-kill remaining processes
        logger.debug("Waiting for processes to terminate gracefully...")
        for processName, process in enumerate(list(self.processes)):
            try:
                if process.poll() is None:
                    process.wait(timeout=PROCESS_TERMINATE_TIMEOUT)
                    logger.debug(f"Process {processName} (PID: {process.pid}) terminated gracefully")
            except subprocess.TimeoutExpired:
                logger.warning(
                    f"Process {processName} (PID: {process.pid}) did not terminate, forcing kill"
                )
                try:
                    process.kill()
                    logger.debug(f"Process {processName} killed with p.kill()")
                except Exception as ProcessKillError:
                    logger.error(f"Failed to kill process {processName}: {ProcessKillError}")
                    # Last resort -> taskkill
                    try:
                        subprocess.run(
                            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                            capture_output=ADB_CAPTURE_OUTPUT,
                            timeout=ADB_TASKKILL_TIMEOUT,
                        )
                        logger.debug(f"Process {processName} killed with taskkill")
                    except Exception as TaskKillError:
                        logger.error(f"Taskkill also failed for process {processName}: {TaskKillError}")
            except Exception as ProcessKillWaitingError:
                logger.error(f"Error waiting for process {processName}: {ProcessKillWaitingError}")

        # Clear process list
        process_count = len(self.processes)
        self.processes = []
        logger.info(f"Cleared {process_count} process(es) from tracking list")

        # Device-side cleanup (scrcpy server and app_process)
        if self.serial and self.adb_bin:
            logger.info(f"Performing device-side cleanup for {self.serial}")

            # Kill scrcpy server
            try:
                logger.debug("Killing scrcpy-server on device")
                result = subprocess.run(
                    [
                        self.adb_bin,
                        "-s",
                        self.serial,
                        "shell",
                        "pkill",
                        "-f",
                        "scrcpy-server",
                    ],
                    capture_output=ADB_CAPTURE_OUTPUT,
                    timeout=SCRCPY_TERMINATE_TIMEOUT,
                )
                if result.returncode == 0:
                    logger.debug("scrcpy-server killed successfully")
                else:
                    logger.debug(f"pkill scrcpy-server returned {result.returncode} (may not have been running)")
            except subprocess.TimeoutExpired:
                logger.warning("Timeout killing scrcpy-server")
            except Exception as ScrcpyKillError:
                logger.warning(f"Error killing scrcpy-server: {ScrcpyKillError}")

            # Kill app_process
            try:
                logger.debug("Killing app_process on device")
                result = subprocess.run(
                    [
                        self.adb_bin,
                        "-s",
                        self.serial,
                        "shell",
                        "pkill",
                        "-f",
                        "app_process",
                    ],
                    capture_output=ADB_CAPTURE_OUTPUT,
                    timeout=SCRCPY_TERMINATE_TIMEOUT,
                )
                if result.returncode == 0:
                    logger.debug("app_process killed successfully")
                else:
                    logger.debug(f"pkill app_process returned {result.returncode} (may not have been running)")
            except subprocess.TimeoutExpired:
                logger.warning("Timeout killing app_process")
            except Exception as AppProcessKillError:
                logger.warning(f"Error killing app_process: {AppProcessKillError}")

            # Remove port forwards
            try:
                logger.debug("Removing ADB port forwards")
                subprocess.run(
                    [self.adb_bin, "-s", self.serial, "forward", "--remove-all"],
                    capture_output=ADB_CAPTURE_OUTPUT,
                    timeout=SCRCPY_TERMINATE_TIMEOUT,
                )
                logger.debug("Port forwards removed")
            except Exception as PortForwardsKillError:
                logger.warning(f"Error removing port forwards: {PortForwardsKillError}")

            # Remove all reverse forwards
            try:
                logger.debug("Removing ADB reverse forwards")
                subprocess.run(
                    [self.adb_bin, "-s", self.serial, "reverse", "--remove-all"],
                    capture_output=ADB_CAPTURE_OUTPUT,
                    timeout=SCRCPY_TERMINATE_TIMEOUT,
                )
                logger.debug("Reverse forwards removed")
            except Exception as ReverseForwardsKillError:
                logger.warning(f"Error removing reverse forwards: {ReverseForwardsKillError}")

            logger.info("Device-side cleanup complete")
        else:
            if not self.serial:
                logger.debug("Skipping device cleanup: no serial")
            if not self.adb_bin:
                logger.debug("Skipping device cleanup: no ADB binary")

        logger.info("ScrcpyManager stopped successfully")
        logger.info("=" * LOG_MULT)
