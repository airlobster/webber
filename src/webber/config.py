from types import SimpleNamespace
from pathlib import Path
import json
from webber.utils import dict_to_namespace, validate_dict
from webber import log

class ConfigSection(SimpleNamespace):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)


def validate_config(c: dict) -> dict:
	schema = {
		"type": "object",
		"properties": {
			"theme": {"type": ["string", "null"]},
			"html": {"type": "object"},
			"http": {"type": "object"},
			"tables": {"type": "object"},
			"repl": {"type": "object"},
		},
		"required": ["theme", "html", "http", "tables", "repl"]
	}
	return validate_dict(c, schema)


def load_config(appname:str) -> ConfigSection:
	namespace = {
		"theme": None,
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
		}
	}
	pathname = Path(f"~/.{appname}.json").expanduser().resolve()
	try:
		with open(pathname, "r") as f:
			d = validate_config(namespace | json.load(f))
			return dict_to_namespace(d)
	except Exception as e:
		pass
	# If the config file does not exist or cannot be read, create it with the default namespace.
	try:
		with open(pathname, "w") as f:
			json.dump(validate_config(namespace), f, indent="\t")
	except Exception as e:
		raise
	return dict_to_namespace(validate_config(namespace))


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
