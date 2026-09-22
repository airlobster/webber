from typing import Any
from webber.algorithms.pushpop import PushPopContainer

class Queue(PushPopContainer):
	def __init__(self, *args):
		super().__init__(*args)

	def push(self, item: Any) -> Any:
		self._items.append(item)
		return item

	def pop(self, defaultvalue:Any=None) -> Any:
		if len(self) == 0:
			if defaultvalue != None:
				return defaultvalue
			raise IndexError("pop from empty queue")
		return self._items.pop(0)

	def peek(self, defaultvalue:Any=None) -> Any:
		if len(self) == 0:
			if defaultvalue != None:
				return defaultvalue
			raise IndexError("peek from empty queue")
		return self._items[0]
