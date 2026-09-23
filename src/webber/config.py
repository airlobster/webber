from types import SimpleNamespace
from pathlib import Path
import json
from webber.ansi import ANSI
from webber import log

def load_config(appname:str) -> type:
	color_scheme = [
		'#C585C0',
		'#4EC9B0',
		'#77C0FF',
		'#B49C6A',
		'#FF7B71',
		'#FFA556',
		'#BC7FB7'
	]
	namespace = {
		"palette" : {
			"html": {
				"title": f"{ANSI.BOLD}{ANSI.UNDERLINE}{ANSI.FG_HEX(color_scheme[5])}",
				"a": ANSI.FG_HEX(color_scheme[2]),
				"link_index": f"{ANSI.FG_HEX(color_scheme[2])}{ANSI.ITALIC}{ANSI.DIM}",
				"h1": f"{ANSI.BOLD}{ANSI.FG_HEX(color_scheme[4])}",
				"h2": f"{ANSI.BOLD}{ANSI.FG_HEX(color_scheme[4])}",
				"h3": f"{ANSI.BOLD}{ANSI.FG_HEX(color_scheme[4])}",
				"h4": f"{ANSI.BOLD}{ANSI.FG_HEX(color_scheme[4])}",
				"h5": f"{ANSI.BOLD}{ANSI.FG_HEX(color_scheme[4])}",
				"h6": f"{ANSI.BOLD}{ANSI.FG_HEX(color_scheme[4])}",
				"pre": f"{ANSI.ITALIC}{ANSI.FG_HEX(color_scheme[1])}",
				"th": f"{ANSI.BOLD}{ANSI.FG_HEX(color_scheme[0])}",
				"td": ANSI.ITALIC,
				"code": ANSI.ITALIC,
				"b": ANSI.BOLD,
				"strong": ANSI.BOLD,
				"b": ANSI.BOLD,
				"i": ANSI.ITALIC,
				"li_bullet": ANSI.FG_HEX(color_scheme[6]),
				"indent": "  ",
				"curr_highlight": ANSI.BOLD + ANSI.FG_HEX('#000000') + ANSI.BG_HEX(color_scheme[1]),
				"highlight": ANSI.BOLD + ANSI.FG_HEX('#ffffff') + ANSI.BG_HEX('#555555'),
			},
			"json": {
				"OPEN_ARRAY": ANSI.FG_HEX(color_scheme[2]),
				"CLOSE_ARRAY": ANSI.FG_HEX(color_scheme[2]),
				"OPEN_OBJECT": ANSI.FG_HEX(color_scheme[2]),
				"CLOSE_OBJECT": ANSI.FG_HEX(color_scheme[2]),
				"TRUE": ANSI.FG_HEX(color_scheme[3]),
				"FALSE": ANSI.FG_HEX(color_scheme[3]),
				"NULL": ANSI.FG_HEX(color_scheme[3]),
				"COMMA": ANSI.FG_HEX(color_scheme[4]),
				"COLON": ANSI.FG_HEX(color_scheme[4]),
				"STRING": ANSI.FG_HEX(color_scheme[5]),
				"NUMBER": ANSI.FG_HEX(color_scheme[6]),
			}
		},
		"html": {
			"blacklist": [
				'html.head',
				'*.nav',
				'*.video',
				'*.dl',
				'*.template',
				'*.style',
				'*.script',
				'*.select',
				'*.button',
				'*.input',
				'*.textarea',
				'*.svg',
				'*.img',
				'*.form'
			]
		},
		"http": {
			"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
			"accept": "text/html, text/plain, application/json"
		},
		"tables": {
			"style": "plain"
		},
		"repl": {
			"beep": True,
			"styles": {
				"title-bar": "bg:#81587F fg:#ffffff",
				"input-box": "fg:#000000 bg:#C6C7C8",
				"status-bar": "bg:#81587F fg:#ffffff",
				"error": "fg:#ff0000",
			}
		}
	}
	def dict_to_namespace(d):
		if isinstance(d, dict):
			return SimpleNamespace(**{k:dict_to_namespace(v) for k,v in d.items()})
		return d
	pathname = Path(f"~/.{appname}.json").expanduser().resolve()
	try:
		with open(pathname, "r") as f:
			d = namespace | json.load(f)
			ns = dict_to_namespace(d)
			return ns
	except Exception as e:
		pass
	# If the config file does not exist or cannot be read, create it with the default namespace.
	try:
		with open(pathname, "w") as f:
			json.dump(namespace, f, indent=4)
	except Exception as e:
		log.warning(f"Failed to write config file: {e}")
	return dict_to_namespace(namespace)


_config = load_config("webber")


# Decorator to attach the global configuration to a function or a class.
def configurable(f):
	global _config
	f.__config__ = _config
	return f


def reinit_config(appname:str) -> None:
	global _config
	try:
		pathname = Path(f"~/.{appname}.json").expanduser().resolve()
		pathname.unlink()
		_config = load_config(appname)
	except Exception as e:
		log.warning(f"Failed to delete config file: {e}")
