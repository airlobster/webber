from typing import Iterable, Tuple
import re

def get_searcher(*queries):
	def qfixup(q):
		# Escape regex special characters to keep search literal.
		q = re.sub(r'([.*?+^$[\]\\(){}|-])', r'\\\1', q)
		# if query ends with '!', ensure whole-word matching.
		if q.endswith('!'):
			q = fr"\b{q[:-1]}\b"
		return q

	# create the compiled regular expression for the search queries
	expr = '|'.join([fr"({qfixup(q)})" for q in queries])
	try:
		reQuery = re.compile(expr, re.IGNORECASE | re.MULTILINE | re.DOTALL)
	except re.error as e:
		raise ValueError(f"Invalid regex: {e}") from e

	def searcher(chunks:Iterable[str]) -> Iterable[Tuple[int, int]]:
		raw = ''.join(chunks) # search on the raw content
		for m in reQuery.finditer(raw):
			yield m.span()

	return searcher


class Searcher:
	def __init__(self):
		self.results = []
		self.current_search_index = -1

	def __iter__(self):
		return iter(self.results)

	def __len__(self):
		return len(self.results)

	def __bool__(self):
		return len(self.results) > 0

	def reset(self):
		self.results = []
		self.current_search_index = -1

	def search(self, chunks:Iterable[str], *queries) -> int:
		self.reset()
		searcher = get_searcher(*queries)
		self.results = list(searcher(chunks))
		return len(self.results)

	def next(self) -> Tuple[int, int] | None:
		if not self.results:
			return None
		self.current_search_index = (self.current_search_index + 1) % len(self.results)
		return self.current()

	def previous(self) -> Tuple[int, int] | None:
		if not self.results:
			return None
		self.current_search_index = \
			(self.current_search_index - 1)	if self.current_search_index > 0 \
			else len(self.results) - 1
		return self.current()

	def current(self) -> Tuple[int, int] | None:
		if not self.results:
			return None
		return self.results[self.current_search_index]

	def rel_pos(self) -> Tuple[int, int]:
		if not self.results:
			return (0, 0)
		return (self.current_search_index, len(self.results))
