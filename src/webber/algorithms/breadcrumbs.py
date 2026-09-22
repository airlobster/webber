from webber.algorithms.stack import Stack

class Breadcrumbs(Stack):
	def __init__(self, *args, delimiter='.', **kwargs):
		super().__init__(*args, **kwargs)
		self._delimiter = delimiter

	def __repr__(self):
		return f"Breadcrumbs({self._delimiter.join(str(item) for item in self._items)})"

	def __str__(self):
		return self._delimiter.join(str(item) for item in self._items)
