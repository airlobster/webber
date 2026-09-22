import os
from prompt_toolkit.history import FileHistory
from webber.utils import make_config_filename

class WebberTuiHistory(FileHistory):
	def __init__(self):
		super().__init__(make_config_filename(".history"))
		# Load existing strings to find the last item if the file already exists
		loaded_strings = list(self.load_history_strings())
		self._last_string = loaded_strings[-1] if loaded_strings else None

	def append_string(self, s:str) -> None:
		if s and s != self._last_string:
			super().append_string(s)
			self._last_string = s

	def reset(self):
		self._last_string = None
		WebberTuiHistory.delete_file()

	@staticmethod
	def delete_file():
		histname = make_config_filename(".history")
		if os.path.exists(histname):
			os.remove(histname)
