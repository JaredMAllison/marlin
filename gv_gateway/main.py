import time
import logging
from gv_gateway.config import load_config
from gv_gateway import imap, router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)


def run() -> None:
    config = load_config()
    log.info("gv-gateway started — polling every %ds", config.poll_interval_seconds)
    while True:
        try:
            for message in imap.fetch_messages(config):
                log.info("Received: %s", message[:60])
                router.route(message, config)
        except Exception as e:
            log.error("Poll error: %s", e)
        time.sleep(config.poll_interval_seconds)


if __name__ == "__main__":
    run()
