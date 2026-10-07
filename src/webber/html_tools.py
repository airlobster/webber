from typing import Callable, Iterable, Iterator, Generator
from types import SimpleNamespace
import html
import re
from html.parser import HTMLParser

##############################################################################

HtmlToken = SimpleNamespace
HtmlFilterFunc = Callable[[Iterator[HtmlToken]], Generator[HtmlToken, None, None]]

##############################################################################

def is_html_void_element(tag: str) -> bool:
	# https://developer.mozilla.org/en-US/docs/Glossary/Void_element
	_voids = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}
	return tag.lower() in _voids

##############################################################################

class LexerEventType:
	INIT = 'INIT'
	BEGIN = 'BEGIN'
	END = 'END'
	DATA = 'DATA'
	COMMENT = 'COMMENT'
	DECL = 'DECL'

class HtmlLexerOption:
	OPT_INCLUDE_COMMENTS = 1 << 0
	OPT_INCLUDE_DECLS = 1 << 1

def html_lexer(opt:int=0) -> Callable[[Iterator[str]], Generator[HtmlToken, None, None]]:
	class MyHTMLParser(HTMLParser):
		def __init__(self):
			super().__init__()
			self.q = []
			self.s = []
			self.changes = 0

		def handle_starttag(self, tag, attrs):
			t = tag.lower()
			self.s.append(t)
			self.q.append(HtmlToken(type=LexerEventType.BEGIN, tag=t, attrs=dict(attrs), pos=self.getpos())) # notify
			if is_html_void_element(t):
				# force end tag for void element
				self.handle_endtag(tag, manual=True)
				self.changes += 1

		def handle_endtag(self, tag, manual=False):
			t = tag.lower()
			# ignore end tags for void elements unless manually generated
			if is_html_void_element(t) and not manual:
				self.changes -= 1
				return
			# ignore mismatched end tags
			if not self.s or t != self.s[-1]:
				self.changes += 1
				return
			self.s.pop(-1)
			self.q.append(HtmlToken(type=LexerEventType.END, tag=t, pos=self.getpos())) # notify

		def handle_data(self, data):
			self.q.append(HtmlToken(type=LexerEventType.DATA, data=data, pos=self.getpos())) # notify

		def handle_comment(self, data):
			if not (opt & HtmlLexerOption.OPT_INCLUDE_COMMENTS):
				return
			self.q.append(HtmlToken(type=LexerEventType.COMMENT, data=data, pos=self.getpos())) # notify

		def handle_decl(self, decl):
			if not (opt & HtmlLexerOption.OPT_INCLUDE_DECLS):
				return
			self.q.append(HtmlToken(type=LexerEventType.DECL, data=decl, pos=self.getpos())) # notify

		def close(self):
			super().close()
			# close remaining open tags
			while self.s:
				self.handle_endtag(self.s[-1], manual=True)
				self.changes += 1

		def get_tokens(self):
			while self.q:
				yield self.q.pop(0)


	def lex(chunks: Iterator[str]) -> Generator[HtmlToken, None, None]:
		parser = MyHTMLParser()
		try:
			for chunk in chunks:
				if not isinstance(chunk, str):
					raise ValueError("Bad pipline: Invalid chunk type. Chunks must be strings")
				parser.feed(chunk)
				yield from parser.get_tokens()
		finally:
			parser.close()
			yield from parser.get_tokens()
			# print(f"Total changes made by lexer: {parser.changes}", file=sys.stderr)

	return lex

##############################################################################

def html_tracker() -> HtmlFilterFunc:
	path = []

	def f(tokens: Iterator[HtmlToken]) -> Generator[HtmlToken, None, None]:
		nonlocal path
		for token in tokens:
			if not isinstance(token, HtmlToken):
				raise ValueError("Bad pipeline: Invalid token type. Tokens must be HtmlToken instances")
			if token.type == LexerEventType.BEGIN:
				path.append(token.tag)
				t_ = HtmlToken(**vars(token), path=path[:])
			elif token.type == LexerEventType.END:
				t_ = HtmlToken(**vars(token), path=path[:])
				path.pop(-1)
			else:
				t_ = HtmlToken(**vars(token), path=path[:])
			yield t_

	return f

##############################################################################

def html_filter(flt:Callable[[HtmlToken], bool]|None=None) -> HtmlFilterFunc:
	swallow = 0

	if not callable(flt):
		flt = lambda _: True

	def f(tokens:Iterator[HtmlToken]) -> Generator[HtmlToken, None, None]:
		nonlocal swallow
		for token in tokens:
			if not isinstance(token, HtmlToken):
				raise ValueError("Bad pipeline: Invalid token type. Tokens must be HtmlToken instances")
			if not hasattr(token, 'path'):
				raise ValueError("Illegal pipeline: html_filter must come after html_tracker")
			if not flt(token):
				if token.type == LexerEventType.BEGIN:
					swallow += 1
				elif token.type == LexerEventType.END:
					if swallow == 0:
						raise ValueError("Mismatched END token encountered while filtering HTML")
					swallow -= 1
				continue
			if swallow:
				continue
			yield token

	return f

##############################################################################

def html_ignore_whitespace() -> HtmlFilterFunc:
	reWS = re.compile(r'[ \t]+')
	prev = ''

	def f(tokens: Iterator[HtmlToken]) -> Generator[HtmlToken, None, None]:
		nonlocal prev
		for token in tokens:
			if not isinstance(token, HtmlToken):
				raise ValueError("Bad pipeline: Invalid token type. Tokens must be HtmlToken instances")
			if token.type == LexerEventType.DATA:
				# Collapse consecutive whitespace into a single space
				token.data = reWS.sub(' ', token.data.replace('\r', ''))
				# Strip leading and trailing whitespace
				token.data = token.data.strip(' \t')
				if not token.data or (token.data.isspace() and prev.isspace()):
					continue
				prev = token.data
			yield token

	return f

##############################################################################

def html_builder() -> Callable[[Iterator[HtmlToken]], Generator[str, None, None]]:
	def f(tokens: Iterator[HtmlToken]) -> Generator[str, None, None]:
		for token in tokens:
			if not isinstance(token, HtmlToken):
				raise ValueError("Bad pipeline: Invalid token type. Tokens must be HtmlToken instances")
			if token.type == LexerEventType.BEGIN:
				attrs = ' '.join(f'{k}="{v}"' for k, v in token.attrs.items())
				yield f"<{token.tag} {attrs}>" if attrs else f"<{token.tag}>"
			elif token.type == LexerEventType.END and not is_html_void_element(token.tag):
				yield f"</{token.tag}>"
			elif token.type == LexerEventType.DATA:
				yield html.escape(token.data)
			elif token.type == LexerEventType.COMMENT:
				yield f"<!-- {html.escape(token.data)} -->"
			elif token.type == LexerEventType.DECL:
				yield f"<!{token.data}>"

	return f

##############################################################################

# predefined filters

def filter_forbidden_tags(forbidden: Iterable[str]) -> HtmlFilterFunc:
	lcf = {f.lower() for f in forbidden}
	return html_filter(lambda token: not any(p in lcf for p in token.path))
