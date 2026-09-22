import os
import sys
from types import SimpleNamespace
from typing import Any, Callable, Iterable
from pathlib import Path
import shutil
import shlex
from functools import wraps
from contextlib import contextmanager
from webber.context import context

# iterator interceptor
def intercept(it:Iterable[Any], visit:Callable[[Any], None]|None=None):
	for e in it:
		if callable(visit):
			visit(e)
		yield e


# Decorator to handle BrokenPipeError gracefully by redirecting stdout and stderr to /dev/null
def handle_broken_pipe(func:Callable[..., Any]) -> Callable[..., Any]:
	@wraps(func)
	def wrapper(*args, **kwargs):
		try:
			return func(*args, **kwargs)
		except BrokenPipeError:
			devnull = os.open(os.devnull, os.O_WRONLY)
			os.dup2(devnull, sys.stdout.fileno())
			os.dup2(devnull, sys.stderr.fileno())
			sys.exit(0)
	return wrapper


def get_terminal_size() -> tuple[int, int]:
	# Try to get terminal size from environment variables first
	try:
		return (int(os.environ['COLUMNS']), int(os.environ['LINES']))
	except:
		pass

	# Try to get terminal size from the controlling terminal (/dev/tty)
	try:
		with open('/dev/tty') as f:
			return os.get_terminal_size(f.fileno())
	except:
		pass

	# Try to get terminal size from the standard error file descriptor
	try:
		return os.get_terminal_size(sys.stderr.fileno())
	except:
		pass

	# Fallback to default size
	# This will return the terminal size based on the environment or default to (80, 24) if unavailable
	return shutil.get_terminal_size()


@contextmanager
def terminal_resize_handler(f):
	import signal
	import asyncio
	def resize_handler(signum, frame):
		asyncio.create_task(f)
	try:
		signal.signal(signal.SIGWINCH, resize_handler)
		yield
	finally:
		signal.signal(signal.SIGWINCH, signal.SIG_DFL)


def first_truthy(*args) -> Any:
	for arg in args:
		if arg:
			return arg
	return None


def doc(text:str) -> Callable:
	def decorator(f):
		f.__doc__ = text
		return f
	return decorator


def clip_string(s:str, max_length:int):
	if len(s) > max_length:
		return s[:max(max_length-7, 0)] + "..."
	return s


@context
def make_config_filename(extension:str):
	appname = make_config_filename.__context__.appname
	return str(Path(f"~/.{appname}{extension}").expanduser().resolve())


# Function to set a breakpoint conditionally based on a callable that returns a boolean
def set_breakpoint(f:Callable[[], bool]|None=None) -> None:
	if not callable(f) or f():
		breakpoint()


# Function to restart the application, optionally excluding certain command-line arguments
def restart(args:SimpleNamespace, exclude:list[str]):
	print("Restarting application...")
	python = sys.executable
	positional_keys = getattr(args, '_positionals', [])
	positionals = [getattr(args, e) for e in positional_keys]
	d = {
		k:v for k,v in vars(args).items()
		if k not in exclude and k not in positional_keys and not k.startswith('_')
		}
	with_values = [
		f"--{k}={shlex.quote(str(v))}"
		for k,v in d.items()
		if not isinstance(v, bool)
		]
	without_values = [
		f"--{k}"
		for k,v in d.items()
		if isinstance(v, bool) and v
		]
	elements = [sys.argv[0], *with_values, *without_values, *positionals]
	os.execl(python, python, *elements)


def make_absolute_url(base:str, url:str) -> str:
	from urllib import parse
	if parse.urlparse(url).netloc:
		return url
	return parse.urljoin(base, url)
