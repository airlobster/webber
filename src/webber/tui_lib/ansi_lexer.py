from prompt_toolkit.lexers import Lexer
from prompt_toolkit.formatted_text import to_formatted_text, ANSI as ptk_ansi


class AnsiBufferLexer(Lexer):
	def __init__(self, get_colored_line=None):
		super().__init__()
		self.get_colored_line = get_colored_line

	def lex_document(self, document):
		def get_line(lineno):
			if self.get_colored_line:
				ft = to_formatted_text(ptk_ansi(self.get_colored_line(lineno)))
			else:
				ft = to_formatted_text(ptk_ansi(document.lines[lineno]))
			# consolidate consecutive fragments with the same style
			new_fragments = []
			prev_style = ''
			buf = []
			for style, text in ft:
				if style != prev_style:
					if buf:
						new_fragments.append((prev_style, ''.join(buf)))
						buf.clear()
					prev_style = style
				buf.extend(list(text))
			# leftovers
			if buf:
				new_fragments.append((prev_style, ''.join(buf)))
			return new_fragments
		return get_line
