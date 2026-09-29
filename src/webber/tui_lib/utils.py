from prompt_toolkit.layout import Window
from prompt_toolkit.selection import SelectionType
from prompt_toolkit.buffer import Buffer

# Utility functions for text selection and scrolling within a prompt_toolkit Window.
def select_text(buffer:Buffer, start:int, end:int):
	buffer.cursor_position = end
	buffer.start_selection(selection_type=SelectionType.CHARACTERS)
	buffer.cursor_position = start

# Get the range of visible lines within a prompt_toolkit Window.
# Returns a tuple of (start, current, end).
def get_visible_lines_range(area:Window) -> tuple[int, int, int]:
	start = area.render_info.first_visible_line()
	current = area.content.buffer.document.cursor_position_row
	end = area.render_info.last_visible_line()
	return start, current, end

# Scroll the content of a prompt_toolkit Window by a specified number of lines.
# Positive values scroll down, negative values scroll up.
def vscroll(area:Window, count:int) -> bool:
	if not count:
		return False
	buffer = area.content.buffer
	current = buffer.document.cursor_position_row
	t,c,b = get_visible_lines_range(area)
	if count < 0:
		n = max(c - t + abs(count), 1)
		buffer.cursor_up(count=n)
	elif count > 0:
		n = max(b - c + abs(count), 1)
		buffer.cursor_down(count=n)
	return buffer.document.cursor_position_row != current
