from abc import abstractmethod
from types import SimpleNamespace
from typing import Iterable, Tuple, List
import re
from webber.algorithms.stack import Stack
from webber.algorithms.queue import Queue
from webber.algorithms.textmanip import render_table
from webber.context import context
from webber.ansi import ANSI
from webber.profile import profiled

class LexerEventType:
	INIT = 'INIT'
	BEGIN = 'BEGIN'
	END = 'END'
	DATA = 'DATA'

@context
def html_lexer(text:str) -> Iterable[str]:
	from html.parser import HTMLParser

	class MyHtmlParser(HTMLParser):
		def __init__(self, *args, **kwargs):
			super().__init__(*args, **kwargs)
			self.blacklist = set(html_lexer.__context__.config.html.blacklist)
			self.q = Queue()
			self.swallow = 0

		def handle_starttag(self, tag, attrs):
			t = tag.lower()
			is_void = self.is_void(t)
			is_black = self.is_black(t)
			if is_black:
				# start swallowing blacklisted tag
				self.swallow += 1
			if self.swallow:
				# if it's a void element, it means we will ignore end events on it,
				# so we decrement the swallow counter immediately for void blacklisted elements
				if is_void and is_black:
					self.swallow -= 1
				return
			self.notify(SimpleNamespace(type=LexerEventType.BEGIN, tag=t, attrs=attrs))
			# manually signal a close-tag for void elements
			if is_void:
				self.handle_endtag(tag, manual=True)

		def handle_endtag(self, tag, manual=False):
			t = tag.lower()
			is_void = self.is_void(t)
			is_black = self.is_black(t)
			# if is a void-element, see only end-events WE triggered ourselves
			if is_void and not manual:
				return
			if self.swallow:
				if is_black:
					self.swallow -= 1
				return
			self.notify(SimpleNamespace(type=LexerEventType.END, tag=t))

		def handle_data(self, data):
			if self.swallow:
				return
			self.notify(SimpleNamespace(type=LexerEventType.DATA, data=data))

		def notify(self, event:SimpleNamespace):
			self.q.push(event)

		def get_tokens(self):
			while self.q:
				yield self.q.pop()

		def is_void(self, tag:str) -> bool:
			# https://developer.mozilla.org/en-US/docs/Glossary/Void_element
			void = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}
			return any(t.lower() == tag.lower() for t in void)

		def is_black(self, tag:str) -> bool:
			return any(tag.lower() == t.lower() for t in self.blacklist)

	parser = MyHtmlParser()
	parser.feed(text)
	yield from parser.get_tokens()

##############################################################################
##############################################################################

__resets = []

def register_for_reset(f):
	__resets.append(f)
	return f


@context
class TagBaseBehavior:
	block_items = {'p', 'pre', 'li', 'div'}
	tagid_counter = 0

	@register_for_reset
	@staticmethod
	def reset_globals():
		TagBaseBehavior.tagid_counter = 0

	def __init__(self, parent, ev:SimpleNamespace, context:SimpleNamespace):
		self.parent = parent
		self.children = []
		self.tag = ev.tag if ev else None
		self.attrs = dict(ev.attrs) if ev and ev.attrs else {}
		self.context = context
		self.color = getattr(TagBaseBehavior.__context__.config.palette, self.tag, None) if self.tag else None
		self.tagid = TagBaseBehavior.tagid_counter
		TagBaseBehavior.tagid_counter += 1

	def __repr__(self):
		return f"{self.__class__.__name__}#{self.tagid}({self.tag})"

	def on_event(self, e:SimpleNamespace):
		if e.type == LexerEventType.INIT:
			pass
		elif e.type == LexerEventType.BEGIN:
			t = self.context.active_tags.push(self.dispatch(e))
			self.children.append(t)
			t.on_event(SimpleNamespace(type=LexerEventType.INIT,))
		elif e.type == LexerEventType.END:
			t = self.context.active_tags.peek()
			if t.tag != e.tag:
				raise ValueError(f"Mismatched end tag: expected {t.tag}, got {e.tag}")
			self.context.active_tags.pop()
		elif e.type == LexerEventType.DATA:
			self.children.append(TextItemBehavior(self, e.data))

	def render(self):
		use_color = self.color and self.color != TagBaseBehavior.__context__.config.palette.none
		for child in self.children:
			if use_color:
				yield self.color
			yield from child.render()
			if use_color:
				yield TagBaseBehavior.__context__.config.palette.none

	def dispatch(self, e:SimpleNamespace):
		if e.tag == 'table':
			t = TableTagBehavior(self, e, self.context)
		elif e.tag == 'pre':
			t = PreformattedTagBehavior(self, e, self.context)
		elif e.tag == 'a':
			t = LinkTagBehavior(self, e, self.context)
		elif e.tag == 'ul':
			t = UnorderedListBehavior(self, e, self.context)
		elif e.tag == 'ol':
			t = OrderedListBehavior(self, e, self.context)
		elif e.tag == 'li':
			t = ListItemBehavior(self, e, self.context)
		elif e.tag in {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}:
			t = HeaderElementBehavior(self, e, self.context)
		elif e.tag in TagBaseBehavior.block_items:
			t = BlockItemBehavior(self, e, self.context)
		else:
			t = TagBaseBehavior(self, e, self.context)
		return t

	def has_valid_content(self):
		a = [ ''.join(c.render()) for c in self.children ]
		s = ANSI.strip(''.join(a)).strip()
		return len(s) > 0

	# Helper method to convert rendered content into a one-liner string
	@staticmethod
	def one_liner(g):
		return ' '.join(re.sub(r'\s+', ' ', ''.join(g)).strip().split()).strip()

