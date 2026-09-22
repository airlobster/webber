import sys
from typing import Tuple
import argparse
import shlex

# Custom ArgumentParser that can unparse a SimpleNamespace back into command-line arguments
class UnparsableArgumentParser(argparse.ArgumentParser):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

	def unparse(self, parsed:argparse.Namespace, exclude:Tuple[str]=[]) -> tuple[str, ...]:
		# map destinations to their corresponding option strings
		options = {a.dest:a.option_strings[-1] for a in self._actions if a.option_strings}

		# Identify positional arguments by checking which actions have no option strings
		positional_keys = [action.dest for action in self._actions if not action.option_strings]
		positionals = [getattr(parsed, e) for e in positional_keys]

		# Extract non-positional arguments into a dictionary, excluding specified keys
		d = {
			k:v for k,v in vars(parsed).items()
			if k not in exclude and k not in positional_keys
			}

		# Separate arguments into those with values and boolean flags
		with_values = [
			f"{options[k]}={shlex.quote(str(v))}"
			for k,v in d.items()
			if not isinstance(v, bool)
			]
		without_values = [
			f"{options[k]}"
			for k,v in d.items()
			if isinstance(v, bool) and v
			]

		# Combine all elements into the final command-line argument tuple
		elements = tuple([sys.argv[0], *with_values, *without_values, *positionals])

		return elements
