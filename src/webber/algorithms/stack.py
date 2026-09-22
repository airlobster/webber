from typing import Any
from webber.algorithms.pushpop import PushPopContainer
from webber import log

class Stack(PushPopContainer):
	def __init__(self, *args):
		super().__init__(*args)

	def push(self, item: Any) -> Any:
		self._items.append(item)
		return item

	def pop(self, defaultvalue:Any=None, guard=None) -> Any:
		if len(self) == 0:
			log.warning("Attempted to pop from an empty stack.")
			return defaultvalue
		if guard is not None and self._items[-1] != guard:
			log.warning(f"Attempted to pop from the stack with guard {guard}, but the top item is {self._items[-1]}.")
			return defaultvalue
		return self._items.pop()

	def peek(self, defaultvalue:Any=None) -> Any:
		if len(self) == 0:
			log.warning("Attempted to peek from an empty stack.")
			return defaultvalue
		return self._items[-1]