##############################################################################

class DocumentRoot(TagBaseBehavior):
	@register_for_reset
	@staticmethod
	def reset_globals():
		pass

	def __init__(self, context:SimpleNamespace):
		super().__init__(parent=None, ev=None, context=context)

##############################################################################

class IgnoreWhitespaces(TagBaseBehavior):
	@classmethod
	def reset_globals(cls):
		pass

	def __init__(self, parent, ev:SimpleNamespace, context:SimpleNamespace):
		super().__init__(parent, ev, context)

	def on_event(self, e):
		# if e.type == LexerEventType.DATA:
		# 	e.data = e.data.strip()
		# 	if not e.data:
		# 		return
		super().on_event(e)

##############################################################################

class TextItemBehavior(TagBaseBehavior):
	@classmethod
	def reset_globals(cls):
		pass

	def __init__(self, parent, text:str):
		super().__init__(parent, ev=None, context=None)
		self.tag = 'TEXT'
		self.text = text

	def render(self):
		yield self.text

##############################################################################

class BlockItemBehavior(IgnoreWhitespaces):
	@classmethod
	def reset_globals(cls):
		pass

	def __init__(self, parent, ev:SimpleNamespace, context:SimpleNamespace):
		super().__init__(parent, ev, context)

	def render(self):
		yield '\n'
		yield from super().render()

##############################################################################

class ListItemBehavior(IgnoreWhitespaces):
	nest = 0

	@classmethod
	def reset_globals(cls):
		ListItemBehavior.nest = 0

	def __init__(self, parent, ev:SimpleNamespace, context:SimpleNamespace):
		super().__init__(parent, ev, context)
		self._nest = UnorderedListBehavior.nest

	def on_event(self, ev:SimpleNamespace):
		if ev.type == LexerEventType.INIT:
			UnorderedListBehavior.nest += 1
		elif ev.type == LexerEventType.END:
			UnorderedListBehavior.nest -= 1
		elif ev.type == LexerEventType.DATA:
			return
		return super().on_event(ev)

	def render(self):
		if not self.has_valid_content():
			return
		bullet_color = getattr(TagBaseBehavior.__context__.config.palette, 'li_bullet')
		indent = getattr(TagBaseBehavior.__context__.config.palette, 'indent', '  ')
		for child in self.children:
			if child.tag != 'li':
				continue
			if not child.has_valid_content():
				continue
			if bullet_color:
				yield bullet_color
			yield f'\n{indent*(self._nest+1)}{''.join(self.render_bullet())} '
			if bullet_color:
				yield TagBaseBehavior.__context__.config.palette.none
			yield ''.join(child.render()).lstrip()
		yield '\n'

	@abstractmethod
	def render_bullet(self):
		return
		yield

##############################################################################

class UnorderedListBehavior(ListItemBehavior):
	@classmethod
	def reset_globals(cls):
		pass

	def __init__(self, parent, ev:SimpleNamespace, context:SimpleNamespace):
		super().__init__(parent, ev, context)

	def render_bullet(self):
		yield '\u25cf'

##############################################################################

class OrderedListBehavior(ListItemBehavior):
	@classmethod
	def reset_globals(cls):
		pass

	def __init__(self, parent, ev:SimpleNamespace, context:SimpleNamespace):
		super().__init__(parent, ev, context)
		self.counter = 0

	def render_bullet(self):
		self.counter += 1
		yield f'{self.counter}.'

##############################################################################

class ListItemBehavior(IgnoreWhitespaces):
	@classmethod
	def reset_globals(cls):
		pass

	def __init__(self, parent, ev:SimpleNamespace, context:SimpleNamespace):
		super().__init__(parent, ev, context)

	def render(self):
		s = ''.join(super().render()).strip()
		yield s

##############################################################################

