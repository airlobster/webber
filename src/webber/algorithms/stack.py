from typing import Any
from webber.algorithms.pushpop import PushPopContainer

class Stack(PushPopContainer):
	def __init__(self, *args):
		super().__init__(*args)

	def push(self, item: Any) -> Any:
		self._items.append(item)
		return item

	def pop(self, defaultvalue:Any=None) -> Any:
		if len(self) == 0:
			if defaultvalue != None:
				return defaultvalue
			raise IndexError("pop from empty stack")
		return self._items.pop()

	def peek(self, defaultvalue:Any=None) -> Any:
		if len(self) == 0:
			if defaultvalue != None:
				return defaultvalue
			raise IndexError("peek from empty stack")
		return self._items[-1]
