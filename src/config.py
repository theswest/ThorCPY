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

# src/config.py
import json
import os
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages global configuration settings"""

    def __init__(self, path):
        self.path = path
        logger.info(f"Initializing ConfigManager with path: {path}")

        # Ensure directory exists
        try:
            dir_path = os.path.dirname(self.path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create config directory: {e}", exc_info=True)
            raise

    def load(self):
        """Load config from disk"""
        if not os.path.exists(self.path):
            logger.debug(f"Config file does not exist: {self.path}, returning defaults")
            return {}

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                config = json.load(f)
            logger.debug(f"Loaded config: {config}")
            return config
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error reading {self.path}: {e}", exc_info=True)
            return {}
        except Exception as e:
            logger.error(f"Error loading config: {e}", exc_info=True)
            return {}

    def save(self, config):
        """Save config to disk"""
        try:
            logger.info(f"Saving config: {config}")
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
            logger.info("Config saved successfully")
        except Exception as e:
            logger.error(f"Failed to save config: {e}", exc_info=True)
            raise

    def get(self, key, default=None):
        """Get a config value"""
        config = self.load()
        return config.get(key, default)

    def set(self, key, value):
        """Set a config value"""
        config = self.load()
        config[key] = value
        self.save(config)
