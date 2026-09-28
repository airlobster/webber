from prompt_toolkit.lexers import Lexer
from prompt_toolkit.formatted_text import to_formatted_text, ANSI as ptk_ansi


class AnsiBufferLexer(Lexer):
	def __init__(self, get_colored_line=None):
		super().__init__()
		self.get_colored_line = get_colored_line

	def lex_document(self, document):
		def get_line(lineno):
			if self.get_colored_line:
				return to_formatted_text(ptk_ansi(self.get_colored_line(lineno)))
			return to_formatted_text(ptk_ansi(document.lines[lineno]))
		return get_line
