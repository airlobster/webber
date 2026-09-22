from typing import Callable
from types import SimpleNamespace
import shlex
import re


class CommandBindings:
	def __init__(self):
		self.commands = {}

	# decorator for command handlers
	def add(self, cmd:str, help:str=None) -> Callable:
		def decorator(f:Callable):
			if cmd in self.commands:
				raise ValueError(f"Command '{cmd}' is already registered.")
			self.commands[cmd] = f
			if help:
				f.__doc__ = help
			return f
		return decorator

	# Retrieve all registered command names
	def get_commands(self):
		return self.commands.keys()

	def get_help_info(self) -> tuple:
		return tuple(
			SimpleNamespace(cmd=cmd, help=f.__doc__)
			for cmd, f in sorted(self.commands.items(), key=lambda e: e[0])
		)

	# Parse a command string and return a callable that executes the command
	def parse_command(self, command:str) -> Callable[..., None]:
		elements = shlex.split(command.strip())
		if not elements:
			return None
		cmd, *args = elements
		if cmd not in self.commands:
			# treat it as a URL or link
			args = [cmd, *args]
			cmd = 'navigate'
		return lambda: self.commands[cmd](*args)
