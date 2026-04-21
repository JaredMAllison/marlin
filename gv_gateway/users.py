import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

USERS_PATH = Path.home() / ".config" / "marlin" / "users.json"


@dataclass
class User:
    user_id: str
    key_file: Path
    email: Optional[str]
    broadcast_name: Optional[str]
    ntfy_topic: Optional[str]
    routes: list[str]


def load_users(path: Path = USERS_PATH) -> list["User"]:
    with open(path) as f:
        data = json.load(f)
    return [
        User(
            user_id=uid,
            key_file=Path(cfg["key_file"]).expanduser(),
            email=cfg.get("email"),
            broadcast_name=cfg.get("broadcast_name"),
            ntfy_topic=cfg.get("ntfy_topic"),
            routes=cfg.get("routes", []),
        )
        for uid, cfg in data.items()
    ]
