from typing import Dict, Iterable
from types import SimpleNamespace
import re
from webber.context import context
from webber.ansi import ANSI

##############################################################################

def json_lexer(tab_width:int=4):
	token_types = {
		"WS": r"[ \t\n]",
		"OPEN_ARRAY": r"\[",
		"CLOSE_ARRAY": r"\]",
		"OPEN_OBJECT": r"\{",
		"CLOSE_OBJECT": r"\}",
		"TRUE": r"true",
		"FALSE": r"false",
		"NULL": r"null",
		"COMMA": r",",
		"COLON": r":",
		"STRING": r'(?<=")(\\.|[^"\\])*(?=")',
		"NUMBER": r"-?\d+(\.\d+)?([eE][+-]?\d+)?",
	}
	expr = "|".join(f"(?P<{name}>{pattern})" for name, pattern in token_types.items())
	regex = re.compile(expr, re.DOTALL | re.MULTILINE)
	row = 1
	col = 1

	def generate_tokens(s:str):
		def update_position(value):
			nonlocal row, col
			for c in value:
				if c == "\n":
					row += 1
					col = 1
				elif c == "\t":
					col += tab_width - (col % tab_width)
				else:
					col += 1
		for match in regex.finditer(s):
			for name, value in match.groupdict().items():
				if value is None:
					continue
				if name == "WS":
					update_position(value)
					continue # aside from updating the position, ignore whitespaces
				yield SimpleNamespace(type=name, value=value, pos=(row, col))
				update_position(value)

	return generate_tokens

##############################################################################

class CachedIterator:
	def __init__(self, iterable: Iterable):
		self.iterable = iter(iterable)
		self.q = []

	def __iter__(self):
		return self

	def __next__(self):
		if self.q:
			return self.q.pop(0)
		return next(self.iterable)

	def unget(self, value):
		self.q.append(value)

##############################################################################

def json_parser(tokens:Iterable[SimpleNamespace]):
	it = iter(CachedIterator(tokens))

	def expect(token, *expected_types):
		if token.type not in expected_types:
			raise ValueError(f"Expected token types {expected_types}, got {token.type}")
		return token

	def parse_value():
		token = next(it)
		if token.type == "OPEN_ARRAY":
			it.unget(token)
			yield from parse_array()
		elif token.type == "OPEN_OBJECT":
			it.unget(token)
			yield from parse_object()
		elif token.type in ("TRUE", "FALSE", "NULL", "NUMBER", "STRING"):
			yield token
		else:
			raise ValueError(f"Unexpected token: {token}")

	def parse_object():
		yield expect(next(it), "OPEN_OBJECT")
		yield from parse_object_members()
		yield expect(next(it), "CLOSE_OBJECT")

	def parse_object_members():
		while True:
			token = next(it)
			if token.type == "CLOSE_OBJECT":
				it.unget(token)
				break
			it.unget(token)
			yield SimpleNamespace(type="BEGIN_OBJECT_MEMBER", value=None)
			yield from parse_object_member()
			token = next(it)
			if token.type == "COMMA":
				yield token
				yield SimpleNamespace(type="END_OBJECT_MEMBER", value=None)
				continue
			yield SimpleNamespace(type="END_OBJECT_MEMBER", value=None)
			it.unget(token)

	def parse_object_member():
		yield SimpleNamespace(type="KEY", value=expect(next(it), "STRING").value) # key
		yield expect(next(it), "COLON")
		yield from parse_value()

	def parse_array():
		yield expect(next(it), "OPEN_ARRAY")
		yield from parse_array_elements()
		yield expect(next(it), "CLOSE_ARRAY")

	def parse_array_elements():
		while True:
			token = next(it)
			if token.type == "CLOSE_ARRAY":
				it.unget(token)
				break
			it.unget(token)
			yield SimpleNamespace(type="BEGIN_ARRAY_ELEMENT", value=None)
			yield from parse_value()
			token = next(it)
			if token.type == "COMMA":
				yield token
				yield SimpleNamespace(type="END_ARRAY_ELEMENT", value=None)
				continue
			yield SimpleNamespace(type="END_ARRAY_ELEMENT", value=None)
			it.unget(token)

	yield from parse_value()

##############################################################################

@context
def json_render(tokens:Iterable[SimpleNamespace], indent:str|int=4):
	indent = " " * indent if isinstance(indent, int) else indent
	palette = getattr(json_render.__context__.config.palette, "json", SimpleNamespace())
	nest = 0
	for token in tokens:
		color = getattr(palette, token.type, '')
		yield color
		if token.type in ("OPEN_ARRAY", "OPEN_OBJECT"):
			yield token.value
			nest += 1
		elif token.type in ("CLOSE_ARRAY", "CLOSE_OBJECT"):
			nest -= 1
			yield f"\n{indent * nest}"
			yield color # re-apply color after '\n'
			yield token.value
		elif token.type in ("BEGIN_OBJECT_MEMBER", "BEGIN_ARRAY_ELEMENT"):
			yield f"\n{indent * nest}"
			yield color # re-apply color after '\n'
		elif token.type in ("END_OBJECT_MEMBER", "END_ARRAY_ELEMENT"):
			pass
		elif token.type == "KEY":
			yield f'"{token.value}"'
		elif token.type == "STRING":
			yield f'"{token.value}"'
		elif token.type == "NUMBER":
			yield f"{token.value}"
		elif token.type in ("TRUE", "FALSE", "NULL"):
			yield token.value
		elif token.type == "COMMA":
			yield token.value
		elif token.type == "COLON":
			yield token.value
			yield " "
		# reset color if palette is used
		if color:
			yield ANSI.RESET

##############################################################################

def json_lexer_wrapper(content:str):
	yield from json_lexer()(content)

def json_renderer_wrapper(tokens:Iterable[SimpleNamespace], links):
	yield from json_render(json_parser(tokens), indent=4)
