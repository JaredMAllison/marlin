import logging
from gv_gateway.config import load_config
from gv_gateway.keys import generate_key, email_key
from gv_gateway.users import load_users

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)


def run() -> None:
    config = load_config()
    users = load_users()
    for user in users:
        word = generate_key(key_path=user.key_file)
        if user.email:
            email_key(word, user, config)
            log.info("Key rotated and emailed to %s (%s)", user.email, user.user_id)
        else:
            log.info("Key rotated for %s (no email configured)", user.user_id)


if __name__ == "__main__":
    run()
