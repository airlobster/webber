import sys
import sys
import shutil
from contextlib import contextmanager
from webber.ansi import ANSI

class COLOR_CAT:
	INFO = ANSI.FG_256(111)
	WARNING = ANSI.FG_256(214)
	ERROR = ANSI.FG_256(167)
	TITLE = f"{ANSI.BOLD}{ANSI.REVERSED}{ANSI.FG_8(97)}"
	QUOTE = ANSI.FG_256(151)

levels = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "TRACE"]

color_mode = "auto"
level = levels.index("INFO")

def set_level(log_level:str):
	global level
	idx = levels.index(log_level.upper())
	if idx < 0:
		raise ValueError(f"Invalid log level: {log_level}")
	level = idx

def leveled(f):
	def wrapper(*args, **kwargs):
		if levels.index(f.__name__.upper()) > level:
			return
		return f(*args, **kwargs)
	return wrapper


@contextmanager
def color(color_code:str="", file=sys.stderr):
	"""
	Context manager to temporarily change the text color in the console.
	Args:
			file: The file object (e.g., sys.stdout or sys.stderr) to which the color change will be applied.
			color_code (str): The ANSI color code to set the text color.
	"""
	if color_mode == "always":
		colorize = True
	elif color_mode == "never":
		colorize = False
	elif color_mode == "auto":
		colorize = file.isatty() if hasattr(file, 'isatty') else False
	try:
		if colorize:
			print(f"{color_code}{ANSI.ITALIC}", file=file, end='')  # Set text color
		yield
	finally:
		if colorize:
			print(f"{ANSI.RESET}", file=file, end='')  # Reset text color
		print(file=file, end='', flush=True)

@leveled
def debug(*args, **kwargs):
		"""
		Logs the provided arguments to the console.
		Args:
				*args: Variable length argument list to be logged.
				**kwargs: Arbitrary keyword arguments to be logged.
		"""
		file = kwargs.get('file', sys.stderr)
		with color(ANSI.DIM, file=file):
			print(*args, **{**kwargs, 'file': file})


@leveled
def trace(*args, **kwargs):
		"""
		Logs the provided arguments to the console.
		Args:
				*args: Variable length argument list to be logged.
				**kwargs: Arbitrary keyword arguments to be logged.
		"""
		file = kwargs.get('file', sys.stderr)
		with color(file=file):
			print(*args, **{**kwargs, 'file': file})


@leveled
def error(*args, **kwargs):
		"""
		Logs the provided arguments to the console in red color to indicate an error.
		Args:
				*args: Variable length argument list to be logged.
				**kwargs: Arbitrary keyword arguments to be logged.
		"""
		file = kwargs.get('file', sys.stderr)
		with color(COLOR_CAT.ERROR, file=file):
			print(*args, **{**kwargs, 'file': file})


@leveled
def warning(*args, **kwargs):
		"""
		Logs the provided arguments to the console in yellow color to indicate a warning.
		Args:
				*args: Variable length argument list to be logged.
				**kwargs: Arbitrary keyword arguments to be logged.
		"""
		file = kwargs.get('file', sys.stderr)
		with color(COLOR_CAT.WARNING, file=file):
			print(*args, **{**kwargs, 'file': file})


@leveled
def info(*args, **kwargs):
		"""
		Logs the provided arguments to the console in blue color to indicate informational messages.
		Args:
				*args: Variable length argument list to be logged.
				**kwargs: Arbitrary keyword arguments to be logged.
		"""
		file = kwargs.get('file', sys.stderr)
		with color(COLOR_CAT.INFO, file=file):
			print(*args, **{**kwargs, 'file': file})


def auto(*args, **kwargs):
		"""
		Logs the provided arguments to the console in default color.
		Use incoming colors if any, otherwise use ANSI.INFO.
		Args:
				*args: Variable length argument list to be logged.
				**kwargs: Arbitrary keyword arguments to be logged.
		"""
		file = kwargs.get('file', sys.stderr)
		has_colors = any('\033[' in a for a in args if isinstance(a, str))
		with color("" if has_colors else COLOR_CAT.INFO, file=file):
			print(*args, **{**kwargs, 'file': file})


def separator(file=sys.stderr):
		"""
		Prints a separator line to the console for better readability.
		"""
		w = shutil.get_terminal_size().columns
		trace("-" * (w-2), file=file)


@contextmanager
def block(header:str, file=sys.stderr, func=trace):
		"""
		Context manager to create a block of log messages with a header.
		Args:
				header (str): The header of the block.
				file: The file to which the block should be logged.
				func: The function to use for printing the block header. Defaults to `trace`.
		"""
		func(file=file)
		with color(COLOR_CAT.TITLE, file=file):
			w = shutil.get_terminal_size().columns
			func(f"** {header:<{w-4}}", file=file)
		try:
			yield
		finally:
			pass
