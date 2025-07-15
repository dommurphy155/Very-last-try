# state_manager.py

import json
import threading
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class StateManager:
    def __init__(self, state_file):
        self.state_file = Path(state_file)
        self.lock = threading.Lock()

    def load_state(self):
        if not self.state_file.exists():
            logger.info("State file not found. Initializing new state.")
            return {
                "open_trades": {},
                "trade_history": [],
                "last_scan": None,
                "cooldown_until": None,
                # Add other necessary default state keys here
            }
        try:
            with self.lock, self.state_file.open("r") as f:
                state = json.load(f)
            logger.info("State loaded successfully.")
            return state
        except Exception as e:
            logger.error(f"Failed to load state file: {e}")
            return {
                "open_trades": {},
                "trade_history": [],
                "last_scan": None,
                "cooldown_until": None,
            }

    def save_state(self, state):
        try:
            with self.lock, self.state_file.open("w") as f:
                json.dump(state, f, indent=2)
            logger.debug("State saved successfully.")
        except Exception as e:
            logger.error(f"Failed to save state file: {e}")