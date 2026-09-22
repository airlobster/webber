from typing import Callable
from prompt_toolkit.completion import Completer, Completion

class DynamicCompleter(Completer):
	def __init__(self, words_callback:Callable[[], list[str]]):
		super().__init__()
		self.words_callback = words_callback

	def get_completions(self, document, complete_event):
			text_before_cursor = document.text_before_cursor
			if not text_before_cursor:
				return
			dynamic_words = self.words_callback()
			for word in dynamic_words:
				if text_before_cursor.lower() in word.lower():
					yield Completion(word, start_position=-len(text_before_cursor))
