import logging.config

cfg = {
    "disable_existing_loggers": False,
    "version": 1,
    "formatters": {
        "short": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "formatter": "short",
            "class": "logging.StreamHandler",
        }
    },
    "loggers": {
        "BBChat": {"handlers": ["console"], "level": "DEBUG"},
        "plugins": {"handlers": ["console"], "level": "DEBUG"},
    },
}


def config():
    logging.config.dictConfig(cfg)
