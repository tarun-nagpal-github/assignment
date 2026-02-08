"""
Simple file-based store for user tags (saved filter lists).
"""
import json
from pathlib import Path
from typing import Optional
from uuid import uuid4

STORAGE_PATH = Path(__file__).resolve().parent / "data" / "tags.json"


def _ensure_storage():
    STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not STORAGE_PATH.exists():
        STORAGE_PATH.write_text("{}")


def _load() -> dict:
    _ensure_storage()
    return json.loads(STORAGE_PATH.read_text())


def _save(data: dict) -> None:
    _ensure_storage()
    STORAGE_PATH.write_text(json.dumps(data, indent=2))


def get_tags(user_id: str) -> list[dict]:
    data = _load()
    return data.get(user_id, [])


def create_tag(user_id: str, name: str, filter_snapshot: Optional[dict] = None) -> dict:
    data = _load()
    if user_id not in data:
        data[user_id] = []
    tag = {
        "id": str(uuid4()),
        "name": name,
        "filter_snapshot": filter_snapshot or {},
    }
    data[user_id].append(tag)
    _save(data)
    return tag


def delete_tag(user_id: str, tag_id: str) -> bool:
    data = _load()
    if user_id not in data:
        return False
    before = len(data[user_id])
    data[user_id] = [t for t in data[user_id] if t.get("id") != tag_id]
    if len(data[user_id]) < before:
        _save(data)
        return True
    return False
