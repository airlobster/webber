import sys
import logging


logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    )


def get_levels():
	return list(logging.getLevelNamesMapping().keys())


def set_global_level(level:str):
	logging.getLogger().setLevel(logging.getLevelNamesMapping().get(level.upper()))


def create_logger(name=None):
	logger = logging.getLogger(name)
	return logger
