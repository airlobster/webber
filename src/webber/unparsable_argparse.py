import sys
from types import SimpleNamespace
from typing import Tuple
import argparse
import shlex

# Custom ArgumentParser that can unparse a SimpleNamespace back into command-line arguments
class UnparsableArgumentParser(argparse.ArgumentParser):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

	def unparse(self, parsed:argparse.Namespace, exclude:Tuple[str]=[]) -> tuple[str, ...]:
		def flatten(a):
			if isinstance(a, list):
				for e in a:
					yield from flatten(e)
			else:
				yield shlex.quote(a)

		if exclude is None:
			exclude = []

		# map some important info from non-positional actions to their dest
		dests = {
			a.dest:SimpleNamespace(option=a.option_strings[-1], default=a.default)
			for a in self._actions
			if a.option_strings
			}

		# collect positional arguments into a dictionary
		positionals = {
			a.dest:getattr(parsed, a.dest)
			for a in self._actions
			if not a.option_strings
			}

		# Extract non-positional arguments into a dictionary, excluding specified keys
		# and those that are set to their default value
		d = {
			k:v for k,v in vars(parsed).items()
			if (k not in exclude) and (k not in positionals.keys()) and (v != dests[k].default or dests[k].default == argparse.SUPPRESS)
			}

		# Separate arguments into those with values and boolean flags
		with_values = [
			[ dests[k].option, v ]
			for k,v in d.items()
			if not isinstance(v, bool)
			]
		without_values = [
			f"{dests[k].option}"
			for k,v in d.items()
			if isinstance(v, bool) and v
			]

		# Combine all elements into the final command-line argument tuple
		args_out = tuple([
			shlex.quote(sys.argv[0]),
			*flatten(with_values),
			*without_values,
			*positionals.values()
			])

		return args_out
