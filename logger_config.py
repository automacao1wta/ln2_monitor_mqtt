import logging
from datetime import datetime
from sys import stdout


def setup_logger(name=__name__):
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Create handler and set level
    handler = logging.StreamHandler(stdout)

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Add formatter to ch
    handler.setFormatter(formatter)

    # Add ch to logger
    logger.addHandler(handler)

    return logger

# Configure logger
logger = setup_logger()
