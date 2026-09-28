from prompt_toolkit.layout import BufferControl


class NoCursorBufferControl(BufferControl):
	def create_content(self, width, height):
		content = super().create_content(width, height)
		content.show_cursor = False
		return content
