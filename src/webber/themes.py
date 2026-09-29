from typing import Iterable
from types import SimpleNamespace
from pathlib import Path
from glob import glob
import json
from webber.context import get_context
from webber.ansi import ANSI
from webber.utils import dict_to_namespace, validate_dict


color_scheme = [
	'#C585C0',
	'#4EC9B0',
	'#77C0FF',
	'#B49C6A',
	'#FF7B71',
	'#FFA556',
	'#BC7FB7'
]

default_palette = {
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
		"KEY": ANSI.FG_RGB(129, 161, 193),
		"STRING": ANSI.FG_RGB(163, 190, 140),
		"NUMBER": ANSI.FG_RGB(208, 135, 112),
		"TRUE": ANSI.FG_RGB(180, 142, 173),
		"FALSE": ANSI.FG_RGB(180, 142, 173),
		"NULL": ANSI.FG_RGB(235, 203, 139),
		"COMMA": ANSI.FG_RGB(76, 86, 106),
		"COLON": ANSI.FG_RGB(76, 86, 106),
		"OPEN_ARRAY": ANSI.FG_RGB(216, 222, 233),
		"CLOSE_ARRAY": ANSI.FG_RGB(216, 222, 233),
		"OPEN_OBJECT": ANSI.FG_RGB(216, 222, 233),
		"CLOSE_OBJECT": ANSI.FG_RGB(216, 222, 233),
	},
	"repl": {
		"title-bar": "reverse",
		"status-bar": "reverse",
		"search-match": "reverse",
		"error": "bg:#7f0000",
		"logo": "fg:#E24D00 bg:#ffffff"
	}
}

def ensure_themes_dir() -> Path:
	appname = get_context().appname
	themes_dir = Path(f"~/.{appname}").expanduser().resolve()
	themes_dir.mkdir(parents=False, exist_ok=True)
	return themes_dir


def installed_themes() -> Iterable[str]:
	themes_dir = ensure_themes_dir()
	mask = str(themes_dir / "*.theme")
	for g in glob(mask):
		yield Path(g).name


def validate_theme(j: dict) -> dict:
	schema = {
		"type": "object",
		"properties": {
			"html": {"type": "object"},
			"json": {"type": "object"},
			"repl": {"type": "object"},
		},
		"required": ["html", "json", "repl"]
	}
	return validate_dict(j, schema)


def load_theme(basename:str|None=None) -> SimpleNamespace:
	try:
		if basename is None or not basename.strip():
			return dict_to_namespace(validate_theme(default_palette))
		themes_dir = ensure_themes_dir()
		suffix = Path(basename).suffix
		filename = Path.joinpath(themes_dir, basename) \
			if suffix \
			else Path.joinpath(themes_dir, f"{basename}.theme")
		with open(filename, "r") as f:
			j = validate_theme(json.load(f))
			return dict_to_namespace(j)
	except:
		raise
