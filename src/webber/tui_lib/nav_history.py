
class NavigationHistory:
	def __init__(self):
		self.history = []
		self.index = -1

	def add(self, url):
		if self.index > -1 and self.history[self.index] == url:
			return
		self.history.append(url)
		self.index = len(self.history) - 1

	def back(self):
		if self.index > 0:
			self.index -= 1
			return self.history[self.index]
		return None

	def forward(self):
		if self.index < len(self.history) - 1:
			self.index += 1
			return self.history[self.index]
		return None

	def current(self):
		if 0 <= self.index < len(self.history):
			return self.history[self.index]
		return None
