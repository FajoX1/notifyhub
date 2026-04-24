import logging
import sys
from pathlib import Path


class CustomFormatter(logging.Formatter):
    FORMATS = {
        logging.DEBUG: "DEBUG: %(name)s - %(message)s",
        logging.INFO: "%(asctime)s - %(name)s - INFO - %(message)s",
        logging.WARNING: "%(asctime)s - %(name)s - WARNING - %(message)s",
        logging.ERROR: "%(asctime)s - %(name)s - ERROR - %(message)s",
        logging.CRITICAL: "%(asctime)s - %(name)s - CRITICAL - %(message)s",
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


def setup_logging():

    logger = logging.getLogger("app.core")
    logger.setLevel(logging.DEBUG)

    logger.propagate = False

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(CustomFormatter())

    log_file = Path("logs/app.log")
    log_file.parent.mkdir(exist_ok=True)

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(CustomFormatter())

    if not logger.handlers:
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    django_logger = logging.getLogger("django")
    django_logger.setLevel(logging.WARNING)

    celery_logger = logging.getLogger("celery")
    celery_logger.setLevel(logging.INFO)

    sql_logger = logging.getLogger("django.db.backends")
    sql_logger.setLevel(logging.WARNING)

    return logger


app_logger = setup_logging()

__all__ = [
    "models",
    "services",
    "selectors",
    "views",
    "utils",
    "responses",
    "tasks",
    "app_logger",
]

__version__ = "1.0.0"
__author__ = "NotifyHub Team"
__description__ = "Modern notification platform with async architecture"
