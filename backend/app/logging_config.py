"""Application logging setup for process-managed deployments."""

import logging

APPLICATION_LOGGER_NAME = "app"
APPLICATION_HANDLER_NAME = "stashive-console"


def configure_application_logging() -> None:
    """Make application INFO logs visible without duplicating handlers."""
    logger = logging.getLogger(APPLICATION_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if any(handler.get_name() == APPLICATION_HANDLER_NAME for handler in logger.handlers):
        return

    handler = logging.StreamHandler()
    handler.set_name(APPLICATION_HANDLER_NAME)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
