from typing import Iterable, Callable, List, Tuple
from webber.ansi import ANSI
from webber.context import context
from webber.profile import profiled

# Create a filler function that is aware of ANSI escape sequences and handles text wrapping correctly.
def get_filler(*, width: int, wrap_thresh:int=15, tab_width:int=4) -> Callable[[Iterable[str]], Iterable[str]]:
	ansi = []
	in_ansi = False
	col = 0
	buf = []
	def flush():
		nonlocal col, buf
		if buf:
			yield ''.join(buf)
			buf.clear()
		col = 0
	def ispunct(c: str) -> bool:
		return c in '.,;:!?()[]{}'
	def ansi_aware_fill(text:Iterable[str]) -> Iterable[str]:
		nonlocal ansi, in_ansi, col, buf
		for s in text:
			for c in s:
				if c == '\x1b':
					ansi = [c]
					in_ansi = True
					continue
				if in_ansi:
					ansi.append(c)
					if c.isalpha():
						buf.append(''.join(ansi))
						ansi.clear()
						in_ansi = False
					continue
				buf.append(c)
				if c == '\n':
					yield from flush()
					continue
				if c == '\t':
					# soft wrap on tab expansion
					col += tab_width - (col % tab_width)
					if col >= width:
						buf.append('\n')
						yield from flush()
					continue
				if (c.isspace() or ispunct(c)) and col >= width - wrap_thresh:
					# soft wrap on whitespace
					buf.append('\n')
					yield from flush()
					continue
				if col >= width:
					# hard break using a hyphen and newline
					buf.append('-\n')
					yield from flush()
				col += 1
		# flush any remaining text in the buffer
		yield from flush()

	return ansi_aware_fill

# Reduce consecutive empty lines to a maximum of `max_empty`
def reduce_empty_lines(it:Iterable[str], max_empty:int=2, passthrough:bool=False) -> Iterable[str]:
	def generate():
		nempty = 0
		ws = []
		ansi = []
		in_ansi = False
		if passthrough:
			yield from it
			return
		for s in it:
			for c in s:
				if c == '\x1b':
					ansi.append(c)
					in_ansi = True
					continue
				if in_ansi:
					ansi.append(c)
					if c.isalpha():
						in_ansi = False
					continue
				if c == '\n':
					nempty += 1
					ws.clear()
					continue
				if c.isspace():
					# defer whitespace until we know it's not trailing
					ws.append(c)
					continue
				# non-whitespace character encountered
				# flush linefeeds reduced to max. consecutive allowed
				if nempty:
					yield '\n' * min(nempty, max_empty)
					nempty = 0
				# flush whitespaces
				if ws:
					yield ''.join(ws)
					ws.clear()
				# flush ANSI sequences
				if ansi:
					yield ''.join(ansi)
					ansi.clear()
				yield c
		# flush leftovers
		yield ''.join(ws)
		if nempty:
			yield '\n' * min(nempty, max_empty)
		# end of generate()
	yield from generate()


def ansi_filter(it:Iterable[str], passthrough:bool=True) -> Iterable[str]:
	ansi = []
	for s in it:
		for c in s:
			if c == '\x1b':
				# start of ANSI sequence
				ansi = [c]
				continue
			if ansi:
				ansi.append(c)
				if c.isalpha():
					# end of ANSI sequence
					if passthrough:
						yield ''.join(ansi)
					ansi.clear()
				continue
			yield c


def split_lines(it:Iterable[str], keepends:bool=False) -> Iterable[str]:
	def generate():
		b = []
		for chunk in it:
			for c in chunk:
				if c == '\n':
					if keepends:
						b.append(c)
					# flush
					if b:
						yield ''.join(b)
					b.clear()
				else:
					b.append(c)
		if b:
			yield ''.join(b)
	yield from generate()


