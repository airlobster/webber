import sys
from functools import wraps
import logging
import time
from webber.ansi import ANSI
from webber.context import get_context


class ColoredFormatter(logging.Formatter):
	colors = {
		logging.NOTSET: "",
		logging.DEBUG: ANSI.FG_HEX("#888888"),
		logging.INFO: ANSI.FG_HEX("#00AAFF"),
		logging.WARN: ANSI.FG_HEX("#FFCC00"),
		logging.WARNING: ANSI.FG_HEX("#FFCC00"),
		logging.ERROR: ANSI.FG_HEX("#CC0000"),
		logging.FATAL: ANSI.FG_HEX("#CC00CC"),
		logging.CRITICAL: ANSI.FG_HEX("#CC00CC"),
	}
	log_fmt = "%(name)s|%(levelname)s|%(message)s"

	def format(self, record):
		use_colors = sys.stderr.isatty() or get_context().args.colors == "always"
		if not use_colors:
			return logging.Formatter(ColoredFormatter.log_fmt).format(record)
		s = ColoredFormatter.colors.get(record.levelno, "") + ColoredFormatter.log_fmt + ANSI.RESET
		formatter = logging.Formatter(s)
		return formatter.format(record)


def __init():
	logging.basicConfig(level=logging.INFO)
	logging.getLogger().handlers.clear()
	h = logging.StreamHandler(sys.stderr)
	h.setFormatter(ColoredFormatter())
	logging.getLogger().addHandler(h)


def measure_time():
	start_time = time.perf_counter()
	def stop():
		nonlocal start_time
		return time.perf_counter() - start_time
	return stop


def get_levels():
	return list(logging.getLevelNamesMapping().keys())


def set_global_level(level:str):
	logging.getLogger().setLevel(logging.getLevelNamesMapping().get(level.upper()))


def get_logger(name=None):
	logger = logging.getLogger(name)
	return logger


def logged(logger, level:str="DEBUG"):
	def decorator(func):
		@wraps(func)
		def wrapper(*args, **kwargs):
			method = getattr(logger, level.lower(), logger.debug)
			_args_repr = ', '.join([*map(str, args), *(f"{k}={str(v)}" for k,v in kwargs.items())])
			method(f"Entering {func.__name__}({_args_repr})")
			timer = measure_time()
			result = func(*args, **kwargs)
			method(f"Exiting {func.__name__}({_args_repr}) (took {timer():.4f}s)")
			return result
		return wrapper
	return decorator


__init()
