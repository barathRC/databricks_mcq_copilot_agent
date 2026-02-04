# state_utils.py
import json
from pathlib import Path
from typing import Dict, Any, Optional

STATE_FILE = Path("state.json")


def _load_global_state() -> Dict[str, Any]:
    """Load all users' sessions from state.json."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            return {}
    return {}


def _save_global_state(state: Dict[str, Any]) -> None:
    """Persist all users' sessions to state.json."""
    STATE_FILE.write_text(json.dumps(state, indent=2))


def get_session(username: str, exam_code: str) -> Optional[Dict[str, Any]]:
    """
    Return saved session dict for (username, exam_code), or None.
    Structure in state.json:
    {
      "barath.r": {
        "associate": {...},
        "professional": {...}
      }
    }
    """
    global_state = _load_global_state()
    user_block = global_state.get(username)
    if not isinstance(user_block, dict):
        return None
    return user_block.get(exam_code)


def save_session(username: str, exam_code: str, session: Dict[str, Any]) -> None:
    """
    Persist session for (username, exam_code).
    """
    global_state = _load_global_state()
    user_block = global_state.get(username)
    if not isinstance(user_block, dict):
        user_block = {}
    user_block[exam_code] = session
    global_state[username] = user_block
    _save_global_state(global_state)
