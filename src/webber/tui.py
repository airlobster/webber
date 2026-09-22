from types import SimpleNamespace
import re
from prompt_toolkit import Application
from prompt_toolkit.application import get_app
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit, Window, ConditionalContainer
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.formatted_text import ANSI as ptk_ansi, HTML
from prompt_toolkit.styles import Style
from prompt_toolkit.filters import Condition
from prompt_toolkit.buffer import Buffer
from webber.utils import doc, clip_string, make_absolute_url
from webber.context import context
from webber.tui_lib.cmd_binding import CommandBindings
from webber.tui_lib.nav_history import NavigationHistory
from webber.tui_lib.dyn_completer import DynamicCompleter
from webber.tui_lib.prompt_history import WebberTuiHistory
from webber.tui_lib.search import Searcher
from webber.jinja2_utils import generated_page, text_from_template
from webber.profile import profiled
from webber.ansi import ANSI

from webber.algorithms.textmanip import (
	get_filler,
	add_highlighting,
	raw_position_to_line_index
)

##############################################################################

@context
def tui_session(navigate, render):
	kb = KeyBindings()
	commands = CommandBindings()
	navhist = NavigationHistory()
	history = WebberTuiHistory()
	appname = tui_session.__context__.appname
	version = tui_session.__context__.version
	styles = tui_session.__context__.config.repl.styles
	url = tui_session.__context__.args.url
	orig_content = []
	links = []
	vofs = 0
	total_lines = 0
	current_mode = "main"
	error = None
	searcher = Searcher()

	modes = {
		"main": SimpleNamespace({
			"status_bar": lambda: text_from_template('sb_general', {
					"appname": appname,
					"version": version,
					"url": clip_string(url if url else "", dynamic_width() // 2),
					"position": vofs,
					"total_lines": total_lines,
					"search_rel_pos": searcher.rel_pos(),
				}),
		}),
		"edit": SimpleNamespace({
			"status_bar": lambda: text_from_template('sb_editing')
		}),
	}

	def set_current_mode(mode):
		nonlocal current_mode
		current_mode = mode

	@profiled
	def nav_to(next_url):
		nonlocal orig_content, url, links, error, vofs, searcher, history
		try:
			tmp_links = []
			orig_content = list(render(navigate(next_url, links=tmp_links)))
			links = tmp_links
			navhist.add(next_url)
			url = next_url
			vofs = 0
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
		if current_mode == "edit":
			n += 1 # minus prompt line
		row = get_app().output.get_size().rows
		return row - n

	def dynamic_width():
		return get_app().output.get_size().columns - 1

	def get_adapted_content():
		nonlocal orig_content
		filler = get_filler(width=dynamic_width())
		yield from filler(orig_content)

	@profiled
	def get_visible_content():
		nonlocal vofs, total_lines, orig_content, searcher
		filled_lines = [ *get_adapted_content() ]
		total_lines = len(filled_lines)
		# apply search highlighting to the filled content
		visible = ''.join(add_highlighting(
				filled_lines,
				list(iter(searcher)),
				searcher.current()
				)
			).splitlines(keepends=True)
		# slice and re-join
		visible = ''.join(visible[vofs : vofs + dynamic_height()])
		return ptk_ansi(visible)

	def scroll_to_search_match():
		nonlocal vofs, searcher
		if not searcher:
			return
		chunks = get_adapted_content()
		m = searcher.current()
		line_index = raw_position_to_line_index(chunks, m[0])
		is_already_visible = line_index >= vofs and line_index < vofs + dynamic_height()
		if is_already_visible:
			return
		vofs = max(0, line_index - dynamic_height() // 2)

	def goto_next_search_match():
		nonlocal searcher, vofs
		if not searcher:
			beep()
			return
		searcher.next()
		scroll_to_search_match()

	def goto_previous_search_match():
		nonlocal searcher, vofs
		if not searcher:
			beep()
			return
		searcher.previous()
		scroll_to_search_match()

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

	def get_status_bar():
		if error:
			return HTML(text_from_template('error', {'msg': clip_string(error, dynamic_width()-4)}))
		msg = [f for f in modes[current_mode].status_bar().splitlines() if f.strip()]
		return HTML(' \u2502 '.join(msg))

	content_area = Window(
			content=FormattedTextControl(get_visible_content),
			height=dynamic_height,
			width=dynamic_width,
			)

	prompt_area = TextArea(
		height=1,
		width=dynamic_width,
		prompt=HTML(f'<b>:</b> '),
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
		FormattedTextControl(get_status_bar),
		height=1,
		width=dynamic_width,
		style="class:status-bar"
		)

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

	# reset prompt buffer
	@kb.add("c-c", filter=is_mode("edit"))
	@doc("Reset prompt buffer")
	def _(event):
		prompt_area.buffer.reset()

	# up one line
	@kb.add("up", filter=is_mode("main"))
	@doc("Scroll up one line")
	def _(event):
		nonlocal vofs
		if vofs == 0:
			beep()
			return
		if vofs > 0:
			vofs -= 1

	# up history one line.
	@kb.add("up", filter=is_mode("edit"))
	@doc("Scroll history up one item")
	def _(event):
		if not prompt_area.buffer.history_backward():
			beep()

	# down one line
	@kb.add("down", filter=is_mode("main"))
	@doc("Scroll down one line")
	def _(event):
		nonlocal vofs, total_lines
		hpage = dynamic_height()
		if vofs < total_lines - hpage:
			vofs += 1
		else:
			beep()

	# down history one line
	@kb.add("down", filter=is_mode("edit"))
	@doc("Scroll history down one item")
	def _(event):
		if not prompt_area.buffer.history_forward():
			beep()

	# page up
	@kb.add("pageup", filter=is_mode("main"))
	@kb.add("c-u", filter=is_mode("main"))
	@doc("Scroll one page up")
	def _(event):
		nonlocal vofs
		if vofs == 0:
			beep()
			return
		hpage = dynamic_height() // 2
		vofs = max(0, vofs - hpage)

	# page down
	@kb.add("pagedown", filter=is_mode("main"))
	@kb.add("c-d", filter=is_mode("main"))
	@doc("Scroll one page down")
	def _(event):
		nonlocal vofs, total_lines
		hpage = dynamic_height()
		vofs += hpage // 2
		if vofs > total_lines - hpage:
			vofs = total_lines - hpage
			beep()

	# go to top
	@kb.add("g", filter=is_mode("main"))
	@doc("Go to the top of the document")
	def _(event):
		nonlocal vofs
		if vofs == 0:
			beep()
			return
		vofs = 0

	# go to bottom
	@kb.add("G", filter=is_mode("main"))
	@doc("Go to the bottom of the document")
	def _(event):
		nonlocal vofs, total_lines
		if vofs >= total_lines - dynamic_height():
			beep()
			return
		hpage = dynamic_height()
		vofs = max(0, total_lines - hpage)

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
		nonlocal vofs
		save_vofs = vofs
		handle_submit('reload')
		vofs = save_vofs

	@kb.add("?", filter=is_mode("main"))
	@doc("Show help information")
	def _(event):
		handle_submit('help')

	@kb.add("n", filter=is_mode("main"))
	@doc("Go to the next search match")
	def _(event):
		goto_next_search_match()

	@kb.add("N", filter=is_mode("main"))
	@doc("Go to the previous search match")
	def _(event):
		goto_previous_search_match()

	@commands.add("quit", help="Exit the application")
	@commands.add("q", help="Exit the application")
	def quit_command(*args):
		tui_app.exit()

	@commands.add("nav", help="Navigate to a URL or link", add_to_history=False)
	@commands.add("navigate", help="Navigate to a URL or link", add_to_history=False)
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

	@commands.add("reload", help="Reload the current page")
	def reload_command(*args):
		nonlocal url
		if not url:
			beep()
			return
		nav_to(url)

	@commands.add("?", help="Show this help message")
	@commands.add("help", help="Show this help message")
	def help_command(*args):
		help()

	@commands.add("about", help="Show information about the application")
	def about_command(*args):
		with generated_page("about") as u:
			nav_to(u)

	@commands.add("/", help="Search within the current page")
	@commands.add("find", help="Search within the current page")
	def search_command(*args):
		nonlocal searcher
		searcher.reset()
		if args:
			searcher.search(get_adapted_content(), *args)
			goto_next_search_match()

	@commands.add("w", help="Save the current page")
	@commands.add("save", help="Save the current page")
	def save_command(*args):
		nonlocal url
		if not url:
			beep()
			return
		# Implement the save functionality here
		if len(args) < 1:
			beep()
			raise ValueError("No filename provided for save command")
		content = ANSI.strip(''.join(get_adapted_content()))
		with open(args[0], "w") as f:
			f.write(content)


	root_container = HSplit([
		content_area,
		ConditionalContainer(
			content=prompt_area,
			filter=is_mode("edit")
			),
		status_bar,
	])

	tui_app = Application(
			key_bindings=kb,
			layout=Layout(root_container),
			full_screen=True,
			mouse_support=True,
			style=Style.from_dict(styles),
	)
	tui_app.ttimeoutlen=0.05
	tui_app.timeoutlen=0.05

	history.load_history_strings()
	if url:
		handle_submit(url)
	tui_app.run()

##############################################################################
