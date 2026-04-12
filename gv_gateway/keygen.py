import logging
from gv_gateway.config import load_config
from gv_gateway.keys import generate_key, email_key

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)


def run() -> None:
    config = load_config()
    word = generate_key()
    email_key(word, config)
    log.info("Key rotated and emailed to %s", config.personal_email)


if __name__ == "__main__":
    run()
