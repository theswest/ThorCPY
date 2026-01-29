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

# Hide console windows for subprocesses
CREATE_NO_WINDOW = 0x08000000


# Main ScrcpyManager class
class ScrcpyManager:
    """
    Manages scrcpy instances for controlling and displaying thor's screens
    Handles device detection, window launching, scaling, resolution and process management and shutdown
    """

    def __init__(self, scale=0.6, scrcpy_bin=None, adb_bin=None, enable_audio_top=True):
        """
        Initialize the manager.

        Args:
            scale: float, scaling factor for window resolution
            scrcpy_bin: optional custom path to scrcpy binary
            adb_bin: optional custom path to adb binary
            enable_audio_top: if True, enable audio on top window
        """
        logger.info(
            f"Initializing ScrcpyManager (scale={scale}, audio={enable_audio_top})"
        )

        self.scale = scale
        # Track popen instances
        self.processes = []
        self.serial = None
        self.enable_audio_top = enable_audio_top

        # Base resolutions for top screen
        base_w1 = 1920
        base_h1 = 1080
        self.f_w1 = int(base_w1 * self.scale)
        self.f_h1 = int(base_h1 * self.scale)
        logger.debug(f"Top window resolution: {self.f_w1}x{self.f_h1}")

        # Bottom window resolution and scale
        pxi = (base_w1 * self.scale) / 5.23
        self.f_w2 = int(2.95 * pxi)
        self.f_h2 = int(2.57 * pxi)
        logger.debug(f"Bottom window resolution: {self.f_w2}x{self.f_h2}")

        # Resolve scrcpy and adb binaries
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

        # General scrcpy config
        self.scrcpy_retry_count = 2
        self.scrcpy_start_delay = 1.0
        logger.debug(
            f"Retry count: {self.scrcpy_retry_count}, Start delay: {self.scrcpy_start_delay}s"
        )

    # Binary resolution
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

        # Check system PATH
        found = shutil.which(name)
        if found:
            logger.info(f"Found {name} in system PATH: {found}")
            return found

        logger.warning(f"Binary '{name}' not found in local bin or system PATH")
        return None

    # Device detection
    def detect_device(self):
        """
        Detect and return serial of first connected Android ADB device.

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

        try:
            # Ensure ADB is running
            logger.debug("Starting ADB server")
            result = subprocess.run(
                [self.adb_bin, "start-server"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                logger.warning(f"ADB start-server returned code {result.returncode}")
            else:
                logger.debug("ADB server started successfully")
        except subprocess.TimeoutExpired:
            logger.error("ADB start-server timed out")
        except Exception as e:
            logger.error(f"Failed to start ADB server: {e}", exc_info=True)

        try:
            logger.debug("Querying connected devices")
            out = subprocess.check_output(
                [self.adb_bin, "devices"], text=True, timeout=10
            )
            logger.debug(f"ADB devices output:\n{out}")

            lines = out.strip().splitlines()[1:]  # Skip header line
            devices = [
                l.split()[0] for l in lines if "device" in l and "unauthorized" not in l
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
        except subprocess.CalledProcessError as e:
            logger.error(f"ADB devices command failed: {e}", exc_info=True)
        except Exception as e:
            logger.error(
                f"Unexpected error during device detection: {e}", exc_info=True
            )

        return None

    # Start Scrcpy Windows
    def start_scrcpy(self, serial=None, extra_top_args=None, extra_bottom_args=None):
        """
        Start both scrcpy windows (top and bottom).

        Args:
            serial: optional device serial override
            extra_top_args: additional command-line args for top window
            extra_bottom_args: additional command-line args for bottom window

        Returns:
            List of Popen objects for the scrcpy processes

        Raises:
            RuntimeError: If device serial is missing or scrcpy binary not found
        """
        logger.info("=" * 60)
        logger.info("Starting scrcpy instances")
        logger.info("=" * 60)

        if serial:
            self.serial = serial
            logger.debug(f"Using provided serial: {serial}")

        if not self.serial:
            logger.error("Cannot start scrcpy: No device serial provided")
            raise RuntimeError(
                "No device serial provided to ScrcpyManager.start_scrcpy"
            )

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
            "120",
            "--render-driver",
            "opengl",
            "--mouse-bind=++++",
        ]

        # Pick codecs & bitrates
        bitrate_top = f"{max(8, int(32 * (self.scale**1.5)))}M"
        bitrate_bottom = f"{max(6, int(24 * (self.scale**1.5)))}M"
        logger.info(f"Video bitrates - Top: {bitrate_top}, Bottom: {bitrate_bottom}")

        # Top window arguments
        top_args = base + [
            "--display-id",
            "0",
            "--window-title",
            "TF_T",
            "--window-width",
            str(self.f_w1),
            "--video-bit-rate",
            bitrate_top,
        ]

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
            "4",
            "--window-title",
            "TF_B",
            "--window-width",
            str(self.f_w2),
            "--video-bit-rate",
            bitrate_bottom,
            "--no-audio",
        ]

        if extra_bottom_args:
            bottom_args += extra_bottom_args
            logger.debug(f"Extra bottom args: {extra_bottom_args}")

        # Start screens with retry
        logger.info("Starting TOP window (TF_T)")
        logger.debug(f"Top window command: {' '.join(top_args)}")
        p0 = self._start_with_retry(top_args, "top")

        logger.info(f"Waiting {self.scrcpy_start_delay}s before starting bottom window")
        time.sleep(1.2)

        logger.info("Starting BOTTOM window (TF_B)")
        logger.debug(f"Bottom window command: {' '.join(bottom_args)}")
        p1 = self._start_with_retry(bottom_args, "bottom")

        logger.info("Both scrcpy instances started successfully")
        logger.info("=" * 60)
        return [p0, p1]

    # Start Process with retry
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

                # Prepare log file
                logfile = None
                try:
                    logs_dir = os.path.join(os.getcwd(), "logs")
                    os.makedirs(logs_dir, exist_ok=True)
                    stamp = time.strftime("%Y%m%d_%H%M%S")
                    log_path = os.path.join(logs_dir, f"scrcpy_{label}_{stamp}.log")
                    logfile = open(log_path, "w", encoding="utf-8")
                    logger.debug(f"Scrcpy {label} output logging to: {log_path}")
                except Exception as e:
                    logger.warning(f"Failed to create scrcpy log file: {e}")
                    logfile = None

                stdout = logfile if logfile else subprocess.DEVNULL
                stderr = logfile if logfile else subprocess.DEVNULL

                proc = subprocess.Popen(
                    cmd, stdout=stdout, stderr=stderr, creationflags=CREATE_NO_WINDOW
                )

                # Give it a moment to fail if it's going to
                time.sleep(0.3)
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

            except Exception as e:
                last_exc = e
                logger.warning(
                    f"Scrcpy {label} start attempt {attempt}/{self.scrcpy_retry_count} failed: {e}"
                )
                if attempt < self.scrcpy_retry_count:
                    logger.debug("Waiting 0.7s before retry...")
                    time.sleep(0.7)

        # All attempts failed
        logger.error(
            f"All {self.scrcpy_retry_count} attempts to start scrcpy {label} window failed"
        )
        raise last_exc

    # Check if process is alive
    def _check_process_alive(self):
        """
        Returns the first process that is no longer alive or None if all are running.

        Returns:
            Popen object of dead process or None if all alive
        """
        for i, p in enumerate(self.processes):
            try:
                if p.poll() is not None:
                    logger.warning(
                        f"Process {i} (PID: {p.pid}) is no longer alive (exit code: {p.poll()})"
                    )
                    return p
            except Exception as e:
                logger.error(f"Error checking process {i} status: {e}")
                return p
        return None

    # Stop Process
    def stop(self):
        """
        Stop and cleanup all scrcpy windows politely, then forcefully if needed.
        """
        logger.info("=" * 60)
        logger.info("Stopping ScrcpyManager")
        logger.info("=" * 60)

        if not self.processes:
            logger.info("No scrcpy processes to stop")
            return

        logger.info(f"Stopping {len(self.processes)} scrcpy process(es)")

        # Terminate processes politely
        for i, p in enumerate(list(self.processes)):
            try:
                if p.poll() is None:
                    logger.debug(f"Terminating process {i} (PID: {p.pid})")
                    p.terminate()
                else:
                    logger.debug(f"Process {i} (PID: {p.pid}) already stopped")
            except Exception as e:
                logger.warning(f"Error terminating process {i}: {e}")

        # Wait briefly, then force-kill remaining processes
        logger.debug("Waiting for processes to terminate gracefully...")
        for i, p in enumerate(list(self.processes)):
            try:
                if p.poll() is None:
                    p.wait(timeout=2)
                    logger.debug(f"Process {i} (PID: {p.pid}) terminated gracefully")
            except subprocess.TimeoutExpired:
                logger.warning(
                    f"Process {i} (PID: {p.pid}) did not terminate, forcing kill"
                )
                try:
                    p.kill()
                    logger.debug(f"Process {i} killed with p.kill()")
                except Exception as e:
                    logger.error(f"Failed to kill process {i}: {e}")
                    try:
                        subprocess.run(
                            ["taskkill", "/F", "/T", "/PID", str(p.pid)],
                            capture_output=True,
                            timeout=5,
                        )
                        logger.debug(f"Process {i} killed with taskkill")
                    except Exception as e2:
                        logger.error(f"Taskkill also failed for process {i}: {e2}")
            except Exception as e:
                logger.error(f"Error waiting for process {i}: {e}")

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
                    capture_output=True,
                    timeout=3,
                )
                if result.returncode == 0:
                    logger.debug("scrcpy-server killed successfully")
                else:
                    logger.debug(
                        f"pkill scrcpy-server returned {result.returncode} (may not have been running)"
                    )
            except subprocess.TimeoutExpired:
                logger.warning("Timeout killing scrcpy-server")
            except Exception as e:
                logger.warning(f"Error killing scrcpy-server: {e}")

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
                    capture_output=True,
                    timeout=3,
                )
                if result.returncode == 0:
                    logger.debug("app_process killed successfully")
                else:
                    logger.debug(
                        f"pkill app_process returned {result.returncode} (may not have been running)"
                    )
            except subprocess.TimeoutExpired:
                logger.warning("Timeout killing app_process")
            except Exception as e:
                logger.warning(f"Error killing app_process: {e}")

            # Remove port forwards
            try:
                logger.debug("Removing ADB port forwards")
                subprocess.run(
                    [self.adb_bin, "-s", self.serial, "forward", "--remove-all"],
                    capture_output=True,
                    timeout=3,
                )
                logger.debug("Port forwards removed")
            except Exception as e:
                logger.warning(f"Error removing port forwards: {e}")

            # Remove reverse forwards
            try:
                logger.debug("Removing ADB reverse forwards")
                subprocess.run(
                    [self.adb_bin, "-s", self.serial, "reverse", "--remove-all"],
                    capture_output=True,
                    timeout=3,
                )
                logger.debug("Reverse forwards removed")
            except Exception as e:
                logger.warning(f"Error removing reverse forwards: {e}")

            logger.info("Device-side cleanup complete")
        else:
            if not self.serial:
                logger.debug("Skipping device cleanup: no serial")
            if not self.adb_bin:
                logger.debug("Skipping device cleanup: no ADB binary")

        logger.info("ScrcpyManager stopped successfully")
        logger.info("=" * 60)