class LinkTagBehavior(IgnoreWhitespaces):
	link_id_counter = 0

	@register_for_reset
	@staticmethod
	def reset_globals():
		LinkTagBehavior.link_id_counter = 0

	def __init__(self, parent, ev:SimpleNamespace, context:SimpleNamespace):
		super().__init__(parent, ev, context)
		self.enabled = self.context.links is not None
		if not self.enabled:
			self.color = None

	def render(self):
		if not self.has_valid_content():
			return
		href = self.attrs.get('href', '').strip()
		if not LinkTagBehavior.is_valid_href(href):
			return # skip links without a valid href
		# show link index only if we have a links context
		if self.enabled:
			LinkTagBehavior.link_id_counter += 1
			linkid = LinkTagBehavior.link_id_counter
			self.context.links.append(href)
			yield TagBaseBehavior.__context__.config.palette.link_index
			yield f"{TagBaseBehavior.__context__.config.palette.link_index}{{{linkid}}}"
			yield TagBaseBehavior.__context__.config.palette.none
		yield self.one_liner(super().render())
		yield ' '

	@staticmethod
	def is_valid_href(href):
		return href and re.match(r'^[^#].+$', href)

##############################################################################

class PreformattedTagBehavior(TagBaseBehavior):
	@register_for_reset
	@staticmethod
	def reset_globals():
		pass

	def __init__(self, parent, ev:SimpleNamespace, context:SimpleNamespace):
		super().__init__(parent, ev, context)

	# (we override the render method just so we can add indentation)
	def render(self):
		indent = getattr(TagBaseBehavior.__context__.config.palette, 'indent', ' '*3)
		yield '\n\n'
		lines = ''.join(super().render()).split('\n')
		for line in lines:
			yield indent
			yield line
			yield '\n'
		yield '\n\n'

##############################################################################

class HeaderElementBehavior(IgnoreWhitespaces):
	max_level = 6
	counters = [0] * max_level

	@register_for_reset
	@staticmethod
	def reset_globals():
		HeaderElementBehavior.counters = [0] * HeaderElementBehavior.max_level

	def __init__(self, parent, ev:SimpleNamespace, context:SimpleNamespace):
		super().__init__(parent, ev, context)
		self.level = HeaderElementBehavior.level_from_h_tag(self.tag)
		HeaderElementBehavior.counters[self.level-1] += 1
		# handle missing intermediate header levels
		self.legal = all(HeaderElementBehavior.counters[:self.level])
		# Reset counters for lower-level headers
		for i in range(self.level, HeaderElementBehavior.max_level):
			HeaderElementBehavior.counters[i] = 0
		# Construct the header ID based on the current counters
		self.hid = '.'.join(str(HeaderElementBehavior.counters[i]) for i in range(self.level))

	def render(self):
		if not self.legal:
			return
		if not self.has_valid_content():
			return
		yield '\n\n'
		# header hierarchy indicator
		yield self.color
		yield ANSI.DIM # dim
		yield f"{self.hid}) "
		yield TagBaseBehavior.__context__.config.palette.none
		# header content
		yield self.one_liner(super().render()).strip()
		yield '\n\n'

	@staticmethod
	def level_from_h_tag(tag) -> int:
		m = re.search(r'[hH]([1-6])$', tag)
		if not m:
			raise ValueError(f"Invalid header tag: {tag}")
		return int(m.group(1))

##############################################################################

class TableTagBehavior(TagBaseBehavior):
	@register_for_reset
	@staticmethod
	def reset_globals():
		pass

	def __init__(self, parent, ev:SimpleNamespace, context:SimpleNamespace):
		super().__init__(parent, ev, context)
		self.table = []
		self.in_cell = None

	def on_event(self, e:SimpleNamespace):
		if e.type == LexerEventType.BEGIN:
			if e.tag == 'table':
				super().on_event(e)
			elif e.tag == 'tr':
				self.table.append([])
			elif e.tag == 'th' or e.tag == 'td':
				self.table[-1].append([])
				self.in_cell = e.tag
		elif e.type == LexerEventType.END:
			if e.tag == 'th' or e.tag == 'td':
				self.table[-1][-1] = ' '.join(self.table[-1][-1])
				# add styling
				color = getattr(TableTagBehavior.__context__.config.palette, e.tag, '')
				if color:
					c = self.table[-1][-1]
					c = f"{color}{c}{TableTagBehavior.__context__.config.palette.none}"
					self.table[-1][-1] = c
				self.in_cell = None
			elif e.tag == 'table':
				self.children = [ TextItemBehavior(self, ''.join(render_table(self.table))) ]
				super().on_event(e)
		elif e.type == LexerEventType.DATA:
			if self.in_cell:
				self.table[-1][-1].append(e.data)

	def render(self):
		yield '\n\n'
		yield from super().render()
		yield '\n\n'

##############################################################################
##############################################################################

@profiled
@context
def html_render(tokens: Iterable[Tuple], links:List[str]=None) -> Iterable[str]:
	try:
		# reset globals
		for f in __resets:
			f()
		context = SimpleNamespace(active_tags=Stack(), links=links)
		# create root element
		root = DocumentRoot(context=context)
		# build DOM tree
		context.active_tags.push(root)
		for token in tokens:
			t = context.active_tags.peek()
			t.on_event(token)
		# render DOM tree
		yield from root.render()
		yield '\n'
	finally:
		yield ANSI.RESET

##############################################################################
##############################################################################
