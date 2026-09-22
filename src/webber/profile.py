from time import perf_counter
from functools import wraps
from tabulate import tabulate
from webber.utils import get_terminal_size

_stats = {}

def profiled(func):
	global _stats
	name = f"{func.__module__}.{func.__name__}"
	_stats.setdefault(name, {"count": 0, "total_time": 0.0, "description": func.__doc__})
	@wraps(func)
	def wrapper(*args, **kwargs):
		start = perf_counter()
		result = func(*args, **kwargs)
		end = perf_counter()
		_stats[name]["count"] += 1
		_stats[name]["total_time"] += (end - start)
		return result
	return wrapper


def get_prof_table(ndecimal:int=4):
	t = [
		['Function', 'Description', 'Call Count', 'Total Time', 'Average Time'],
		*[ [
					k,
					v['description'],
					v['count'],
					round(v['total_time'],ndecimal),
					round(v['total_time']/v['count'],ndecimal) if v['count'] > 0 else 0.0
				]
				for k, v in _stats.items()
			]
	]
	return t


def print_prof_table(t: list[list]):
	w,_ = get_terminal_size()
	ncols = len(t[0])
	colwidth = w / ncols - 1
	print(
		tabulate(
			sorted(t[1:], key=lambda x: x[4], reverse=True),
			headers=t[0],
			tablefmt="grid",
			maxcolwidths=[colwidth]*ncols
		)
	)
