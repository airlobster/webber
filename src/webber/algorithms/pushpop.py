from abc import ABC, abstractmethod
from typing import Any, Callable

class PushPopContainer(ABC):
	def __init__(self, *args):
		self._items = []
		for e in args:
			self.push(e)

	def __len__(self) -> int:
		return len(self._items)

	def __bool__(self) -> bool:
		return len(self) > 0

	def __next__(self):
		if not self:
			raise StopIteration
		return self.pop()

	@abstractmethod
	def push(self, item: Any) -> Any:
		pass

	@abstractmethod
	def pop(self, defaultvalue:Any=None) -> Any:
		pass

	@abstractmethod
	def peek(self, defaultvalue:Any=None) -> Any:
		pass

	def pop_until(self, f: Callable[[Any], bool]) -> None:
		while self and not f(self.pop()):
			pass

	def peek(self, defaultvalue:Any=None) -> Any:
		if len(self) == 0:
			if defaultvalue != None:
				return defaultvalue
			raise IndexError("peek from empty stack")
		return self._items[-1]

	def clear(self):
		self._items.clear()

	def find(self, f: Callable[[Any], bool]) -> Any:
		return next((item for item in self._items if f(item)), None)

	def includes(self, f: Callable[[Any], bool]) -> bool:
		return any(f(item) for item in self._items)
