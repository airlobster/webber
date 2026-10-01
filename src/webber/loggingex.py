import sys
from functools import wraps
import logging
from webber.ansi import ANSI


class ColoredFormatter(logging.Formatter):
	colors = {
		logging.NOTSET: "",
		logging.DEBUG: ANSI.FG_HEX("#888888"),
		logging.INFO: ANSI.FG_HEX("#00CC00"),
		logging.WARN: ANSI.FG_HEX("#FFCC00"),
		logging.WARNING: ANSI.FG_HEX("#FFCC00"),
		logging.ERROR: ANSI.FG_HEX("#CC0000"),
		logging.FATAL: ANSI.FG_HEX("#CC00CC"),
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


def get_logger(name=None):
	logger = logging.getLogger(name)
	return logger


def logged(logger):
	def decorator(func):
		@wraps(func)
		def wrapper(*args, **kwargs):
			_args_repr = ', '.join([*map(str, args), *(f"{k}={str(v)}" for k,v in kwargs.items())])
			logger.debug(f"Entering {func.__name__}({_args_repr})")
			result = func(*args, **kwargs)
			logger.debug(f"Exiting {func.__name__}({_args_repr})")
			return result
		return wrapper
	return decorator


__init()
