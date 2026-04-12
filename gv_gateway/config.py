import yaml
from dataclasses import dataclass
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "marlin" / "gv_gateway.yml"


@dataclass
class Config:
    gmail_address: str
    gmail_app_password: str
    personal_email: str
    inbox_path: Path
    poll_interval_seconds: int = 60


def load_config(path: Path = CONFIG_PATH) -> Config:
    with open(path) as f:
        data = yaml.safe_load(f)
    return Config(
        gmail_address=data["gmail_address"],
        gmail_app_password=data["gmail_app_password"],
        personal_email=data["personal_email"],
        inbox_path=Path(data["inbox_path"]),
        poll_interval_seconds=data.get("poll_interval_seconds", 60),
    )
