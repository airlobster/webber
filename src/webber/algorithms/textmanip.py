from typing import Iterable, Callable, List, Tuple
from webber.ansi import ANSI
from webber.context import get_context
from webber.profile import profiled

# Create a filler function that is aware of ANSI escape sequences and handles text wrapping correctly.
def get_filler(*, width: int, wrap_thresh:int=15, tab_width:int=4, add_hyphen:bool=False) -> Callable[[Iterable[str]], Iterable[str]]:
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
					if add_hyphen:
						buf.append('-')
					buf.append('\n')
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
				tablefmt=get_context().config.tables.style,
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


def map_line_indexes_to_ofs(chunks:Iterable[str]) -> list[int]:
	offsets = [0]
	ofs = 0
	for s in chunks:
		for c in s:
			ofs += 1
			if c == '\n':
				offsets.append(ofs)
	return offsets


def compress_ansi(chunks:Iterable[str]) -> Iterable[str]:
	def generate():
		ansi = []
		active_ansi = []
		prev_active_ansi = []
		in_ansi = False
		active = False
		for s in chunks:
			for c in s:
				if c == '\x1b':
					in_ansi = True
					ansi = [c]
				elif in_ansi:
					ansi.append(c)
					if c.isalpha():
						in_ansi = False
						sansi = ''.join(ansi)
						if sansi == ANSI.RESET:
							# reset requested, but we only emit it if there're currently active ANSI codes
							if active_ansi or active:
								yield sansi
								prev_active_ansi.clear()
								active_ansi.clear()
								active = False
						else:
							# accumulate ansi sequences until there's a content that actually need it
							active_ansi.append(sansi)
				elif c.isspace():
					yield c
				else:
					if active_ansi:
						# flush accumulated ANSI sequences if they differ from the previous ones
						if active_ansi != prev_active_ansi:
							yield ''.join(active_ansi)
							prev_active_ansi = active_ansi.copy()
						active_ansi.clear()
						active = True
					yield c
	yield from generate()
