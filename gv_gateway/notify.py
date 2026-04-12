import logging
import subprocess

log = logging.getLogger(__name__)


def send(title: str, body: str) -> None:
    result = subprocess.run(["notify-send", title, body])
    if result.returncode != 0:
        log.warning("notify-send failed (rc=%d)", result.returncode)
