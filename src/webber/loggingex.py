import sys
from functools import wraps
import logging
from webber.ansi import ANSI


class ColoredFormatter(logging.Formatter):
	colors = {
		logging.DEBUG: ANSI.FG_HEX("#888888"),
		logging.INFO: ANSI.FG_HEX("#00CC00"),
		logging.WARNING: ANSI.FG_HEX("#FFCC00"),
		logging.ERROR: ANSI.FG_HEX("#CC0000"),
		logging.CRITICAL: ANSI.FG_HEX("#CC00CC"),
	}
	def format(self, record):
		msg = super().format(record)
		if not sys.stderr.isatty():
			return msg
		color = ColoredFormatter.colors.get(record.levelno, "")
		return f"{color}{msg}{ANSI.RESET}"


def __init():
	logging.basicConfig(
			level=logging.INFO,
			stream=sys.stderr,
	)
	for h in logging.getLogger().handlers:
		h.setFormatter(ColoredFormatter())


def get_levels():
	return list(logging.getLevelNamesMapping().keys())


def set_global_level(level:str):
	logging.getLogger().setLevel(logging.getLevelNamesMapping().get(level.upper()))


def create_logger(name=None):
	logger = logging.getLogger(name)
	return logger


def logged(level:str):
	def decorator(func):
		@wraps(func)
		def wrapper(*args, **kwargs):
			logger = create_logger(func.__module__)
			log_method = getattr(logger, level.lower(), logger.info)
			log_method(f"Entering {func.__name__}")
			result = func(*args, **kwargs)
			log_method(f"Exiting {func.__name__}")
			return result
		return wrapper
	return decorator


__init()
