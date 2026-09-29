from types import SimpleNamespace
from functools import wraps

__context = SimpleNamespace()

def set_context(**kwargs):
	for key, value in kwargs.items():
		setattr(__context, key, value)

def get_context(key=None, default=None):
	if key is None:
		return __context
	return getattr(__context, key, default)
