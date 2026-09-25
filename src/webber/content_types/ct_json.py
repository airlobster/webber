from typing import Dict, Iterable, Any
from collections import namedtuple
import re

JsonToken = namedtuple("JsonToken", ["type", "value", "pos"], defaults=[None, None])

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
		"STRING": r'(?<=")([^"\\\\]|\\\\(["\\\\/bfnrt]|u[0-9a-fA-F]{4}))*(?=")',
		"NUMBER": r"-?\d+(\.\d+)?([eE][+-]?\d+)?",
	}
	expr = "|".join(f"(?P<{name}>{pattern})" for name, pattern in token_types.items())
	regex = re.compile(expr, re.DOTALL | re.MULTILINE)
	row = 0
	col = 0

	def generate_tokens(iterable:Iterable[str]):
		def update_position(value):
			nonlocal row, col
			for c in value:
				if c == "\n":
					row += 1
					col = 0
				elif c == "\t":
					col += tab_width - (col % tab_width)
				else:
					col += 1
		for s in iterable:
			for match in regex.finditer(s):
				for name, value in match.groupdict().items():
					if value is None:
						continue
					if name == "WS":
						update_position(value)
						continue # aside from updating the position, ignore whitespaces
					yield JsonToken(type=name, value=value, pos=(row+1, col+1))
					update_position(value)

	return generate_tokens

##############################################################################

class CachedIterator:
	def __init__(self, iterable: Iterable):
		self.iterable = iter(iterable)
		self.stack = []

	def __iter__(self):
		return self

	def __next__(self):
		if self.stack:
			return self.stack.pop()
		return next(self.iterable)

	def unget(self, value):
		self.stack.append(value)

##############################################################################

def json_parse(tokens:Iterable[JsonToken], validate:bool=True):
	it = iter(CachedIterator(tokens))

	def expect(token, *expected_types):
		if validate and (token.type not in expected_types):
			raise ValueError(f"Expected token types {expected_types}, got {token.type}")
		return token

	def parse_value():
		token = expect(next(it), "OPEN_ARRAY", "OPEN_OBJECT", "TRUE", "FALSE", "NULL", "NUMBER", "STRING")
		if token.type in ("TRUE", "FALSE", "NULL", "NUMBER", "STRING"):
			yield token
			return
		it.unget(token)
		if token.type == "OPEN_ARRAY":
			yield from parse_array()
		elif token.type == "OPEN_OBJECT":
			yield from parse_object()

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
			yield JsonToken(type="BEGIN_OBJECT_MEMBER")
			it.unget(token)
			yield from parse_object_member()
			token = next(it)
			if token.type == "COMMA":
				yield token
				yield JsonToken(type="END_OBJECT_MEMBER")
				continue
			yield JsonToken(type="END_OBJECT_MEMBER")
			it.unget(token)

	def parse_object_member():
		yield JsonToken(type="KEY", value=expect(next(it), "STRING").value)
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
			yield JsonToken(type="BEGIN_ARRAY_ELEMENT")
			it.unget(token)
			yield from parse_value()
			token = next(it)
			if token.type == "COMMA":
				yield token
				yield JsonToken(type="END_ARRAY_ELEMENT")
				continue
			yield JsonToken(type="END_ARRAY_ELEMENT")
			it.unget(token)

	yield from parse_value()

##############################################################################

def json_build_object(tokens:Iterable[JsonToken]) -> Any:
	curr = []
	key = None

	def translate(name, value):
		if name == "NUMBER":
			try:
				return int(value)
			except ValueError:
				return float(value)
		if name == "TRUE":
			return True
		if name == "FALSE":
			return False
		if name == "NULL":
			return None
		return value

	def attach_to_parent(value):
		nonlocal curr, key
		if not curr:
			return
		parent = curr[-1]
		if key:
			parent[key] = value
			key = None
		else:
			parent.append(value)

	for token in tokens:
		if token.type == "OPEN_ARRAY":
			e = []
			attach_to_parent(e)
			curr.append(e)
		elif token.type == "CLOSE_ARRAY":
			o = curr.pop()
			if not curr:
				return o
		elif token.type == "OPEN_OBJECT":
			e = {}
			attach_to_parent(e)
			curr.append(e)
		elif token.type == "CLOSE_OBJECT":
			o = curr.pop()
			if not curr:
				return o
		elif token.type == "KEY":
			key = token.value
		elif token.type in ("STRING", "NUMBER", "TRUE", "FALSE", "NULL"):
			v = translate(token.type, token.value)
			if not curr:
				return v
			attach_to_parent(v)

##############################################################################

def json_render(tokens:Iterable[JsonToken], indent:str|int=4, palette:Dict[str, str]={}):
	indent = " " * indent if isinstance(indent, int) else indent
	palette = {} if palette is None else palette
	nest = 0
	for token in tokens:
		color = palette.get(token.type, '')
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
			yield "\x1b[0m"

##############################################################################
##############################################################################

from types import SimpleNamespace
from webber.context import context

def json_lexer_wrapper(content:str):
	lines = content.splitlines(keepends=True)
	return json_lexer()(lines)

@context
def json_renderer_wrapper(tokens:Iterable[JsonToken]):
	palette = getattr(json_renderer_wrapper.__context__.config.palette, "json", SimpleNamespace())
	return json_render(json_parse(tokens), palette=vars(palette))
