from webber.algorithms.stack import Stack
from webber import log

class Breadcrumbs(Stack):
	def __init__(self, *args, delimiter='.', **kwargs):
		super().__init__(*args, **kwargs)
		self._delimiter = delimiter

	def __repr__(self):
		return f"Breadcrumbs({self._delimiter.join(str(item) for item in self._items)})"

	def __str__(self):
		return self._delimiter.join(str(item) for item in self._items)

	def push(self, item):
		r = super().push(item)
		log.debug(repr(self))
		return r

	def pop(self):
		r = super().pop()
		log.debug(repr(self))
		return r
