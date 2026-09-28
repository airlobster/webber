from types import SimpleNamespace
import re
import html
from urllib.parse import quote
from prompt_toolkit import Application
from prompt_toolkit.application import get_app
from prompt_toolkit.document import Document
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, NumberedMargin
from prompt_toolkit.layout.containers import HSplit, Window, ConditionalContainer
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.selection import SelectionType
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from prompt_toolkit.filters import Condition
from prompt_toolkit.buffer import Buffer
from webber.utils import doc, clip_string, make_absolute_url
from webber.context import context, dynamic_context, set_context
from webber.tui_lib.cmd_binding import CommandBindings
from webber.tui_lib.nav_history import NavigationHistory
from webber.tui_lib.dyn_completer import DynamicCompleter
from webber.tui_lib.prompt_history import WebberTuiHistory
from webber.tui_lib.search import Searcher
from webber.tui_lib.no_cursor_bufctrl import NoCursorBufferControl
from webber.tui_lib.ansi_lexer import AnsiBufferLexer
from webber.jinja2_utils import generated_page, text_from_template
from webber.profile import profiled
from webber.ansi import ANSI

##############################################################################

@context
@dynamic_context
def tui_session(navigate, render):
	kb = KeyBindings()
	commands = CommandBindings()
	navhist = NavigationHistory()
	history = WebberTuiHistory()
	appname = tui_session.__context__.appname
	version = tui_session.__context__.version
	args = tui_session.__context__.args
	line_numbers = args.line_numbers
	styles = vars(tui_session.__context__.config.repl.styles)
	url = tui_session.__context__.args.url
	logo = f"webR v.{version}"
	uncolored_buffer = Buffer(read_only=True)
	colored_buffer = Buffer(read_only=True)
	active_buffer = uncolored_buffer
	links = []
	current_mode = "main"
	error = None
	searcher = Searcher()

	modes = {
		"main": SimpleNamespace({
			"status_bar": lambda: text_from_template('sb_general', {
					"appname": appname,
					"version": version,
					"url": clip_string(url if url else "", dynamic_width() - 20),
					"position": get_visible_lines_range(),
					"total_lines": active_buffer.document.line_count,
					"search_rel_pos": searcher.rel_pos(),
				}),
		}),
		"edit": SimpleNamespace({
			"status_bar": lambda: text_from_template('sb_editing')
		}),
	}

	def get_colored_line(lineno:int) -> str:
		lines = colored_buffer.document.lines
		if 0 <= lineno < len(lines):
			return lines[lineno]
		return ""

	def on_invalidate(*args, **kwargs):
		get_app().invalidate()
		get_app().layout.focus(prompt_area if current_mode == "edit" else content_area)

	def set_current_mode(mode):
		nonlocal current_mode
		current_mode = mode

	def get_visible_lines_range() -> tuple[int, int]:
		start = content_area.render_info.first_visible_line()
		current = active_buffer.document.cursor_position_row
		end = content_area.render_info.last_visible_line()
		return start, current, end

	def vscroll(count):
		t,c,b = get_visible_lines_range()
		if count < 0:
			n = max(c - t + abs(count), 1)
			active_buffer.cursor_up(count=n)
		elif count > 0:
			n = max(b - c + abs(count), 1)
			active_buffer.cursor_down(count=n)

	@profiled
	def nav_to(next_url):
		nonlocal url, links, error, searcher, history, uncolored_buffer, colored_buffer, active_buffer
		try:
			set_context(doc_title=None)
			tmp_links = []
			orig_content = render(navigate(next_url, links=tmp_links))
			s = ''.join(orig_content)
			uncolored_buffer.set_document(Document(text=ANSI.strip(s), cursor_position=0), bypass_readonly=True)
			colored_buffer.set_document(Document(text=s, cursor_position=0), bypass_readonly=True)
			links = tmp_links
			navhist.add(next_url)
			url = next_url
			error = None
			history.append_string(next_url)
		except Exception as e:
			error = str(e)
			raise
		finally:
			searcher.reset()
			get_app().invalidate()

	def beep():
		beep_enabled = tui_session.__context__.config.repl.beep
		if beep_enabled:
			get_app().output.bell()

	def dynamic_height():
		n = 0
		n += 1 # minus status-bar height
		n += 1 # minus title-bar height
		if current_mode == "edit":
			n += 1 # minus prompt line
		rows = get_app().output.get_size().rows
		return rows - n

	def dynamic_width():
		return get_app().output.get_size().columns - 1

	def select_text(start:int, end:int):
		active_buffer.cursor_position = end
		active_buffer.start_selection(selection_type=SelectionType.CHARACTERS)
		active_buffer.cursor_position = start

	def goto_next_search_match():
		nonlocal searcher
		if not searcher:
			beep()
			return
		m = searcher.next()
		select_text(*m)

	def goto_previous_search_match():
		nonlocal searcher
		if not searcher:
			beep()
			return
		m = searcher.previous()
		select_text(*m)

	def is_mode(*modes):
		@Condition
		def _cond():
			nonlocal current_mode
			return current_mode in modes
		return _cond

	def handle_submit(buffer:Buffer|str) -> None:
		nonlocal error, current_mode, searcher
		try:
			text = buffer.text if isinstance(buffer, Buffer) else buffer
			if not text.strip():
				# nothing to process
				searcher.reset()
				beep()
				return
			# resolve command
			f = commands.parse_command(text)
			if not f:
				raise ValueError("Invalid command")
			# run command
			if f():
				history.append_string(text)
			error = None
		except Exception as e:
			error = str(e)
			beep()
		finally:
			# back to normal mode
			set_current_mode("main")
			prompt_area.buffer.reset()

	def help():
		nonlocal commands, kb
		help_info = commands.get_help_info()
		key_bindings = [
			SimpleNamespace(
				keys='\n'.join(key.replace('c-', '&lt;CTRL&gt;+') for key in k.keys),
				help=k.handler.__doc__
				)
			for k in kb.bindings
		]
		with generated_page("help", {'commands': help_info, 'keys': key_bindings}) as u:
			nav_to(u)

	# quit the application (VI/less style)
	@kb.add("q", filter=is_mode("main"))
	@doc("Quit the application (VI/less style)")
	def _(event):
		tui_app.exit()

	# start editing mode (VI/less style)
	@kb.add(":", filter=is_mode("main"))
	@doc("Start editing mode (VI/less style)")
	def _(event):
		set_current_mode("edit")

	@kb.add("escape")
	@doc("Return to view mode")
	def _(event):
		nonlocal error
		searcher.reset()
		error = None
		set_current_mode("main")
		prompt_area.buffer.reset()
		active_buffer.selection_state = None

	# reset prompt buffer
	@kb.add("c-c", filter=is_mode("edit"))
	@doc("Reset prompt buffer")
	def _(event):
		prompt_area.buffer.reset()

	# up history one line.
	@kb.add("up", filter=is_mode("edit"))
	@doc("Scroll history up one item")
	def _(event):
		prompt_area.buffer.history_backward()

	# down history one line
	@kb.add("down", filter=is_mode("edit"))
	@doc("Scroll history down one item")
	def _(event):
		prompt_area.buffer.history_forward()

	@kb.add("up", filter=is_mode("main"))
	@doc("Move cursor up")
	def _(event):
		active_buffer.selection_state = None
		vscroll(-1)

	@kb.add("down", filter=is_mode("main"))
	@doc("Move cursor down")
	def _(event):
		active_buffer.selection_state = None
		vscroll(1)

	@kb.add("pageup", filter=is_mode("main"))
	@kb.add("c-u", filter=is_mode("main"))
	@doc("Scroll up one page")
	def _(event):
		active_buffer.selection_state = None
		vscroll(- dynamic_height() // 2)

	@kb.add("pagedown", filter=is_mode("main"))
	@kb.add("c-d", filter=is_mode("main"))
	@doc("Scroll down one page")
	def _(event):
		active_buffer.selection_state = None
		vscroll(dynamic_height() // 2)

	@kb.add("left", filter=is_mode("main"))
	@doc("Move cursor left")
	def _(event):
		active_buffer.selection_state = None

	@kb.add("right", filter=is_mode("main"))
	@doc("Move cursor right")
	def _(event):
		active_buffer.selection_state = None

	# go to top
	@kb.add("g", filter=is_mode("main"))
	@doc("Go to the top of the document")
	def _(event):
		active_buffer.selection_state = None
		active_buffer.cursor_position = 0

	# go to bottom
	@kb.add("G", filter=is_mode("main"))
	@doc("Go to the bottom of the document")
	def _(event):
		active_buffer.selection_state = None
		active_buffer.cursor_position = len(active_buffer.text)

	# navigate back in history
	@kb.add("home", eager=True, filter=is_mode("main"))
	@doc("Navigate back in history")
	def _(event):
		next_url = navhist.back()
		if next_url:
			handle_submit(next_url)
		else:
			beep()

	# navigate forward in history
	@kb.add("end", eager=True, filter=is_mode("main"))
	@doc("Navigate forward in history")
	def _(event):
		next_url = navhist.forward()
		if next_url:
			handle_submit(next_url)
		else:
			beep()

	# reload the current page
	@kb.add("c-r", filter=is_mode("main"))
	@doc("Reload the current page")
	def _(event):
		save_y = active_buffer.cursor_position
		handle_submit('r')
		active_buffer.cursor_position = save_y

	@kb.add("?", filter=is_mode("main"))
	@doc("Show help information")
	def _(event):
		handle_submit('h')

	@kb.add("n", filter=is_mode("main"))
	# @kb.add("right", filter=is_mode("main"))
	@doc("Go to the next search match")
	def _(event):
		goto_next_search_match()

	@kb.add("N", filter=is_mode("main"))
	# @kb.add("left", filter=is_mode("main"))
	@doc("Go to the previous search match")
	def _(event):
		goto_previous_search_match()

	@commands.add("q", help="Exit the application")
	def quit_command(*args):
		tui_app.exit()

	@commands.add("g", help="Navigate to a URL or link", add_to_history=False)
	def navigate_command(*args):
		if not args:
			beep()
			return
		next_url = args[0]
		# is link index?
		if re.match(r'^#[1-9][0-9]*$', next_url):
			# look it up in the links list
			index = int(next_url[1:])-1
			if index < 0 or index >= len(links):
				raise IndexError("No such link")
			# convert the link index to an absolute URL
			next_url = make_absolute_url(url, links[index])
		nav_to(next_url)

	@commands.add("c", help="Show current page's source", add_to_history=False)
	def source_command(*args):
		nav_to(f"view-source://{quote(url)}")

	@commands.add("r", help="Reload the current page")
	def reload_command(*args):
		nonlocal url
		if not url:
			beep()
			return
		nav_to(url)

	@commands.add("h", help="Show this help message")
	def help_command(*args):
		help()

	@commands.add("a", help="Show information about the application")
	def about_command(*args):
		with generated_page("about") as u:
			nav_to(u)

	@commands.add("/", help="Search within the current page")
	def search_command(*args):
		nonlocal searcher
		searcher.reset()
		if args:
			searcher.search(active_buffer.text, *args)
			goto_next_search_match()

	@commands.add("w", help="Save the current page")
	def save_command(*args):
		nonlocal url
		if not url:
			beep()
			return
		# Implement the save functionality here
		if len(args) < 1:
			beep()
			raise ValueError("No filename provided for save command")
		with open(args[0], "w") as f:
			f.write(ANSI.strip(active_buffer.text))

	def get_title_bar_content():
		title = tui_session.__get_context__('doc_title')
		t = html.escape(title) if title else "-No Title-"
		return HTML(f"<logo> {logo} </logo> <i>{t}</i>")

	def get_status_bar():
		if error:
			return HTML(text_from_template('error', {'msg': error}))
		msg = [f for f in modes[current_mode].status_bar().splitlines() if f.strip()]
		return HTML(' \u2502 '.join(msg))

	title_bar = Window(
			content=FormattedTextControl(
				get_title_bar_content,
				focusable=False
			),
			height=1,
			width=dynamic_width,
			style="class:title-bar",
			)

	content_area = Window(
			content=NoCursorBufferControl(
				buffer=active_buffer,
				focusable=True,
				lexer=AnsiBufferLexer(get_colored_line),
				input_processors=[]
				),
			height=dynamic_height,
			width=dynamic_width,
			wrap_lines=True,
			left_margins=[NumberedMargin()] if line_numbers else [],
			# right_margins=[ScrollbarMargin(display_arrows=True)],
			)

	prompt_area = TextArea(
		height=1,
		width=dynamic_width,
		prompt=HTML(f'<b>:</b>'),
		multiline=False,
		accept_handler=handle_submit,
		history=history,
		completer=DynamicCompleter(lambda: [*commands.get_commands(),*history.get_strings()]),
		complete_while_typing=True,
		read_only=is_mode("main"),
		style="class:input-box",
		)
	prompt_area.control.key_bindings = kb

	status_bar = Window(
		FormattedTextControl(
			get_status_bar,
			focusable=False
		),
		height=1,
		width=dynamic_width,
		style="class:status-bar"
		)

	root_container = HSplit([
		title_bar,
		content_area,
		ConditionalContainer(
			content=prompt_area,
			filter=is_mode("edit")
			),
		status_bar,
	])

	tui_app = Application(
			key_bindings=kb,
			layout=Layout(root_container, focused_element=content_area),
			full_screen=True,
			mouse_support=True,
			style=Style.from_dict(styles),
			on_invalidate=on_invalidate,
	)
	tui_app.ttimeoutlen=0.05
	tui_app.timeoutlen=0.05

	history.load_history_strings()
	if url:
		handle_submit(url)
	tui_app.run()

##############################################################################
