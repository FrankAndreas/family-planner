import logging


def configure() -> None:
    """Logs to stdout (seen in Container Manager). httpx and httpcore log every request with its full URL at INFO and
    DEBUG, and a Google secret address is a password: they only get to say warnings."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    for name in ("httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)
