import sys
sys.path.append("src")
from typing import Iterable, List
from contextlib import contextmanager
from pathlib import Path
import argparse
from urllib.parse import urlsplit
from curl_cffi import requests
from webber.loggingex import create_logger, get_levels, set_global_level
from webber.config import reinit_config, get_config_param
from webber.context import set_context, get_context
from webber.ct_dispatch import get_content_handler, extract_url
from webber.utils import (
	intercept,
	handle_broken_pipe,
	restart,
	load_metadata,
	get_terminal_size
)
from webber.unparsable_argparse import UnparsableArgumentParser
from webber.ansi import ANSI
from webber.tui import tui_session
from webber.algorithms.textmanip import (
	reduce_empty_lines,
	ansi_filter,
	split_lines,
	strip_wrapping_whitespaces,
	fixup_for_bash,
	expand_tabs,
	compress_ansi,
	get_filler
)
from webber.tui_lib.prompt_history import WebberTuiHistory
from webber.profile import get_prof_table, print_prof_table, profiled
from webber.themes import load_theme

log = create_logger(__name__)

@profiled
@contextmanager
def download_content(url:str):
	r = None
	try:
		surl = urlsplit(url)
		if not surl.scheme:
			url = "https://" + url
		http_conf = vars(get_context().config.http)
		r = requests.get(url, headers=dict(http_conf))
		yield r
	finally:
		if r is not None:
			r.close()


@profiled
def navigate(url:str, links:List[str]=None) -> Iterable[str]:
	with download_content(extract_url(url)) as r:
		content_type = r.headers.get('Content-Type', '').split(';')[0]
		encoding = r.encoding if r.encoding else 'utf-8'
		tokenizer, renderer = get_content_handler(url, content_type)
		tokens = intercept(tokenizer(r.content.decode(encoding)), log.debug)
		return renderer(tokens, links)


@profiled
def render_formatted_text(tokens:Iterable, use_colors:bool) -> Iterable[str]:
	stream = \
		compress_ansi(
			ansi_filter(
				fixup_for_bash(
					reduce_empty_lines(
						strip_wrapping_whitespaces(
							split_lines(
								expand_tabs(
									tokens,
									tabsize=4
								),
								keepends=True
							),
						),
						max_empty=2,
					),
				),
				passthrough=use_colors
			)
		)

	for chunk in ''.join(stream).splitlines(keepends=True):
		yield chunk
	yield "\n"


@handle_broken_pipe
def events_loop():
	def render(tokens:Iterable):
		args = get_context().args
		use_colors = args.colors == "always" or (args.colors == "auto" and sys.stdout.isatty())
		w,_ = get_terminal_size()
		filler = get_filler(width=w-1, wrap_thresh=8)
		return filler(render_formatted_text(tokens, use_colors))
	tui_session(navigate=navigate, render=render)


@handle_broken_pipe
@profiled
def batch_mode():
	args = get_context().args
	url = get_context().args.url
	use_colors = args.colors == "always" or (args.colors == "auto" and sys.stdout.isatty())
	chunks = render_formatted_text(navigate(url, links=None), use_colors)
	for chunk in chunks:
		print(chunk, sep='', end='')


def parseCommandLine():
	toml = load_metadata()
	class action_reset(argparse.Action):
		def __call__(self, parser, namespace, values, option_string=None):
			WebberTuiHistory.delete_file()
			reinit_config(toml.project.name)
			restart(parser.unparse(namespace, exclude=["reset"]))
			sys.exit(0)
	debug_features = Path.joinpath(Path(sys.argv[0]).parent, "__debug__.py").exists()
	parser = UnparsableArgumentParser(description=f"{toml.project.name} - command-line web reader", exit_on_error=False)
	parser.add_argument("-v", "--version", action="version", version=f"{toml.project.name} {toml.project.version}")
	parser.add_argument("-b", "--batch", action="store_true", default=False, help="Run in plain text mode")
	parser.add_argument("-C", "--colors", choices=["auto", "always", "never"], default="auto", help="Color output mode")
	parser.add_argument("-l", "--log", choices=get_levels(), help="Set the logging level", default="INFO")
	parser.add_argument("-N", "--line_numbers", action="store_true", default=False, help="Enable line numbers")
	parser.add_argument("-r", "--reset", nargs=0, action=action_reset, help="Reset the application's history and configuration")
	parser.add_argument("url", nargs="?", help="URL")
	if debug_features:
		parser.add_argument("-d", "--debug", action="store_true", default=False, help="Enable debug mode")
		parser.add_argument("-p", "--profile", action="store_true", default=False, help="Enable profiling")
	return parser.parse_args()


def main():
	toml = load_metadata()

	set_context(
		appname=toml.project.name,
		version=toml.project.version,
		author=toml.project.authors[0].name,
		email=toml.project.authors[0].email,
	)

	args = None
	try:
		args = parseCommandLine()
		set_context(args=args)
		set_global_level(args.log)
		if getattr(args, "debug", False):
			# override log level to DEBUG if debug mode is enabled
			set_global_level("DEBUG")
		log.debug(f'CLI args: {args}')

		set_context(
			config=get_config_param(),
			palette=load_theme(get_config_param("theme"))
		)

		# load last build timestamp
		try:
			with open('TIMESTAMP', 'r') as f:
				set_context(timestamp=f.read().strip())
		except Exception as e:
			pass

		# make sure STDIN is a TTY
		if not sys.stdin.isatty():
			raise RuntimeError("Standard input must be a TTY")

		if not args.url:
			raise RuntimeError("No URL provided")

		# determine if batch mode should be used
		batch_run = args.batch or not sys.stdout.isatty() or not sys.stdin.isatty()
		if batch_run:
			batch_mode()
			return
		events_loop()
	except Exception as e:
		# raise
		if args and getattr(args, "debug", False):
			raise e
		print(f"{log.COLOR_CAT.ERROR}{e}{ANSI.RESET}", file=sys.stderr)
		return 1
	finally:
		if args and getattr(args, "profile", False):
			print_prof_table(get_prof_table())
	return 0


if __name__ == "__main__":
	sys.exit(main())
