import logging
import threading
import asyncio

from pythonjsonlogger import jsonlogger

logger = logging.getLogger(__name__)


class JsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)

        try:
            task = asyncio.current_task()
        except RuntimeError:
            task_id = None
        else:
            task_id = id(task)

        if task_id is not None:
            log_record["task_id"] = task_id

        log_record["thread_id"] = threading.get_ident()


def setup_logging(*module_names):
    if not module_names:
        module_names = ("quart_deps", "tests")

    logging.config.dictConfig(
        {
            "version": 1,
            "loggers": {
                module_name: dict(level="INFO", handlers=["console"])
                for module_name in list(module_names) + ["root"]
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "DEBUG",
                    "formatter": "json",
                    "stream": "ext://sys.stdout",
                },
            },
            "formatters": {
                "json": {
                    "format": "%(process)s %(asctime)s %(timestamp)s %(env)s %(zone)s %(levelname)s %(message)s",
                    "()": JsonFormatter,
                    "json_indent": 4,
                },
            },
            "root": {
                "level": "INFO",
                "handlers": ["console"],
            },
        },
    )
