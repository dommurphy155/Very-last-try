import json
import threading
import logging

logger = logging.getLogger(__name__)


class StateManager:
    def __init__(self, filepath="trade_state.json"):
        self.filepath = filepath
        self.lock = threading.Lock()
        self.state = self.load_state()

    def load_state(self):
        try:
            with open(self.filepath, "r") as f:
                state = json.load(f)
                logger.info("State loaded from file.")
                return state
        except (FileNotFoundError, json.JSONDecodeError):
            logger.warning("State file missing or corrupt; starting fresh.")
            return {"open_trades": {}}

    def save_state(self):
        try:
            with self.lock:
                with open(self.filepath, "w") as f:
                    json.dump(self.state, f, indent=4)
            logger.debug("State saved to file.")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def get(self, key, default=None):
        return self.state.get(key, default)

    def set(self, key, value):
        self.state[key] = value
        self.save_state()
