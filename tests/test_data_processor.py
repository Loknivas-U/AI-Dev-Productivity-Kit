import json
import tempfile
import os
from src.data_processor import load_json_file, filter_active_users, calculate_average_score


def test_load_json_file():
    data = {"key": "value", "number": 42}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        tmp_path = f.name
    try:
        result = load_json_file(tmp_path)
        assert result == data
    finally:
        os.unlink(tmp_path)


def test_filter_active_users():
    users = [
        {"name": "Alice", "active": True},
        {"name": "Bob", "active": False},
        {"name": "Carol", "active": True},
    ]
    result = filter_active_users(users)
    assert len(result) == 2
    assert all(u["active"] is True for u in result)


def test_calculate_average_score():
    assert calculate_average_score([10.0, 20.0, 30.0]) == 20.0


def test_calculate_average_score_empty():
    assert calculate_average_score([]) == 0.0
