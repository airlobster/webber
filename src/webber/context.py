from types import SimpleNamespace
from functools import wraps

__context = SimpleNamespace()

def set_context(**kwargs):
	for key, value in kwargs.items():
		setattr(__context, key, value)


# decorator to attach the global context to a function or class
def context(f):
	global __context
	f.__context__ = __context
	return f

def dynamic_context(f):
	global __context
	f.__get_context__ = lambda key: getattr(__context, key, None)
	return f
