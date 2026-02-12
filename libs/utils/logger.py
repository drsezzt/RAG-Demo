import logging
import sys

from shared.config import get_app_config

def init_component_logger(name):
    logger = logging.getLogger(name)
    app_config = get_app_config()

    if not logger.handlers:
        formatter = logging.Formatter(app_config.log_format)

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)

        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    return logger