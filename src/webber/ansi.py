import re

ANSI_PREFIX = "\033["

class ANSI:
	__regex = re.compile(r'\033\[[^a-zA-Z]*[a-zA-Z]')

	@staticmethod
	def FG_8(c:int): return f"{ANSI_PREFIX}{c}m"
	@staticmethod
	def FG_256(c:int): return f"{ANSI_PREFIX}38;5;{c}m"
	@staticmethod
	def BG_256(c:int): return f"{ANSI_PREFIX}48;5;{c}m"
	@staticmethod
	def FG_RGB(r:int, g:int, b:int): return f"{ANSI_PREFIX}38;2;{r};{g};{b}m"
	@staticmethod
	def BG_RGB(r:int, g:int, b:int): return f"{ANSI_PREFIX}48;2;{r};{g};{b}m"
	@staticmethod
	def FG_HEX(hex_code:str):
		hex_code = hex_code.lstrip('#')
		r, g, b = int(hex_code[0:2], 16), int(hex_code[2:4], 16), int(hex_code[4:6], 16)
		return ANSI.FG_RGB(r, g, b)
	@staticmethod
	def BG_HEX(hex_code:str):
		hex_code = hex_code.lstrip('#')
		r, g, b = int(hex_code[0:2], 16), int(hex_code[2:4], 16), int(hex_code[4:6], 16)
		return ANSI.BG_RGB(r, g, b)

	RESET = FG_8(0)
	BOLD = FG_8(1)
	RESET_BOLD = FG_8(22)
	DIM = FG_8(2)
	RESET_DIM = FG_8(22)
	ITALIC = FG_8(3)
	RESET_ITALIC = FG_8(23)
	UNDERLINE = FG_8(4)
	RESET_UNDERLINE = FG_8(24)
	REVERSED = FG_8(7)
	RESET_REVERSED = FG_8(27)
	BLINK = FG_8(5)
	RESET_BLINK = FG_8(25)

	CC_HOME = ANSI_PREFIX + "H"
	@staticmethod
	def CC_MOVE(x:int, y:int): return f"{ANSI_PREFIX}{y};{x}H"
	@staticmethod
	def CC_UP_BY(n:int): return f"{ANSI_PREFIX}{n}A"
	@staticmethod
	def CC_DOWN_BY(n:int): return f"{ANSI_PREFIX}{n}B"
	@staticmethod
	def CC_FORWRD_BY(n:int): return f"{ANSI_PREFIX}{n}C"
	@staticmethod
	def CC_BCKWRD_BY(n:int): return f"{ANSI_PREFIX}{n}D"
	@staticmethod
	def CC_MOVE_COL(x:int): return f"{ANSI_PREFIX}{x}G"

	CC_SAVE_POS = ANSI_PREFIX + "s"
	CC_RESTORE_POS = ANSI_PREFIX + "u"

	CLR_SCREEN = ANSI_PREFIX + "J"
	CLR_TO_EOS = ANSI_PREFIX + "0J"
	CLR_TO_BOS = ANSI_PREFIX + "1J"
	CLR_SCREEN = ANSI_PREFIX + "2J"
	CLR_TO_EOL = ANSI_PREFIX + "0K"
	CLR_TO_BOL = ANSI_PREFIX + "1K"
	CLR_LINE = ANSI_PREFIX + "2K"

	CRSR_HIDE = ANSI_PREFIX + "?25l"
	CRSR_SHOW = ANSI_PREFIX + "?25h"

	SAVE_SCREEN = ANSI_PREFIX + "?1049h"
	RESTORE_SCREEN = ANSI_PREFIX + "?1049l"

	@staticmethod
	def strip(s:str) -> str:
		return ANSI.__regex.sub('', s)