@context
def render_table(table: list[list[str]]) -> Iterable[str]:
	from tabulate import tabulate
	from webber.utils import get_terminal_size
	if not table:
		return
	w, _ = get_terminal_size()
	ncols = len(table[0])
	if ncols == 0:
		return
	maxcolwidth = max((w - 3) // ncols, 4)
	try:
		yield tabulate(table,
				tablefmt=render_table.__context__.config.tables.style,
				maxcolwidths=[maxcolwidth] * ncols,
				disable_numparse=True
			)
	except:
		raise


def strip_wrapping_whitespaces(it:Iterable[str]) -> Iterable[str]:
	def generate():
		leading = True
		ws = []
		for s in it:
			if leading and s.isspace():
				continue
			leading = False
			if s.isspace():
				ws.append(s)
				continue
			# flush any accumulated whitespace before yielding the non-whitespace string
			if ws:
				yield ''.join(ws)
				ws.clear()
			yield s
	yield from generate()


# make sure the active ANSI sequence is reapplied after each newline.
# this filter function also reduces repeated resets
def fixup_for_bash(it:Iterable[str]) -> Iterable[str]:
	def generate():
		ansi_all = []
		ansi = []
		in_ansi = False
		n = 0
		for s in it:
			for c in s:
				if c == '\x1b':
					ansi = [c]
					in_ansi = True
					continue
				if in_ansi:
					ansi.append(c)
					if c.isalpha():
						in_ansi = False
						a = ''.join(ansi)
						yield a
						n += 1
						if a == ANSI.RESET: # is reset?
							ansi_all.clear()
						ansi_all.append(a)
					continue
				# pre-ansi
				if ansi_all and n == 0:
					yield ''.join(ansi_all)
					n += 1
				yield c
				if c == '\n':
					n = 0
		# end of generate()
	yield from generate()


def as_text_lines(it:Iterable[str], keepends: bool=False) -> Iterable[str]:
	line = []
	for s in it:
		for c in s:
			if c == '\n':
				if keepends:
					line.append('\n')
				l = ''.join(line)
				yield l
				line.clear()
			else:
				line.append(c)
	if line:
		l = ''.join(line)
		yield l


def expand_tabs(it:Iterable[str], tabsize: int=4) -> Iterable[str]:
	def generate():
		col = 0
		for s in it:
			for c in s:
				if c == '\r':
					continue
				elif c == '\n':
					yield c
					col = 0
				elif c == '\t':
					spaces = tabsize - (col % tabsize)
					yield ' ' * spaces
					col += spaces
				else:
					yield c
					col += 1
	yield from generate()


@profiled
@context
def add_highlighting(
		chunks:Iterable[str],
		matches:List[Tuple[int, int]],
		current_match:Tuple[int, int]|None
		):
	palette = add_highlighting.__context__.config.palette
	attr_highlight = getattr(palette, 'highlight', ANSI.FG_HEX('#ffffff')+ANSI.BG_HEX('#555555'))
	attr_curr_highlight = getattr(palette, 'curr_highlight', ANSI.FG_HEX('#000000')+ANSI.BG_HEX('#ffffff'))
	pos = 0
	in_ansi = False
	curr_ansi = []
	ansi = []
	match_index = 0
	matches_iter = iter(matches)
	m = next(matches_iter, None)
	for s in chunks:
		for c in s:
			if c == '\x1b':
				ansi = [c]
				yield c
				in_ansi = True
				continue
			if in_ansi:
				ansi.append(c)
				yield c
				if c.isalpha():
					sansi = ''.join(ansi)
					if sansi == ANSI.RESET:
						curr_ansi.clear()
					curr_ansi.append(sansi)
					in_ansi = False
				continue
			if m and pos == m[0]:
					# begin match
					yield attr_curr_highlight if current_match and pos == current_match[0] \
						else attr_highlight
					yield c
					pos += 1
					continue
			if m and pos == m[1]:
					# end match
					yield ANSI.RESET
					yield from curr_ansi
					yield c
					pos += 1
					# next match to wait for
					match_index += 1
					m = next(matches_iter, None)
					continue
			yield c
			pos += 1


def raw_position_to_line_index(chunks:Iterable[str], pos:int) -> int:
	line_index = 0
	current_pos = 0
	in_ansi = False
	for s in chunks:
		for c in s:
			if c == '\x1b':
				in_ansi = True
				continue
			if in_ansi:
				if c.isalpha():
					in_ansi = False
				continue
			if current_pos == pos:
				return line_index
			if c == '\n':
				line_index += 1
			current_pos += 1
	return -1
