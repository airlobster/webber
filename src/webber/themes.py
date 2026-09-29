from typing import Iterable
from types import SimpleNamespace
from pathlib import Path
from glob import glob
import json
from webber.context import get_context

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


def load_theme(basename:str) -> SimpleNamespace:
	def dict_to_namespace(o):
		if isinstance(o, dict):
			return SimpleNamespace(**{k: dict_to_namespace(v) for k, v in o.items()})
		return o
	themes_dir = ensure_themes_dir()
	filename = Path.joinpath(themes_dir, basename)
	ext = Path(filename).suffix
	if ext != ".theme":
		raise ValueError(f"Invalid theme file extension: {ext}")
	try:
		with open(filename, "r") as f:
			j = json.load(f)
			return dict_to_namespace(j)
	except Exception as e:
		raise RuntimeError(f"{filename.name} is not a valid theme file")
	return SimpleNamespace()
