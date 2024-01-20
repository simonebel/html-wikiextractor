import logging
from pathlib import Path

from conf import SRC_DIR


def _get_name(file: str) -> str:
    path = Path(file)
    name = []
    while path.name != "src":
        name.append(path.name)
        path = path.parent

    return "/".join(name)


def get_log(filename: str):
    name = _get_name(filename)

    level = logging.INFO
    logger = logging.getLogger(name)
    logger.setLevel(level)

    formatter = logging.Formatter(
        "[%(levelname)s] - %(asctime)s - %(name)s:%(lineno)d: %(message)s"
    )
    default_handler = logging.StreamHandler()
    default_handler.setFormatter(formatter)
    logger.addHandler(default_handler)

    return logger
