from __future__ import annotations
import json
from pathlib import Path


def load_json_file(filepath: str) -> dict:
    """Load and parse a JSON file from disk."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def filter_active_users(users: list[dict]) -> list[dict]:
    """Return only users where active is True."""
    return [user for user in users if user.get("active") is True]


def calculate_average_score(scores: list[float]) -> float:
    """Calculate the average of a list of scores."""
    if not scores:
        return 0.0
    return sum(scores) / len(scores)
